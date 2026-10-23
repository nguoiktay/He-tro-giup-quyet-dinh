import os
import json
import math
import joblib
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import RandomForestRegressor

import config

RF_THPT_PATH = os.path.join(os.path.dirname(__file__), "data", "models", "rf_thpt_best.joblib")
RF_HOC_BA_PATH = os.path.join(os.path.dirname(__file__), "data", "models", "rf_hoc_ba_metadata.joblib")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RF_THPT_METADATA_PATH = os.path.join(DATA_DIR, "models", "rf_thpt_metadata.json")
CALIBRATOR_PATH = os.path.join(DATA_DIR, "models", "conformal_calibrator_thpt.json")
BENCHMARK_REPORT_PATH = os.path.join(DATA_DIR, "reports", "model_comparison_benchmark.csv")
FEATURE_IMPORTANCE_PATH = os.path.join(DATA_DIR, "reports", "feature_importance_thpt.csv")
HYBRID_MODEL_LABEL = "Dự báo lai (công thức xu hướng + RF)"
FORECAST_RECORDS_PATH = os.path.join(os.path.dirname(__file__), "data", "processed", f"forecast_records_{config.TARGET_YEAR}.csv")
if not os.path.exists(FORECAST_RECORDS_PATH):
    FORECAST_RECORDS_PATH = os.path.join(os.path.dirname(__file__), "data", "processed", "forecast_records_2026.csv")


class RFTrendResidualRegressor(BaseEstimator, RegressorMixin):

    def __init__(self, n_estimators=250, max_depth=6, min_samples_leaf=20, blend_weight=0.15,
                 reversion_coef=-0.18, random_state=42):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.blend_weight = blend_weight
        self.reversion_coef = reversion_coef
        self.random_state = random_state
        self.rf = None

    def __setstate__(self, state):
        state.setdefault("reversion_coef", -0.18)
        super().__setstate__(state)

    def fit(self, X, y):
        df_x = pd.DataFrame(X).copy()
        lag1 = df_x["score_lag_1"].fillna(df_x["score_lag_1"].median())
        delta = y - lag1
        trend = lag1 - df_x["score_lag_2"].fillna(lag1)

        feats = pd.DataFrame({
            "score_lag_1": lag1,
            "score_lag_2": df_x["score_lag_2"].fillna(lag1),
            "trend": trend,
            "score_diff_lag": df_x.get("score_diff_lag", pd.Series(0, index=df_x.index)).fillna(0),
            "rolling": df_x.get("score_rolling_mean_2y", lag1).fillna(lag1)
        })

        self.rf = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_leaf=self.min_samples_leaf,
            random_state=self.random_state,
            n_jobs=-1
        )
        self.rf.fit(feats, delta)
        return self

    def predict(self, X):
        df_x = pd.DataFrame(X).copy()
        median_lag = df_x["score_lag_1"].median() if not df_x.empty and df_x["score_lag_1"].notna().any() else 24.0
        lag1 = df_x["score_lag_1"].fillna(median_lag)
        trend = lag1 - df_x["score_lag_2"].fillna(lag1)

        feats = pd.DataFrame({
            "score_lag_1": lag1,
            "score_lag_2": df_x["score_lag_2"].fillna(lag1),
            "trend": trend,
            "score_diff_lag": df_x.get("score_diff_lag", pd.Series(0, index=df_x.index)).fillna(0),
            "rolling": df_x.get("score_rolling_mean_2y", lag1).fillna(lag1)
        })

        delta_rf = self.rf.predict(feats)
        return self.combine(lag1.to_numpy(), delta_rf, trend.to_numpy(), self.blend_weight, self.reversion_coef)

    def predict_components(self, X) -> Dict[str, np.ndarray]:
        df_x = pd.DataFrame(X).copy()
        median_lag = df_x["score_lag_1"].median() if not df_x.empty and df_x["score_lag_1"].notna().any() else 24.0
        lag1 = df_x["score_lag_1"].fillna(median_lag)
        trend = lag1 - df_x["score_lag_2"].fillna(lag1)
        feats = pd.DataFrame({
            "score_lag_1": lag1,
            "score_lag_2": df_x["score_lag_2"].fillna(lag1),
            "trend": trend,
            "score_diff_lag": df_x.get("score_diff_lag", pd.Series(0, index=df_x.index)).fillna(0),
            "rolling": df_x.get("score_rolling_mean_2y", lag1).fillna(lag1)
        })
        return {"lag1": lag1.to_numpy(), "delta_rf": self.rf.predict(feats), "trend": trend.to_numpy()}

    @staticmethod
    def combine(lag1, delta_rf, trend, blend_weight: float, reversion_coef: float):
        rev = reversion_coef * trend
        return lag1 + blend_weight * delta_rf + (1.0 - blend_weight) * rev


