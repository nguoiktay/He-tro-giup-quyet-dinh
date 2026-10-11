import os
import csv
import json
import threading
import pandas as pd
from typing import Dict, List, Optional, Any

CSV_DIR = os.path.join(os.path.dirname(__file__), "data", "csv")
os.makedirs(CSV_DIR, exist_ok=True)

_lock = threading.RLock()
_cache: Dict[str, List[Dict[str, Any]]] = {}


def inferNganhIdFromName(name: str) -> Optional[int]:
    n = str(name).lower()
    if 'công nghệ thông tin' in n or 'cntt' in n or 'tin học' in n: return 1
    if 'khoa học máy tính' in n: return 2
    if 'mạng máy tính' in n or 'truyền thông dữ liệu' in n: return 3
    if 'kỹ thuật phần mềm' in n or 'phần mềm' in n: return 4
    if 'hệ thống thông tin' in n: return 5
    if 'trí tuệ nhân tạo' in n or 'artificial intelligence' in n: return 6
    if 'an toàn thông tin' in n or 'an ninh mạng' in n: return 7
    if 'khoa học dữ liệu' in n or 'data science' in n: return 8
    if 'marketing' in n: return 10
    if 'tài chính' in n or 'ngân hàng' in n: return 11
    if 'kế toán' in n: return 12
    if 'kiểm toán' in n: return 13
    if 'kinh doanh quốc tế' in n: return 14
    if 'thương mại điện tử' in n: return 15
    if 'logistics' in n or 'chuỗi cung ứng' in n: return 16
    if 'cơ điện tử' in n or 'cơ khí' in n: return 17
    if 'điện tử' in n or 'viễn thông' in n or 'kỹ thuật điện' in n: return 18
    if 'tự động hóa' in n or 'điều khiển' in n: return 19
    if 'ô tô' in n or 'động lực' in n: return 20
    if 'hóa học' in n or 'thực phẩm' in n or 'sinh học' in n or 'hóa sinh' in n: return 21
    if 'xây dựng' in n or 'giao thông' in n or 'cầu đường' in n: return 22
    if 'kiến trúc' in n or 'nội thất' in n or 'quy hoạch' in n: return 23
    if 'y khoa' in n or 'y học' in n or 'bác sĩ' in n or 'y đa khoa' in n: return 24
    if 'dược' in n: return 25
    if 'răng' in n: return 26
    if 'điều dưỡng' in n or 'hộ sinh' in n: return 27
    if 'sư phạm toán' in n: return 28
    if 'sư phạm tiếng anh' in n or 'sư phạm anh' in n: return 29
    if 'sư phạm ngữ văn' in n or 'sư phạm văn' in n: return 30
    if 'sư phạm vật lý' in n or 'sư phạm lý' in n: return 31
    if 'luật kinh tế' in n: return 33
    if 'luật' in n: return 32
    if 'kinh tế quốc tế' in n: return 35
    if 'kinh tế' in n: return 34
    if 'tiếng anh' in n or 'ngôn ngữ anh' in n: return 36
    if 'tiếng trung' in n or 'ngôn ngữ trung' in n: return 37
    if 'tiếng hàn' in n or 'ngôn ngữ hàn' in n: return 39
    if 'tiếng nhật' in n or 'ngôn ngữ nhật' in n: return 43
    if 'báo chí' in n: return 40
    if 'truyền thông' in n or 'quan hệ công chúng' in n: return 41
    if 'mầm non' in n: return 42
    if 'quản trị' in n or 'kinh doanh' in n or 'khách sạn' in n or 'du lịch' in n or 'nhân lực' in n: return 9
    return None

