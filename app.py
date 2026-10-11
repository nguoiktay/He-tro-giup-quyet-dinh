import os
import datetime
import math
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Header, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from csvDatabase import CsvDatabase
from scoringService import ScoringService
from mlService import mlServiceInstance
from authService import AuthService, verifyJwtToken
from admissionService import AdmissionService
from schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    ToHopMonCreateRequest,
    PhuongThucCreateRequest,
    DiemChuanCreateRequest,
    ScoreCalculationRequest,
    StudentProfileInput,
    WishlistSaveRequest
)

app = FastAPI(
    title="Hệ Thống Hỗ Trợ Đề Xuất Nguyện Vọng Đại Học",
    description="Hệ thống hỗ trợ tra cứu và đề xuất nguyện vọng đại học theo kết quả thi THPT và học bạ.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def getCurrentUser(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    return AuthService.layThongTinNguoiDung(token)


def requireAdmin(currentUser: Optional[Dict[str, Any]] = Depends(getCurrentUser)):
    if not currentUser:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để thực hiện chức năng này.")
    if currentUser.get("vaiTro") != "quanTriVien":
        raise HTTPException(status_code=403, detail="Chức năng chỉ dành cho Quản trị viên (Admin).")
    return currentUser


def requireAuth(currentUser: Optional[Dict[str, Any]] = Depends(getCurrentUser)):
    if not currentUser:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để thực hiện thao tác này.")
    return currentUser


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
def getProfile(currentUser: Optional[Dict[str, Any]] = Depends(getCurrentUser)):
    if not currentUser:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập hoặc token hết hạn.")
    return currentUser


@app.get("/api/combinations")
def getCombinations():
    return CsvDatabase.readAll("toHopMon")


@app.post("/api/combinations")
def createCombination(req: ToHopMonCreateRequest, admin: Dict[str, Any] = Depends(requireAdmin)):
    existing = CsvDatabase.findWhere("toHopMon", {"maToHop": req.maToHop.upper()})
    if existing:
        raise HTTPException(status_code=400, detail=f"Mã tổ hợp '{req.maToHop}' đã tồn tại.")

    newComb = CsvDatabase.insert("toHopMon", {
        "maToHop": req.maToHop.upper(),
        "tenToHop": req.tenToHop,
        "mon1": req.mon1,
        "mon2": req.mon2,
        "mon3": req.mon3
    })
    return {"thanhCong": True, "thongBao": "Đã thêm tổ hợp mới.", "toHopMon": newComb}


@app.get("/api/methods")
def getMethods():
    return CsvDatabase.readAll("phuongThucXetTuyen")


@app.post("/api/methods")
def createMethod(req: PhuongThucCreateRequest, admin: Dict[str, Any] = Depends(requireAdmin)):
    existing = CsvDatabase.findWhere("phuongThucXetTuyen", {"maPhuongThuc": req.maPhuongThuc.upper()})
    if existing:
        raise HTTPException(status_code=400, detail=f"Mã phương thức '{req.maPhuongThuc}' đã tồn tại.")

    newMethod = CsvDatabase.insert("phuongThucXetTuyen", {
        "maPhuongThuc": req.maPhuongThuc.upper(),
        "tenPhuongThuc": req.tenPhuongThuc,
        "moTa": req.moTa or ""
    })
    return {"thanhCong": True, "thongBao": "Đã thêm phương thức tuyển sinh mới.", "phuongThuc": newMethod}


@app.get("/api/universities")
def getUniversities(limit: int = 100, query: Optional[str] = None):
    unis = CsvDatabase.readAll("truongDaiHoc")
    if query:
        q = query.lower()
        unis = [u for u in unis if q in str(u.get("tenTruong", "")).lower() or q in str(u.get("maTruong", "")).lower()]
    return unis[:limit]


@app.get("/api/majors")
def getMajors(limit: int = 100, query: Optional[str] = None):
    majors = CsvDatabase.readAll("nganhHoc")
    if query:
        q = query.lower()
        majors = [m for m in majors if q in str(m.get("tenNganh", "")).lower() or q in str(m.get("maNganh", "")).lower()]
    return majors[:limit]


@app.get("/api/benchmarks")
def getBenchmarks(limit: int = 100, truongId: Optional[int] = None, phuongThucId: Optional[int] = None):
    conds = {}
    if truongId:
        conds["truongDaiHocId"] = truongId
    if phuongThucId:
        conds["phuongThucXetTuyenId"] = phuongThucId
    if conds:
        return CsvDatabase.findWhere("diemChuan", conds)[:limit]
    return CsvDatabase.readAll("diemChuan")[:limit]


@app.get("/api/explore-benchmarks")
def exploreBenchmarks(query: Optional[str] = None, limit: int = 50):
    allUnis = {u["id"]: u for u in CsvDatabase.readAll("truongDaiHoc")}
    allMajors = {m["id"]: m for m in CsvDatabase.readAll("nganhHoc")}
    allCombs = {c["id"]: c for c in CsvDatabase.readAll("toHopMon")}
    allMethods = {m["id"]: m for m in CsvDatabase.readAll("phuongThucXetTuyen")}
    allBenchmarks = CsvDatabase.readAll("diemChuan")

    q = str(query or "").strip().lower()

    results = []
    for b in allBenchmarks:
        u = allUnis.get(b.get("truongDaiHocId"), {})
        m = allMajors.get(b.get("nganhHocId"), {})
        comb = allCombs.get(b.get("toHopMonId"), {})
        method = allMethods.get(b.get("phuongThucXetTuyenId"), {})

        tenTruong = u.get("tenTruong", "")
        maTruong = u.get("maTruong", "")
        tenNganh = b.get("tenChuongTrinh") or m.get("tenNganh", "")
        maNganh = m.get("maNganh", "")
        maToHop = comb.get("maToHop", "")

        if q:
            match = (
                q in tenTruong.lower() or
                q in maTruong.lower() or
                q in tenNganh.lower() or
                q in maNganh.lower() or
                q in maToHop.lower()
            )
            if not match:
                continue

        scoreVal = b.get("diemChuan")
        hpInfo = AdmissionService.uocLuongHocPhi(u, m)
        results.append({
            "maTruong": maTruong,
            "tenTruong": tenTruong,
            "tenNganh": tenNganh,
            "tenChuongTrinh": b.get("tenChuongTrinh", ""),
            "programId": b.get("programId", ""),
            "tenPhuongThuc": method.get("tenPhuongThuc", "Xét tuyển"),
            "maPhuongThuc": method.get("maPhuongThuc", "PT01"),
            "maToHop": maToHop,
            "nam": b.get("nam", 2025),
            "diemChuan": float(scoreVal) if (scoreVal is not None and str(scoreVal).strip() != "") else None,
            "hocPhiUocTinh": hpInfo["hocPhiText"],
            "chiTieu": int(b.get("chiTieu") or 100)
        })

        if len(results) >= limit:
            break

    return results


@app.post("/api/benchmarks")
def createBenchmark(req: DiemChuanCreateRequest, admin: Dict[str, Any] = Depends(requireAdmin)):
    newBc = CsvDatabase.insert("diemChuan", req.model_dump())
    return {"thanhCong": True, "thongBao": "Đã thêm điểm chuẩn mới.", "diemChuan": newBc}


@app.post("/api/calculate-score")
def calculateScore(req: ScoreCalculationRequest):
    for mon, diem in req.diemMonHoc.items():
        if diem is not None:
            if not isinstance(diem, (int, float)) or not math.isfinite(diem) or diem < 0.0 or diem > 10.0:
                raise HTTPException(status_code=400, detail=f"Điểm môn '{mon}' phải nằm trong thang điểm hợp lệ từ 0.0 đến 10.0")

    diemToHop = ScoringService.tinhDiemToHop(req.diemMonHoc, req.maToHop)
    if diemToHop is None:
        raise HTTPException(status_code=400, detail=f"Không đủ điểm các môn bắt buộc của tổ hợp {req.maToHop}")

    diemUuTien = ScoringService.tinhDiemUuTien(req.khuVuc or "KV3", req.doiTuong or "NONE", diemToHop)
    diemXetTuyen = ScoringService.tinhDiemXetTuyen(diemToHop, diemUuTien)

    return {
        "maToHop": req.maToHop,
        "diemToHop": diemToHop,
        "diemUuTien": diemUuTien,
        "diemXetTuyen": diemXetTuyen
    }


@app.post("/api/profile")
def saveStudentProfile(req: StudentProfileInput, currentUser: Optional[Dict[str, Any]] = Depends(getCurrentUser)):
    data = req.model_dump()
    data["nguoiDungId"] = currentUser["id"] if currentUser else None

    if isinstance(data.get("phuongThucMongMuon"), list):
        data["phuongThucMongMuon"] = ",".join(data["phuongThucMongMuon"])

    data["ngayCapNhat"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    savedProfile = CsvDatabase.insert("hoSoHocSinh", data)
    return {"thanhCong": True, "thongBao": "Đã lưu hồ sơ học sinh.", "hoSo": savedProfile}


@app.post("/api/recommend")
def recommendWishes(req: StudentProfileInput):
    profileDict = req.model_dump()
    res = AdmissionService.deXuatNguyenVong(profileDict)
    return res


@app.get("/api/compare-methods/{truongDaiHocId}/{nganhHocId}")
def compareMethods(truongDaiHocId: int, nganhHocId: int):
    return AdmissionService.soSanhPhuongThucCuaNganh(truongDaiHocId, nganhHocId)


@app.post("/api/wishlist/save")
def saveWishlist(req: WishlistSaveRequest, user: Dict[str, Any] = Depends(requireAuth)):
    danhSachDict = [item.model_dump() for item in req.danhSachNguyenVong]
    res = AdmissionService.luuDanhSachNguyenVong(user["id"], danhSachDict)
    if not res.get("thanhCong"):
        raise HTTPException(status_code=400, detail=res.get("thongBao", "Lưu nguyện vọng thất bại."))
    return res


@app.get("/api/wishlist-history")
def getWishlistHistory(user: Dict[str, Any] = Depends(requireAuth)):
    uId = user.get("id")
    userProfiles = CsvDatabase.findWhere("hoSoHocSinh", {"nguoiDungId": uId})
    if not userProfiles:
        return []

    profileIds = set()
    for p in userProfiles:
        try:
            profileIds.add(int(float(p["id"])))
        except (ValueError, TypeError):
            pass

    allWishes = CsvDatabase.readAll("goiYNguyenVong")
    userWishes = []
    for w in allWishes:
        wHsId = w.get("hoSoHocSinhId")
        if wHsId is not None:
            try:
                if int(float(wHsId)) in profileIds:
                    userWishes.append(w)
            except (ValueError, TypeError):
                pass

    allUnis = {u["id"]: u for u in CsvDatabase.readAll("truongDaiHoc")}
    allMajors = {m["id"]: m for m in CsvDatabase.readAll("nganhHoc")}
    allCombs = {c["id"]: c for c in CsvDatabase.readAll("toHopMon")}
    allMethods = {m["id"]: m for m in CsvDatabase.readAll("phuongThucXetTuyen")}

    enriched = []
    for w in userWishes[-20:]:
        wCopy = dict(w)
        uni = allUnis.get(w.get("truongDaiHocId"), {})
        major = allMajors.get(w.get("nganhHocId"), {})
        comb = allCombs.get(w.get("toHopMonId"), {})
        method = allMethods.get(w.get("phuongThucXetTuyenId"), {})

        rawPrgName = w.get("tenChuongTrinh")
        rawPrgId = w.get("programId")
        rawCaseId = w.get("admissionCaseId")

        def _cleanStr(val: Any) -> str:
            if val is None:
                return ""
            s = str(val).strip()
            return "" if s.lower() in ("nan", "none", "null") else s

        wCopy["tenTruong"] = uni.get("tenTruong", "Đại học")
        wCopy["maTruong"] = uni.get("maTruong", "UNI")
        wCopy["tenNganh"] = major.get("tenNganh", "Ngành học")
        wCopy["tenChuongTrinh"] = _cleanStr(rawPrgName) or major.get("tenNganh", "Ngành học")
        wCopy["programId"] = _cleanStr(rawPrgId)
        wCopy["admissionCaseId"] = _cleanStr(rawCaseId)
        wCopy["maNganh"] = major.get("maNganh", "")
        wCopy["maToHop"] = comb.get("maToHop", "")
        wCopy["tenPhuongThuc"] = method.get("tenPhuongThuc", "")
        wCopy["maPhuongThuc"] = method.get("maPhuongThuc", "")
        enriched.append(wCopy)

    return enriched


FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serveRoot():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/{filename}")
    def serveStaticFile(filename: str):
        targetPath = os.path.join(FRONTEND_DIR, filename)
        if os.path.isfile(targetPath):
            return FileResponse(targetPath)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    print(" Hệ thống đề xuất và lựa chọn  nguyện vọng đại học tối ưu cho học sinh THPT sử dụng thuật toán Random Forest ")
    print(" Server dang chay tai: http://127.0.0.1:8000")
    print(" Mo trinh duyet va truy cap dia chi tren de su dung.")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)