class MlService:
    def __init__(self):
        self.model_thpt = None
        self.model_hoc_ba = None
        self.model_thpt_verified = False
        self.forecast_df = None
        self._forecast_by_program: Dict[str, List[Dict[str, Any]]] = {}
        self._load_models()
        self._load_forecast_data()

    def _load_models(self) -> None:
        self.model_thpt_verified = False
        if os.path.exists(RF_THPT_PATH):
            try:
                self.model_thpt = joblib.load(RF_THPT_PATH)
                test_x = pd.DataFrame([{
                    "score_lag_1": 25.0,
                    "score_lag_2": 24.5,
                    "score_diff_lag": 0.5,
                    "score_rolling_mean_2y": 24.75
                }])
                self.model_thpt.predict(test_x)
                self.model_thpt_verified = True
            except Exception:
                self.model_thpt = None
                self.model_thpt_verified = False
        else:
            self.model_thpt = None

        if os.path.exists(RF_HOC_BA_PATH):
            try:
                self.model_hoc_ba = joblib.load(RF_HOC_BA_PATH)
            except Exception:
                self.model_hoc_ba = None
        else:
            self.model_hoc_ba = None

    def _load_forecast_data(self) -> None:
        self._forecast_by_program = {}
        if os.path.exists(FORECAST_RECORDS_PATH):
            try:
                self.forecast_df = pd.read_csv(FORECAST_RECORDS_PATH)
                for _, row in self.forecast_df.iterrows():
                    prog_id = str(row.get("program_id", "")).strip()
                    if not prog_id:
                        continue
                    comb_raw = str(row.get("subject_combination", "")) if pd.notna(row.get("subject_combination")) else ""
                    tokens = {t.strip().upper() for t in comb_raw.replace(",", ";").split(";") if t.strip()}
                    item = {
                        "university_code": str(row.get("university_code", "")).strip().upper(),
                        "method_code": str(row.get("method_code", "")).strip().upper(),
                        "program_id": prog_id,
                        "admission_case_id": str(row.get("admission_case_id", "")).strip(),
                        "combination_tokens": tokens,
                        "predicted_cutoff": row.get("predicted_cutoff"),
                        "uncertainty_radius_80": row.get("uncertainty_radius_80", 0.5),
                        "lower_bound_80": row.get("lower_bound_80"),
                        "upper_bound_80": row.get("upper_bound_80"),
                        "historical_cutoff_2026": row.get("historical_cutoff_2026"),
                        "historical_cutoff_2025": row.get("historical_cutoff_2025"),
                        "target_year": int(row.get("target_year", config.TARGET_YEAR)),
                        "model_version": row.get("model_version", "RF_THPT_TIME_SERIES_V4_2027"),
                        "forecast_status": str(row.get("forecast_status", "")).strip().upper()
                    }
                    self._forecast_by_program.setdefault(prog_id, []).append(item)
            except Exception:
                self.forecast_df = None
                self._forecast_by_program = {}
        else:
            self.forecast_df = None
            self._forecast_by_program = {}

    def getModelStatus(self, methodCode: str) -> Dict[str, Any]:
        is_thpt = "THPT" in methodCode.upper() or methodCode.upper() in ["PT01", "1"]
        if is_thpt:
            if self.model_thpt is not None:
                return {
                    "sanSang": True,
                    "phuongPhap": "Du bao lai (cong thuc xu huong + RF)",
                    "cheDo": "Du bao ket hop tra cuu lich su",
                    "thongBao": "Mo hinh du bao lai THPT dang hoat dong."
                }
            return {
                "sanSang": False,
                "phuongPhap": "Chua co mo hinh",
                "cheDo": "Tra cuu diem chuan lich su",
                "thongBao": "Mo hinh cua phuong thuc THPT chua san sang. Vui long chay train.py de huan luyen."
            }
        else:
            return {
                "sanSang": False,
                "phuongPhap": "Tra cuu diem chuan chinh thuc",
                "cheDo": "Tra cuu diem chuan chinh thuc",
                "thongBao": "Phuong thuc hoc ba su dung diem chuan chinh thuc do khong co chuoi thoi gian lien tuc."
            }

    def getModelInfo(self) -> Dict[str, Any]:

        def _read_json(path: str) -> Dict[str, Any]:
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, ValueError):
                return {}

        def _read_csv(path: str) -> Optional[pd.DataFrame]:
            try:
                return pd.read_csv(path, encoding="utf-8-sig")
            except (OSError, ValueError):
                return None

        meta = _read_json(RF_THPT_METADATA_PATH)
        cal = _read_json(CALIBRATOR_PATH)
        ci80 = cal.get("intervals", {}).get("confidence_80", {})

        so_sanh = []
        chi_so_mo_hinh: Dict[str, Optional[float]] = {"r2": None, "mae": None, "rmse": None}
        df_bench = _read_csv(BENCHMARK_REPORT_PATH)
        if df_bench is not None and "Model / Method" in df_bench.columns:
            for _, r in df_bench.iterrows():
                row = {
                    "phuongPhap": str(r["Model / Method"]).strip(),
                    "loai": str(r.get("Type", "")).strip(),
                    "mae": float(r["Test MAE"]) if pd.notna(r.get("Test MAE")) else None,
                    "rmse": float(r["Test RMSE"]) if pd.notna(r.get("Test RMSE")) else None,
                    "r2": float(r["Test R2"]) if pd.notna(r.get("Test R2")) else None,
                }
                so_sanh.append(row)
                if row["phuongPhap"] == HYBRID_MODEL_LABEL:
                    chi_so_mo_hinh = {"r2": row["r2"], "mae": row["mae"], "rmse": row["rmse"]}

        feature_importance = []
        df_feat = _read_csv(FEATURE_IMPORTANCE_PATH)
        if df_feat is not None and {"feature", "importance_mean"} <= set(df_feat.columns):
            feature_importance = [
                {"dacTrung": str(r["feature"]), "doQuanTrong": round(float(r["importance_mean"]), 4)}
                for _, r in df_feat.iterrows()
            ]

        tong = int(meta.get("total_records") or 0)
        so_rf = int(meta.get("thpt_ml_predictions") or 0)
        so_lag1 = int(meta.get("thpt_lag1_fallbacks") or 0)
        so_tra_cuu = int(meta.get("hoc_ba_lookups") or 0)
        so_truong_rf = None
        if self.forecast_df is not None and "forecast_status" in self.forecast_df.columns:
            rf_rows = self.forecast_df[self.forecast_df["forecast_status"] == "PREDICTED_TIME_SERIES"]
            so_truong_rf = int(rf_rows["university_code"].nunique())

        return {
            "thanhCong": True,
            "phienBan": meta.get("model_name", "RFTrendResidualRegressor"),
            "tenPhuongPhap": HYBRID_MODEL_LABEL,
            "scikitLearn": meta.get("scikit_learn_version"),
            "trangThai": "Hoat dong" if self.model_thpt_verified else "Chua nap duoc mo hinh",
            "namDuBao": meta.get("target_year", config.TARGET_YEAR),
            "namThamChieu": config.REFERENCE_YEAR,
            "dacTrungDauVao": meta.get("input_features", []),
            "soMauHuanLuyen": cal.get("train_size"),
            "tapHieuChinh": cal.get("calibration_set"),
            "tapKiemThu": cal.get("test_set"),
            "r2": chi_so_mo_hinh["r2"],
            "mae": chi_so_mo_hinh["mae"],
            "rmse": chi_so_mo_hinh["rmse"],
            "khoangTinCay": {
                "mucTinCayDanhNghia": ci80.get("nominal_coverage", 0.8),
                "banKinhDiem": ci80.get("radius_points", meta.get("calibrated_radius_80")),
                "doPhuThucTe": ci80.get("empirical_test_coverage"),
                "phuongPhap": cal.get("method"),
            },
            "doPhuChuongTrinh": {
                "tongBanGhi": tong,
                "duBaoMoHinh": so_rf,
                "uocLuongNamTruoc": so_lag1,
                "traCuuDiemChuan": so_tra_cuu,
                "tyLeDuBaoMoHinh": round(so_rf / tong, 4) if tong else None,
                "soTruongCoDuBao": so_truong_rf,
            },
            "featureImportance": feature_importance,
            "soSanhPhuongPhap": so_sanh,
            "ghiChu": (
                f"Chỉ {so_rf:,}/{tong:,} bản ghi điểm chuẩn ({so_truong_rf or '?'} trường) được dự báo bằng mô hình; "
                "các bản ghi còn lại dùng điểm năm trước hoặc tra cứu điểm chuẩn chính thức đã công bố. "
                f"Điểm dự báo có sai số ±{ci80.get('radius_points', '?')} điểm ở mức tin cậy danh nghĩa 80%."
            ),
        }

    def getForecastInfo(
        self,
        universityCode: str,
        programId: str = "",
        admissionCaseId: str = "",
        methodCode: str = "PT01",
        combinationCode: str = "A00"
    ) -> Optional[Dict[str, Any]]:
        if not getattr(self, "_forecast_by_program", None) or not programId:
            return None

        candidates = self._forecast_by_program.get(programId)
        if not candidates:
            return None

        is_thpt = "THPT" in methodCode.upper() or methodCode.upper() in ["PT01", "1"]
        m_code = "THPT" if is_thpt else "HOC_BA"
        u_code = universityCode.strip().upper()
        target_comb = combinationCode.strip().upper() if combinationCode else ""

        matched = []
        for c in candidates:
            if c["university_code"] != u_code:
                continue
            if c["method_code"] != m_code:
                continue
            if int(c.get("target_year", 0)) != config.TARGET_YEAR:
                continue

            req_case = str(admissionCaseId).strip().upper() if admissionCaseId else ""
            if req_case and req_case != "CHUA_RO":
                c_case = str(c.get("admission_case_id", "")).strip().upper()
                if c_case and c_case != "CHUA_RO":
                    case_matched = (c_case == req_case) or (req_case in c_case) or (c_case in req_case)
                    if not case_matched:
                        continue

            if target_comb and target_comb not in c["combination_tokens"]:
                continue
            matched.append(c)

        if not matched:
            return None

        row = matched[0]
        pred_score = row.get("predicted_cutoff")
        if pd.isna(pred_score) or float(pred_score) <= 0:
            return None

        radius = row.get("uncertainty_radius_80", 0.5)
        low_bound = row.get("lower_bound_80")
        up_bound = row.get("upper_bound_80")
        hist_2026 = row.get("historical_cutoff_2026")
        hist_2025 = row.get("historical_cutoff_2025")
        target_year = int(row.get("target_year", config.TARGET_YEAR))
        model_version = row.get("model_version", "RF_THPT_TIME_SERIES_V4_2027")

        fc_status = row.get("forecast_status", "")
        m_ver = str(model_version).strip().upper()

        if fc_status == "PREDICTED_TIME_SERIES" or "RF" in m_ver:
            forecast_type = "HYBRID_RF"
            forecast_type_label = "Dự báo lai (công thức xu hướng + RF)"
        elif fc_status == "FALLBACK_LAG1_ONLY" or "LAG1" in m_ver:
            forecast_type = "BASELINE_LAG1"
            forecast_type_label = "Ước lượng theo điểm năm trước"
        else:
            forecast_type = "HISTORICAL_ONLY"
            forecast_type_label = "Điểm chuẩn chính thức"

        return {
            "predictedCutoff": round(float(pred_score), 2),
            "uncertaintyRadius": round(float(radius), 2) if pd.notna(radius) else 0.5,
            "lowerBound80": round(float(low_bound), 2) if pd.notna(low_bound) else None,
            "upperBound80": round(float(up_bound), 2) if pd.notna(up_bound) else None,
            "historicalCutoff2026": round(float(hist_2026), 2) if pd.notna(hist_2026) else None,
            "historicalCutoff2025": round(float(hist_2025), 2) if pd.notna(hist_2025) else None,
            "targetYear": target_year,
            "admissionCaseId": row.get("admission_case_id", ""),
            "modelVersion": str(model_version) if pd.notna(model_version) else "RF_THPT_TIME_SERIES_V4_2027",
            "forecastType": forecast_type,
            "forecastTypeLabel": forecast_type_label,
            "displayLabel": forecast_type_label
        }

    def predictSuitability(
        self,
        studentScore: float,
        benchmarkScore: float,
        methodCode: str = "PT01",
        combinationCode: str = "A00",
        uniTier: int = 2,
        uncertaintyRadius: float = 0.5,
        scoreScale: str = "SCALE_30",
        namThamChieu: int = 2025,
        coDuBao: bool = False,
        forecastType: str = "HISTORICAL_ONLY"
    ) -> Dict[str, Any]:
        delta = round(studentScore - benchmarkScore, 2)

        if coDuBao and uncertaintyRadius is not None and float(uncertaintyRadius) > 0:
            sigma_base = float(uncertaintyRadius) / 1.28155
        else:
            ref_year = int(namThamChieu) if namThamChieu else config.REFERENCE_YEAR
            lag = max(1, config.TARGET_YEAR - ref_year)
            if lag == 1:
                sigma_base = 1.83
            elif lag == 2:
                sigma_base = 2.54
            else:
                sigma_base = 3.00

        if scoreScale in ("GPA_10", "THANG_10"):
            sigma = sigma_base * (10.0 / 30.0)
        elif scoreScale in ("SCALE_40", "THANG_40"):
            sigma = sigma_base * (40.0 / 30.0)
        else:
            sigma = sigma_base

        sigma = max(0.2, sigma)
        z = delta / sigma

        chi_so_thuan_loi = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0))) * 100.0
        chi_so_thuan_loi = max(5.0, min(99.0, round(float(chi_so_thuan_loi), 1)))

        if chi_so_thuan_loi >= config.TIER_SAFE_THRESHOLD:
            nhom_nguyen_vong = "An toàn"
            muc_do_phu_hop = "Rất phù hợp"
            muc_do_rui_ro = "Thấp"
        elif chi_so_thuan_loi >= config.TIER_SUITABLE_THRESHOLD:
            nhom_nguyen_vong = "Vừa sức"
            muc_do_phu_hop = "Phù hợp"
            muc_do_rui_ro = "Trung bình"
        elif chi_so_thuan_loi >= config.TIER_CHALLENGE_THRESHOLD:
            nhom_nguyen_vong = "Thử sức"
            muc_do_phu_hop = "Cân nhắc"
            muc_do_rui_ro = "Trung bình"
        else:
            nhom_nguyen_vong = "Rủi ro cao"
            muc_do_phu_hop = "Thử sức"
            muc_do_rui_ro = "Cao"

        return {
            "doPhuHop": chi_so_thuan_loi,
            "chiSoThuanLoi": chi_so_thuan_loi,
            "chiSoThuanLoiDiem": chi_so_thuan_loi,
            "xacSuatDo": chi_so_thuan_loi,
            "sigma": round(sigma, 3),
            "zScore": round(z, 2),
            "nhomNguyenVong": nhom_nguyen_vong,
            "mucDoPhuHop": muc_do_phu_hop,
            "mucDoRuiRo": muc_do_rui_ro,
            "delta": delta
        }


mlServiceInstance = MlService()
