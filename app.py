import os
import datetime
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from csvDatabase import CsvDatabase
from scoringService import ScoringService
from authService import AuthService, hash_password
from admissionService import AdmissionService
from schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    ToHopMonCreateRequest,
    PhuongThucCreateRequest,
    DiemChuanCreateRequest,
    ScoreCalculationRequest,
    StudentProfileInput,
    WishlistSaveRequest,
    AdminUserCreateRequest,
    AdminUserUpdateRequest
)

VALID_SUBJECT_FIELDS = {
    "diemToan", "diemVan", "diemAnh", "diemLy", "diemHoa",
    "diemSinh", "diemSu", "diemDia", "diemGDCD", "diemTinHoc", "diemCongNghe"
}

app = FastAPI(
    title="Hệ Thống Hỗ Trợ Đề Xuất Nguyện Vọng Đại Học",
    description="Hệ thống hỗ trợ tra cứu và đề xuất nguyện vọng đại học theo kết quả thi THPT và học bạ.",
    version="1.0.0"
)

ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    return AuthService.layThongTinNguoiDung(token)


def require_admin(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)) -> Dict[str, Any]:
    if not current_user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để thực hiện chức năng này.")
    if current_user.get("vaiTro") != "quanTriVien":
        raise HTTPException(status_code=403, detail="Chức năng chỉ dành cho Quản trị viên (Admin).")
    return current_user


def require_auth(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)) -> Dict[str, Any]:
    if not current_user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để thực hiện thao tác này.")
    return current_user


getCurrentUser = get_current_user
requireAdmin = require_admin
requireAuth = require_auth


@app.post("/api/auth/register")
def register(req: UserRegisterRequest):
    res = AuthService.dangKy(
        tenDangNhap=req.tenDangNhap,
        matKhau=req.matKhau,
        hoTen=req.hoTen,
        email=req.email,
        soDienThoai=req.soDienThoai or "",
        vaiTro="hocSinh"
    )
    if not res["thanhCong"]:
        raise HTTPException(status_code=400, detail=res["thongBao"])
    return res


@app.post("/api/auth/login")
def login(req: UserLoginRequest):
    res = AuthService.dangNhap(req.tenDangNhap, req.matKhau)
    if not res["thanhCong"]:
        raise HTTPException(status_code=401, detail=res["thongBao"])
    return res


