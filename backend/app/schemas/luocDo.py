
from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field

# 1. Xác thực tài khoản
class DangKyYeuCau(BaseModel):
    tenDangNhap: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=100)
    matKhau: str = Field(..., min_length=6, max_length=100)
    xacNhanMatKhau: str = Field(..., min_length=6, max_length=100)
    hoTen: str = Field(..., min_length=2, max_length=100)

class DangNhapYeuCau(BaseModel):
    tenDangNhap: str
    matKhau: str

class DangNhapPhanHoi(BaseModel):
    maToken: str
    loaiToken: str = "bearer"
    vaiTro: str
    tenDangNhap: str
    hoTen: str
    nguoiDungId: int

# 2. Hồ sơ học sinh
class HoSoHocSinhCapNhat(BaseModel):
    hoTen: Optional[str] = None
    ngaySinh: Optional[str] = None
    truongTHPT: Optional[str] = None
    khuVuc: Optional[str] = 'Miền Bắc'
    khuVucUuTien: Optional[str] = 'KV3'
    doiTuongUuTien: Optional[str] = 'DT0'
    diemToan: Optional[float] = 0.0
    diemVan: Optional[float] = 0.0
    diemAnh: Optional[float] = 0.0
    diemLy: Optional[float] = 0.0
    diemHoa: Optional[float] = 0.0
    diemSinh: Optional[float] = 0.0
    diemSu: Optional[float] = 0.0
    diemDia: Optional[float] = 0.0
    diemGDCD: Optional[float] = 0.0
    diemTrungBinh: Optional[float] = 0.0
    diemHocBa: Optional[float] = 0.0
    diemDanhGiaNangLuc: Optional[float] = 0.0
    chungChiQuocTe: Optional[str] = 'Không'
    toHop: Optional[str] = 'A00'
    mucHocPhi: Optional[str] = 'Dưới 20 triệu/năm'
    khuVucMongMuon: Optional[str] = 'Toàn quốc'
    loaiTruongMongMuon: Optional[str] = 'Tất cả'
    soThichNganh: Optional[str] = 'Công nghệ thông tin'

class HoSoHocSinhPhanHoi(HoSoHocSinhCapNhat):
    id: int
    nguoiDungId: int
    class Config:
        from_attributes = True

# 3. Yêu cầu tư vấn AI & Dự đoán
class TuVanYeuCau(BaseModel):
    diemToan: float = Field(..., ge=0.0, le=10.0)
    diemVan: float = Field(..., ge=0.0, le=10.0)
    diemAnh: float = Field(..., ge=0.0, le=10.0)
    diemLy: float = Field(default=0.0, ge=0.0, le=10.0)
    diemHoa: float = Field(default=0.0, ge=0.0, le=10.0)
    diemSinh: float = Field(default=0.0, ge=0.0, le=10.0)
    diemSu: float = Field(default=0.0, ge=0.0, le=10.0)
    diemDia: float = Field(default=0.0, ge=0.0, le=10.0)
    diemGDCD: float = Field(default=0.0, ge=0.0, le=10.0)
    diemTrungBinh: Optional[float] = 0.0
    diemHocBa: Optional[float] = 0.0
    diemDanhGiaNangLuc: Optional[float] = 0.0
    chungChiQuocTe: Optional[str] = 'Không'
    danhSachToHopDaChon: List[str] = Field(..., min_length=1)
    danhSachPhuongThucMongMuon: List[str] = Field(..., min_length=1)
    khuVuc: Optional[str] = 'Miền Bắc'
    khuVucUuTien: Optional[str] = 'KV3'
    doiTuongUuTien: Optional[str] = 'DT0'
    soThichNganh: Optional[str] = 'Công nghệ thông tin'
    nhomNganh: Optional[str] = 'Công nghệ thông tin'
    mucHocPhi: Optional[str] = 'Dưới 20 triệu/năm'
    khuVucMongMuon: Optional[str] = 'Toàn quốc'
    loaiTruongMongMuon: Optional[str] = 'Tất cả'
    diemThiDuKien: Optional[float] = None

