import os
import threading
from typing import Dict, List, Optional, Any
import pandas as pd

import config

CSV_DIR = os.path.join(os.path.dirname(__file__), "data", "csv")
os.makedirs(CSV_DIR, exist_ok=True)

_lock = threading.RLock()
_cache: Dict[str, List[Dict[str, Any]]] = {}

STRING_DTYPES: Dict[str, str] = {
    "soDienThoai": "str",
    "maTruong": "str",
    "maNganh": "str",
    "maToHop": "str",
    "maPhuongThuc": "str",
    "programId": "str",
    "admissionCaseId": "str",
    "tenDangNhap": "str",
    "email": "str",
    "calculationRuleId": "str",
    "scoreScale": "str",
    "chungChiQuocTe": "str",
}

STRING_MATCH_FIELDS = {
    "tenDangNhap", "email", "soDienThoai", "maTruong", "maNganh",
    "maToHop", "maPhuongThuc", "programId", "admissionCaseId",
    "vaiTro", "khuVuc", "loaiTruong", "khuVucUuTien", "doiTuongUuTien",
    "khuVucMongMuon", "nganhMongMuon", "calculationRuleId", "scoreScale"
}


def infer_nganh_id_from_name(name: str) -> Optional[int]:
    n = str(name).lower()
    if 'quản lý đất đai' in n: return None
    if 'công nghệ thông tin' in n or 'cntt' in n or 'tin học' in n or 'kỹ thuật máy tính' in n or 'máy tính' in n: return 1
    if 'khoa học máy tính' in n: return 2
    if 'mạng máy tính' in n or 'truyền thông dữ liệu' in n: return 3
    if 'kỹ thuật phần mềm' in n or 'phần mềm' in n: return 4
    if 'hệ thống thông tin' in n: return 5
    if 'trí tuệ nhân tạo' in n or 'artificial intelligence' in n: return 6
    if 'an toàn thông tin' in n or 'an ninh mạng' in n: return 7
    if 'khoa học dữ liệu' in n or 'data science' in n: return 8
    if 'marketing' in n: return 10
    if 'tài chính' in n or 'ngân hàng' in n or 'bảo hiểm' in n or 'hải quan' in n: return 11
    if 'kế toán' in n: return 12
    if 'kiểm toán' in n: return 13
    if 'kinh doanh quốc tế' in n: return 14
    if 'thương mại điện tử' in n: return 15
    if 'logistics' in n or 'chuỗi cung ứng' in n: return 16
    if 'cơ điện tử' in n or 'cơ khí' in n: return 17
    if 'điện tử' in n or 'viễn thông' in n or 'kỹ thuật điện' in n: return 18
    if 'tự động hóa' in n or 'điều khiển' in n: return 19
    if 'ô tô' in n or 'động lực' in n: return 20
    if 'hóa học' in n or 'hoá học' in n or 'thực phẩm' in n or 'sinh học' in n or 'hóa sinh' in n or 'công nghệ sinh học' in n: return 21
    if 'xây dựng' in n or 'giao thông' in n or 'cầu đường' in n or 'kỹ thuật công trình' in n: return 22
    if 'kiến trúc' in n or 'nội thất' in n or 'quy hoạch' in n: return 23
    if 'y khoa' in n or 'y học' in n or 'bác sĩ' in n or 'y đa khoa' in n or 'dự phòng' in n or 'y tế công cộng' in n or 'xét nghiệm' in n or 'dinh dưỡng' in n: return 24
    if 'dược' in n: return 25
    if 'răng' in n: return 26
    if 'điều dưỡng' in n or 'hộ sinh' in n or 'phục hồi chức năng' in n: return 27
    if 'sư phạm toán' in n: return 28
    if 'sư phạm tiếng anh' in n or 'sư phạm anh' in n: return 29
    if 'sư phạm ngữ văn' in n or 'sư phạm văn' in n: return 30
    if 'sư phạm vật lý' in n or 'sư phạm lý' in n: return 31
    if 'sư phạm' in n or 'tiểu học' in n or 'giáo dục' in n: return 28
    if 'luật kinh tế' in n: return 33
    if 'luật' in n: return 32
    if 'kinh tế quốc tế' in n or 'quan hệ quốc tế' in n: return 35
    if 'kinh tế' in n: return 34
    if 'tiếng anh' in n or 'ngôn ngữ anh' in n: return 36
    if 'tiếng trung' in n or 'ngôn ngữ trung' in n: return 37
    if 'tiếng hàn' in n or 'ngôn ngữ hàn' in n: return 39
    if 'tiếng nhật' in n or 'ngôn ngữ nhật' in n: return 43
    if 'báo chí' in n: return 40
    if 'truyền thông' in n or 'quan hệ công chúng' in n or 'đồ họa' in n or 'thiết kế' in n: return 41
    if 'mầm non' in n: return 42
    if 'quản trị' in n or 'kinh doanh' in n or 'khách sạn' in n or 'du lịch' in n or 'nhân lực' in n or 'bất động sản' in n or 'quản lý công nghiệp' in n: return 9
    return None