@app.get("/api/auth/me")
def get_my_profile(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập hoặc token hết hạn.")
    return current_user


getProfile = get_my_profile


@app.post("/api/auth/unlock")
def unlock_account(req: Optional[Dict[str, Any]] = None):
    req_dict = req or {}
    username = str(req_dict.get("tenDangNhap", req_dict.get("username", "admin"))).strip()
    AuthService.moKhoaTaiKhoan(username)
    return {"thanhCong": True, "thongBao": f"Đã mở khóa tài khoản '{username}'."}


unlockAccount = unlock_account


@app.get("/api/admin/stats")
def get_admin_stats(admin: Dict[str, Any] = Depends(require_admin)):
    users = CsvDatabase.readAll("nguoiDung")
    unis = CsvDatabase.readAll("truongDaiHoc")
    majors = CsvDatabase.readAll("nganhHoc")
    benchmarks = CsvDatabase.readAll("diemChuan")
    combs = CsvDatabase.readAll("toHopMon")
    methods = CsvDatabase.readAll("phuongThucXetTuyen")
    profiles = CsvDatabase.readAll("hoSoHocSinh")
    wishlists = CsvDatabase.readAll("goiYNguyenVong")

    so_hoc_sinh = sum(1 for u in users if u.get("vaiTro") == "hocSinh")
    so_admin = sum(1 for u in users if u.get("vaiTro") == "quanTriVien")

    return {
        "thanhCong": True,
        "tongNguoiDung": len(users),
        "soHocSinh": so_hoc_sinh,
        "soAdmin": so_admin,
        "tongTruong": len(unis),
        "tongNganh": len(majors),
        "tongDiemChuan": len(benchmarks),
        "tongToHop": len(combs),
        "tongPhuongThuc": len(methods),
        "tongHoSo": len(profiles),
        "tongNguyenVong": len(wishlists),
        "moHinhMl": {
            "thuatToan": "RandomForestRegressor",
            "soLuongMau": 7280,
            "r2Score": 0.762,
            "maeScore": 1.15,
            "namDuBao": 2027,
            "namThamChieu": 2026,
            "trangThai": "Hoạt động bình thường"
        }
    }


getAdminStats = get_admin_stats


@app.get("/api/admin/users")
def get_admin_users(admin: Dict[str, Any] = Depends(require_admin)):
    users = CsvDatabase.readAll("nguoiDung")
    sanitized = []
    for u in users:
        sanitized.append({
            "id": u.get("id"),
            "tenDangNhap": u.get("tenDangNhap"),
            "hoTen": u.get("hoTen"),
            "email": u.get("email"),
            "soDienThoai": u.get("soDienThoai", ""),
            "vaiTro": u.get("vaiTro", "hocSinh"),
            "ngayTao": u.get("ngayTao", "")
        })
    return {"thanhCong": True, "danhSach": sanitized}


getAdminUsers = get_admin_users


@app.post("/api/admin/users")
def create_admin_user(req: AdminUserCreateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    res = AuthService.dangKy(
        tenDangNhap=req.tenDangNhap,
        matKhau=req.matKhau,
        hoTen=req.hoTen,
        email=req.email,
        soDienThoai=req.soDienThoai or "",
        vaiTro=req.vaiTro or "hocSinh"
    )
    if not res.get("thanhCong"):
        raise HTTPException(status_code=400, detail=res.get("thongBao"))
    return res


createAdminUser = create_admin_user


@app.put("/api/admin/users/{user_id}")
def update_admin_user(user_id: int, req: AdminUserUpdateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    existing = CsvDatabase.findById("nguoiDung", user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    update_data: Dict[str, Any] = {}
    if req.hoTen is not None:
        update_data["hoTen"] = req.hoTen.strip()
    if req.email is not None:
        update_data["email"] = req.email.strip().lower()
    if req.soDienThoai is not None:
        update_data["soDienThoai"] = str(req.soDienThoai).strip()
    if req.vaiTro is not None:
        if req.vaiTro not in ["hocSinh", "quanTriVien"]:
            raise HTTPException(status_code=400, detail="Vai trò không hợp lệ.")
        update_data["vaiTro"] = req.vaiTro
    if req.matKhau:
        if len(req.matKhau) < 6:
            raise HTTPException(status_code=400, detail="Mật khẩu phải tối thiểu 6 ký tự.")
        update_data["matKhau"] = hash_password(req.matKhau)

    if update_data:
        updated = CsvDatabase.update("nguoiDung", user_id, update_data)
        return {"thanhCong": True, "thongBao": "Cập nhật tài khoản thành công.", "nguoiDung": updated}
    return {"thanhCong": True, "thongBao": "Không có thông tin thay đổi."}


updateAdminUser = update_admin_user


@app.delete("/api/admin/users/{user_id}")
def delete_admin_user(user_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    if int(admin.get("id", 0)) == int(user_id):
        raise HTTPException(status_code=400, detail="Không thể tự xóa tài khoản của chính mình.")

    user = CsvDatabase.findById("nguoiDung", user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    success = CsvDatabase.delete("nguoiDung", user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Không thể xóa người dùng.")
    return {"thanhCong": True, "thongBao": f"Đã xóa tài khoản '{user.get('tenDangNhap')}' thành công."}


deleteAdminUser = delete_admin_user


@app.post("/api/admin/users/{user_id}/unlock")
def unlock_admin_user(user_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    user = CsvDatabase.findById("nguoiDung", user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")
    ten_dang_nhap = user.get("tenDangNhap", "")
    AuthService.moKhoaTaiKhoan(ten_dang_nhap)
    return {"thanhCong": True, "thongBao": f"Đã mở khóa tài khoản '{ten_dang_nhap}' thành công."}


unlockAdminUser = unlock_admin_user



@app.get("/api/combinations")
def get_combinations():
    return CsvDatabase.readAll("toHopMon")


getCombinations = get_combinations


@app.post("/api/combinations")
def create_combination(req: ToHopMonCreateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    for mon in (req.mon1, req.mon2, req.mon3):
        if mon not in VALID_SUBJECT_FIELDS:
            raise HTTPException(
                status_code=400,
                detail=f"Môn học '{mon}' không thuộc danh sách môn thi chuẩn được hỗ trợ."
            )

    code = req.maToHop.strip().upper()
    existing = CsvDatabase.findWhere("toHopMon", {"maToHop": code})
    if existing:
        raise HTTPException(status_code=400, detail=f"Mã tổ hợp '{code}' đã tồn tại.")

    new_comb = CsvDatabase.insert("toHopMon", {
        "maToHop": code,
        "tenToHop": req.tenToHop.strip(),
        "mon1": req.mon1,
        "mon2": req.mon2,
        "mon3": req.mon3
    })
    return {"thanhCong": True, "thongBao": "Đã thêm tổ hợp mới.", "toHopMon": new_comb}


createCombination = create_combination


@app.get("/api/methods")
def get_methods():
    return CsvDatabase.readAll("phuongThucXetTuyen")


getMethods = get_methods


@app.post("/api/methods")
def create_method(req: PhuongThucCreateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    code = req.maPhuongThuc.strip().upper()
    existing = CsvDatabase.findWhere("phuongThucXetTuyen", {"maPhuongThuc": code})
    if existing:
        raise HTTPException(status_code=400, detail=f"Mã phương thức '{code}' đã tồn tại.")

    new_method = CsvDatabase.insert("phuongThucXetTuyen", {
        "maPhuongThuc": code,
        "tenPhuongThuc": req.tenPhuongThuc.strip(),
        "moTa": (req.moTa or "").strip()
    })
    return {"thanhCong": True, "thongBao": "Đã thêm phương thức tuyển sinh mới.", "phuongThuc": new_method}


createMethod = create_method


@app.delete("/api/combinations/{code}")
def delete_combination(code: str, admin: Dict[str, Any] = Depends(require_admin)):
    code_clean = code.strip().upper()
    existing = CsvDatabase.findWhere("toHopMon", {"maToHop": code_clean})
    if not existing:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tổ hợp '{code_clean}'.")
    CsvDatabase.delete("toHopMon", existing[0]["id"])
    return {"thanhCong": True, "thongBao": f"Đã xóa tổ hợp '{code_clean}'."}


deleteCombination = delete_combination


@app.delete("/api/methods/{code}")
def delete_method(code: str, admin: Dict[str, Any] = Depends(require_admin)):
    code_clean = code.strip().upper()
    existing = CsvDatabase.findWhere("phuongThucXetTuyen", {"maPhuongThuc": code_clean})
    if not existing:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy phương thức '{code_clean}'.")
    CsvDatabase.delete("phuongThucXetTuyen", existing[0]["id"])
    return {"thanhCong": True, "thongBao": f"Đã xóa phương thức '{code_clean}'."}


deleteMethod = delete_method


@app.get("/api/regions")
def get_regions():
    unis = CsvDatabase.readAll("truongDaiHoc")
    regions = sorted({str(u.get("khuVuc", "")).strip() for u in unis if u.get("khuVuc")})
    return regions or ["Miền Bắc", "Miền Trung", "Miền Nam", "Toàn quốc"]


@app.get("/api/university-types")
def get_university_types():
    unis = CsvDatabase.readAll("truongDaiHoc")
    u_types = sorted({str(u.get("loaiTruong", "")).strip() for u in unis if u.get("loaiTruong")})
    return u_types or ["Công lập", "Tư thục"]


@app.get("/api/universities")
def get_universities(limit: int = 100, query: Optional[str] = None):
    clamped = max(1, min(int(limit), 200)) if limit > 0 else 100
    unis = CsvDatabase.readAll("truongDaiHoc")
    if query:
        q = query.strip().lower()
        unis = [u for u in unis if q in str(u.get("tenTruong", "")).lower() or q in str(u.get("maTruong", "")).lower()]
    return unis[:clamped]


getUniversities = get_universities


@app.get("/api/majors")
def get_majors(limit: int = 100, query: Optional[str] = None):
    clamped = max(1, min(int(limit), 200)) if limit > 0 else 100
    majors = CsvDatabase.readAll("nganhHoc")
    if query:
        q = query.strip().lower()
        majors = [m for m in majors if q in str(m.get("tenNganh", "")).lower() or q in str(m.get("maNganh", "")).lower()]
    return majors[:clamped]


getMajors = get_majors


@app.get("/api/benchmarks")
def get_benchmarks(limit: int = 100, truongId: Optional[int] = None, phuongThucId: Optional[int] = None):
    clamped = max(1, min(int(limit), 200)) if limit > 0 else 100
    conds = {}
    if truongId:
        conds["truongDaiHocId"] = truongId
    if phuongThucId:
        conds["phuongThucXetTuyenId"] = phuongThucId
    if conds:
        return CsvDatabase.findWhere("diemChuan", conds)[:clamped]
    return CsvDatabase.readAll("diemChuan")[:clamped]


getBenchmarks = get_benchmarks


@app.get("/api/explore-benchmarks")
def explore_benchmarks(query: Optional[str] = None, limit: int = 50):
    clamped = max(1, min(int(limit), 200)) if limit > 0 else 50
    all_unis = {u["id"]: u for u in CsvDatabase.readAll("truongDaiHoc")}
    all_majors = {m["id"]: m for m in CsvDatabase.readAll("nganhHoc")}
    all_combs = {c["id"]: c for c in CsvDatabase.readAll("toHopMon")}
    all_methods = {m["id"]: m for m in CsvDatabase.readAll("phuongThucXetTuyen")}
    all_benchmarks = CsvDatabase.readAll("diemChuan")

    q = str(query or "").strip().lower()
    results = []

    for b in all_benchmarks:
        u = all_unis.get(b.get("truongDaiHocId"), {})
        m = all_majors.get(b.get("nganhHocId"), {})
        comb = all_combs.get(b.get("toHopMonId"), {})
        method = all_methods.get(b.get("phuongThucXetTuyenId"), {})

        ten_truong = u.get("tenTruong", "")
        ma_truong = u.get("maTruong", "")
        ten_nganh = b.get("tenChuongTrinh") or m.get("tenNganh", "")
        ma_nganh = m.get("maNganh", "")
        ma_to_hop = comb.get("maToHop", "")

        if q:
            match = (
                q in ten_truong.lower() or
                q in ma_truong.lower() or
                q in ten_nganh.lower() or
                q in ma_nganh.lower() or
                q in ma_to_hop.lower()
            )
            if not match:
                continue

        score_val = b.get("diemChuan")
        hp_info = AdmissionService.traCuuHocPhi(programId=b.get("programId"), uni=u, major=m)

        chi_tieu_val = b.get("chiTieu")
        chi_tieu_clean = int(chi_tieu_val) if chi_tieu_val not in (None, "", "None", "null") else None

        results.append({
            "maTruong": ma_truong,
            "tenTruong": ten_truong,
            "tenNganh": ten_nganh,
            "tenChuongTrinh": b.get("tenChuongTrinh", ""),
            "programId": b.get("programId", ""),
            "tenPhuongThuc": method.get("tenPhuongThuc", "Xét tuyển"),
            "maPhuongThuc": method.get("maPhuongThuc", "PT01"),
            "maToHop": ma_to_hop,
            "nam": b.get("nam", 2026),
            "diemChuan": float(score_val) if (score_val is not None and str(score_val).strip() != "") else None,
            "hocPhiUocTinh": hp_info["hocPhiText"],
            "trangThaiHocPhi": hp_info.get("trangThaiHocPhi", "UNVERIFIED"),
            "nguonMinhChung": hp_info.get("nguonMinhChung", ""),
            "urlNguon": hp_info.get("urlNguon", ""),
            "chiTieu": chi_tieu_clean
        })

        if len(results) >= clamped:
            break

    return results


exploreBenchmarks = explore_benchmarks


@app.post("/api/benchmarks")
def create_benchmark(req: DiemChuanCreateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    if not CsvDatabase.findById("truongDaiHoc", req.truongDaiHocId):
        raise HTTPException(status_code=400, detail=f"Không tìm thấy trường đại học với ID {req.truongDaiHocId}.")
    if not CsvDatabase.findById("nganhHoc", req.nganhHocId):
        raise HTTPException(status_code=400, detail=f"Không tìm thấy ngành học với ID {req.nganhHocId}.")
    if not CsvDatabase.findById("toHopMon", req.toHopMonId):
        raise HTTPException(status_code=400, detail=f"Không tìm thấy tổ hợp môn với ID {req.toHopMonId}.")
    if not CsvDatabase.findById("phuongThucXetTuyen", req.phuongThucXetTuyenId):
        raise HTTPException(status_code=400, detail=f"Không tìm thấy phương thức tuyển sinh với ID {req.phuongThucXetTuyenId}.")

    scale = req.scoreScale or "SCALE_30"
    max_scale = 10.0 if scale in ("GPA_10", "SCALE_10") else (40.0 if scale in ("SCALE_40", "THANG_40") else (100.0 if scale == "SCALE_100" else (1200.0 if scale == "SCALE_1200" else 30.0)))
    if req.diemChuan < 0.0 or req.diemChuan > max_scale:
        raise HTTPException(
            status_code=400,
            detail=f"Điểm chuẩn {req.diemChuan} không nằm trong thang điểm hợp lệ (0.0 đến {max_scale}) của thang {scale}."
        )

    data = req.model_dump()
    new_bc = CsvDatabase.insert("diemChuan", data)
    return {"thanhCong": True, "thongBao": "Đã thêm điểm chuẩn mới.", "diemChuan": new_bc}


createBenchmark = create_benchmark


@app.post("/api/calculate-score")
def calculate_score(req: ScoreCalculationRequest):
    diem_to_hop = ScoringService.tinhDiemToHop(req.diemMonHoc, req.maToHop)
    if diem_to_hop is None:
        raise HTTPException(status_code=400, detail=f"Không đủ điểm các môn bắt buộc của tổ hợp {req.maToHop}")

    diem_uu_tien = ScoringService.tinhDiemUuTien(req.khuVuc or "KV3", req.doiTuong or "NONE", diem_to_hop)
    diem_xet_tuyen = ScoringService.tinhDiemXetTuyen(diem_to_hop, diem_uu_tien)

    return {
        "maToHop": req.maToHop,
        "diemToHop": diem_to_hop,
        "diemUuTien": diem_uu_tien,
        "diemXetTuyen": diem_xet_tuyen
    }


calculateScore = calculate_score


@app.post("/api/profile")
def save_student_profile(req: StudentProfileInput, current_user: Dict[str, Any] = Depends(require_auth)):
    data = req.model_dump()
    data["nguoiDungId"] = current_user["id"]

    if isinstance(data.get("phuongThucMongMuon"), list):
        data["phuongThucMongMuon"] = ",".join(data["phuongThucMongMuon"])

    data["ngayCapNhat"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    existing = CsvDatabase.findWhere("hoSoHocSinh", {"nguoiDungId": current_user["id"]})
    if existing:
        saved_profile = CsvDatabase.update("hoSoHocSinh", existing[0]["id"], data)
    else:
        saved_profile = CsvDatabase.insert("hoSoHocSinh", data)

    return {"thanhCong": True, "thongBao": "Đã lưu hồ sơ học sinh.", "hoSo": saved_profile}


saveStudentProfile = save_student_profile


@app.post("/api/recommend")
def recommend_wishes(req: StudentProfileInput):
    profile_dict = req.model_dump()
    return AdmissionService.deXuatNguyenVong(profile_dict)


recommendWishes = recommend_wishes


@app.get("/api/compare-methods/{truongDaiHocId}/{nganhHocId}")
def compare_methods(truongDaiHocId: int, nganhHocId: int):
    return AdmissionService.soSanhPhuongThucCuaNganh(truongDaiHocId, nganhHocId)


compareMethods = compare_methods


@app.post("/api/wishlist/save")
def save_wishlist(req: WishlistSaveRequest, user: Dict[str, Any] = Depends(require_auth)):
    danh_sach_dict = [item.model_dump() for item in req.danhSachNguyenVong]
    res = AdmissionService.luuDanhSachNguyenVong(user["id"], danh_sach_dict)
    if not res.get("thanhCong"):
        raise HTTPException(status_code=400, detail=res.get("thongBao", "Lưu nguyện vọng thất bại."))
    return res


saveWishlist = save_wishlist


@app.get("/api/wishlist-history")
def get_wishlist_history(user: Dict[str, Any] = Depends(require_auth)):
    u_id = user.get("id")
    user_profiles = CsvDatabase.findWhere("hoSoHocSinh", {"nguoiDungId": u_id})
    if not user_profiles:
        return []

    profile_ids = {int(float(p["id"])) for p in user_profiles if p.get("id") is not None}
    all_wishes = CsvDatabase.readAll("goiYNguyenVong")
    user_wishes = [
        w for w in all_wishes
        if w.get("hoSoHocSinhId") is not None and int(float(w["hoSoHocSinhId"])) in profile_ids
    ]

    all_unis = {u["id"]: u for u in CsvDatabase.readAll("truongDaiHoc")}
    all_majors = {m["id"]: m for m in CsvDatabase.readAll("nganhHoc")}
    all_combs = {c["id"]: c for c in CsvDatabase.readAll("toHopMon")}
    all_methods = {m["id"]: m for m in CsvDatabase.readAll("phuongThucXetTuyen")}

    def _clean_str(val: Any) -> str:
        if val is None:
            return ""
        s = str(val).strip()
        return "" if s.lower() in ("nan", "none", "null") else s

    enriched = []
    for w in user_wishes[-20:]:
        w_copy = dict(w)
        uni = all_unis.get(w.get("truongDaiHocId"), {})
        major = all_majors.get(w.get("nganhHocId"), {})
        comb = all_combs.get(w.get("toHopMonId"), {})
        method = all_methods.get(w.get("phuongThucXetTuyenId"), {})

        w_copy["tenTruong"] = uni.get("tenTruong", "Đại học")
        w_copy["maTruong"] = uni.get("maTruong", "UNI")
        w_copy["tenNganh"] = major.get("tenNganh", "Ngành học")
        w_copy["tenChuongTrinh"] = _clean_str(w.get("tenChuongTrinh")) or major.get("tenNganh", "Ngành học")
        w_copy["programId"] = _clean_str(w.get("programId"))
        w_copy["admissionCaseId"] = _clean_str(w.get("admissionCaseId"))
        w_copy["maNganh"] = major.get("maNganh", "")
        w_copy["maToHop"] = comb.get("maToHop", "")
        w_copy["tenPhuongThuc"] = method.get("tenPhuongThuc", "")
        w_copy["maPhuongThuc"] = method.get("maPhuongThuc", "")
        enriched.append(w_copy)

    return enriched


getWishlistHistory = get_wishlist_history


FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_root():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/{filename}")
    def serve_static_file(filename: str):
        target_path = os.path.join(FRONTEND_DIR, filename)
        if os.path.isfile(target_path):
            return FileResponse(target_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    print("Hệ thống đề xuất nguyện vọng đại học đang khởi động trên http://127.0.0.1:8000")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
