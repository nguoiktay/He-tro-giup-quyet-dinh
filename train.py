import os
import sys
import json
import argparse
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import KFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from mlService import RFTrendResidualRegressor


def load_datasets(data_dir: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    thpt_path = os.path.join(data_dir, "training", "thpt_rf_dataset.csv")
    hb_path = os.path.join(data_dir, "training", "hoc_ba_rf_dataset.csv")
    up_path = os.path.join(data_dir, "metadata", "university_programs.csv")
    um_path = os.path.join(data_dir, "metadata", "universities_master.csv")

    if not os.path.exists(thpt_path):
        raise FileNotFoundError(f"Khong tim thay file: {thpt_path}")
    if not os.path.exists(hb_path):
        raise FileNotFoundError(f"Khong tim thay file: {hb_path}")

    df_thpt = pd.read_csv(thpt_path, low_memory=False)
    df_hb = pd.read_csv(hb_path, low_memory=False)
    df_up = pd.read_csv(up_path, low_memory=False) if os.path.exists(up_path) else pd.DataFrame()
    df_um = pd.read_csv(um_path, low_memory=False) if os.path.exists(um_path) else pd.DataFrame()

    return df_thpt, df_hb, df_up, df_um


BLEND_WEIGHT_GRID = [0.0, 0.15, 0.3, 0.5, 0.7, 1.0]
REVERSION_COEF_GRID = [0.0, -0.06, -0.12, -0.18, -0.24, -0.30]


def _metrics(y_true, y_pred) -> Dict[str, float]:
    return {
        "MAE": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "R2": round(float(r2_score(y_true, y_pred)), 4),
    }


def _bootstrap_mae_diff(y_true, pred_a, pred_b, n_boot: int = 2000, seed: int = 42) -> Dict[str, float]:
    err_a = np.abs(np.asarray(y_true) - np.asarray(pred_a))
    err_b = np.abs(np.asarray(y_true) - np.asarray(pred_b))
    diff = err_a - err_b
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(diff), size=(n_boot, len(diff)))
    boot = diff[idx].mean(axis=1)
    return {
        "mae_diff": round(float(diff.mean()), 4),
        "ci95_low": round(float(np.quantile(boot, 0.025)), 4),
        "ci95_high": round(float(np.quantile(boot, 0.975)), 4),
        "p_a_better": round(float(np.mean(boot < 0)), 4),
    }


