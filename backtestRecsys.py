import argparse
import json
import os
import shutil
import tempfile
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import config
import mlService
from admissionService import AdmissionService
from csvDatabase import CsvDatabase
from mlService import RFTrendResidualRegressor, mlServiceInstance
from train import load_datasets

BASE = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE, "data")
REPORT_DIR = os.path.join(DATA_DIR, "reports")
BACKTEST_YEAR = 2026
TIER_ORDER = ["An toàn", "Vừa sức", "Thử sức", "Rủi ro cao"]

PT01_COMBOS = ["A00", "A01", "B00", "C00", "D01"]
PT01_TOTALS = list(range(15, 30))
PT02_COMBOS = ["A00", "D01"]
PT02_TOTALS = list(range(18, 30))


def _fit_backtest_model() -> Tuple[RFTrendResidualRegressor, float]:
    df_thpt = load_datasets(DATA_DIR)[0]
    eligible = df_thpt[df_thpt["ml_eligibility"] == "TRAIN_READY"]
    feats = ["score_lag_1", "score_lag_2", "score_diff_lag", "score_rolling_mean_2y"]
    train_df = eligible[eligible["split"] == "train"].dropna(subset=["score_lag_1", "benchmark_score"])
    val_df = eligible[eligible["split"] == "validation"].dropna(subset=["score_lag_1", "benchmark_score"])
    model = RFTrendResidualRegressor(n_estimators=250, max_depth=6, min_samples_leaf=20, blend_weight=0.15)
    model.fit(train_df[feats], train_df["benchmark_score"])
    resid = np.abs(val_df["benchmark_score"] - model.predict(val_df[feats]))
    return model, round(float(np.quantile(resid, 0.80)), 2)


def _build_forecasts(model: RFTrendResidualRegressor, radius: float, mode: str) -> pd.DataFrame:
    src = pd.read_csv(os.path.join(DATA_DIR, "processed", "forecast_records_2026.csv"))
    thpt = src[src["method_code"] == "THPT"].copy()
    lag1 = pd.to_numeric(thpt["historical_cutoff_2025"], errors="coerce")
    lag2 = pd.to_numeric(thpt["historical_cutoff_2024"], errors="coerce")
    thpt = thpt[lag1.notna()].copy()
    lag1, lag2 = lag1[thpt.index], lag2[thpt.index]

    has_both = lag2.notna()
    pred = lag1.copy()
    if mode == "hybrid" and has_both.any():
        X = pd.DataFrame({
            "score_lag_1": lag1[has_both],
            "score_lag_2": lag2[has_both],
            "score_diff_lag": lag1[has_both] - lag2[has_both],
            "score_rolling_mean_2y": (lag1[has_both] + lag2[has_both]) / 2.0,
        })
        pred[has_both] = model.predict(X)

    use_model = has_both if mode == "hybrid" else pd.Series(False, index=thpt.index)
    thpt["predicted_cutoff"] = pred.round(2)
    thpt["forecast_status"] = np.where(use_model, "PREDICTED_TIME_SERIES", "FALLBACK_LAG1_ONLY")
    thpt["model_version"] = np.where(use_model, "RF_THPT_BACKTEST_2026", "BASELINE_LAG1_2026")
    thpt["uncertainty_radius_80"] = radius
    thpt["lower_bound_80"] = (thpt["predicted_cutoff"] - radius).round(2)
    thpt["upper_bound_80"] = (thpt["predicted_cutoff"] + radius).round(2)
    thpt["target_year"] = BACKTEST_YEAR
    thpt["historical_cutoff_2026"] = lag1
    return thpt.drop(columns=["actual_cutoff_2026"])


def _profiles() -> List[Dict[str, Any]]:
    profiles = []
    for combo in PT01_COMBOS:
        for total in PT01_TOTALS:
            profiles.append({"method": "PT01", "combo": combo, "total": total})
    for combo in PT02_COMBOS:
        for total in PT02_TOTALS:
            profiles.append({"method": "PT02", "combo": combo, "total": total})
    return profiles


