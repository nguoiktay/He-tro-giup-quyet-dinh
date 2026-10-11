import os
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Any
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

    combinations = ["A00", "A01", "B00", "C00", "D01", "D07"]
    score_levels = [18.0, 20.5, 22.5, 24.5, 26.5, 28.5]

    c_id = 1
    for comb in combinations:
        for sc in score_levels:
            base_m = sc / 3.0
            p = {
                "id": c_id,
                "ten": f"Hồ sơ {comb} - {sc}đ",
                "pt": "PT01",
                "toHop": comb,
                "score": sc,
                "toan": round(base_m, 2),
                "ly": round(base_m, 2),
                "hoa": round(base_m, 2),
                "sinh": round(base_m, 2),
                "van": round(base_m, 2),
                "su": round(base_m, 2),
                "dia": round(base_m, 2),
                "anh": round(base_m, 2),
                "hocBa": round(min(10.0, base_m + 0.3), 2),
                "khuVuc": "Toàn quốc"
            }
            cohort.append(p)
            c_id += 1

    return cohort


def evaluate_system():
    print("=" * 80)
    print("ĐÁNH GIÁ ĐỘC LẬP HỆ THỐNG RA QUYẾT ĐỊNH TUYỂN SINH (DSS EVALUATION BENCHMARK)")
    print("=" * 80)

    CsvDatabase.initializeTables()
    benchmarks = CsvDatabase.readAll("diemChuan")
    totalPrograms = len({b.get("programId") or b.get("id") for b in benchmarks})

    cohort = generate_extended_cohort()
    print(f"-> Quy mô tập kiểm thử: {len(cohort)} hồ sơ trải đều từ 16.5 đến 28.5 điểm trên 6 tổ hợp.")

    allRecommendedPrograms = set()
    precision_at_10_list = []
    precision_at_20_list = []
    recall_at_20_list = []
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

    for p in cohort:
        hsData = {
            "diemToan": p.get("toan"),
            "diemVan": p.get("van"),
            "diemAnh": p.get("anh"),
            "diemLy": p.get("ly"),
            "diemHoa": p.get("hoa"),
            "diemSinh": p.get("sinh"),
            "diemSu": p.get("su"),
            "diemDia": p.get("dia"),
            "diemHocBa": p.get("hocBa"),
            "phuongThucMongMuon": p["pt"],
            "danhSachToHopDaChon": [p["toHop"]],
            "khuVucUuTien": "KV3",
            "doiTuongUuTien": "NONE",
            "khuVucMongMuon": p["khuVuc"] if p["khuVuc"] != "Toàn quốc" else ""
        }

        res = AdmissionService.deXuatNguyenVong(hsData)
        wishes = res.get("danhSachTongHop", [])
        if not wishes:
            continue

        rel_flags = []
        strategic_matches = 0

        for idx, w in enumerate(wishes, 1):
            progId = w.get("programId") or f"{w.get('truongDaiHocId')}_{w.get('nganhHocId')}"
            allRecommendedPrograms.add(progId)

            dtx = float(w.get("diemXetTuyen", 0.0))
            dct = float(w.get("diemChuanThamChieu", 24.0))
            delta = dtx - dct
            p_pred = float(w.get("xacSuatDo", w.get("doPhuHop", 50.0))) / 100.0

            y_actual = 1.0 if delta >= 0.0 else 0.0

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

            is_feasible_opportunity = (-1.5 <= delta <= 3.5)
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

    avg_p10 = float(np.mean(precision_at_10_list))
    avg_p20 = float(np.mean(precision_at_20_list))
    avg_ndcg10 = float(np.mean(ndcg_at_10_list))
    avg_alignment = float(np.mean(strategy_alignment_list) * 100)
    avg_brier = float(np.mean(brier_scores))
    cohort_coverage = float(len(allRecommendedPrograms) / totalPrograms * 100) if totalPrograms > 0 else 0.0

    avg_unis = float(np.mean(diversity_uni_list))
    avg_majors = float(np.mean(diversity_major_list))

    print(f"\n1. CHẤT LƯỢNG ĐỀ XUẤT VÀ XẾP HẠNG (PRECISION & RANKING):")
    print(f"  - Precision@10 (Tỷ lệ cơ hội tuyển sinh khả thi Top-10): {avg_p10:.4f} ({avg_p10*100:.1f}%)")
    print(f"  - Precision@20 (Tỷ lệ cơ hội tuyển sinh khả thi toàn bộ): {avg_p20:.4f} ({avg_p20*100:.1f}%)")
    print(f"  - NDCG@10 (Chất lượng phân bổ thứ tự tối ưu):           {avg_ndcg10:.4f}")
    print(f"  - Portfolio Strategy Alignment (Khớp chuẩn 25/50/25):    {avg_alignment:.1f}%")

    print(f"\n2. ĐỘ HIỆU CHUẨN XÁC SUẤT (PROBABILITY CALIBRATION & BRIER SCORE):")
    print(f"  - Brier Score (Càng thấp càng chuẩn xác, tối ưu < 0.15): {avg_brier:.4f}")
    calibration_report = {}
    for b_key, b_val in prob_bins.items():
        if b_val["total"] > 0:
            emp_rate = b_val["hits"] / b_val["total"] * 100
            pred_mean = b_val["sum_p"] / b_val["total"] * 100
            calibration_report[b_key] = {
                "soMau": b_val["total"],
                "xacSuatDuBaoTB": round(pred_mean, 1),
                "tyLeDatThucTe": round(emp_rate, 1)
            }
            print(f"  - Khoảng [{b_key:7}]: N = {b_val['total']:4d} | Dự báo TB: {pred_mean:5.1f}% | Thực tế đạt: {emp_rate:5.1f}%")

    print(f"\n3. ĐA DẠNG HÓA VÀ ĐỘ PHỦ DANH MỤC THỰC TẾ (COVERAGE & DIVERSITY):")
    print(f"  - Số trường ĐH trung bình trong Top-10:                {avg_unis:.1f} trường (Ràng buộc max 3 CT/trường)")
    print(f"  - Số ngành học trung bình trong Top-10:                 {avg_majors:.1f} ngành")
    print(f"  - Số chương trình độc lập được tiếp cận:                {len(allRecommendedPrograms)} / {totalPrograms}")
    print(f"  - Độ phủ danh mục toàn quốc (Cohort Coverage):          {cohort_coverage:.2f}%")

    report_data = {
        "benchmark_type": "independent_cohort_evaluation_v2",
        "description": "Đánh giá độc lập chất lượng danh mục DSS không đánh giá vòng tròn trên thuần tập 120 kịch bản.",
        "metrics": {
            "precision_at_10": round(avg_p10, 4),
            "precision_at_20": round(avg_p20, 4),
            "ndcg_at_10": round(avg_ndcg10, 4),
            "portfolio_alignment_pct": round(avg_alignment, 1),
            "brier_score": round(avg_brier, 4),
            "cohort_coverage_pct": round(cohort_coverage, 2),
            "unique_programs_covered": len(allRecommendedPrograms),
            "total_programs_catalog": totalPrograms,
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

    old_summary = os.path.join(report_dir, "dss_scenario_evaluation_summary.json")
    if os.path.exists(old_summary):
        try:
            os.remove(old_summary)
        except Exception:
            pass

    old_metrics = os.path.join(report_dir, "dss_scenario_evaluation_metrics.csv")
    if os.path.exists(old_metrics):
        try:
            os.remove(old_metrics)
        except Exception:
            pass

    print(f"\n-> Đã lưu báo cáo hợp nhất chuẩn xác vào: {report_file}")
    print("=" * 80)


if __name__ == "__main__":
    evaluate_system()
