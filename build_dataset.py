import argparse
import os
import re
import sys
from typing import Dict, Any, Tuple, Optional

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
SRC_RAW_DEFAULT = os.path.join(BASE, "data", "sources_archive", "tuyensinh247_historical_2018_2024.csv")
SRC_PROCESSED_DEFAULT = os.path.join(BASE, "data", "processed", "thpt_cutoff_clean_final.csv")
META_DIR_DEFAULT = os.path.join(BASE, "data", "metadata")
REF_DEFAULT = os.path.join(BASE, "data", "training", "thpt_rf_dataset.csv")
OUT_DEFAULT = os.path.join(BASE, "data", "training", "thpt_rf_dataset.csv")
OUT_CLEAN_DEFAULT = os.path.join(BASE, "data", "processed", "thpt_cutoff_clean_rebuilt.csv")

FIRST_YEAR = 2020
TRAIN_MAX_YEAR = 2024
VALIDATION_YEAR = 2025
TEST_YEAR = 2026

OUTPUT_COLUMNS = [
    "year", "split", "university_id", "university_code", "university_name", "program_id",
    "program_name", "admission_code", "admission_case_id", "subject_combination", "sub_criteria",
    "method_code", "score_uniformity_policy", "source_record_id", "lag_1_record_id",
    "lag_1_link_type", "score_lag_1", "lag_2_record_id", "lag_2_link_type", "score_lag_2",
    "score_diff_lag", "score_rolling_mean_2y", "benchmark_score", "score_scale", "lag_gap_status",
    "most_recent_prior_year", "most_recent_prior_score", "prior_gap_years", "source_id",
    "history_status", "ml_eligibility", "verified",
]


def slug(text: Any) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", str(text)).strip("_")


def make_case_id(row: pd.Series) -> str:
    case_id = f"CASE_{row['university_code']}_{row['admission_code']}_{slug(row['subject_combination'])}"
    if slug(row.get("sub", "")):
        case_id += "_" + slug(row["sub"])
    return case_id