def compare_hybrid_variants(
    model: RFTrendResidualRegressor,
    X_val: pd.DataFrame, y_val: pd.Series,
    X_test: pd.DataFrame, y_test: pd.Series,
    report_dir: str,
) -> Dict[str, Any]:
    comp_val = model.predict_components(X_val)
    comp_test = model.predict_components(X_test)
    combine = RFTrendResidualRegressor.combine

    grid_rows = []
    for bw in BLEND_WEIGHT_GRID:
        for rc in REVERSION_COEF_GRID:
            p_val = combine(comp_val["lag1"], comp_val["delta_rf"], comp_val["trend"], bw, rc)
            p_test = combine(comp_test["lag1"], comp_test["delta_rf"], comp_test["trend"], bw, rc)
            m_val, m_test = _metrics(y_val, p_val), _metrics(y_test, p_test)
            grid_rows.append({
                "blend_weight": bw, "reversion_coef": rc,
                "val_MAE": m_val["MAE"], "val_RMSE": m_val["RMSE"],
                "test_MAE": m_test["MAE"], "test_RMSE": m_test["RMSE"],
            })
    df_grid = pd.DataFrame(grid_rows).sort_values(["val_MAE", "val_RMSE"]).reset_index(drop=True)
    df_grid["val_rank"] = np.arange(1, len(df_grid) + 1)
    df_grid.to_csv(os.path.join(report_dir, "hybrid_param_search.csv"), index=False, encoding="utf-8-sig")
    best = df_grid.iloc[0]

    def _pred(comp, bw, rc):
        return combine(comp["lag1"], comp["delta_rf"], comp["trend"], bw, rc)

    variants = {
        "Lag-1 (diem nam truoc)": (comp_val["lag1"], comp_test["lag1"]),
        "Trung binh 2 nam": (X_val["score_rolling_mean_2y"].fillna(X_val["score_lag_1"]).to_numpy(),
                             X_test["score_rolling_mean_2y"].fillna(X_test["score_lag_1"]).to_numpy()),
        "RF thuan tren phan du (blend=1.0)": (_pred(comp_val, 1.0, 0.0), _pred(comp_test, 1.0, 0.0)),
        f"Cong thuc hoi quy thuan (blend=0, coef={model.reversion_coef})": (
            _pred(comp_val, 0.0, model.reversion_coef), _pred(comp_test, 0.0, model.reversion_coef)),
        f"Ban lai dang dung (blend={model.blend_weight}, coef={model.reversion_coef})": (
            _pred(comp_val, model.blend_weight, model.reversion_coef),
            _pred(comp_test, model.blend_weight, model.reversion_coef)),
        f"Ban lai tot nhat tren validation (blend={best.blend_weight}, coef={best.reversion_coef})": (
            _pred(comp_val, best.blend_weight, best.reversion_coef),
            _pred(comp_test, best.blend_weight, best.reversion_coef)),
    }
    lag1_test = comp_test["lag1"]
    var_rows = []
    for name, (p_val, p_test) in variants.items():
        m_val, m_test = _metrics(y_val, p_val), _metrics(y_test, p_test)
        boot = _bootstrap_mae_diff(y_test, p_test, lag1_test)
        var_rows.append({
            "Phuong phap": name,
            "Val MAE": m_val["MAE"], "Val RMSE": m_val["RMSE"], "Val R2": m_val["R2"],
            "Test MAE": m_test["MAE"], "Test RMSE": m_test["RMSE"], "Test R2": m_test["R2"],
            "Test MAE - Lag1": boot["mae_diff"],
            "CI95 thap": boot["ci95_low"], "CI95 cao": boot["ci95_high"],
            "P(tot hon Lag1)": boot["p_a_better"],
        })
    df_var = pd.DataFrame(var_rows)
    df_var.to_csv(os.path.join(report_dir, "model_variants_comparison.csv"), index=False, encoding="utf-8-sig")

    current = df_grid[(df_grid["blend_weight"] == model.blend_weight) & (df_grid["reversion_coef"] == model.reversion_coef)]
    current_rank = int(current["val_rank"].iloc[0]) if not current.empty else None
    print("\nSo sanh bien the mo hinh (validation 2025 / test 2026):")
    print(df_var[["Phuong phap", "Val MAE", "Test MAE", "Test MAE - Lag1", "CI95 thap", "CI95 cao"]].to_string(index=False))
    print(f"Tham so tot nhat tren validation: blend={best.blend_weight}, coef={best.reversion_coef} "
          f"(val MAE={best.val_MAE}); tham so dang dung xep hang {current_rank}/{len(df_grid)}")
    return {
        "best_blend_weight": float(best.blend_weight),
        "best_reversion_coef": float(best.reversion_coef),
        "current_val_rank": current_rank,
        "grid_size": len(df_grid),
    }


