import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import RandomForestRegressor

RF_THPT_PATH = os.path.join(os.path.dirname(__file__), "data", "models", "rf_thpt_best.joblib")
RF_HOC_BA_PATH = os.path.join(os.path.dirname(__file__), "data", "models", "rf_hoc_ba_metadata.joblib")
FORECAST_RECORDS_PATH = os.path.join(os.path.dirname(__file__), "data", "processed", "forecast_records_2026.csv")


class RFTrendResidualRegressor(BaseEstimator, RegressorMixin):
    def __init__(self, n_estimators=250, max_depth=6, min_samples_leaf=20, blend_weight=0.15, random_state=42):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.blend_weight = blend_weight
        self.random_state = random_state
        self.rf = None

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
        rev = -0.18 * trend
        comb_delta = self.blend_weight * delta_rf + (1.0 - self.blend_weight) * rev
        return (lag1 + comb_delta).to_numpy()


class MlService:

    def __init__(self):
        self.modelThpt = None
        self.modelHocBa = None
        self.forecastDf = None
        self._loadModels()
        self._loadForecastData()

    def _loadModels(self):
        if os.path.exists(RF_THPT_PATH):
            try:
                self.modelThpt = joblib.load(RF_THPT_PATH)
            except Exception as e:
                print(f"[MlService] Không thể nạp mô hình THPT: {e}")
                self.modelThpt = None
        else:
            self.modelThpt = None

        if os.path.exists(RF_HOC_BA_PATH):
            try:
                self.modelHocBa = joblib.load(RF_HOC_BA_PATH)
            except Exception as e:
                print(f"[MlService] Không thể nạp mô hình Học bạ: {e}")
                self.modelHocBa = None
        else:
            self.modelHocBa = None

    def _loadForecastData(self):
        self._forecastByProgram = {}
        if os.path.exists(FORECAST_RECORDS_PATH):
            try:
                self.forecastDf = pd.read_csv(FORECAST_RECORDS_PATH)
                for _, row in self.forecastDf.iterrows():
                    progId = str(row.get("program_id", "")).strip()
                    if not progId:
                        continue
                    combRaw = str(row.get("subject_combination", "")) if pd.notna(row.get("subject_combination")) else ""
                    tokens = {t.strip().upper() for t in combRaw.replace(",", ";").split(";") if t.strip()}
                    item = {
                        "university_code": str(row.get("university_code", "")).strip().upper(),
                        "method_code": str(row.get("method_code", "")).strip().upper(),
                        "program_id": progId,
                        "admission_case_id": str(row.get("admission_case_id", "")).strip(),
                        "combination_tokens": tokens,
                        "predicted_cutoff": row.get("predicted_cutoff"),
                        "uncertainty_radius_80": row.get("uncertainty_radius_80", 0.5),
                        "lower_bound_80": row.get("lower_bound_80"),
                        "upper_bound_80": row.get("upper_bound_80"),
                        "historical_cutoff_2025": row.get("historical_cutoff_2025"),
                        "target_year": row.get("target_year", 2026),
                        "model_version": row.get("model_version", "RF_THPT_TIME_SERIES_V3"),
                        "forecast_status": str(row.get("forecast_status", "")).strip().upper()
                    }
                    self._forecastByProgram.setdefault(progId, []).append(item)
            except Exception as e:
                print(f"[MlService] Không thể nạp forecast_records_2026.csv: {e}")
                self.forecastDf = None
                self._forecastByProgram = {}
        else:
            self.forecastDf = None
            self._forecastByProgram = {}

    def isModelReady(self, methodCode: str) -> bool:
        isThpt = "THPT" in methodCode.upper() or methodCode.upper() in ["PT01", "1"]
        if isThpt:
            return self.modelThpt is not None
        return self.modelHocBa is not None

    def getModelStatus(self, methodCode: str) -> Dict[str, Any]:
        isThpt = "THPT" in methodCode.upper() or methodCode.upper() in ["PT01", "1"]
        if isThpt:
            if self.modelThpt is not None:
                return {
                    "sanSang": True,
                    "phuongPhap": "Random Forest THPT (chuỗi thời gian 2-lag)",
                    "cheDo": "Dự báo kết hợp tra cứu lịch sử",
                    "thongBao": "Mô hình Random Forest THPT đang hoạt động."
                }
            return {
                "sanSang": False,
                "phuongPhap": "Chưa có mô hình",
                "cheDo": "Tra cứu điểm chuẩn lịch sử",
                "thongBao": "Mô hình của phương thức THPT chưa sẵn sàng. Vui lòng chạy train.py để huấn luyện."
            }
        else:
            return {
                "sanSang": False,
                "phuongPhap": "Tra cứu điểm chuẩn chính thức",
                "cheDo": "Tra cứu điểm chuẩn chính thức",
                "thongBao": "Phương thức học bạ sử dụng điểm chuẩn chính thức do không có chuỗi thời gian liên tục."
            }

    def predictCutoff(self, methodCode: str, featureRow: Dict[str, Any]) -> Optional[float]:
        try:
            isThpt = "THPT" in methodCode.upper() or methodCode.upper() in ["PT01", "1"]
            model = self.modelThpt if isThpt else self.modelHocBa
            if model is None:
                return None

            dfInput = pd.DataFrame([featureRow])
            pred = float(model.predict(dfInput)[0])
            return round(pred, 2)
        except Exception:
            return None

    def getForecastInfo(
        self,
        universityCode: str,
        programId: str = "",
        admissionCaseId: str = "",
        methodCode: str = "PT01",
        combinationCode: str = "A00"
    ) -> Optional[Dict[str, Any]]:
        if not getattr(self, "_forecastByProgram", None) or not programId:
            return None

        candidates = self._forecastByProgram.get(programId)
        if not candidates:
            return None

        isThpt = "THPT" in methodCode.upper() or methodCode.upper() in ["PT01", "1"]
        mCode = "THPT" if isThpt else "HOC_BA"
        uCode = universityCode.strip().upper()
        targetComb = combinationCode.strip().upper() if combinationCode else ""

        matched = []
        for c in candidates:
            if c["university_code"] != uCode:
                continue
            if c["method_code"] != mCode:
                continue
            if admissionCaseId and admissionCaseId != "CHUA_RO" and c["admission_case_id"] != admissionCaseId:
                continue
            if targetComb and targetComb not in c["combination_tokens"]:
                continue
            matched.append(c)

        if not matched:
            return None

        row = matched[0]
        predScore = row.get("predicted_cutoff")
        if pd.isna(predScore) or float(predScore) <= 0:
            return None

        radius = row.get("uncertainty_radius_80", 0.5)
        lowBound = row.get("lower_bound_80")
        upBound = row.get("upper_bound_80")
        hist2025 = row.get("historical_cutoff_2025")
        targetYear = row.get("target_year", 2026)
        modelVersion = row.get("model_version", "RF_THPT_TIME_SERIES_V3")

        fcStatus = row.get("forecast_status", "")
        mVer = str(modelVersion).strip().upper()

        if fcStatus == "PREDICTED_TIME_SERIES" or "RF" in mVer:
            forecastType = "RANDOM_FOREST"
            forecastTypeLabel = "Dự báo Random Forest"
        elif fcStatus == "FALLBACK_LAG1_ONLY" or "LAG1" in mVer:
            forecastType = "BASELINE_LAG1"
            forecastTypeLabel = "Ước lượng theo điểm năm trước"
        else:
            forecastType = "HISTORICAL_ONLY"
            forecastTypeLabel = "Điểm chuẩn chính thức"

        return {
            "predictedCutoff": round(float(predScore), 2),
            "uncertaintyRadius": round(float(radius), 2) if pd.notna(radius) else 0.5,
            "lowerBound80": round(float(lowBound), 2) if pd.notna(lowBound) else None,
            "upperBound80": round(float(upBound), 2) if pd.notna(upBound) else None,
            "historicalCutoff2025": round(float(hist2025), 2) if pd.notna(hist2025) else None,
            "targetYear": int(targetYear) if pd.notna(targetYear) else 2026,
            "modelVersion": str(modelVersion) if pd.notna(modelVersion) else "RF_THPT_TIME_SERIES_V3",
            "forecastType": forecastType,
            "forecastTypeLabel": forecastTypeLabel,
            "displayLabel": forecastTypeLabel
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
        import math

        delta = round(studentScore - benchmarkScore, 2)

        if coDuBao and uncertaintyRadius is not None and float(uncertaintyRadius) > 0:
            sigma_base = max(1.80, float(uncertaintyRadius) / 1.28155)
        else:
            lag = max(1, 2027 - int(namThamChieu if namThamChieu else 2026))
            if lag == 1:
                sigma_base = 1.83
            elif lag == 2:
                sigma_base = 2.54
            else:
                sigma_base = 3.00

        if scoreScale in ["GPA_10", "THANG_10"]:
            sigma = sigma_base * (10.0 / 30.0)
        elif scoreScale in ["SCALE_40", "THANG_40"]:
            sigma = sigma_base * (40.0 / 30.0)
        else:
            sigma = sigma_base

        sigma = max(0.2, sigma)
        z = delta / sigma

        chiSoThuanLoi = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0))) * 100.0
        chiSoThuanLoi = max(5.0, min(99.0, round(float(chiSoThuanLoi), 1)))

        if chiSoThuanLoi >= 80.0:
            nhomNguyenVong = "An toàn"
            mucDoPhuHop = "Rất phù hợp"
            mucDoRuiRo = "Thấp"
        elif chiSoThuanLoi >= 40.0:
            nhomNguyenVong = "Vừa sức"
            mucDoPhuHop = "Phù hợp"
            mucDoRuiRo = "Trung bình"
        elif chiSoThuanLoi >= 15.0:
            nhomNguyenVong = "Thử sức"
            mucDoPhuHop = "Cân nhắc"
            mucDoRuiRo = "Trung bình"
        else:
            nhomNguyenVong = "Rủi ro cao"
            mucDoPhuHop = "Thử sức"
            mucDoRuiRo = "Cao"

        return {
            "doPhuHop": chiSoThuanLoi,
            "chiSoThuanLoiDiem": chiSoThuanLoi,
            "xacSuatDo": chiSoThuanLoi,
            "sigma": round(sigma, 3),
            "zScore": round(z, 2),
            "nhomNguyenVong": nhomNguyenVong,
            "mucDoPhuHop": mucDoPhuHop,
            "mucDoRuiRo": mucDoRuiRo,
            "delta": delta
        }


mlServiceInstance = MlService()