def _profile_payload(p: Dict[str, Any]) -> Dict[str, Any]:
    each = round(p["total"] / 3.0, 2)
    combo_fields = {c["maToHop"]: (c["mon1"], c["mon2"], c["mon3"]) for c in CsvDatabase.readAll("toHopMon")}
    payload = {f: each for f in combo_fields[p["combo"]]}
    payload.update({
        "phuongThucMongMuon": [p["method"]],
        "danhSachToHopDaChon": [p["combo"]],
        "khuVucUuTien": "KV3",
        "doiTuongUuTien": "NONE",
    })
    if p["method"] == "PT02":
        payload["diemHocBa"] = each
    return payload


def _truth_index(benchmarks: List[Dict[str, Any]]) -> Tuple[Dict, Dict]:
    exact, loose = {}, defaultdict(list)
    for b in benchmarks:
        if int(b.get("nam", 0)) != BACKTEST_YEAR or b.get("diemChuan") in (None, ""):
            continue
        key = (b["truongDaiHocId"], str(b.get("programId") or ""), b["toHopMonId"], b["phuongThucXetTuyenId"])
        exact[key + (str(b.get("admissionCaseId") or ""),)] = b
        loose[key].append(b)
    return exact, loose


def _actual_cutoff(item: Dict[str, Any], exact: Dict, loose: Dict) -> Optional[float]:
    key = (item["truongDaiHocId"], str(item.get("programId") or ""), item["toHopMonId"], item["phuongThucXetTuyenId"])
    rec = exact.get(key + (str(item.get("admissionCaseId") or ""),))
    if rec is None:
        candidates = [b for b in loose.get(key, []) if b.get("scoreScale") == item.get("scoreScale")]
        if len(candidates) != 1:
            return None
        rec = candidates[0]
    if rec.get("scoreScale") != item.get("scoreScale"):
        return None
    return float(rec["diemChuan"])


def _run_variant(variant: str, profiles: List[Dict[str, Any]], exact: Dict, loose: Dict) -> List[Dict[str, Any]]:
    rows = []
    for idx, p in enumerate(profiles):
        res = AdmissionService.deXuatNguyenVong(_profile_payload(p))
        for item in res.get("danhSachTongHop", []):
            actual = _actual_cutoff(item, exact, loose)
            rows.append({
                "bienThe": variant,
                "hoSo": idx,
                "phuongThuc": p["method"],
                "toHop": p["combo"],
                "tongDiem": p["total"],
                "maTruong": item["maTruong"],
                "programId": item["programId"],
                "nhomNguyenVong": item["nhomNguyenVong"],
                "namThamChieu": int(item["namThamChieu"]),
                "coDuBao": item["coDuBao"],
                "diemXetTuyen": item["diemXetTuyen"],
                "diemSoSanh": item["diemChuanDuBao"] if item["coDuBao"] else item["diemChuanThamChieu"],
                "diemChuanThat2026": actual,
                "chiSoThuanLoi": item["chiSoThuanLoi"],
                "do": None if actual is None else bool(item["diemXetTuyen"] >= actual),
            })
    return rows


