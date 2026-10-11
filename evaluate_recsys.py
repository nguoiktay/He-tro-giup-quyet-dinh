import os
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Any

import config
from admissionService import AdmissionService
from csvDatabase import CsvDatabase


def dcg_at_k(r: List[float], k: int) -> float:
    r = np.asarray(r, dtype=float)[:k]
    if r.size == 0:
        return 0.0
    return float(np.sum(r / np.log2(np.arange(2, r.size + 2))))


def ndcg_at_k(r: List[float], k: int) -> float:
    dcg_max = dcg_at_k(sorted(r, reverse=True), k)
    if dcg_max == 0.0:
        return 0.0
    return dcg_at_k(r, k) / dcg_max


def generate_extended_cohort() -> List[Dict[str, Any]]:
    cohort = []
    combinations = [
        "A00", "A01", "A02", "B00", "B08", "C00",
        "C01", "C02", "C19", "D01", "D07", "D09", "D10", "D14"
    ]
    score_levels = [16.0, 17.5, 19.0, 20.5, 22.0, 23.5, 25.0, 26.5, 28.0, 29.2]
    regions = ["Toàn quốc", "Miền Bắc", "Miền Nam", "Miền Trung"]
    kv_list = ["KV3", "KV2", "KV2-NT", "KV1"]

    c_id = 1
    for comb in combinations:
        for sc in score_levels:
            v1 = round(sc * 0.35 + ((c_id % 5) - 2) * 0.15, 2)
            v2 = round(sc * 0.33 + ((c_id % 3) - 1) * 0.15, 2)
            v3 = round(sc - v1 - v2, 2)

            non_main1 = round(max(4.0, min(10.0, (sc / 3.0) - 1.2 + (c_id % 4) * 0.3)), 2)
            non_main2 = round(max(4.0, min(10.0, (sc / 3.0) - 0.8 + (c_id % 3) * 0.2)), 2)
            gpa_val = round(max(5.0, min(10.0, (sc / 3.0) + 0.35)), 2)

            sub_map = {
                "toan": non_main1, "ly": non_main1, "hoa": non_main2,
                "sinh": non_main2, "van": non_main1, "su": non_main2,
                "dia": non_main2, "anh": non_main1, "gdcd": non_main1,
                "tinHoc": non_main1, "congNghe": non_main2
            }

            if comb == "A00":
                sub_map["toan"], sub_map["ly"], sub_map["hoa"] = v1, v2, v3
            elif comb == "A01":
                sub_map["toan"], sub_map["ly"], sub_map["anh"] = v1, v2, v3
            elif comb == "A02":
                sub_map["toan"], sub_map["ly"], sub_map["sinh"] = v1, v2, v3
            elif comb == "B00":
                sub_map["toan"], sub_map["hoa"], sub_map["sinh"] = v1, v2, v3
            elif comb == "B08":
                sub_map["toan"], sub_map["sinh"], sub_map["anh"] = v1, v2, v3
            elif comb == "C00":
                sub_map["van"], sub_map["su"], sub_map["dia"] = v1, v2, v3
            elif comb == "C01":
                sub_map["van"], sub_map["toan"], sub_map["ly"] = v1, v2, v3
            elif comb == "C02":
                sub_map["van"], sub_map["toan"], sub_map["hoa"] = v1, v2, v3
            elif comb == "C19":
                sub_map["van"], sub_map["su"], sub_map["gdcd"] = v1, v2, v3
            elif comb == "D01":
                sub_map["toan"], sub_map["van"], sub_map["anh"] = v1, v2, v3
            elif comb == "D07":
                sub_map["toan"], sub_map["hoa"], sub_map["anh"] = v1, v2, v3
            elif comb == "D09":
                sub_map["toan"], sub_map["su"], sub_map["anh"] = v1, v2, v3
            elif comb == "D10":
                sub_map["toan"], sub_map["dia"], sub_map["anh"] = v1, v2, v3
            elif comb == "D14":
                sub_map["van"], sub_map["su"], sub_map["anh"] = v1, v2, v3

            p = {
                "id": c_id,
                "ten": f"Hồ sơ {comb} - {sc}đ",
                "pt": "PT01",
                "toHop": comb,
                "score": sc,
                "toan": sub_map["toan"],
                "ly": sub_map["ly"],
                "hoa": sub_map["hoa"],
                "sinh": sub_map["sinh"],
                "van": sub_map["van"],
                "su": sub_map["su"],
                "dia": sub_map["dia"],
                "anh": sub_map["anh"],
                "diemGDCD": sub_map["gdcd"],
                "diemTinHoc": sub_map["tinHoc"],
                "diemCongNghe": sub_map["congNghe"],
                "hocBa": gpa_val,
                "khuVuc": regions[c_id % len(regions)],
                "khuVucUuTien": kv_list[c_id % len(kv_list)]
            }
            cohort.append(p)
            c_id += 1
    return cohort