def clean_raw_tuyensinh247(
    raw_path: str,
    meta_dir: str = META_DIR_DEFAULT
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Khong tim thay file du lieu tho: {raw_path}")

    raw = pd.read_csv(raw_path, low_memory=False)
    n_initial = len(raw)
    report: Dict[str, Any] = {"tong_dong_ban_dau": n_initial}

    df = raw[raw["Năm"] >= FIRST_YEAR].copy()
    report["loai_bo_nam_cu_truoc_2020"] = n_initial - len(df)
    n_step1 = len(df)

    df = df.dropna(subset=["Điểm chuẩn", "Mã trường xét tuyển", "Tổ hợp", "Mã xét tuyển"]).copy()
    df = df[df["Điểm chuẩn"] > 0].copy()
    report["loai_bo_khuyet_diem_hoac_diem_am"] = n_step1 - len(df)
    n_step2 = len(df)

    df["subject_combination"] = df["Tổ hợp"].astype(str).str.strip().str.upper()
    valid_comb = df["subject_combination"].str.match(r"^[A-Z][0-9]{2}$", na=False)
    df = df[valid_comb].copy()
    report["loai_bo_to_hop_mon_loi"] = n_step2 - len(df)
    n_step3 = len(df)

    df["Ghi chú"] = df["Ghi chú"].fillna("").astype(str).str.strip()
    is_scale_40 = (
        df["Loại điểm"].astype(str).str.contains("40")
        | df["Ghi chú"].str.contains("thang 40", case=False)
    )
    df["score_scale"] = np.where(is_scale_40, "SCALE_40", "SCALE_30")

    valid_score = np.where(
        is_scale_40,
        (df["Điểm chuẩn"] >= 15.0) & (df["Điểm chuẩn"] <= 40.5),
        (df["Điểm chuẩn"] >= 10.0) & (df["Điểm chuẩn"] <= 30.5)
    )
    df = df[valid_score].copy()
    report["loai_bo_diem_ngoai_lai"] = n_step3 - len(df)
    n_step4 = len(df)

    df["sub_criteria"] = df["Ghi chú"].apply(
        lambda g: g if any(k in g.lower() for k in ["chỉ tuyển", "nhân hệ số", "tiếng anh", "bài thi", "nam", "nữ", "clc"]) else ""
    )

    df = df.drop_duplicates(
        subset=["Mã trường xét tuyển", "Năm", "Mã xét tuyển", "subject_combination", "sub_criteria"]
    ).copy()
    report["loai_bo_ban_ghi_trung_lap"] = n_step4 - len(df)
    report["tong_dong_sau_lam_sach"] = len(df)

    unis_path = os.path.join(meta_dir, "universities_master.csv")
    progs_path = os.path.join(meta_dir, "university_programs.csv")

    df["university_code"] = df["Mã trường xét tuyển"].astype(str).str.strip().str.upper()
    df["year"] = df["Năm"].astype(int)
    df["benchmark_score"] = df["Điểm chuẩn"].astype(float)
    df["score_raw"] = df["benchmark_score"]
    df["admission_code"] = df["Mã xét tuyển"].astype(str).str.strip()
    df["program_name"] = df["Tên Ngành"].astype(str).str.strip()
    df["method_code"] = "THPT"
    df["score_type"] = "BENCHMARK_SCORE"
    df["score_basis"] = "RAW_3_SUBJECTS"
    df["calculation_rule_id"] = np.where(df["score_scale"] == "SCALE_40", "RULE_THPT_STD_40", "RULE_THPT_STD_30")
    df["conversion_rule_id"] = "NONE"
    df["source_id"] = "SRC_TUYENSINH247_HISTORICAL_2018_2024"
    df["verification_status"] = "VERIFIED"

    if os.path.exists(unis_path):
        df_unis = pd.read_csv(unis_path)
        u_sub = df_unis[["university_code", "university_id", "university_name", "province", "region", "university_type"]].drop_duplicates("university_code")
        df = df.merge(u_sub, on="university_code", how="left")
    else:
        df["university_id"] = "UNI_" + df["university_code"]
        df["university_name"] = df["Tên Trường"]
        df["province"] = df["Tỉnh/ Thành phố"]
        df["region"] = df["Khu vực"]
        df["university_type"] = df["Loại đơn vị"]

    if os.path.exists(progs_path):
        df_progs = pd.read_csv(progs_path)
        p_sub = df_progs[["university_code", "admission_code", "program_id", "major_id", "major_name", "major_group_id"]].drop_duplicates(["university_code", "admission_code"])
        df = df.merge(p_sub, on=["university_code", "admission_code"], how="left")
        df["program_id"] = df["program_id"].fillna("PRG_" + df["university_code"] + "_" + df["admission_code"].astype(str))
        df["major_group_id"] = df["major_group_id"].fillna("GRP_OTHER")
        df["major_id"] = df["major_id"].fillna("MAJ_UNKNOWN")
        df["major_name"] = df["major_name"].fillna(df["program_name"])
    else:
        df["program_id"] = "PRG_" + df["university_code"] + "_" + df["admission_code"].astype(str)
        df["major_group_id"] = "GRP_OTHER"
        df["major_id"] = "MAJ_UNKNOWN"
        df["major_name"] = df["program_name"]

    df["_idx"] = np.arange(1, len(df) + 1)
    df["record_id"] = df.apply(lambda r: f"REC_THPT_{r['year']}_{r['university_code']}_{r['_idx']:06d}", axis=1)
    df = df.drop(columns=["_idx"]).reset_index(drop=True)

    return df, report


def clean_processed_data(df: pd.DataFrame, method: str = "THPT") -> Tuple[pd.DataFrame, Dict[str, Any]]:
    initial_count = len(df)
    report: Dict[str, Any] = {"initial_rows": initial_count}

    if "method_code" in df.columns:
        df = df[df["method_code"].astype(str).str.strip().str.upper() == method.upper()].copy()
    report["after_method_filter"] = len(df)

    str_cols = ["university_code", "admission_code", "subject_combination", "program_id"]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    if "sub_criteria" in df.columns:
        df["sub_criteria"] = df["sub_criteria"].fillna("").astype(str).str.strip()
    else:
        df["sub_criteria"] = ""

    valid_mask = df["benchmark_score"].notna()
    if "score_scale" in df.columns:
        valid_30 = (df["score_scale"].astype(str).str.contains("30")) & (df["benchmark_score"] > 0) & (df["benchmark_score"] <= 30.5)
        valid_40 = (df["score_scale"].astype(str).str.contains("40")) & (df["benchmark_score"] > 0) & (df["benchmark_score"] <= 40.5)
        valid_other = (~df["score_scale"].astype(str).str.contains("30|40")) & (df["benchmark_score"] > 0) & (df["benchmark_score"] <= 100)
        score_mask = valid_30 | valid_40 | valid_other
    else:
        score_mask = (df["benchmark_score"] > 0) & (df["benchmark_score"] <= 40.5)

    df = df[valid_mask & score_mask].copy()
    report["after_score_validation"] = len(df)

    if "record_id" in df.columns:
        df = df.drop_duplicates(subset=["record_id"]).copy()
    else:
        dedup_keys = [c for c in ["program_id", "year", "subject_combination", "sub_criteria", "method_code"] if c in df.columns]
        if dedup_keys:
            df = df.drop_duplicates(subset=dedup_keys).copy()
    report["final_clean_rows"] = len(df)
    report["removed_invalid_rows"] = initial_count - len(df)

    return df, report


def build_dataset(src_path: str, is_raw: bool = False) -> pd.DataFrame:
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"Khong tim thay file nguon: {src_path}")

    df_sample = pd.read_csv(src_path, nrows=5, low_memory=False)
    raw_col_indicators = {"Khu vực", "Tỉnh/ Thành phố", "Mã trường xét tuyển", "Tên Ngành", "Điểm chuẩn"}
    is_raw_detected = is_raw or bool(raw_col_indicators.intersection(set(df_sample.columns)))

    if is_raw_detected:
        print("[TIEN TRINH 1/2] Kich hoat quy trinh lam sach du lieu tho (Raw Data Cleaning ETL)...")
        df, report = clean_raw_tuyensinh247(src_path)
        print(f"  + Tong so dong ban dau:                {report['tong_dong_ban_dau']:,}")
        print(f"  + Loai bo cac nam cu truoc 2020:       -{report['loai_bo_nam_cu_truoc_2020']:,} dong")
        print(f"  + Loai bo dong khuyet diem:            -{report['loai_bo_khuyet_diem_hoac_diem_am']:,} dong")
        print(f"  + Loai bo to hop mon khong hop le:     -{report['loai_bo_to_hop_mon_loi']:,} dong")
        print(f"  + Loai bo diem ngoai lai (outlier):    -{report['loai_bo_diem_ngoai_lai']:,} dong")
        print(f"  + Loai bo ban ghi trung lap (dedup):   -{report['loai_bo_ban_ghi_trung_lap']:,} dong")
        print(f"  => Ket qua sau lam sach tho:           {report['tong_dong_sau_lam_sach']:,} dong")
    else:
        df = pd.read_csv(src_path, low_memory=False)
        df, report = clean_processed_data(df, method="THPT")
        print(f"[Lam sach data] Ban dau: {report['initial_rows']:,} dong -> Sau lam sach: {report['final_clean_rows']:,} dong")

    print("\n[TIEN TRINH 2/2] Xay dung dac trung tre va phan chia tap huan luyen (Feature Engineering)...")
    df["sub"] = df["sub_criteria"].fillna("").astype(str).str.strip()
    df["sub_key"] = df["sub"].str.lower()
    df["comb_key"] = df["subject_combination"].astype(str).str.strip().str.upper()
    df["admission_case_id"] = df.apply(make_case_id, axis=1)
    df["_order"] = np.arange(len(df))

    df = df.sort_values(["year", "record_id"]).reset_index(drop=True)
    n_scores = df.groupby(["program_id", "year", "sub_key"])["benchmark_score"].transform("nunique")
    df["score_uniformity_policy"] = np.where(
        n_scores > 1,
        "CASE_DIFFERENTIATED_SCORE_POLICY",
        "COMMON_PROGRAM_SCORE_POLICY"
    )

    by_case = {
        (r.program_id, r.comb_key, r.sub_key, r.year): (r.record_id, r.benchmark_score)
        for r in df.itertuples()
    }
    common = (
        df[df["score_uniformity_policy"] == "COMMON_PROGRAM_SCORE_POLICY"]
        .groupby(["program_id", "year", "sub_key"])
        .first()
    )
    by_program = {k: (r.record_id, r.benchmark_score) for k, r in common.iterrows()}
    last_per_program_year = df.groupby(["program_id", "year"]).last()
    prog_years: Dict[str, list] = {}
    for (pid, yr), r in last_per_program_year.iterrows():
        prog_years.setdefault(pid, []).append((yr, r.benchmark_score))

    def find_lag(row, k):
        y = row.year - k
        hit = by_case.get((row.program_id, row.comb_key, row.sub_key, y))
        if hit:
            return hit[0], "EXACT_CASE_MATCH", hit[1]

        hit = by_program.get((row.program_id, y, row.sub_key))
        if hit and row.score_uniformity_policy == "COMMON_PROGRAM_SCORE_POLICY":
            return hit[0], "COMMON_PROGRAM_FALLBACK", hit[1]
        return None, "NONE", np.nan

    lag1 = [find_lag(r, 1) for r in df.itertuples()]
    lag2 = [find_lag(r, 2) for r in df.itertuples()]
    df["lag_1_record_id"], df["lag_1_link_type"], df["score_lag_1"] = zip(*lag1)
    df["lag_2_record_id"], df["lag_2_link_type"], df["score_lag_2"] = zip(*lag2)

    both = df["score_lag_1"].notna() & df["score_lag_2"].notna()
    df["score_diff_lag"] = np.where(both, df["score_lag_1"] - df["score_lag_2"], np.nan)
    df["score_rolling_mean_2y"] = np.where(both, (df["score_lag_1"] + df["score_lag_2"]) / 2.0, np.nan)

    def prior(row):
        cands = [(y, s) for y, s in prog_years.get(row.program_id, []) if y < row.year]
        if not cands:
            return np.nan, np.nan, np.nan
        y, s = max(cands)
        return y, s, row.year - y

    pr = [prior(r) for r in df.itertuples()]
    df["most_recent_prior_year"], df["most_recent_prior_score"], df["prior_gap_years"] = zip(*pr)

    has1, has2 = df["score_lag_1"].notna(), df["score_lag_2"].notna()
    df["lag_gap_status"] = np.select(
        [df["year"] == FIRST_YEAR, has1 & has2, has1 & ~has2, df["most_recent_prior_year"].notna()],
        ["BASELINE_COMMENCEMENT_2020", "FULL_2LAG_CONTINUOUS", "MISSING_T_MINUS_2_ONLY", "GAP_MISSING_T_MINUS_1"],
        default="NO_PRIOR_HISTORY_NEW_PROGRAM"
    )
    df["history_status"] = np.select(
        [has1 & has2, has1],
        ["TRAIN_READY", "INSUFFICIENT_HISTORY_1Y"],
        default="NO_HISTORY"
    )
    df["ml_eligibility"] = df["history_status"]

    df["split"] = np.select(
        [df["year"] <= TRAIN_MAX_YEAR, df["year"] == VALIDATION_YEAR, df["year"] == TEST_YEAR],
        ["train", "validation", "test"],
        default="inference"
    )

    df["source_record_id"] = df["record_id"]
    df["verified"] = (
        df["verification_status"].astype(str).str.upper().str.startswith("VERIFIED")
        if "verification_status" in df.columns
        else True
    )

    result_df = df.sort_values("_order")[OUTPUT_COLUMNS].reset_index(drop=True)
    return result_df