inferNganhIdFromName = infer_nganh_id_from_name


def _clean_val(val: Any) -> Any:
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    if s.lower() in ("nan", "none", "null"):
        return None
    return val


def _sanitize_record(row: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _clean_val(v) for k, v in row.items()}


def _write_df_atomic(df: pd.DataFrame, file_path: str, cols: Optional[List[str]] = None) -> None:
    target_df = df[cols] if cols is not None else df
    tmp_path = f"{file_path}.tmp.{os.getpid()}_{threading.get_ident()}"
    target_df.to_csv(tmp_path, index=False, encoding="utf-8-sig")
    os.replace(tmp_path, file_path)


class CsvDatabase:
    CSV_DIR = CSV_DIR

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
        "diemChuan": [
            "id", "truongDaiHocId", "nganhHocId", "toHopMonId", "phuongThucXetTuyenId",
            "nam", "diemChuan", "chiTieu", "programId", "tenChuongTrinh",
            "admissionCaseId", "scoreScale", "calculationRuleId"
        ],
        "nguoiDung": ["id", "tenDangNhap", "matKhau", "hoTen", "email", "soDienThoai", "vaiTro", "ngayTao"],
        "hoSoHocSinh": [
            "id", "nguoiDungId", "diemToan", "diemVan", "diemAnh", "diemLy", "diemHoa",
            "diemSinh", "diemSu", "diemDia", "diemGDCD", "diemTinHoc", "diemCongNghe",
            "diemHocBa", "diemDanhGiaNangLuc", "diemDanhGiaTuDuy", "chungChiQuocTe",
            "khuVucUuTien", "doiTuongUuTien", "khuVucMongMuon", "nganhMongMuon",
            "nganSach", "phuongThucMongMuon", "ngayCapNhat"
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
    def initializeTables(cls) -> None:
        with _lock:
            if not os.path.exists(cls.FILE_PATHS["toHopMon"]):
                initial_combs = [
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
                _write_df_atomic(pd.DataFrame(initial_combs), cls.FILE_PATHS["toHopMon"], cls.COLUMNS["toHopMon"])

            if not os.path.exists(cls.FILE_PATHS["phuongThucXetTuyen"]):
                initial_methods = [
                    {"id": 1, "maPhuongThuc": "PT01", "tenPhuongThuc": "Xét theo điểm thi tốt nghiệp THPT", "moTa": "Xét tuyển dựa trên tổng điểm thi 3 môn trong kỳ thi tốt nghiệp THPT theo tổ hợp"},
                    {"id": 2, "maPhuongThuc": "PT02", "tenPhuongThuc": "Xét theo học bạ THPT (3 năm hoặc 5-6 học kỳ)", "moTa": "Xét tuyển kết quả học tập bậc THPT theo từng tổ hợp hoặc điểm trung bình chung GPA"},
                    {"id": 3, "maPhuongThuc": "PT03", "tenPhuongThuc": "Xét theo điểm thi Đánh giá năng lực (ĐHQG Hà Nội / ĐHQG TP.HCM)", "moTa": "Xét tuyển điểm kỳ thi HSA (ĐHQG Hà Nội) hoặc APT (ĐHQG TP.HCM) quy đổi"},
                    {"id": 4, "maPhuongThuc": "PT04", "tenPhuongThuc": "Xét theo điểm thi Đánh giá tư duy (Đại học Bách Khoa Hà Nội)", "moTa": "Xét tuyển dựa trên kết quả kỳ thi Đánh giá tư duy TSA thang điểm 100"},
                    {"id": 5, "maPhuongThuc": "PT05", "tenPhuongThuc": "Xét tuyển thẳng / ưu tiên xét tuyển theo quy chế Bộ GD&ĐT", "moTa": "Dành cho học sinh đạt giải quốc gia, quốc tế, học sinh trường chuyên"},
                    {"id": 6, "maPhuongThuc": "PT06", "tenPhuongThuc": "Xét tuyển kết hợp chứng chỉ quốc tế (IELTS, SAT, ACT...) với học bạ hoặc điểm thi", "moTa": "Quy đổi chứng chỉ ngoại ngữ kết hợp điểm học bạ hoặc môn thi THPT"},
                    {"id": 7, "maPhuongThuc": "PT07", "tenPhuongThuc": "Xét tuyển theo phương thức riêng của trường", "moTa": "Bài thi năng khiếu, phỏng vấn, hồ sơ năng lực theo đề án riêng từng trường"}
                ]
                _write_df_atomic(pd.DataFrame(initial_methods), cls.FILE_PATHS["phuongThucXetTuyen"], cls.COLUMNS["phuongThucXetTuyen"])

            if not os.path.exists(cls.FILE_PATHS["truongDaiHoc"]):
                src_uni = os.path.join(os.path.dirname(__file__), "data", "metadata", "universities_master.csv")
                if os.path.exists(src_uni):
                    df_src = pd.read_csv(src_uni)
                    df_u = pd.DataFrame({
                        "id": range(1, len(df_src) + 1),
                        "maTruong": df_src["university_code"],
                        "tenTruong": df_src["university_name"],
                        "diaChi": df_src["province"].fillna("Hà Nội"),
                        "khuVuc": df_src["region"].fillna("Miền Bắc"),
                        "loaiTruong": df_src["university_type"].fillna("Công lập"),
                        "trangWeb": df_src["official_website"].fillna("")
                    })
                    _write_df_atomic(df_u, cls.FILE_PATHS["truongDaiHoc"], cls.COLUMNS["truongDaiHoc"])

            if not os.path.exists(cls.FILE_PATHS["nganhHoc"]):
                src_prg = os.path.join(os.path.dirname(__file__), "data", "metadata", "programs_master.csv")
                if os.path.exists(src_prg):
                    df_p = pd.read_csv(src_prg)
                    df_n = pd.DataFrame({
                        "id": range(1, len(df_p) + 1),
                        "maNganh": df_p["program_code"].astype(str),
                        "tenNganh": df_p["program_name"],
                        "nhomNganh": df_p["field_name"].fillna("Khác"),
                        "moTa": df_p["degree_level"].fillna("Đại học chính quy")
                    })
                    _write_df_atomic(df_n, cls.FILE_PATHS["nganhHoc"], cls.COLUMNS["nganhHoc"])

            if not os.path.exists(cls.FILE_PATHS["diemChuan"]):
                cls._initBenchmarksFromCleanData()

            if not os.path.exists(cls.FILE_PATHS["nguoiDung"]):
                default_users = []
                if config.ENV != "production":
                    import sys
                    print("\n[CANH BAO BAO MAT] Dang khoi tao tai khoan phat trien mac dinh (admin/hocsinh). Hay doi mat khau ngay hoac dat ENV=production khi trien khai thuc te!\n", file=sys.stderr)
                    default_users = [
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
                _write_df_atomic(pd.DataFrame(default_users), cls.FILE_PATHS["nguoiDung"], cls.COLUMNS["nguoiDung"])

            if not os.path.exists(cls.FILE_PATHS["hoSoHocSinh"]):
                default_profile = [
                    {
                        "id": 1,
                        "nguoiDungId": 2,
                        "diemToan": 8.8, "diemVan": 7.5, "diemAnh": 8.5,
                        "diemLy": 8.2, "diemHoa": 8.0, "diemSinh": 6.5,
                        "diemSu": 7.0, "diemDia": 7.0, "diemGDCD": 8.5,
                        "diemTinHoc": None, "diemCongNghe": None,
                        "diemHocBa": 8.5, "diemDanhGiaNangLuc": 880.0,
                        "diemDanhGiaTuDuy": None,
                        "chungChiQuocTe": "IELTS 6.5",
                        "khuVucUuTien": "KV1", "doiTuongUuTien": "NONE",
                        "khuVucMongMuon": None, "nganhMongMuon": None, "nganSach": None,
                        "phuongThucMongMuon": "PT01,PT02,PT03",
                        "ngayCapNhat": "2026-01-01 08:00:00"
                    }
                ]
                _write_df_atomic(pd.DataFrame(default_profile), cls.FILE_PATHS["hoSoHocSinh"], cls.COLUMNS["hoSoHocSinh"])

            if not os.path.exists(cls.FILE_PATHS["goiYNguyenVong"]):
                _write_df_atomic(pd.DataFrame(columns=cls.COLUMNS["goiYNguyenVong"]), cls.FILE_PATHS["goiYNguyenVong"], cls.COLUMNS["goiYNguyenVong"])

    @classmethod
    def _initBenchmarksFromCleanData(cls) -> None:
        df_uni = pd.read_csv(cls.FILE_PATHS["truongDaiHoc"])
        df_nganh = pd.read_csv(cls.FILE_PATHS["nganhHoc"])
        df_tohop = pd.read_csv(cls.FILE_PATHS["toHopMon"])

        uni_by_code = dict(zip(df_uni["maTruong"].astype(str), df_uni["id"]))
        nganh_by_ma = dict(zip(df_nganh["maNganh"].astype(str), df_nganh["id"]))
        unknown_nganh_id = nganh_by_ma.get("UNKNOWN", len(df_nganh))
        tohop_map = dict(zip(df_tohop["maToHop"].astype(str), df_tohop["id"]))

        up_path = os.path.join(os.path.dirname(__file__), "data", "metadata", "university_programs.csv")
        program_to_major = {}
        if os.path.exists(up_path):
            df_up = pd.read_csv(up_path)
            for _, row in df_up.iterrows():
                pid = str(row["program_id"]).strip()
                mid = str(row["major_id"]).replace("MAJ_", "").strip()
                program_to_major[pid] = mid

        seen_keys = set()
        records = []
        rec_id = 1

        thpt_path = os.path.join(os.path.dirname(__file__), "data", "processed", "forecast_records_2026.csv")
        if os.path.exists(thpt_path):
            fc_df = pd.read_csv(thpt_path)
            thpt_df = fc_df[fc_df["method_code"].str.upper() == "THPT"]
            for _, r in thpt_df.iterrows():
                u_code = str(r.get("university_code", "")).strip()
                u_id = uni_by_code.get(u_code)
                if not u_id:
                    continue
                prog_id = str(r.get("program_id", "")).strip()
                prog_name = str(r.get("program_name", "")).strip()
                case_id = str(r.get("admission_case_id", "")).strip()
                scale = str(r.get("score_scale", "SCALE_30")).strip()
                rule_id = str(r.get("calculation_rule_id", "RULE_THPT_STD_30")).strip()

                maj_code = program_to_major.get(prog_id, "UNKNOWN")
                nganh_id = nganh_by_ma.get(maj_code, unknown_nganh_id)
                if nganh_id == unknown_nganh_id and prog_name:
                    inferred = infer_nganh_id_from_name(prog_name)
                    if inferred:
                        nganh_id = inferred

                score_2025 = r.get("historical_cutoff_2025")
                if pd.isna(score_2025) or float(score_2025) <= 0:
                    score_2025 = r.get("predicted_cutoff")
                if pd.isna(score_2025) or float(score_2025) <= 0:
                    continue
                score_val = round(float(score_2025), 2)

                comb_tokens = [c.strip() for c in str(r.get("subject_combination", "")).replace(",", ";").split(";") if c.strip()]
                for c_token in comb_tokens:
                    t_id = tohop_map.get(c_token)
                    if not t_id:
                        continue
                    key = (int(u_id), prog_id or int(nganh_id), case_id, int(t_id), 1, 2025)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    records.append({
                        "id": rec_id,
                        "truongDaiHocId": int(u_id),
                        "nganhHocId": int(nganh_id),
                        "toHopMonId": int(t_id),
                        "phuongThucXetTuyenId": 1,
                        "nam": 2025,
                        "diemChuan": score_val,
                        "chiTieu": None,
                        "programId": prog_id,
                        "tenChuongTrinh": prog_name,
                        "admissionCaseId": case_id,
                        "scoreScale": scale,
                        "calculationRuleId": rule_id
                    })
                    rec_id += 1

        catalog_path = os.path.join(os.path.dirname(__file__), "data", "processed", "recommendation_catalog.csv")
        if os.path.exists(catalog_path):
            cat_df = pd.read_csv(catalog_path)
            cat_thpt = cat_df[cat_df["method_code"].str.upper() == "THPT"]
            for _, r in cat_thpt.iterrows():
                u_code = str(r.get("university_code", "")).strip()
                u_id = uni_by_code.get(u_code)
                if not u_id:
                    continue
                prog_id = str(r.get("program_id", "")).strip()
                prog_name = str(r.get("program_name", "")).strip()
                case_id = str(r.get("admission_code", "")).strip()
                scale = str(r.get("score_scale", "SCALE_30")).strip()
                rule_id = str(r.get("calculation_rule_id", "RULE_THPT_STD_30")).strip()

                maj_code = str(r.get("major_id", "")).replace("MAJ_", "").strip()
                nganh_id = nganh_by_ma.get(maj_code, unknown_nganh_id)
                if nganh_id == unknown_nganh_id and prog_name:
                    inferred = infer_nganh_id_from_name(prog_name)
                    if inferred:
                        nganh_id = inferred

                b_score = r.get("latest_cutoff_score")
                if pd.isna(b_score) or float(b_score) <= 0:
                    continue
                score_val = round(float(b_score), 2)
                year_val = int(r.get("latest_cutoff_year", 2025))

                comb_tokens = [c.strip() for c in str(r.get("subject_combination", "")).replace(",", ";").split(";") if c.strip()]
                for c_token in comb_tokens:
                    t_id = tohop_map.get(c_token)
                    if not t_id:
                        continue
                    key = (int(u_id), prog_id or int(nganh_id), case_id, int(t_id), 1, year_val)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    records.append({
                        "id": rec_id,
                        "truongDaiHocId": int(u_id),
                        "nganhHocId": int(nganh_id),
                        "toHopMonId": int(t_id),
                        "phuongThucXetTuyenId": 1,
                        "nam": year_val,
                        "diemChuan": score_val,
                        "chiTieu": None,
                        "programId": prog_id,
                        "tenChuongTrinh": prog_name,
                        "admissionCaseId": case_id,
                        "scoreScale": scale,
                        "calculationRuleId": rule_id
                    })
                    rec_id += 1

        hb_path = os.path.join(os.path.dirname(__file__), "data", "processed", "hoc_ba_cutoff_clean_final.csv")
        if os.path.exists(hb_path):
            hb_df = pd.read_csv(hb_path)
            hb_df = hb_df[hb_df["verification_status"] == "VERIFIED"]
            for _, r in hb_df.iterrows():
                u_code = str(r.get("university_code", "")).strip()
                u_id = uni_by_code.get(u_code)
                if not u_id:
                    continue
                maj_code = str(r.get("major_id", "")).replace("MAJ_", "").strip()
                nganh_id = nganh_by_ma.get(maj_code, unknown_nganh_id)
                prog_id = str(r.get("program_id", "")).strip()
                prog_name = str(r.get("program_name", "")).strip()
                case_id = str(r.get("admission_code", "")).strip()
                scale = str(r.get("score_scale", "SCALE_30")).strip()
                rule_id = str(r.get("calculation_rule_id", "RULE_HB_STD_30")).strip()

                if nganh_id == unknown_nganh_id and prog_name:
                    inferred = infer_nganh_id_from_name(prog_name)
                    if inferred:
                        nganh_id = inferred

                b_score = r.get("benchmark_score")
                if pd.isna(b_score) or float(b_score) <= 0:
                    continue
                score_val = round(float(b_score), 2)
                year_val = int(r.get("year", 2026))

                comb_tokens = [c.strip() for c in str(r.get("subject_combination", "")).replace(",", ";").split(";") if c.strip()]
                for c_token in comb_tokens:
                    t_id = tohop_map.get(c_token)
                    if not t_id:
                        continue
                    key = (int(u_id), prog_id or int(nganh_id), case_id, int(t_id), 2, year_val)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    records.append({
                        "id": rec_id,
                        "truongDaiHocId": int(u_id),
                        "nganhHocId": int(nganh_id),
                        "toHopMonId": int(t_id),
                        "phuongThucXetTuyenId": 2,
                        "nam": year_val,
                        "diemChuan": score_val,
                        "chiTieu": None,
                        "programId": prog_id,
                        "tenChuongTrinh": prog_name,
                        "admissionCaseId": case_id,
                        "scoreScale": scale,
                        "calculationRuleId": rule_id
                    })
                    rec_id += 1

        _write_df_atomic(pd.DataFrame(records), cls.FILE_PATHS["diemChuan"], cls.COLUMNS["diemChuan"])

    @classmethod
    def clearCache(cls, tableName: Optional[str] = None) -> None:
        with _lock:
            if tableName:
                _cache.pop(tableName, None)
            else:
                _cache.clear()

    @classmethod
    def setDatabaseDirectory(cls, newDir: str) -> None:
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
                return [dict(r) for r in _cache[tableName]]

            file_path = cls.FILE_PATHS.get(tableName)
            if not file_path or not os.path.exists(file_path):
                return []

            expected_cols = cls.COLUMNS.get(tableName, [])
            df = pd.read_csv(file_path, dtype=STRING_DTYPES)

            for c in expected_cols:
                if c not in df.columns:
                    df[c] = None

            raw_records = df[expected_cols].where(pd.notna(df[expected_cols]), None).to_dict(orient="records")
            cleaned = [_sanitize_record(r) for r in raw_records]
            _cache[tableName] = cleaned
            return [dict(r) for r in cleaned]

    @classmethod
    def findById(cls, tableName: str, recordId: int) -> Optional[Dict[str, Any]]:
        records = cls.readAll(tableName)
        for r in records:
            r_id = r.get("id")
            if r_id is not None and int(float(r_id)) == int(recordId):
                return dict(r)
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
                if rv is None and v is None:
                    continue

                if k in STRING_MATCH_FIELDS:
                    if str(rv).strip().lower() != str(v).strip().lower():
                        match = False
                        break
                    continue

                try:
                    if float(rv) == float(v):
                        continue
                except (ValueError, TypeError):
                    pass

                if str(rv).strip() != str(v).strip():
                    match = False
                    break

            if match:
                matched.append(dict(r))
        return matched

    @classmethod
    def insert(cls, tableName: str, data: Dict[str, Any]) -> Dict[str, Any]:
        file_path = cls.FILE_PATHS.get(tableName)
        if not file_path:
            raise ValueError(f"Bang {tableName} khong ton tai.")

        cols = cls.COLUMNS[tableName]
        with _lock:
            existing = cls.readAll(tableName)
            max_id = max([int(float(r.get("id", 0))) for r in existing], default=0)
            data["id"] = max_id + 1

            new_row = _sanitize_record({c: data.get(c, None) for c in cols})
            updated_records = existing + [new_row]

            _write_df_atomic(pd.DataFrame(updated_records), file_path, cols)
            cls.clearCache(tableName)
            return dict(new_row)

    @classmethod
    def update(cls, tableName: str, recordId: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        file_path = cls.FILE_PATHS.get(tableName)
        if not file_path or not os.path.exists(file_path):
            return None

        cols = cls.COLUMNS[tableName]
        with _lock:
            records = cls.readAll(tableName)
            updated_row = None

            for idx, r in enumerate(records):
                if int(float(r.get("id", -1))) == int(recordId):
                    for k, v in data.items():
                        if k in cols and k != "id":
                            r[k] = v
                    updated_row = _sanitize_record(r)
                    records[idx] = updated_row
                    break

            if updated_row:
                _write_df_atomic(pd.DataFrame(records), file_path, cols)
                cls.clearCache(tableName)
                return dict(updated_row)
            return None

    @classmethod
    def delete(cls, tableName: str, recordId: int) -> bool:
        file_path = cls.FILE_PATHS.get(tableName)
        if not file_path or not os.path.exists(file_path):
            return False

        cols = cls.COLUMNS[tableName]
        with _lock:
            records = cls.readAll(tableName)
            initial_len = len(records)
            filtered = [r for r in records if int(float(r.get("id", -1))) != int(recordId)]

            if len(filtered) < initial_len:
                _write_df_atomic(pd.DataFrame(filtered), file_path, cols)
                cls.clearCache(tableName)
                return True
            return False

    read_all = readAll
    find_by_id = findById
    find_where = findWhere
    clear_cache = clearCache
    set_database_dir = setDatabaseDirectory
    initialize_tables = initializeTables


CsvDatabase.initializeTables()