class CsvDatabase:

    FILE_PATHS = {
        "toHopMon": os.path.join(CSV_DIR, "toHopMon.csv"),
        "phuongThucXetTuyen": os.path.join(CSV_DIR, "phuongThucXetTuyen.csv"),
        "truongDaiHoc": os.path.join(CSV_DIR, "truongDaiHoc.csv"),
        "nganhHoc": os.path.join(CSV_DIR, "nganhHoc.csv"),
        "diemChuan": os.path.join(CSV_DIR, "diemChuan.csv"),
        "nguoiDung": os.path.join(CSV_DIR, "nguoiDung.csv"),
        "hoSoHocSinh": os.path.join(CSV_DIR, "hoSoHocSinh.csv"),
        "goiYNguyenVong": os.path.join(CSV_DIR, "goiYNguyenVong.csv"),
        "hocPhi": os.path.join(CSV_DIR, "hocPhi.csv")
    }

    COLUMNS = {
        "toHopMon": ["id", "maToHop", "tenToHop", "mon1", "mon2", "mon3"],
        "phuongThucXetTuyen": ["id", "maPhuongThuc", "tenPhuongThuc", "moTa"],
        "truongDaiHoc": ["id", "maTruong", "tenTruong", "diaChi", "khuVuc", "loaiTruong", "trangWeb"],
        "nganhHoc": ["id", "maNganh", "tenNganh", "nhomNganh", "moTa"],
        "diemChuan": ["id", "truongDaiHocId", "nganhHocId", "toHopMonId", "phuongThucXetTuyenId", "nam", "diemChuan", "chiTieu", "programId", "tenChuongTrinh", "admissionCaseId", "scoreScale", "calculationRuleId"],
        "nguoiDung": ["id", "tenDangNhap", "matKhau", "hoTen", "email", "soDienThoai", "vaiTro", "ngayTao"],
        "hoSoHocSinh": [
            "id", "nguoiDungId", "diemToan", "diemVan", "diemAnh", "diemLy", "diemHoa", 
            "diemSinh", "diemSu", "diemDia", "diemGDCD", "diemHocBa", "diemDanhGiaNangLuc", 
            "chungChiQuocTe", "khuVucUuTien", "doiTuongUuTien", "phuongThucMongMuon", "ngayCapNhat"
        ],
        "goiYNguyenVong": [
            "id", "hoSoHocSinhId", "truongDaiHocId", "nganhHocId", "toHopMonId", "phuongThucXetTuyenId", 
            "diemXetTuyen", "diemChuanThamChieu", "doPhuHop", "mucDoPhuHop", "mucDoRuiRo", "thuTuUuTien", "ngayTao",
            "programId", "tenChuongTrinh", "admissionCaseId"
        ],
        "hocPhi": [
            "id", "programId", "truongDaiHocId", "maTruong", "tenTruong", "tenChuongTrinh",
            "namApDung", "khoaApDung", "hocPhiToiThieu", "hocPhiToiDa", "donViTinh",
            "loaiHocPhi", "trangThaiHocPhi", "hocPhiDisplay", "nguonMinhChung", "urlNguon", "ghiChu"
        ]
    }

    @classmethod
    def initializeTables(cls):
        with _lock:
            if not os.path.exists(cls.FILE_PATHS["toHopMon"]):
                initialCombinations = [
                    {"id": 1, "maToHop": "A00", "tenToHop": "Toán, Lý, Hóa", "mon1": "diemToan", "mon2": "diemLy", "mon3": "diemHoa"},
                    {"id": 2, "maToHop": "A01", "tenToHop": "Toán, Lý, Anh", "mon1": "diemToan", "mon2": "diemLy", "mon3": "diemAnh"},
                    {"id": 3, "maToHop": "A02", "tenToHop": "Toán, Lý, Sinh", "mon1": "diemToan", "mon2": "diemLy", "mon3": "diemSinh"},
                    {"id": 4, "maToHop": "B00", "tenToHop": "Toán, Hóa, Sinh", "mon1": "diemToan", "mon2": "diemHoa", "mon3": "diemSinh"},
                    {"id": 5, "maToHop": "B08", "tenToHop": "Toán, Sinh, Anh", "mon1": "diemToan", "mon2": "diemSinh", "mon3": "diemAnh"},
                    {"id": 6, "maToHop": "C00", "tenToHop": "Văn, Sử, Địa", "mon1": "diemVan", "mon2": "diemSu", "mon3": "diemDia"},
                    {"id": 7, "maToHop": "C01", "tenToHop": "Văn, Toán, Lý", "mon1": "diemVan", "mon2": "diemToan", "mon3": "diemLy"},
                    {"id": 8, "maToHop": "C02", "tenToHop": "Văn, Toán, Hóa", "mon1": "diemVan", "mon2": "diemToan", "mon3": "diemHoa"},
                    {"id": 9, "maToHop": "C19", "tenToHop": "Văn, Sử, GDCD", "mon1": "diemVan", "mon2": "diemSu", "mon3": "diemGDCD"},
                    {"id": 10, "maToHop": "D01", "tenToHop": "Toán, Văn, Anh", "mon1": "diemToan", "mon2": "diemVan", "mon3": "diemAnh"},
                    {"id": 11, "maToHop": "D07", "tenToHop": "Toán, Hóa, Anh", "mon1": "diemToan", "mon2": "diemHoa", "mon3": "diemAnh"},
                    {"id": 12, "maToHop": "D09", "tenToHop": "Toán, Sử, Anh", "mon1": "diemToan", "mon2": "diemSu", "mon3": "diemAnh"},
                    {"id": 13, "maToHop": "D10", "tenToHop": "Toán, Địa, Anh", "mon1": "diemToan", "mon2": "diemDia", "mon3": "diemAnh"},
                    {"id": 14, "maToHop": "D14", "tenToHop": "Văn, Sử, Anh", "mon1": "diemVan", "mon2": "diemSu", "mon3": "diemAnh"}
                ]
                pd.DataFrame(initialCombinations)[cls.COLUMNS["toHopMon"]].to_csv(cls.FILE_PATHS["toHopMon"], index=False, encoding="utf-8-sig")

            if not os.path.exists(cls.FILE_PATHS["phuongThucXetTuyen"]):
                initialMethods = [
                    {"id": 1, "maPhuongThuc": "PT01", "tenPhuongThuc": "Xét theo điểm thi tốt nghiệp THPT", "moTa": "Xét tuyển dựa trên tổng điểm thi 3 môn trong kỳ thi tốt nghiệp THPT theo tổ hợp"},
                    {"id": 2, "maPhuongThuc": "PT02", "tenPhuongThuc": "Xét theo học bạ THPT (3 năm hoặc 5-6 học kỳ)", "moTa": "Xét tuyển kết quả học tập bậc THPT theo từng tổ hợp hoặc điểm trung bình chung GPA"},
                    {"id": 3, "maPhuongThuc": "PT03", "tenPhuongThuc": "Xét theo điểm thi Đánh giá năng lực (ĐHQG Hà Nội / ĐHQG TP.HCM)", "moTa": "Xét tuyển điểm kỳ thi HSA (ĐHQG Hà Nội) hoặc APT (ĐHQG TP.HCM) quy đổi"},
                    {"id": 4, "maPhuongThuc": "PT04", "tenPhuongThuc": "Xét theo điểm thi Đánh giá tư duy (Đại học Bách Khoa Hà Nội)", "moTa": "Xét tuyển dựa trên kết quả kỳ thi Đánh giá tư duy TSA thang điểm 100"},
                    {"id": 5, "maPhuongThuc": "PT05", "tenPhuongThuc": "Xét tuyển thẳng / ưu tiên xét tuyển theo quy chế Bộ GD&ĐT", "moTa": "Dành cho học sinh đạt giải quốc gia, quốc tế, học sinh trường chuyên"},
                    {"id": 6, "maPhuongThuc": "PT06", "tenPhuongThuc": "Xét tuyển kết hợp chứng chỉ quốc tế (IELTS, SAT, ACT...) với học bạ hoặc điểm thi", "moTa": "Quy đổi chứng chỉ ngoại ngữ kết hợp điểm học bạ hoặc môn thi THPT"},
                    {"id": 7, "maPhuongThuc": "PT07", "tenPhuongThuc": "Xét tuyển theo phương thức riêng của trường", "moTa": "Bài thi năng khiếu, phỏng vấn, hồ sơ năng lực theo đề án riêng từng trường"}
                ]
                pd.DataFrame(initialMethods)[cls.COLUMNS["phuongThucXetTuyen"]].to_csv(cls.FILE_PATHS["phuongThucXetTuyen"], index=False, encoding="utf-8-sig")

            if not os.path.exists(cls.FILE_PATHS["truongDaiHoc"]):
                srcUniPath = os.path.join(os.path.dirname(__file__), "data", "metadata", "universities_master.csv")
                if os.path.exists(srcUniPath):
                    dfSrc = pd.read_csv(srcUniPath)
                    dfUni = pd.DataFrame({
                        "id": range(1, len(dfSrc) + 1),
                        "maTruong": dfSrc["university_code"],
                        "tenTruong": dfSrc["university_name"],
                        "diaChi": dfSrc["province"].fillna("Hà Nội"),
                        "khuVuc": dfSrc["region"].fillna("Miền Bắc"),
                        "loaiTruong": dfSrc["university_type"].fillna("Công lập"),
                        "trangWeb": dfSrc["official_website"].fillna("")
                    })
                    dfUni[cls.COLUMNS["truongDaiHoc"]].to_csv(cls.FILE_PATHS["truongDaiHoc"], index=False, encoding="utf-8-sig")
                else:
                    demoUnis = [
                        {"id": 1, "maTruong": "BKA", "tenTruong": "Đại học Bách khoa Hà Nội", "diaChi": "Hà Nội", "khuVuc": "Miền Bắc", "loaiTruong": "Công lập", "trangWeb": "https://hust.edu.vn"},
                        {"id": 2, "maTruong": "QHI", "tenTruong": "Trường ĐH Công nghệ - ĐHQGHN", "diaChi": "Hà Nội", "khuVuc": "Miền Bắc", "loaiTruong": "Công lập", "trangWeb": "https://uet.vnu.edu.vn"},
                        {"id": 3, "maTruong": "KHA", "tenTruong": "Trường Đại học Kinh tế Quốc dân", "diaChi": "Hà Nội", "khuVuc": "Miền Bắc", "loaiTruong": "Công lập", "trangWeb": "https://neu.edu.vn"}
                    ]
                    pd.DataFrame(demoUnis)[cls.COLUMNS["truongDaiHoc"]].to_csv(cls.FILE_PATHS["truongDaiHoc"], index=False, encoding="utf-8-sig")

            if not os.path.exists(cls.FILE_PATHS["nganhHoc"]):
                srcPrgPath = os.path.join(os.path.dirname(__file__), "data", "metadata", "programs_master.csv")
                if os.path.exists(srcPrgPath):
                    dfSrcP = pd.read_csv(srcPrgPath)
                    dfNganh = pd.DataFrame({
                        "id": range(1, len(dfSrcP) + 1),
                        "maNganh": dfSrcP["program_code"].astype(str),
                        "tenNganh": dfSrcP["program_name"],
                        "nhomNganh": dfSrcP["field_name"].fillna("Khác"),
                        "moTa": dfSrcP["degree_level"].fillna("Đại học chính quy")
                    })
                    dfNganh[cls.COLUMNS["nganhHoc"]].to_csv(cls.FILE_PATHS["nganhHoc"], index=False, encoding="utf-8-sig")

            if not os.path.exists(cls.FILE_PATHS["diemChuan"]):
                cls._initBenchmarksFromCleanData()

            if not os.path.exists(cls.FILE_PATHS["nguoiDung"]):
                defaultUsers = [
                    {
                        "id": 1,
                        "tenDangNhap": "admin",
                        "matKhau": "ba91268edb819c6f406436b6303606c3d033fbc324ff58684f4d1222b002046f",
                        "hoTen": "Quản Trị Viên Hệ Thống",
                        "email": "admin@dss-admission.edu.vn",
                        "soDienThoai": "0988888888",
                        "vaiTro": "quanTriVien",
                        "ngayTao": "2026-01-01 08:00:00"
                    },
                    {
                        "id": 2,
                        "tenDangNhap": "hocsinh",
                        "matKhau": "8f92002e71697ca70c59967f90431e8036517f1caaf476140de786fbf45090c1",
                        "hoTen": "Nguyễn Văn Thí Sinh",
                        "email": "thisinh@gmail.com",
                        "soDienThoai": "0912345678",
                        "vaiTro": "hocSinh",
                        "ngayTao": "2026-01-01 08:00:00"
                    }
                ]
                pd.DataFrame(defaultUsers)[cls.COLUMNS["nguoiDung"]].to_csv(cls.FILE_PATHS["nguoiDung"], index=False, encoding="utf-8-sig")

            if not os.path.exists(cls.FILE_PATHS["hoSoHocSinh"]):
                defaultProfile = [
                    {
                        "id": 1,
                        "nguoiDungId": 2,
                        "diemToan": 8.8, "diemVan": 7.5, "diemAnh": 8.5,
                        "diemLy": 8.2, "diemHoa": 8.0, "diemSinh": 6.5,
                        "diemSu": 7.0, "diemDia": 7.0, "diemGDCD": 8.5,
                        "diemHocBa": 8.5, "diemDanhGiaNangLuc": 880.0,
                        "chungChiQuocTe": "IELTS 6.5",
                        "khuVucUuTien": "KV1", "doiTuongUuTien": "NONE",
                        "phuongThucMongMuon": "PT01,PT02,PT03",
                        "ngayCapNhat": "2026-01-01 08:00:00"
                    }
                ]
                pd.DataFrame(defaultProfile)[cls.COLUMNS["hoSoHocSinh"]].to_csv(cls.FILE_PATHS["hoSoHocSinh"], index=False, encoding="utf-8-sig")

            if not os.path.exists(cls.FILE_PATHS["goiYNguyenVong"]):
                pd.DataFrame(columns=cls.COLUMNS["goiYNguyenVong"]).to_csv(cls.FILE_PATHS["goiYNguyenVong"], index=False, encoding="utf-8-sig")

    @classmethod
    def _initBenchmarksFromCleanData(cls):
        dfUni = pd.read_csv(cls.FILE_PATHS["truongDaiHoc"])
        dfNganh = pd.read_csv(cls.FILE_PATHS["nganhHoc"])
        dfToHop = pd.read_csv(cls.FILE_PATHS["toHopMon"])

        uniByCode = dict(zip(dfUni["maTruong"].astype(str), dfUni["id"]))
        nganhByMa = dict(zip(dfNganh["maNganh"].astype(str), dfNganh["id"]))
        unknownNganhId = nganhByMa.get("UNKNOWN", len(dfNganh))
        toHopMap = dict(zip(dfToHop["maToHop"].astype(str), dfToHop["id"]))

        upPath = os.path.join(os.path.dirname(__file__), "data", "metadata", "university_programs.csv")
        programToMajor = {}
        if os.path.exists(upPath):
            dfUp = pd.read_csv(upPath)
            for _, row in dfUp.iterrows():
                pid = str(row["program_id"]).strip()
                mid = str(row["major_id"]).replace("MAJ_", "").strip()
                programToMajor[pid] = mid

        seenKeys = set()
        records = []
        recId = 1

        thptPath = os.path.join(os.path.dirname(__file__), "data", "processed", "forecast_records_2026.csv")
        if os.path.exists(thptPath):
            fcDf = pd.read_csv(thptPath)
            thptDf = fcDf[fcDf["method_code"].str.upper() == "THPT"]
            for _, r in thptDf.iterrows():
                uCode = str(r.get("university_code", "")).strip()
                uId = uniByCode.get(uCode)
                if not uId:
                    continue
                programId = str(r.get("program_id", "")).strip()
                programName = str(r.get("program_name", "")).strip()
                caseId = str(r.get("admission_case_id", "")).strip()
                scale = str(r.get("score_scale", "SCALE_30")).strip()
                ruleId = str(r.get("calculation_rule_id", "RULE_THPT_STD_30")).strip()

                majorCode = programToMajor.get(programId, "UNKNOWN")
                nganhId = nganhByMa.get(majorCode, unknownNganhId)
                if nganhId == unknownNganhId and programName:
                    inferred = inferNganhIdFromName(programName)
                    if inferred:
                        nganhId = inferred

                score2025 = r.get("historical_cutoff_2025")
                if pd.isna(score2025) or float(score2025) <= 0:
                    score2025 = r.get("predicted_cutoff")
                if pd.isna(score2025) or float(score2025) <= 0:
                    continue
                scoreVal = round(float(score2025), 2)

                combRaw = str(r.get("subject_combination", "")).replace(",", ";")
                combTokens = [c.strip() for c in combRaw.split(";") if c.strip()]
                for cToken in combTokens:
                    tId = toHopMap.get(cToken)
                    if not tId:
                        continue
                    key = (int(uId), programId or int(nganhId), caseId, int(tId), 1, 2025)
                    if key in seenKeys:
                        continue
                    seenKeys.add(key)
                    records.append({
                        "id": recId,
                        "truongDaiHocId": int(uId),
                        "nganhHocId": int(nganhId),
                        "toHopMonId": int(tId),
                        "phuongThucXetTuyenId": 1,
                        "nam": 2025,
                        "diemChuan": scoreVal,
                        "chiTieu": 100,
                        "programId": programId,
                        "tenChuongTrinh": programName,
                        "admissionCaseId": caseId,
                        "scoreScale": scale,
                        "calculationRuleId": ruleId
                    })
                    recId += 1

        catalogPath = os.path.join(os.path.dirname(__file__), "data", "processed", "recommendation_catalog.csv")
        if os.path.exists(catalogPath):
            catDf = pd.read_csv(catalogPath)
            catThpt = catDf[catDf["method_code"].str.upper() == "THPT"]
            for _, r in catThpt.iterrows():
                uCode = str(r.get("university_code", "")).strip()
                uId = uniByCode.get(uCode)
                if not uId:
                    continue
                programId = str(r.get("program_id", "")).strip()
                programName = str(r.get("program_name", "")).strip()
                caseId = str(r.get("admission_code", "")).strip()
                scale = str(r.get("score_scale", "SCALE_30")).strip()
                ruleId = str(r.get("calculation_rule_id", "RULE_THPT_STD_30")).strip()

                majorCode = str(r.get("major_id", "")).replace("MAJ_", "").strip()
                nganhId = nganhByMa.get(majorCode, unknownNganhId)
                if nganhId == unknownNganhId and programName:
                    inferred = inferNganhIdFromName(programName)
                    if inferred:
                        nganhId = inferred

                bScore = r.get("latest_cutoff_score")
                if pd.isna(bScore) or float(bScore) <= 0:
                    continue
                scoreVal = round(float(bScore), 2)
                yearVal = int(r.get("latest_cutoff_year", 2025))

                combRaw = str(r.get("subject_combination", "")).replace(",", ";")
                combTokens = [c.strip() for c in combRaw.split(";") if c.strip()]
                for cToken in combTokens:
                    tId = toHopMap.get(cToken)
                    if not tId:
                        continue
                    key = (int(uId), programId or int(nganhId), caseId, int(tId), 1, yearVal)
                    if key in seenKeys:
                        continue
                    seenKeys.add(key)
                    records.append({
                        "id": recId,
                        "truongDaiHocId": int(uId),
                        "nganhHocId": int(nganhId),
                        "toHopMonId": int(tId),
                        "phuongThucXetTuyenId": 1,
                        "nam": yearVal,
                        "diemChuan": scoreVal,
                        "chiTieu": 100,
                        "programId": programId,
                        "tenChuongTrinh": programName,
                        "admissionCaseId": caseId,
                        "scoreScale": scale,
                        "calculationRuleId": ruleId
                    })
                    recId += 1

        hbPath = os.path.join(os.path.dirname(__file__), "data", "processed", "hoc_ba_cutoff_clean_final.csv")
        if os.path.exists(hbPath):
            hbDf = pd.read_csv(hbPath)
            hbDf = hbDf[hbDf["verification_status"] == "VERIFIED"]
            for _, r in hbDf.iterrows():
                uCode = str(r.get("university_code", "")).strip()
                uId = uniByCode.get(uCode)
                if not uId:
                    continue
                majorCode = str(r.get("major_id", "")).replace("MAJ_", "").strip()
                nganhId = nganhByMa.get(majorCode, unknownNganhId)
                programId = str(r.get("program_id", "")).strip()
                programName = str(r.get("program_name", "")).strip()
                caseId = str(r.get("admission_code", "")).strip()
                scale = str(r.get("score_scale", "SCALE_30")).strip()
                ruleId = str(r.get("calculation_rule_id", "RULE_HB_STD_30")).strip()

                if nganhId == unknownNganhId and programName:
                    inferred = inferNganhIdFromName(programName)
                    if inferred:
                        nganhId = inferred

                bScore = r.get("benchmark_score")
                if pd.isna(bScore) or float(bScore) <= 0:
                    continue
                scoreVal = round(float(bScore), 2)
                yearVal = int(r.get("year", 2026))

                combRaw = str(r.get("subject_combination", "")).replace(",", ";")
                combTokens = [c.strip() for c in combRaw.split(";") if c.strip()]
                for cToken in combTokens:
                    tId = toHopMap.get(cToken)
                    if not tId:
                        continue
                    key = (int(uId), programId or int(nganhId), caseId, int(tId), 2, yearVal)
                    if key in seenKeys:
                        continue
                    seenKeys.add(key)
                    records.append({
                        "id": recId,
                        "truongDaiHocId": int(uId),
                        "nganhHocId": int(nganhId),
                        "toHopMonId": int(tId),
                        "phuongThucXetTuyenId": 2,
                        "nam": yearVal,
                        "diemChuan": scoreVal,
                        "chiTieu": 100,
                        "programId": programId,
                        "tenChuongTrinh": programName,
                        "admissionCaseId": caseId,
                        "scoreScale": scale,
                        "calculationRuleId": ruleId
                    })
                    recId += 1

        if not records:
            records = [
                {"id": 1, "truongDaiHocId": 1, "nganhHocId": 1, "toHopMonId": 1, "phuongThucXetTuyenId": 1, "nam": 2025, "diemChuan": 28.5, "chiTieu": 120, "programId": "", "tenChuongTrinh": "", "admissionCaseId": "", "scoreScale": "SCALE_30", "calculationRuleId": "RULE_THPT_STD_30"},
                {"id": 2, "truongDaiHocId": 1, "nganhHocId": 1, "toHopMonId": 2, "phuongThucXetTuyenId": 1, "nam": 2025, "diemChuan": 28.2, "chiTieu": 120, "programId": "", "tenChuongTrinh": "", "admissionCaseId": "", "scoreScale": "SCALE_30", "calculationRuleId": "RULE_THPT_STD_30"},
                {"id": 3, "truongDaiHocId": 1, "nganhHocId": 1, "toHopMonId": 1, "phuongThucXetTuyenId": 2, "nam": 2025, "diemChuan": 29.0, "chiTieu": 50, "programId": "", "tenChuongTrinh": "", "admissionCaseId": "", "scoreScale": "SCALE_30", "calculationRuleId": "RULE_HB_STD_30"}
            ]

        dfDc = pd.DataFrame(records)[cls.COLUMNS["diemChuan"]]
        dfDc.to_csv(cls.FILE_PATHS["diemChuan"], index=False, encoding="utf-8-sig")

    @classmethod
    def clearCache(cls, tableName: Optional[str] = None):
        with _lock:
            if tableName:
                _cache.pop(tableName, None)
            else:
                _cache.clear()

    @classmethod
    def setDatabaseDirectory(cls, newDir: str):
        with _lock:
            cls.CSV_DIR = newDir
            cls.FILE_PATHS = {
                k: os.path.join(newDir, f"{k}.csv") for k in cls.COLUMNS
            }
            cls.clearCache()

    @classmethod
    def readAll(cls, tableName: str) -> List[Dict[str, Any]]:
        with _lock:
            if tableName in _cache:
                return _cache[tableName]
            filePath = cls.FILE_PATHS.get(tableName)
            if not filePath or not os.path.exists(filePath):
                return []
            df = pd.read_csv(filePath, dtype={"soDienThoai": str, "maTruong": str, "maNganh": str, "maToHop": str, "maPhuongThuc": str, "programId": str, "admissionCaseId": str})
            records = df.where(pd.notna(df), None).to_dict(orient="records")
            cleaned = []
            for r in records:
                cleanRow = {}
                for k, v in r.items():
                    if pd.isna(v) or v is None:
                        cleanRow[k] = None
                    else:
                        if k == "soDienThoai":
                            sVal = str(v).strip()
                            if sVal.endswith(".0"):
                                sVal = sVal[:-2]
                            if len(sVal) == 9 and not sVal.startswith("0"):
                                sVal = "0" + sVal
                            v = sVal
                        cleanRow[k] = v
                cleaned.append(cleanRow)
            _cache[tableName] = cleaned
            return cleaned

    @classmethod
    def findById(cls, tableName: str, recordId: int) -> Optional[Dict[str, Any]]:
        records = cls.readAll(tableName)
        for r in records:
            if int(r.get("id")) == int(recordId):
                return r
        return None

    @classmethod
    def findWhere(cls, tableName: str, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        records = cls.readAll(tableName)
        matched = []
        for r in records:
            match = True
            for k, v in conditions.items():
                rv = r.get(k)
                if rv is None and v is not None:
                    match = False
                    break
                if rv is not None and v is None:
                    match = False
                    break
                try:
                    if float(rv) == float(v):
                        continue
                except (ValueError, TypeError):
                    pass
                if str(rv).strip() != str(v).strip():
                    match = False
                    break
            if match:
                matched.append(r)
        return matched

    @classmethod
    def insert(cls, tableName: str, data: Dict[str, Any]) -> Dict[str, Any]:
        filePath = cls.FILE_PATHS.get(tableName)
        if not filePath:
            raise ValueError(f"Bảng {tableName} không tồn tại.")

        cols = cls.COLUMNS[tableName]
        with _lock:
            records = []
            if os.path.exists(filePath):
                df = pd.read_csv(filePath)
                records = df.where(pd.notna(df), None).to_dict(orient="records")

            maxId = max([int(r.get("id", 0)) for r in records], default=0)
            data["id"] = maxId + 1

            newRow = {c: data.get(c, None) for c in cols}
            if "soDienThoai" in newRow and newRow["soDienThoai"] is not None:
                pStr = str(newRow["soDienThoai"]).strip()
                if pStr.endswith(".0"):
                    pStr = pStr[:-2]
                if len(pStr) == 9 and not pStr.startswith("0"):
                    pStr = "0" + pStr
                newRow["soDienThoai"] = pStr
            records.append(newRow)

            pd.DataFrame(records)[cols].to_csv(filePath, index=False, encoding="utf-8-sig")
            _cache.pop(tableName, None)
            return newRow

    @classmethod
    def update(cls, tableName: str, recordId: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        filePath = cls.FILE_PATHS.get(tableName)
        if not filePath or not os.path.exists(filePath):
            return None

        cols = cls.COLUMNS[tableName]
        with _lock:
            df = pd.read_csv(filePath)
            records = df.where(pd.notna(df), None).to_dict(orient="records")

            updatedRow = None
            for idx, r in enumerate(records):
                if int(r.get("id")) == int(recordId):
                    for k, v in data.items():
                        if k in cols and k != "id":
                            r[k] = v
                    updatedRow = r
                    records[idx] = r
                    break

            if updatedRow:
                pd.DataFrame(records)[cols].to_csv(filePath, index=False, encoding="utf-8-sig")
                _cache.pop(tableName, None)
            return updatedRow

    @classmethod
    def delete(cls, tableName: str, recordId: int) -> bool:
        filePath = cls.FILE_PATHS.get(tableName)
        if not filePath or not os.path.exists(filePath):
            return False

        cols = cls.COLUMNS[tableName]
        with _lock:
            df = pd.read_csv(filePath)
            records = df.where(pd.notna(df), None).to_dict(orient="records")

            initialLen = len(records)
            records = [r for r in records if int(r.get("id")) != int(recordId)]

            if len(records) < initialLen:
                pd.DataFrame(records)[cols].to_csv(filePath, index=False, encoding="utf-8-sig")
                _cache.pop(tableName, None)
                return True
            return False

CsvDatabase.initializeTables()