def train_thpt_branch(
    df_thpt: pd.DataFrame,
    df_up: pd.DataFrame,
    df_um: pd.DataFrame,
    save_path: Optional[str] = None,
    write_reports: bool = True
) -> Dict[str, Any]:
    print("\nHuan luyen mo hinh diem thi THPT: ")

    if not df_up.empty:
        up_sub = df_up[["program_id", "major_group_id", "program_type"]].drop_duplicates("program_id")
        df_thpt = df_thpt.merge(up_sub, on="program_id", how="left")
    if not df_um.empty:
        um_sub = df_um[["university_id", "university_type", "region"]].drop_duplicates("university_id")
        df_thpt = df_thpt.merge(um_sub, on="university_id", how="left")

    eligible = df_thpt[df_thpt["ml_eligibility"] == "TRAIN_READY"].copy()
    train_df = eligible[eligible["split"] == "train"].copy().dropna(subset=["score_lag_1", "benchmark_score"])
    val_df = eligible[eligible["split"] == "validation"].copy().dropna(subset=["score_lag_1", "benchmark_score"])
    test_df = eligible[eligible["split"] == "test"].copy().dropna(subset=["score_lag_1", "benchmark_score"])

    print(f"Tong so mau TRAIN_READY: {len(eligible):,}")
    print(f"  - Train (nam <= 2024):       {len(train_df):,} mau")
    print(f"  - Validation (nam 2025):     {len(val_df):,} mau")
    print(f"  - Test (nam 2026):           {len(test_df):,} mau")

    feature_cols = [
        "score_lag_1", "score_lag_2", "score_diff_lag", "score_rolling_mean_2y"
    ]
    target_col = "benchmark_score"

    X_train, y_train = train_df[feature_cols], train_df[target_col]
    X_val, y_val = val_df[feature_cols], val_df[target_col]
    X_test, y_test = test_df[feature_cols], test_df[target_col]

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = []
    for tr_idx, va_idx in kf.split(X_train):
        m_cv = RFTrendResidualRegressor(n_estimators=100, max_depth=6, min_samples_leaf=20)
        m_cv.fit(X_train.iloc[tr_idx], y_train.iloc[tr_idx])
        p_cv = m_cv.predict(X_train.iloc[va_idx])
        cv_scores.append(mean_absolute_error(y_train.iloc[va_idx], p_cv))
    print(f"Cross-Validation 5-Fold MAE tren Train: {np.mean(cv_scores):.4f} (+/-{np.std(cv_scores):.4f})")

    model = RFTrendResidualRegressor(n_estimators=250, max_depth=6, min_samples_leaf=20, blend_weight=0.15)
    model.fit(X_train, y_train)

    y_pred_val = model.predict(X_val)
    mae_val = mean_absolute_error(y_val, y_pred_val)
    rmse_val = np.sqrt(mean_squared_error(y_val, y_pred_val))
    r2_val = r2_score(y_val, y_pred_val)
    residuals_val = np.abs(y_val - y_pred_val)
    q80 = float(np.quantile(residuals_val, 0.80))

    y_pred_rf = model.predict(X_test)
    mae_rf = mean_absolute_error(y_test, y_pred_rf)
    rmse_rf = np.sqrt(mean_squared_error(y_test, y_pred_rf))
    r2_rf = r2_score(y_test, y_pred_rf)

    y_pred_b1 = test_df["score_lag_1"]
    mae_b1 = mean_absolute_error(y_test, y_pred_b1)
    rmse_b1 = np.sqrt(mean_squared_error(y_test, y_pred_b1))
    r2_b1 = r2_score(y_test, y_pred_b1)

    y_pred_b2 = test_df["score_rolling_mean_2y"]
    mae_b2 = mean_absolute_error(y_test, y_pred_b2)
    rmse_b2 = np.sqrt(mean_squared_error(y_test, y_pred_b2))
    r2_b2 = r2_score(y_test, y_pred_b2)

    dt = DecisionTreeRegressor(max_depth=6, random_state=42)
    dt.fit(X_train.fillna(X_train.median()), y_train)
    y_pred_dt = dt.predict(X_test.fillna(X_train.median()))
    mae_dt = mean_absolute_error(y_test, y_pred_dt)
    rmse_dt = np.sqrt(mean_squared_error(y_test, y_pred_dt))
    r2_dt = r2_score(y_test, y_pred_dt)

    print(f"\nKet qua so sanh tren tap kiem thu 2026 (N = {len(X_test):,}):")
    headers = ["Phuong phap / Mo hinh", "Phan loai", " MAE", " RMSE", " R2"]
    rows = [
        ["Baseline 1: Diem nam truoc (Lag 1)", "Naive Baseline", f"{mae_b1:.4f}", f"{rmse_b1:.4f}", f"{r2_b1:.4f}"],
        ["Baseline 2: Trung binh 2 nam (Mean 2Y)", "Naive Baseline", f"{mae_b2:.4f}", f"{rmse_b2:.4f}", f"{r2_b2:.4f}"],
        ["Baseline 3: Decision Tree don le (Depth=6)", "Single Tree", f"{mae_dt:.4f}", f"{rmse_dt:.4f}", f"{r2_dt:.4f}"],
        ["Du bao lai (cong thuc xu huong + RF)", "Hybrid Ensemble", f"{mae_rf:.4f}", f"{rmse_rf:.4f}", f"{r2_rf:.4f}"]
    ]
    col_w = [42, 18, 12, 12, 12]
    print("".join(h.ljust(col_w[i]) for i, h in enumerate(headers)))
    print("-" * sum(col_w))
    for r in rows:
        print("".join(c.ljust(col_w[i]) for i, c in enumerate(r)))

    print(f"- Tap tham dinh 2025: MAE={mae_val:.4f}, RMSE={rmse_val:.4f}, R2={r2_val:.4f}, Khoang tin cay 80% = +/-{q80:.2f} diem")
    print(f"- Tap kiem thu 2026: Du bao lai MAE={mae_rf:.4f} < Baseline Lag-1 MAE={mae_b1:.4f} (R2={r2_rf:.4f})")

    residuals_test = np.abs(y_test - y_pred_rf)
    test_cov = float(np.mean(residuals_test <= q80))

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        joblib.dump(model, save_path)
        print(f"\n[OK] Da luu mo hinh THPT vao: {save_path}")

    report_dir = os.path.join(os.path.dirname(__file__), "data", "reports")
    os.makedirs(report_dir, exist_ok=True)
    search = compare_hybrid_variants(model, X_val, y_val, X_test, y_test, report_dir)
    if not write_reports:
        return {"model": model, "mae": mae_rf, "rmse": rmse_rf, "r2": r2_rf, "q80": q80, "search": search}

    bench_csv = os.path.join(report_dir, "model_comparison_benchmark.csv")
    branch = "THPT (Time Series 2-Lag)"
    bench_rows = [
        ("Baseline 1: Điểm năm trước (Lag 1)", mae_b1, rmse_b1, r2_b1, "Naïve Baseline"),
        ("Baseline 2: Trung bình 2 năm (Mean 2Y)", mae_b2, rmse_b2, r2_b2, "Naïve Baseline"),
        ("Baseline 3: Decision Tree đơn lẻ (Depth=6)", mae_dt, rmse_dt, r2_dt, "Single Tree Model"),
        ("Dự báo lai (công thức xu hướng + RF)", mae_rf, rmse_rf, r2_rf, "Hybrid Ensemble"),
    ]
    df_bench = pd.DataFrame([
        {"Model / Method": name, "Test MAE": round(mae, 4), "Test RMSE": round(rmse, 4),
         "Test R2": round(r2, 4), "Type": kind, "Branch": branch}
        for name, mae, rmse, r2, kind in bench_rows
    ])
    df_bench.to_csv(bench_csv, index=False, encoding="utf-8-sig")

    feat_csv = os.path.join(report_dir, "feature_importance_thpt.csv")
    feat_names = ["score_lag_1", "score_lag_2", "trend", "score_diff_lag", "score_rolling_mean_2y"]
    if hasattr(model, "rf") and hasattr(model.rf, "feature_importances_"):
        df_feat = pd.DataFrame({
            "feature": feat_names,
            "importance_mean": model.rf.feature_importances_
        }).sort_values("importance_mean", ascending=False)
        df_feat.to_csv(feat_csv, index=False, encoding="utf-8-sig")

    return {
        "model": model,
        "mae": mae_rf, "rmse": rmse_rf, "r2": r2_rf, "q80": q80,
        "test_cov": test_cov, "train_size": len(train_df),
        "val_size": len(val_df), "test_size": len(test_df)
    }


