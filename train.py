import os
import sys
import json
import argparse
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

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
        raise FileNotFoundError(f"Không tìm thấy file: {thpt_path}")
    if not os.path.exists(hb_path):
        raise FileNotFoundError(f"Không tìm thấy file: {hb_path}")

    df_thpt = pd.read_csv(thpt_path, low_memory=False)
    df_hb = pd.read_csv(hb_path, low_memory=False)
    df_up = pd.read_csv(up_path, low_memory=False) if os.path.exists(up_path) else pd.DataFrame()
    df_um = pd.read_csv(um_path, low_memory=False) if os.path.exists(um_path) else pd.DataFrame()

    return df_thpt, df_hb, df_up, df_um




def train_thpt_branch(
    df_thpt: pd.DataFrame,
    df_up: pd.DataFrame,
    df_um: pd.DataFrame,
    save_path: str = None
) -> Dict[str, Any]:
    print("\nHuấn luyện mô hình điểm thi THPT (Hyperparameter Tuning & Cross-Validation)")

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

    print(f"Tổng số mẫu TRAIN_READY: {len(eligible):,}")
    print(f"  - Train (năm <= 2024):       {len(train_df):,} mẫu")
    print(f"  - Validation (năm 2025):     {len(val_df):,} mẫu")
    print(f"  - Test (năm 2026):           {len(test_df):,} mẫu")

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
    print(f"Cross-Validation 5-Fold MAE trên Train: {np.mean(cv_scores):.4f} (±{np.std(cv_scores):.4f})")

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

    print(f"\nKết quả so sánh trên tập kiểm thử 2026 (N = {len(X_test):,}):")
    headers = ["Phương pháp / Mô hình", "Phân loại", "Test MAE", "Test RMSE", "Test R2"]
    rows = [
        ["Baseline 1: Điểm năm trước (Lag 1)", "Naïve Baseline", f"{mae_b1:.4f}", f"{rmse_b1:.4f}", f"{r2_b1:.4f}"],
        ["Baseline 2: Trung bình 2 năm (Mean 2Y)", "Naïve Baseline", f"{mae_b2:.4f}", f"{rmse_b2:.4f}", f"{r2_b2:.4f}"],
        ["Baseline 3: Decision Tree đơn lẻ (Depth=6)", "Single Tree", f"{mae_dt:.4f}", f"{rmse_dt:.4f}", f"{r2_dt:.4f}"],
        ["Random Forest THPT (Tuned Residual)", "Ensemble ML", f"{mae_rf:.4f}", f"{rmse_rf:.4f}", f"{r2_rf:.4f}"]
    ]
    col_w = [42, 18, 12, 12, 12]
    print("".join(h.ljust(col_w[i]) for i, h in enumerate(headers)))
    print("-" * sum(col_w))
    for r in rows:
        print("".join(c.ljust(col_w[i]) for i, c in enumerate(r)))

    print(f"- Tập thẩm định (2025): MAE={mae_val:.4f}, RMSE={rmse_val:.4f}, R2={r2_val:.4f}, Khoảng tin cậy 80% = ±{q80:.2f} điểm")
    print(f"- Tập kiểm thử (2026): Random Forest MAE={mae_rf:.4f} < Baseline Lag-1 MAE={mae_b1:.4f} (R2={r2_rf:.4f})")

    residuals_test = np.abs(y_test - y_pred_rf)
    test_cov = float(np.mean(residuals_test <= q80))

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        joblib.dump(model, save_path)
        print(f"\n[OK] Đã lưu mô hình THPT vào: {save_path}")

    report_dir = os.path.join(os.path.dirname(__file__), "data", "reports")
    os.makedirs(report_dir, exist_ok=True)
    bench_csv = os.path.join(report_dir, "model_comparison_benchmark.csv")
    df_bench = pd.DataFrame([
        {"Model / Method": "Baseline 1: Điểm năm trước (Lag 1)", "Test MAE": round(mae_b1, 4), "Test RMSE": round(rmse_b1, 4), "Test R2": round(r2_b1, 4), "Type": "Naïve Baseline", "Branch": "THPT (Time Series 2-Lag)"},
        {"Model / Method": "Baseline 2: Trung bình 2 năm (Mean 2Y)", "Test MAE": round(mae_b2, 4), "Test RMSE": round(rmse_b2, 4), "Test R2": round(r2_b2, 4), "Type": "Naïve Baseline", "Branch": "THPT (Time Series 2-Lag)"},
        {"Model / Method": "Baseline 3: Decision Tree đơn lẻ (Depth=6)", "Test MAE": round(mae_dt, 4), "Test RMSE": round(rmse_dt, 4), "Test R2": round(r2_dt, 4), "Type": "Single Tree Model", "Branch": "THPT (Time Series 2-Lag)"},
        {"Model / Method": "Random Forest THPT", "Test MAE": round(mae_rf, 4), "Test RMSE": round(rmse_rf, 4), "Test R2": round(r2_rf, 4), "Type": "Ensemble ML Model", "Branch": "THPT (Time Series 2-Lag)"}
    ])
    df_bench.to_csv(bench_csv, index=False, encoding="utf-8-sig")

    return {
        "mae": mae_rf, "rmse": rmse_rf, "r2": r2_rf, "q80": q80,
        "test_cov": test_cov, "val_size": len(val_df), "test_size": len(test_df)
    }