def compare(new: pd.DataFrame, ref_path: str) -> bool:
    if not os.path.exists(ref_path):
        print(f"Khong tim thay file goc de doi chieu: {ref_path}")
        return True

    ref = pd.read_csv(ref_path, low_memory=False)
    a = new.set_index("source_record_id")
    b = ref.set_index("source_record_id")
    common_idx = a.index.intersection(b.index)
    print(f"So dong: tao lai {len(a):,} | file goc {len(b):,} | trung khop ID {len(common_idx):,}")

    b = b.loc[common_idx]
    a = a.loc[common_idx]

    key_cols = [
        "split", "admission_case_id", "score_lag_1", "score_lag_2",
        "score_diff_lag", "score_rolling_mean_2y", "benchmark_score", "ml_eligibility"
    ]
    ok = True
    print("\n[Doi chieu cac cot cot loi phuc vu huan luyen mo hinh]:")
    for col in key_cols + [c for c in OUTPUT_COLUMNS if c not in key_cols and c != "source_record_id"]:
        x, y = a[col], b[col]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            same = np.isclose(x.astype(float), y.astype(float), equal_nan=True)
        else:
            same = (x.fillna("").astype(str) == y.fillna("").astype(str)).to_numpy()
        n_diff = int((~same).sum())
        if col in key_cols:
            ok &= (n_diff == 0)
        if col == key_cols[-1]:
            print("\n[Doi chieu cac cot thong tin mo ta khac]:")
        status = "Khop hoan toan 100%" if n_diff == 0 else f"KHAC {n_diff} dong ({same.mean() * 100:.3f}% khop)"
        print(f"  {col:<26} -> {status}")

    same_order = (
        (new["source_record_id"].to_numpy() == ref["source_record_id"].to_numpy()).all()
        if len(new) == len(ref)
        else False
    )
    print(f"\nThu tu sap xep dong giong file goc: {'DUNG' if same_order else 'KHONG'}")
    ok &= bool(same_order)

    ready = (a["ml_eligibility"] == "TRAIN_READY")
    print(f"Tong so mau TRAIN_READY: {ready.sum():,} | Theo tung tap:", a[ready]["split"].value_counts().to_dict())
    return ok


