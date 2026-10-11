import math
import re
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional, Any, Union


class UserRegisterRequest(BaseModel):
    tenDangNhap: str = Field(..., min_length=3, max_length=50)
    matKhau: str = Field(..., min_length=6)
    hoTen: str
    email: str
    soDienThoai: Optional[str] = ""
    vaiTro: Optional[str] = "hocSinh"

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValueError("Email không đúng định dạng hợp lệ.")
        return clean

    @field_validator("soDienThoai")
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> str:
        if not v:
            return ""
        clean = str(v).strip()
        if clean.endswith(".0"):
            clean = clean[:-2]
        if len(clean) == 9 and not clean.startswith("0"):
            clean = "0" + clean
        return clean


class UserLoginRequest(BaseModel):
    tenDangNhap: str
    matKhau: str


class ToHopMonCreateRequest(BaseModel):
    maToHop: str = Field(..., min_length=3, max_length=10)
    tenToHop: str
    mon1: str
    mon2: str
    mon3: str


class PhuongThucCreateRequest(BaseModel):
    maPhuongThuc: str = Field(..., min_length=3, max_length=10)
    tenPhuongThuc: str
    moTa: Optional[str] = ""


class DiemChuanCreateRequest(BaseModel):
    truongDaiHocId: int
    nganhHocId: int
    toHopMonId: int
    phuongThucXetTuyenId: int
    nam: int = 2025
    diemChuan: float
    chiTieu: Optional[int] = 100
    programId: Optional[str] = ""
    tenChuongTrinh: Optional[str] = ""
    admissionCaseId: Optional[str] = ""
    scoreScale: Optional[str] = "SCALE_30"
    calculationRuleId: Optional[str] = "RULE_THPT_STD_30"


class ScoreCalculationRequest(BaseModel):
    diemMonHoc: Dict[str, Optional[float]]
    maToHop: str
    khuVuc: Optional[str] = "KV3"
    doiTuong: Optional[str] = "NONE"

    @field_validator("diemMonHoc")
    @classmethod
    def validate_diem_mon_hoc(cls, v: Dict[str, Optional[float]]) -> Dict[str, Optional[float]]:
        for mon, val in v.items():
            if val is not None:
                if not isinstance(val, (int, float)) or not math.isfinite(val) or val < 0.0 or val > 10.0:
                    raise ValueError(f"Điểm môn '{mon}' phải là số hữu hạn trong thang điểm từ 0.0 đến 10.0.")
        return v


class StudentProfileInput(BaseModel):
    id: Optional[int] = None
    nguoiDungId: Optional[int] = None
    diemToan: Optional[float] = None
    diemVan: Optional[float] = None
    diemAnh: Optional[float] = None
    diemLy: Optional[float] = None
    diemHoa: Optional[float] = None
    diemSinh: Optional[float] = None
    diemSu: Optional[float] = None
    diemDia: Optional[float] = None
    diemGDCD: Optional[float] = None
    diemTinHoc: Optional[float] = None
    diemCongNghe: Optional[float] = None
    diemHocBa: Optional[float] = None
    diemDanhGiaNangLuc: Optional[float] = None
    diemDanhGiaTuDuy: Optional[float] = None
    chungChiQuocTe: Optional[str] = None
    khuVucUuTien: Optional[str] = "KV3"
    doiTuongUuTien: Optional[str] = "NONE"
    khuVucMongMuon: Optional[str] = None
    nganhMongMuon: Optional[str] = None
    nganSach: Optional[float] = None
    mucHocPhi: Optional[str] = None
    filterTuition: Optional[str] = None
    namTuyenSinh: Optional[int] = 2027
    calculationRuleId: Optional[str] = None
    scoreScale: Optional[str] = None
    phuongThucMongMuon: Optional[Union[List[str], str]] = "PT01"
    danhSachToHopDaChon: Optional[List[str]] = ["A00"]

    @field_validator(
        "diemToan", "diemVan", "diemAnh", "diemLy", "diemHoa",
        "diemSinh", "diemSu", "diemDia", "diemGDCD", "diemTinHoc", "diemCongNghe", "diemHocBa"
    )
    @classmethod
    def validate_subject_score(cls, v):
        if v is not None:
            if not math.isfinite(v) or v < 0.0 or v > 10.0:
                raise ValueError("Điểm môn học phải nằm trong thang điểm từ 0.0 đến 10.0")
        return v

    @field_validator("diemDanhGiaNangLuc")
    @classmethod
    def validate_dgnl(cls, v):
        if v is not None:
            if not math.isfinite(v) or v < 0.0 or v > 1200.0:
                raise ValueError("Điểm đánh giá năng lực phải từ 0.0 đến 1200.0")
        return v

    @field_validator("diemDanhGiaTuDuy")
    @classmethod
    def validate_dgtd(cls, v):
        if v is not None:
            if not math.isfinite(v) or v < 0.0 or v > 100.0:
                raise ValueError("Điểm đánh giá tư duy phải từ 0.0 đến 100.0")
        return v

    @field_validator("phuongThucMongMuon")
    @classmethod
    def validate_method(cls, v):
        if v is None:
            return ["PT01"]
        methods = []
        if isinstance(v, list):
            methods = [m.strip().upper() for m in v if m and m.strip()]
        else:
            methods = [m.strip().upper() for m in str(v).split(",") if m and m.strip()]

        if not methods:
            raise ValueError("Vui lòng chọn 1 phương thức xét tuyển")
        if len(methods) > 1:
            raise ValueError("Chỉ hỗ trợ chọn đúng 1 phương thức xét tuyển (PT01 hoặc PT02) cho mỗi lần tư vấn")
        if methods[0] not in ["PT01", "PT02"]:
            raise ValueError(f"Phương thức '{methods[0]}' không được hỗ trợ. Hiện chỉ hỗ trợ PT01 (THPT) và PT02 (Học bạ)")
        return methods


class WishlistItemInput(BaseModel):
    truongDaiHocId: Optional[int] = None
    nganhHocId: Optional[int] = None
    toHopMonId: Optional[int] = None
    phuongThucXetTuyenId: Optional[int] = None
    diemXetTuyen: Optional[float] = None
    diemChuanThamChieu: Optional[float] = None
    doPhuHop: Optional[float] = None
    mucDoPhuHop: Optional[str] = None
    mucDoRuiRo: Optional[str] = None
    thuTuUuTien: Optional[str] = None
    programId: Optional[str] = None
    tenChuongTrinh: Optional[str] = None
    admissionCaseId: Optional[str] = None


class WishlistSaveRequest(BaseModel):
    danhSachNguyenVong: List[WishlistItemInput]