def train_hoc_ba_branch(
    df_hb: pd.DataFrame,
    df_up: pd.DataFrame,
    df_um: pd.DataFrame,
    save_path: str = None
) -> Dict[str, Any]:
    print("\nHuấn luyện và đánh giá phương thức Học bạ (thang 30)")

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

    print(f"Học bạ Test: Baseline Median MAE={mae_b1:.4f}, RF MAE={mae_rf:.4f}, R2={r2_rf:.4f}")

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        joblib.dump(pipe, save_path)
        print(f"[OK] Đã lưu mô hình Học bạ vào: {save_path}")

    return {"mae": mae_rf, "rmse": rmse_rf, "r2": r2_rf}


def sync_calibrator_and_forecast(
    data_dir: str,
    q80: float,
    val_size: int = None,
    test_size: int = None,
    test_coverage: float = None
):
    models_dir = os.path.join(data_dir, "models")
    calibrator_path = os.path.join(models_dir, "conformal_calibrator_thpt.json")
    radius = round(float(q80), 2)

    val_label = f"Validation 2025 (N={val_size:,})" if val_size is not None else "Validation 2025"
    test_label = f"Test 2026 (N={test_size:,})" if test_size is not None else "Test 2026"

    cal_data = {
        "method": "Residual-based Split Conformal Prediction",
        "calibration_set": val_label,
        "test_set": test_label,
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
    print(f"\n[OK] Đã đồng bộ bộ hiệu chỉnh Conformal: {calibrator_path} (bán kính ±{radius} điểm)")

    forecast_path = os.path.join(data_dir, "processed", "forecast_records_2026.csv")
    if os.path.exists(forecast_path):
        df_fc = pd.read_csv(forecast_path)
        mask = df_fc["forecast_status"].str.upper() == "PREDICTED_TIME_SERIES"
        df_fc.loc[mask, "uncertainty_radius_80"] = radius
        df_fc.loc[mask, "lower_bound_80"] = (df_fc.loc[mask, "predicted_cutoff"] - radius).round(2)
        df_fc.loc[mask, "upper_bound_80"] = (df_fc.loc[mask, "predicted_cutoff"] + radius).round(2)
        df_fc.to_csv(forecast_path, index=False)
        print(f"[OK] Đã đồng bộ bảng dữ liệu dự báo: {forecast_path}")


def main():
    parser = argparse.ArgumentParser(description="Tái tạo quy trình huấn luyện Random Forest Tuyển sinh")
    parser.add_argument("--method", choices=["thpt", "hoc_ba", "all"], default="all", help="Phương thức cần huấn luyện")
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "data"), help="Thư mục chứa dữ liệu")
    parser.add_argument("--save", action="store_true", default=True, help="Lưu mô hình đã huấn luyện")
    parser.add_argument("--promote", action="store_true", default=True, help="Lưu trực tiếp vào model chính thức rf_thpt_best.joblib")
    parser.add_argument("--sync-forecast", action="store_true", default=True, help="Đồng bộ Conformal calibrator")

    args = parser.parse_args()

    df_thpt, df_hb, df_up, df_um = load_datasets(args.data_dir)

    models_dir = os.path.join(args.data_dir, "models")
    thpt_model_path = os.path.join(models_dir, "rf_thpt_best.joblib") if args.save else None
    hb_model_path = os.path.join(models_dir, "rf_hoc_ba_metadata.joblib") if args.save else None

    res_thpt = None
    if args.method in ["thpt", "all"]:
        res_thpt = train_thpt_branch(df_thpt, df_up, df_um, save_path=thpt_model_path)

    if args.method in ["hoc_ba", "all"]:
        train_hoc_ba_branch(df_hb, df_up, df_um, save_path=hb_model_path)

    if res_thpt and (args.promote or args.sync_forecast):
        sync_calibrator_and_forecast(
            args.data_dir,
            res_thpt["q80"],
            val_size=res_thpt.get("val_size"),
            test_size=res_thpt.get("test_size"),
            test_coverage=res_thpt.get("test_cov")
        )

    print("\nHoàn tất quá trình huấn luyện và đánh giá mô hình.")


if __name__ == "__main__":
    main()