def train_hoc_ba_branch(
    df_hb: pd.DataFrame,
    df_up: pd.DataFrame,
    df_um: pd.DataFrame,
    save_path: Optional[str] = None
) -> Dict[str, Any]:
    print("\nHuan luyen va danh gia phuong thuc Hoc ba (thang 30)")

    if not df_up.empty:
        up_sub = df_up[["program_id", "major_group_id", "program_type"]].drop_duplicates("program_id")
        df_hb = df_hb.merge(up_sub, on="program_id", how="left")
    if not df_um.empty:
        um_sub = df_um[["university_id", "university_type", "region"]].drop_duplicates("university_id")
        df_hb = df_hb.merge(um_sub, on="university_id", how="left")

    std_hb = df_hb[df_hb["score_scale"] == "SCALE_30"].copy()
    train_df = std_hb[std_hb["year"] <= 2025].copy()
    test_df = std_hb[std_hb["year"] == 2026].copy()

    cat_cols = ["major_group_id", "program_type", "university_type", "region", "subject_combination"]
    target_col = "benchmark_score"

    X_train, y_train = train_df[cat_cols], train_df[target_col]
    X_test, y_test = test_df[cat_cols], test_df[target_col]

    prep = ColumnTransformer(transformers=[
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), cat_cols)
    ])
    pipe = Pipeline([("prep", prep), ("rf", RandomForestRegressor(n_estimators=300, max_depth=16, min_samples_leaf=3, random_state=42, n_jobs=-1))])
    pipe.fit(X_train, y_train)

    y_pred_rf = pipe.predict(X_test)
    mae_rf = mean_absolute_error(y_test, y_pred_rf)
    rmse_rf = np.sqrt(mean_squared_error(y_test, y_pred_rf))
    r2_rf = r2_score(y_test, y_pred_rf)

    group_medians = train_df.groupby("major_group_id")["benchmark_score"].median().to_dict()
    overall_median = train_df["benchmark_score"].median()
    y_pred_median = test_df["major_group_id"].map(group_medians).fillna(overall_median)
    mae_b1 = mean_absolute_error(y_test, y_pred_median)
    rmse_b1 = np.sqrt(mean_squared_error(y_test, y_pred_median))
    r2_b1 = r2_score(y_test, y_pred_median)

    print(f"Hoc ba Test: Baseline Median MAE={mae_b1:.4f}, RF MAE={mae_rf:.4f}, R2={r2_rf:.4f}")

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        joblib.dump(pipe, save_path)
        print(f"[OK] Da luu mo hinh Hoc ba vao: {save_path}")

    return {"mae": mae_rf, "rmse": rmse_rf, "r2": r2_rf}