class NguyenVongChiTiet(BaseModel):
    truongDaiHocId: int
    tenTruong: str
    nganhHocId: int
    tenNganh: str
    maNganh: str
    nhomNganh: str
    toHopMonId: int
    maToHop: str
    tenToHop: str
    phuongThucXetTuyenId: int
    maPhuongThuc: str
    tenPhuongThuc: str
    diemChuan: float
    diemXetTuyen: float
    diemUuTien: float
    doLechDiem: float
    doPhuHop: float
    mucDoPhuHop: str
    mucDoRuiRo: str
    lyDo: str
    thuTuNguyenVong: int
    loaiTruong: Optional[str] = 'Công lập'
    hocPhi: Optional[str] = ''

class TuVanPhanHoi(BaseModel):
    ketQuaDuDoanId: int
    phienBanMoHinh: str
    thoiGianTao: str
    danhSachNguyenVong: List[NguyenVongChiTiet]
    doQuanTrongDacTrung: Dict[str, float]
    chiSoDanhGia: Dict[str, float]

# 4. Danh mục Master Data
class ToHopMonPhanHoi(BaseModel):
    id: int
    maToHop: str
    tenToHop: str
    mon1: str
    mon2: str
    mon3: str
    class Config:
        from_attributes = True

class ToHopMonYeuCau(BaseModel):
    maToHop: str
    tenToHop: str
    mon1: str
    mon2: str
    mon3: str

class PhuongThucXetTuyenPhanHoi(BaseModel):
    id: int
    maPhuongThuc: str
    tenPhuongThuc: str
    moTa: Optional[str] = None
    class Config:
        from_attributes = True

class PhuongThucXetTuyenYeuCau(BaseModel):
    maPhuongThuc: str
    tenPhuongThuc: str
    moTa: Optional[str] = None

class TruongDaiHocPhanHoi(BaseModel):
    id: int
    tenTruong: str
    diaChi: Optional[str] = None
    loaiTruong: Optional[str] = 'Công lập'
    hocPhi: Optional[str] = None
    website: Optional[str] = None
    moTa: Optional[str] = None
    class Config:
        from_attributes = True

class TruongDaiHocYeuCau(BaseModel):
    tenTruong: str
    diaChi: Optional[str] = None
    loaiTruong: Optional[str] = 'Công lập'
    hocPhi: Optional[str] = None
    website: Optional[str] = None
    moTa: Optional[str] = None

class NganhHocPhanHoi(BaseModel):
    id: int
    truongDaiHocId: int
    tenTruong: Optional[str] = None
    tenNganh: str
    maNganh: str
    nhomNganh: str
    moTa: Optional[str] = None
    class Config:
        from_attributes = True

class NganhHocYeuCau(BaseModel):
    truongDaiHocId: int
    tenNganh: str
    maNganh: str
    nhomNganh: str
    moTa: Optional[str] = None

class DiemChuanPhanHoi(BaseModel):
    id: int
    truongDaiHocId: int
    tenTruong: Optional[str] = None
    nganhHocId: int
    tenNganh: Optional[str] = None
    toHopMonId: int
    maToHop: Optional[str] = None
    phuongThucXetTuyenId: int
    maPhuongThuc: Optional[str] = None
    tenPhuongThuc: Optional[str] = None
    nam: int
    diemChuan: float
    chiTieu: Optional[int] = 100
    class Config:
        from_attributes = True

class DiemChuanYeuCau(BaseModel):
    truongDaiHocId: int
    nganhHocId: int
    toHopMonId: int
    phuongThucXetTuyenId: int
    nam: int
    diemChuan: float
    chiTieu: Optional[int] = 100

class YeuThichYeuCau(BaseModel):
    truongDaiHocId: int
    nganhHocId: Optional[int] = None

class YeuThichPhanHoi(BaseModel):
    id: int
    truongDaiHocId: int
    tenTruong: str
    nganhHocId: Optional[int] = None
    tenNganh: Optional[str] = None
    thoiGianTao: str
    class Config:
        from_attributes = True