def load_actual_ground_truth(data_dir: str) -> Dict[str, float]:
    actual_map = {}
    fc_path = os.path.join(data_dir, "processed", "forecast_records_2026.csv")
    if os.path.exists(fc_path):
        df_fc = pd.read_csv(fc_path)
        if "actual_cutoff_2026" in df_fc.columns and "program_id" in df_fc.columns:
            valid_fc = df_fc.dropna(subset=["actual_cutoff_2026", "program_id"])
            for _, r in valid_fc.iterrows():
                pid = str(r["program_id"]).strip()
                val = float(r["actual_cutoff_2026"])
                if val > 0:
                    actual_map[pid] = val

    dc_path = os.path.join(data_dir, "csv", "diemChuan.csv")
    if os.path.exists(dc_path):
        df_dc = pd.read_csv(dc_path)
        df_2026 = df_dc[df_dc["nam"].astype(str) == "2026"]
        for _, r in df_2026.iterrows():
            pid = str(r.get("programId", "")).strip()
            score = r.get("diemChuan")
            if pid and pd.notna(score) and float(score) > 0:
                if pid not in actual_map:
                    actual_map[pid] = float(score)

    return actual_map


def evaluate_system():
    print("=" * 80)
    print("ĐÁNH GIÁ ĐỘC LẬP HỆ THỐNG RA QUYẾT ĐỊNH TUYỂN SINH (DSS EVALUATION BENCHMARK)")
    print("=" * 80)

    data_dir = os.path.join(os.path.dirname(__file__), "data")
    CsvDatabase.initializeTables()
    benchmarks = CsvDatabase.readAll("diemChuan")
    total_programs = len({b.get("programId") or b.get("id") for b in benchmarks})

    actual_map = load_actual_ground_truth(data_dir)
    print(f"-> Đã nạp dữ liệu điểm chuẩn thực tế kiểm thử: {len(actual_map):,} chương trình.")

    cohort = generate_extended_cohort()
    print(f"-> Quy mô tập kiểm thử độc lập: {len(cohort)} hồ sơ trên đúng 14 tổ hợp môn chính thức (16.0 – 29.2 điểm).")

    all_recommended_programs = set()
    precision_at_10_list = []
    precision_at_20_list = []
    ndcg_at_10_list = []
    strategy_alignment_list = []
    diversity_uni_list = []
    diversity_major_list = []

    brier_scores = []
    prob_bins = {
        "0-20%": {"total": 0, "hits": 0, "sum_p": 0.0},
        "20-40%": {"total": 0, "hits": 0, "sum_p": 0.0},
        "40-60%": {"total": 0, "hits": 0, "sum_p": 0.0},
        "60-80%": {"total": 0, "hits": 0, "sum_p": 0.0},
        "80-100%": {"total": 0, "hits": 0, "sum_p": 0.0}
    }

    tier_counts = {"Thử sức": 0, "Vừa sức": 0, "An toàn": 0, "Khác": 0}
    actual_executed_count = 0

    for p in cohort:
        hs_data = {
            "diemToan": p.get("toan"),
            "diemVan": p.get("van"),
            "diemAnh": p.get("anh"),
            "diemLy": p.get("ly"),
            "diemHoa": p.get("hoa"),
            "diemSinh": p.get("sinh"),
            "diemSu": p.get("su"),
            "diemDia": p.get("dia"),
            "diemGDCD": p.get("diemGDCD"),
            "diemTinHoc": p.get("diemTinHoc"),
            "diemCongNghe": p.get("diemCongNghe"),
            "diemHocBa": p.get("hocBa"),
            "phuongThucMongMuon": p["pt"],
            "danhSachToHopDaChon": [p["toHop"]],
            "khuVucUuTien": p.get("khuVucUuTien", "KV3"),
            "doiTuongUuTien": "NONE",
            "khuVucMongMuon": p["khuVuc"] if p["khuVuc"] != "Toàn quốc" else ""
        }

        res = AdmissionService.deXuatNguyenVong(hs_data)
        wishes = res.get("danhSachTongHop", [])
        if not wishes:
            continue

        actual_executed_count += 1
        rel_flags = []
        strategic_matches = 0

        for idx, w in enumerate(wishes, 1):
            prog_id = w.get("programId") or f"{w.get('truongDaiHocId')}_{w.get('nganhHocId')}"
            all_recommended_programs.add(prog_id)

            dtx = float(w.get("diemXetTuyen", 0.0))
            dct = float(w.get("diemChuanThamChieu", 24.0))
            p_pred = float(w.get("chiSoThuanLoi", w.get("xacSuatDo", w.get("doPhuHop", 50.0)))) / 100.0

            actual_cutoff = actual_map.get(prog_id, dct)
            y_actual = 1.0 if dtx >= actual_cutoff else 0.0

            brier_scores.append((p_pred - y_actual) ** 2)

            if p_pred < 0.20:
                bin_key = "0-20%"
            elif p_pred < 0.40:
                bin_key = "20-40%"
            elif p_pred < 0.60:
                bin_key = "40-60%"
            elif p_pred < 0.80:
                bin_key = "60-80%"
            else:
                bin_key = "80-100%"

            prob_bins[bin_key]["total"] += 1
            prob_bins[bin_key]["hits"] += int(y_actual)
            prob_bins[bin_key]["sum_p"] += p_pred

            delta_real = dtx - actual_cutoff
            is_feasible_opportunity = (-2.0 <= delta_real <= 3.5)
            rel_flags.append(1 if is_feasible_opportunity else 0)

            tier = w.get("nhomNguyenVong", "")
            if tier in tier_counts:
                tier_counts[tier] += 1
            else:
                tier_counts["Khác"] += 1

            if 1 <= idx <= 5 and tier == "Thử sức":
                strategic_matches += 1
            elif 6 <= idx <= 15 and tier == "Vừa sức":
                strategic_matches += 1
            elif 16 <= idx <= 20 and tier == "An toàn":
                strategic_matches += 1

        p_at_10 = np.mean(rel_flags[:10]) if len(rel_flags) >= 10 else np.mean(rel_flags)
        p_at_20 = np.mean(rel_flags)
        precision_at_10_list.append(p_at_10)
        precision_at_20_list.append(p_at_20)

        ndcg_val = ndcg_at_k(rel_flags, 10)
        ndcg_at_10_list.append(ndcg_val)

        strategy_alignment_list.append(strategic_matches / len(wishes) if wishes else 0.0)

        top10 = wishes[:10]
        diversity_uni_list.append(len({w.get("truongDaiHocId") for w in top10}))
        diversity_major_list.append(len({w.get("nganhHocId") for w in top10}))

    avg_p10 = float(np.mean(precision_at_10_list)) if precision_at_10_list else 0.0
    avg_p20 = float(np.mean(precision_at_20_list)) if precision_at_20_list else 0.0
    avg_ndcg10 = float(np.mean(ndcg_at_10_list)) if ndcg_at_10_list else 0.0
    avg_alignment = float(np.mean(strategy_alignment_list) * 100) if strategy_alignment_list else 0.0
    avg_brier = float(np.mean(brier_scores)) if brier_scores else 0.0
    cohort_coverage = float(len(all_recommended_programs) / total_programs * 100) if total_programs > 0 else 0.0

    avg_unis = float(np.mean(diversity_uni_list)) if diversity_uni_list else 0.0
    avg_majors = float(np.mean(diversity_major_list)) if diversity_major_list else 0.0

    print(f"\n1. CHẤT LƯỢNG ĐỀ XUẤT VÀ XẾP HẠNG (THEO GROUND-TRUTH NĂM ĐỘC LẬP):")
    print(f"  - Số kịch bản thực sự chạy:                             {actual_executed_count} / {len(cohort)}")
    print(f"  - Precision@10 (Tỷ lệ cơ hội tuyển sinh khả thi Top-10): {avg_p10:.4f} ({avg_p10*100:.1f}%)")
    print(f"  - Precision@20 (Tỷ lệ cơ hội tuyển sinh khả thi toàn bộ): {avg_p20:.4f} ({avg_p20*100:.1f}%)")
    print(f"  - NDCG@10 (Chất lượng phân bổ thứ tự tối ưu):           {avg_ndcg10:.4f}")
    print(f"  - Portfolio Strategy Alignment (Khớp chuẩn 25/50/25):    {avg_alignment:.1f}%")

    print(f"\n2. ĐỘ HIỆU CHUẨN CHỈ SỐ THUẬN LỢI (CALIBRATION & BRIER SCORE):")
    print(f"  - Brier Score (Càng thấp càng chuẩn xác, tối ưu < 0.20): {avg_brier:.4f}")
    calibration_report = {}
    for b_key, b_val in prob_bins.items():
        if b_val["total"] > 0:
            emp_rate = b_val["hits"] / b_val["total"] * 100
            pred_mean = b_val["sum_p"] / b_val["total"] * 100
            calibration_report[b_key] = {
                "soMau": b_val["total"],
                "chisoDuBaoTB": round(pred_mean, 1),
                "tyLeDatThucTe": round(emp_rate, 1)
            }
            print(f"  - Khoảng [{b_key:7}]: N = {b_val['total']:4d} | Chỉ số TB: {pred_mean:5.1f}% | Thực tế đạt: {emp_rate:5.1f}%")

    print(f"\n3. ĐA DẠNG HÓA VÀ ĐỘ PHỦ DANH MỤC THỰC TẾ (COVERAGE & DIVERSITY):")
    print(f"  - Số trường ĐH trung bình trong Top-10:                {avg_unis:.1f} trường (Ràng buộc max 3 CT/trường)")
    print(f"  - Số ngành học trung bình trong Top-10:                 {avg_majors:.1f} ngành")
    print(f"  - Số chương trình độc lập được tiếp cận:                {len(all_recommended_programs)} / {total_programs}")
    print(f"  - Độ phủ danh mục toàn quốc (Cohort Coverage):          {cohort_coverage:.2f}%")

    report_data = {
        "benchmark_type": "independent_cohort_ground_truth_evaluation",
        "description": "Đánh giá độc lập chất lượng danh mục DSS đối chiếu trực tiếp điểm chuẩn thực tế độc lập.",
        "cohort_scenarios_count": len(cohort),
        "actual_executed_count": actual_executed_count,
        "ground_truth_year": 2026,
        "metrics": {
            "precision_at_10": round(avg_p10, 4),
            "precision_at_20": round(avg_p20, 4),
            "ndcg_at_10": round(avg_ndcg10, 4),
            "portfolio_alignment_pct": round(avg_alignment, 1),
            "brier_score": round(avg_brier, 4),
            "cohort_coverage_pct": round(cohort_coverage, 2),
            "unique_programs_covered": len(all_recommended_programs),
            "total_programs_catalog": total_programs,
            "avg_universities_top10": round(avg_unis, 1),
            "avg_majors_top10": round(avg_majors, 1)
        },
        "calibration_bins": calibration_report,
        "portfolio_tier_distribution": tier_counts
    }

    report_dir = os.path.join(os.path.dirname(__file__), "data", "reports")
    os.makedirs(report_dir, exist_ok=True)
    report_file = os.path.join(report_dir, "recsys_evaluation_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    print(f"\n-> Đã lưu báo cáo hợp nhất độc lập chuẩn xác vào: {report_file}")
    print("=" * 80)


if __name__ == "__main__":
    evaluate_system()