def generate_and_release_forecast_2027(
    data_dir: str,
    model_thpt: Any,
    q80: float
) -> str:
    import sklearn
    radius = round(float(q80), 2)
    src_forecast = os.path.join(data_dir, "processed", "forecast_records_2026.csv")
    if not os.path.exists(src_forecast):
        raise FileNotFoundError(f"Khong tim thay file nguon: {src_forecast}")

    df_src = pd.read_csv(src_forecast)
    records_2027 = []
    thpt_ml_count = 0
    thpt_lag1_count = 0
    hb_count = 0

    for idx, row in df_src.iterrows():
        r = dict(row)
        prog_id = str(r.get("program_id", "")).strip()
        adm_case = str(r.get("admission_case_id", "")).strip()
        m_code = str(r.get("method_code", "")).strip().upper()
        scale = str(r.get("score_scale", "SCALE_30")).strip()
        calc_rule = str(r.get("calculation_rule_id", "RULE_THPT_STD_30")).strip()
        u_code = str(r.get("university_code", "")).strip().upper()

        c_2026 = r.get("actual_cutoff_2026")
        c_2025 = r.get("historical_cutoff_2025")
        val_2026 = float(c_2026) if pd.notna(c_2026) and str(c_2026).strip() != "" else None
        val_2025 = float(c_2025) if pd.notna(c_2025) and str(c_2025).strip() != "" else None

        if m_code == "THPT" and val_2026 is not None and val_2025 is not None and model_thpt is not None:
            feat_df = pd.DataFrame([{
                "score_lag_1": val_2026,
                "score_lag_2": val_2025,
                "score_diff_lag": val_2026 - val_2025,
                "score_rolling_mean_2y": (val_2026 + val_2025) / 2.0
            }])
            pred = float(model_thpt.predict(feat_df)[0])
            pred = round(pred, 2)
            f_status = "PREDICTED_TIME_SERIES"
            m_version = "RF_THPT_TIME_SERIES_V4_2027"
            thpt_ml_count += 1
        elif m_code == "THPT" and val_2026 is not None:
            pred = round(val_2026, 2)
            f_status = "FALLBACK_LAG1_ONLY"
            m_version = "BASELINE_LAG1_2027"
            thpt_lag1_count += 1
        elif m_code == "THPT" and val_2025 is not None:
            pred = round(val_2025, 2)
            f_status = "FALLBACK_LAG2_ONLY"
            m_version = "BASELINE_LAG2_2027"
            thpt_lag1_count += 1
        else:
            pred = round(val_2026, 2) if val_2026 is not None else (round(val_2025, 2) if val_2025 is not None else 0.0)
            f_status = "HISTORICAL_LOOKUP_ONLY"
            m_version = "HISTORICAL_LOOKUP_2027"
            hb_count += 1

        f_id = f"FC_2027_{u_code}_{idx+1:05d}"
        low_80 = round(pred - radius, 2) if pred > 0 else 0.0
        up_80 = round(pred + radius, 2) if pred > 0 else 0.0
        low_90 = round(pred - radius * 1.28, 2) if pred > 0 else 0.0
        up_90 = round(pred + radius * 1.28, 2) if pred > 0 else 0.0

        records_2027.append({
            "forecast_id": f_id,
            "target_year": 2027,
            "method_code": m_code,
            "program_id": prog_id,
            "admission_case_id": adm_case,
            "university_code": u_code,
            "university_name": r.get("university_name", ""),
            "program_name": r.get("program_name", ""),
            "subject_combination": r.get("subject_combination", ""),
            "sub_criteria": r.get("sub_criteria", ""),
            "forecast_status": f_status,
            "model_version": m_version,
            "predicted_cutoff": pred,
            "uncertainty_radius_80": radius,
            "lower_bound_80": low_80,
            "upper_bound_80": up_80,
            "lower_bound_90": low_90,
            "upper_bound_90": up_90,
            "historical_cutoff_2026": val_2026,
            "historical_cutoff_2025": val_2025,
            "historical_cutoff_2024": r.get("historical_cutoff_2024"),
            "score_scale": scale,
            "calculation_rule_id": calc_rule
        })

    df_2027 = pd.DataFrame(records_2027)
    out_path = os.path.join(data_dir, "processed", "forecast_records_2027.csv")
    df_2027.to_csv(out_path, index=False, encoding="utf-8-sig")

    meta_path = os.path.join(data_dir, "models", "rf_thpt_metadata.json")
    meta = {
        "model_name": "RFTrendResidualRegressor",
        "scikit_learn_version": sklearn.__version__,
        "target_year": 2027,
        "input_features": ["score_lag_1", "score_lag_2", "score_diff_lag", "score_rolling_mean_2y"],
        "calibrated_radius_80": radius,
        "total_records": len(df_2027),
        "thpt_ml_predictions": thpt_ml_count,
        "thpt_lag1_fallbacks": thpt_lag1_count,
        "hoc_ba_lookups": hb_count
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] du lieu du bao 2027: {out_path}")
    print(f"  - Tong so ban ghi du bao: {len(df_2027):,}")
    print(f"  - THPT du bao bang mo hinh Random Forest: {thpt_ml_count:,}")
    print(f"  - THPT tra cuu theo baseline 1 nam: {thpt_lag1_count:,}")
    print(f"  - Phuong thuc hoc ba / tra cuu lich su: {hb_count:,}")
    return out_path