def main():
    parser = argparse.ArgumentParser(description="Script lam sach du lieu tho va xay dung dataset huan luyen ML")
    parser.add_argument("--src", default=None, help="Duong dan file du lieu dau vao (mac dinh tu dong chon)")
    parser.add_argument("--raw", action="store_true", help="Chay quy trinh lam sach truc tiep tu file tho Tuyensinh247")
    parser.add_argument("--ref", default=REF_DEFAULT, help="Duong dan file tham chieu chuan de kiem tra doi chieu")
    parser.add_argument("--out", default=OUT_DEFAULT, help="Duong dan file ket qua xuat ra")
    parser.add_argument("--save-clean", default=None, help="Duong dan luu file CSV sau khi lam sach tho")
    parser.add_argument("--check-only", action="store_true", help="Chi kiem tra va doi chieu du lieu, khong ghi de file")
    args = parser.parse_args()

    if args.src:
        src_path = args.src
    elif args.raw:
        src_path = SRC_RAW_DEFAULT
    else:
        src_path = SRC_PROCESSED_DEFAULT

    print("QUY TRINH LAM SACH DU LIEU VA XAY DUNG DATASET HUAN LUYEN (BUILD_DATASET)")
    print(f"Nguon du lieu dau vao: {src_path}")

    if args.save_clean or (args.raw and args.save_clean is None):
        clean_save_target = args.save_clean or OUT_CLEAN_DEFAULT
        if args.raw or "tuyensinh247" in src_path.lower():
            df_cleaned, _ = clean_raw_tuyensinh247(src_path)
            os.makedirs(os.path.dirname(os.path.abspath(clean_save_target)), exist_ok=True)
            df_cleaned.to_csv(clean_save_target, index=False)
            print(f">> Da luu bang du lieu lam sach tho vao: {clean_save_target}")

    df_built = build_dataset(src_path, is_raw=args.raw)
    print(f"\nDa xay dung thanh cong: {len(df_built):,} ban ghi.")

    if args.ref and os.path.exists(args.ref) and not args.raw:
        print("\nTien hanh doi chieu chat luong voi dataset tham chieu...")
        is_matched = compare(df_built, args.ref)
        if is_matched:
            print("\n>> KET QUA DOI CHIEU: CHUAN XAC 100% VOI DU LIEU GOC.")
        else:
            print("\n>> CANH BAO: Phat hien sai khac so voi du lieu goc.")

    if not args.check_only:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        df_built.to_csv(args.out, index=False)
        print(f"\n>> Da luu dataset hoan chinh vao: {args.out}")


if __name__ == "__main__":
    main()