def _summarize(df: pd.DataFrame) -> Dict[str, Any]:
    ref_years = {str(k): int(v) for k, v in df["namThamChieu"].value_counts().sort_index().items()}
    match_by_year = {str(k): round(float(g["do"].notna().mean()), 4) for k, g in df.groupby("namThamChieu")}
    known = df[df["do"].notna()].copy()
    if known.empty:
        return {
            "soNguyenVong": int(len(df)),
            "soCoDiemChuan2026": 0,
            "phanBoNamThamChieu": ref_years,
            "ghiChu": "Khong nguyen vong nao khop duoc diem chuan 2026 (ma chuong trinh nam 2025 va 2026 khong trung nhau), "
                      "nen khong danh gia duoc.",
        }
    known["do"] = known["do"].astype(bool)
    p = known["chiSoThuanLoi"] / 100.0
    by_tier = {}
    for tier in TIER_ORDER:
        t = known[known["nhomNguyenVong"] == tier]
        if t.empty:
            continue
        by_tier[tier] = {
            "soNguyenVong": int(len(t)),
            "tyLeDoThucTe": round(float(t["do"].mean()), 4),
            "chiSoThuanLoiTrungBinh": round(float(t["chiSoThuanLoi"].mean() / 100.0), 4),
        }

    bins = [0, 0.15, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    known["bin"] = pd.cut(p, bins=bins, include_lowest=True)
    calibration = [
        {"khoang": str(k), "soNguyenVong": int(len(g)),
         "duDoanTrungBinh": round(float(g["chiSoThuanLoi"].mean() / 100.0), 4),
         "tyLeDoThucTe": round(float(g["do"].mean()), 4)}
        for k, g in known.groupby("bin", observed=True)
    ]

    per_profile = known.groupby("hoSo").agg(
        soDo=("do", "sum"),
        coAnToanDo=("do", lambda s: bool(s[known.loc[s.index, "nhomNguyenVong"] == "An toàn"].any())),
    )
    with_forecast = known[known["coDuBao"]]
    return {
        "soNguyenVong": int(len(df)),
        "soCoDiemChuan2026": int(len(known)),
        "tyLeKhopDiemChuan2026": round(len(known) / len(df), 4) if len(df) else None,
        "phanBoNamThamChieu": ref_years,
        "tyLeKhopTheoNamThamChieu": match_by_year,
        "brierScore": round(float(np.mean((p - known["do"]) ** 2)), 4),
        "theoNhom": by_tier,
        "hieuChinhChiSoThuanLoi": calibration,
        "tyLeHoSoCoItNhat1NVDo": round(float((per_profile["soDo"] > 0).mean()), 4),
        "tyLeHoSoCoNVAnToanDo": round(float(per_profile["coAnToanDo"].mean()), 4),
        "soNVDoTrungBinhMoiHoSo": round(float(per_profile["soDo"].mean()), 2),
        "maeDiemSoSanhVsThat": round(float(np.mean(np.abs(known["diemSoSanh"] - known["diemChuanThat2026"]))), 4),
        "maeDiemSoSanhVsThatCoDuBao": (
            round(float(np.mean(np.abs(with_forecast["diemSoSanh"] - with_forecast["diemChuanThat2026"]))), 4)
            if not with_forecast.empty else None
        ),
    }


def run(max_age: int = 0) -> Dict[str, Any]:
    original_csv_dir = CsvDatabase.CSV_DIR
    original_years = (config.TARGET_YEAR, config.REFERENCE_YEAR)
    original_max_age = config.MAX_REFERENCE_AGE
    original_forecast_path = mlService.FORECAST_RECORDS_PATH

    all_benchmarks = CsvDatabase.readAll("diemChuan")
    exact, loose = _truth_index(all_benchmarks)

    model, radius = _fit_backtest_model()
    tmp = tempfile.mkdtemp(prefix="dss_backtest_")
    csv_dir = os.path.join(tmp, "csv")
    os.makedirs(csv_dir)
    for f in os.listdir(original_csv_dir):
        src = os.path.join(original_csv_dir, f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(csv_dir, f))
    dc = pd.read_csv(os.path.join(original_csv_dir, "diemChuan.csv"), dtype=str, keep_default_na=False)
    dc[pd.to_numeric(dc["nam"], errors="coerce") < BACKTEST_YEAR].to_csv(
        os.path.join(csv_dir, "diemChuan.csv"), index=False, encoding="utf-8-sig")

    rows: List[Dict[str, Any]] = []
    try:
        CsvDatabase.setDatabaseDirectory(csv_dir)
        config.TARGET_YEAR, config.REFERENCE_YEAR = BACKTEST_YEAR, BACKTEST_YEAR - 1
        config.MAX_REFERENCE_AGE = max_age
        profiles = _profiles()
        for variant in ("hybrid", "lag1"):
            fc_path = os.path.join(tmp, f"forecast_{variant}.csv")
            _build_forecasts(model, radius, variant).to_csv(fc_path, index=False, encoding="utf-8-sig")
            mlService.FORECAST_RECORDS_PATH = fc_path
            mlServiceInstance._load_forecast_data()
            variant_profiles = profiles if variant == "hybrid" else [p for p in profiles if p["method"] == "PT01"]
            rows.extend(_run_variant(variant, variant_profiles, exact, loose))
    finally:
        CsvDatabase.setDatabaseDirectory(original_csv_dir)
        config.TARGET_YEAR, config.REFERENCE_YEAR = original_years
        config.MAX_REFERENCE_AGE = original_max_age
        mlService.FORECAST_RECORDS_PATH = original_forecast_path
        mlServiceInstance._load_forecast_data()
        shutil.rmtree(tmp, ignore_errors=True)

    df = pd.DataFrame(rows)
    os.makedirs(REPORT_DIR, exist_ok=True)
    df.to_csv(os.path.join(REPORT_DIR, "recsys_backtest_2026_items.csv"), index=False, encoding="utf-8-sig")

    report = {
        "moTa": "Goi y cho nam 2026 chi dung du lieu den 2025, doi chieu voi diem chuan 2026 that.",
        "phamVi": "Chi danh gia duoc cac nguyen vong co diem chuan 2026 that cung chuong trinh, to hop, phuong thuc, thang diem. "
                  "Ty le do va Brier tinh tren tap do.",
        "banKinh80HieuChinh2025": radius,
        "tuoiMocToiDa": max_age,
        "hoSoGiaLap": {
            "PT01": {"toHop": PT01_COMBOS, "tongDiem": [PT01_TOTALS[0], PT01_TOTALS[-1]]},
            "PT02": {"toHop": PT02_COMBOS, "tongDiem": [PT02_TOTALS[0], PT02_TOTALS[-1]]},
            "ghiChu": "Cac mon bang nhau, KV3, khong uu tien, khong loc khu vuc/nganh/hoc phi.",
        },
        "nguongNhom": {"An toàn": config.TIER_SAFE_THRESHOLD / 100, "Vừa sức": config.TIER_SUITABLE_THRESHOLD / 100,
                       "Thử sức": config.TIER_CHALLENGE_THRESHOLD / 100},
        "ketQua": {
            "PT01_duBaoLai": _summarize(df[(df["bienThe"] == "hybrid") & (df["phuongThuc"] == "PT01")]),
            "PT01_duBaoLag1": _summarize(df[(df["bienThe"] == "lag1") & (df["phuongThuc"] == "PT01")]),
            "PT02_traCuuDiemChuan2025": _summarize(df[(df["bienThe"] == "hybrid") & (df["phuongThuc"] == "PT02")]),
        },
    }
    with open(os.path.join(REPORT_DIR, "recsys_backtest_2026.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest he goi y cho nam 2026")
    parser.add_argument("--max-age", type=int, default=0, help="Tuoi toi da cua diem chuan lam moc (-1: khong gioi han)")
    result = run(parser.parse_args().max_age)
    for name, s in result["ketQua"].items():
        if not s["soCoDiemChuan2026"]:
            print(f"\n== {name}: {s['soNguyenVong']} NV - {s['ghiChu']}")
            continue
        print(f"\n== {name}: {s['soNguyenVong']} NV, khop diem 2026: {s['tyLeKhopDiemChuan2026']}, Brier {s['brierScore']}")
        print(f"  Nam tham chieu: {s['phanBoNamThamChieu']}; ty le khop theo nam: {s['tyLeKhopTheoNamThamChieu']}")
        for tier, t in s["theoNhom"].items():
            print(f"  {tier:10s} n={t['soNguyenVong']:4d}  do thuc te {t['tyLeDoThucTe']:.1%}  "
                  f"chi so TB {t['chiSoThuanLoiTrungBinh']:.1%}")
        print(f"  Ho so co ≥1 NV do: {s['tyLeHoSoCoItNhat1NVDo']:.1%}; co NV An toan do: {s['tyLeHoSoCoNVAnToanDo']:.1%}; "
              f"MAE diem so sanh: {s['maeDiemSoSanhVsThat']}")
    print("\nBao cao: data/reports/recsys_backtest_2026.json")