def sync_calibrator_and_forecast(
    data_dir: str,
    q80: float,
    train_size: Optional[int] = None,
    val_size: Optional[int] = None,
    test_size: Optional[int] = None,
    test_coverage: Optional[float] = None,
    model_thpt: Any = None,
    regenerated_predictions: bool = True
) -> None:
    models_dir = os.path.join(data_dir, "models")
    calibrator_path = os.path.join(models_dir, "conformal_calibrator_thpt.json")
    radius = round(float(q80), 2)

    val_label = f"Validation 2025 (N={val_size:,})" if val_size is not None else "Validation 2025"
    test_label = f"Test 2026 (N={test_size:,})" if test_size is not None else "Test 2026"

    cal_data = {
        "method": "Residual-based Split Conformal Prediction",
        "calibration_set": val_label,
        "test_set": test_label,
        "train_size": train_size,
        "intervals": {
            "confidence_80": {
                "radius_points": radius,
                "nominal_coverage": 0.8,
                "empirical_test_coverage": round(test_coverage, 4) if test_coverage is not None else 0.8
            }
        }
    }
    with open(calibrator_path, "w", encoding="utf-8") as f:
        json.dump(cal_data, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Da dong bo bo hieu chinh Conformal: {calibrator_path} (ban kinh +/-{radius} diem)")

    if regenerated_predictions and model_thpt is not None:
        generate_and_release_forecast_2027(data_dir, model_thpt, q80)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tai tao quy trinh huan luyen Random Forest")
    parser.add_argument("--method", choices=["thpt", "hoc_ba", "all"], default="all", help="Phuong thuc can huan luyen")
    parser.add_argument("--compare-only", action="store_true",
                        help="Chi so sanh bien the mo hinh va do tham so tron, khong luu model hay bao cao chinh")
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "data"), help="Thu muc chua du lieu")
    parser.add_argument("--save", action=argparse.BooleanOptionalAction, default=True, help="Luu mo hinh da huan luyen")
    parser.add_argument("--promote", action=argparse.BooleanOptionalAction, default=True, help="Luu vao model chinh thuc rf_thpt_best.joblib")
    parser.add_argument("--sync-forecast", action=argparse.BooleanOptionalAction, default=True, help="Dong bo Conformal calibrator")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    df_thpt, df_hb, df_up, df_um = load_datasets(args.data_dir)

    if args.compare_only:
        train_thpt_branch(df_thpt, df_up, df_um, save_path=None, write_reports=False)
        return

    models_dir = os.path.join(args.data_dir, "models")
    thpt_model_path = os.path.join(models_dir, "rf_thpt_best.joblib") if (args.save and args.promote) else None
    hb_model_path = os.path.join(models_dir, "rf_hoc_ba_metadata.joblib") if (args.save and args.promote) else None

    res_thpt = None
    if args.method in ["thpt", "all"]:
        res_thpt = train_thpt_branch(df_thpt, df_up, df_um, save_path=thpt_model_path)

    if args.method in ["hoc_ba", "all"]:
        train_hoc_ba_branch(df_hb, df_up, df_um, save_path=hb_model_path)

    if res_thpt and args.sync_forecast:
        sync_calibrator_and_forecast(
            args.data_dir,
            res_thpt["q80"],
            train_size=res_thpt.get("train_size"),
            val_size=res_thpt.get("val_size"),
            test_size=res_thpt.get("test_size"),
            test_coverage=res_thpt.get("test_cov"),
            model_thpt=res_thpt.get("model"),
            regenerated_predictions=True
        )

    print("\nHoan tat qua trinh huan luyen.")


if __name__ == "__main__":
    main()
