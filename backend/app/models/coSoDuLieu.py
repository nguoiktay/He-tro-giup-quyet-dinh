# -*- coding: utf-8 -*-
"""
Các thực thể ORM SQLAlchemy tương ứng với 10 bảng trong CSDL MySQL heTroGiupQuyetDinh.
Quy tắc bắt buộc: Tiếng Việt không dấu, camelCase cho biến và thuộc tính, PascalCase cho Class, KHÔNG có dấu gạch dưới (_).
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.cauHinh import caiDat

GocMoHinh = declarative_base()

dongCoCSDL = create_engine(
    caiDat.duongDanKetNoiCSDL,
    pool_pre_ping=True,
    pool_recycle=3600
)

PhienLamViec = sessionmaker(autocommit=False, autoflush=False, bind=dongCoCSDL)

def layPhienLamViecCSDL():
    phien = PhienLamViec()
    try:
        yield phien
    finally:
        phien.close()

# Bảng người dùng
class NguoiDung(GocMoHinh):
    __tablename__ = 'nguoiDung'

    id = Column(Integer, primary_key=True, index=True)
    tenDangNhap = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    matKhau = Column(String(255), nullable=False)
    vaiTro = Column(String(20), default='hocSinh') 
    thoiGianTao = Column(DateTime, default=datetime.utcnow)

    hoSo = relationship('HoSoHocSinh', back_populates='nguoiDung', uselist=False, cascade='all, delete-orphan')
    danhSachDuDoan = relationship('KetQuaDuDoan', back_populates='nguoiDung', cascade='all, delete-orphan')
    danhSachYeuThich = relationship('YeuThich', back_populates='nguoiDung', cascade='all, delete-orphan')

# Bảng hồ sơ học sinh
class HoSoHocSinh(GocMoHinh):
    __tablename__ = 'hoSoHocSinh'

    id = Column(Integer, primary_key=True, index=True)
    nguoiDungId = Column(Integer, ForeignKey('nguoiDung.id'), unique=True, nullable=False)
    hoTen = Column(String(100), nullable=False)
    ngaySinh = Column(String(20))
    truongTHPT = Column(String(150))
    khuVuc = Column(String(50), default='Miền Bắc')
    khuVucUuTien = Column(String(20), default='KV3')
    doiTuongUuTien = Column(String(20), default='DT0')
    diemToan = Column(Float, default=0.0)
    diemVan = Column(Float, default=0.0)
    diemAnh = Column(Float, default=0.0)
    diemLy = Column(Float, default=0.0)
    diemHoa = Column(Float, default=0.0)
    diemSinh = Column(Float, default=0.0)
    diemSu = Column(Float, default=0.0)
    diemDia = Column(Float, default=0.0)
    diemGDCD = Column(Float, default=0.0)
    diemTrungBinh = Column(Float, default=0.0)
    diemHocBa = Column(Float, default=0.0)
    diemDanhGiaNangLuc = Column(Float, default=0.0)
    chungChiQuocTe = Column(String(50), default='Không')
    toHop = Column(String(100), default='A00')
    mucHocPhi = Column(String(50), default='Dưới 20 triệu/năm')
    khuVucMongMuon = Column(String(50), default='Toàn quốc')
    loaiTruongMongMuon = Column(String(50), default='Tất cả')
    soThichNganh = Column(String(100), default='Công nghệ thông tin')

    nguoiDung = relationship('NguoiDung', back_populates='hoSo')

# 3. Bảng trường đại học
class TruongDaiHoc(GocMoHinh):
    __tablename__ = 'truongDaiHoc'

    id = Column(Integer, primary_key=True, index=True)
    tenTruong = Column(String(150), nullable=False, index=True)
    diaChi = Column(String(255))
    loaiTruong = Column(String(50), default='Công lập')
    hocPhi = Column(String(100))
    website = Column(String(150))
    moTa = Column(Text)

    danhSachNganh = relationship('NganhHoc', back_populates='truong', cascade='all, delete-orphan')
    danhSachDiemChuan = relationship('DiemChuan', back_populates='truong', cascade='all, delete-orphan')

# 4. Bảng ngành học
class NganhHoc(GocMoHinh):
    __tablename__ = 'nganhHoc'

    id = Column(Integer, primary_key=True, index=True)
    truongDaiHocId = Column(Integer, ForeignKey('truongDaiHoc.id'), nullable=False)
    tenNganh = Column(String(150), nullable=False, index=True)
    maNganh = Column(String(50), nullable=False)
    nhomNganh = Column(String(100), nullable=False)
    moTa = Column(Text)

    truong = relationship('TruongDaiHoc', back_populates='danhSachNganh')
    danhSachDiemChuan = relationship('DiemChuan', back_populates='nganh', cascade='all, delete-orphan')

# 5. Bảng tổ hợp môn
class ToHopMon(GocMoHinh):
    __tablename__ = 'toHopMon'

    id = Column(Integer, primary_key=True, index=True)
    maToHop = Column(String(20), unique=True, nullable=False, index=True)
    tenToHop = Column(String(100), nullable=False)
    mon1 = Column(String(50), nullable=False)
    mon2 = Column(String(50), nullable=False)
    mon3 = Column(String(50), nullable=False)

    danhSachDiemChuan = relationship('DiemChuan', back_populates='toHop')

# 6. Bảng phương thức xét tuyển
class PhuongThucXetTuyen(GocMoHinh):
    __tablename__ = 'phuongThucXetTuyen'

    id = Column(Integer, primary_key=True, index=True)
    maPhuongThuc = Column(String(20), unique=True, nullable=False, index=True)
    tenPhuongThuc = Column(String(150), nullable=False)
    moTa = Column(Text)

    danhSachDiemChuan = relationship('DiemChuan', back_populates='phuongThuc')

# 7. Bảng điểm chuẩn
class DiemChuan(GocMoHinh):
    __tablename__ = 'diemChuan'

    id = Column(Integer, primary_key=True, index=True)
    truongDaiHocId = Column(Integer, ForeignKey('truongDaiHoc.id'), nullable=False)
    nganhHocId = Column(Integer, ForeignKey('nganhHoc.id'), nullable=False)
    toHopMonId = Column(Integer, ForeignKey('toHopMon.id'), nullable=False)
    phuongThucXetTuyenId = Column(Integer, ForeignKey('phuongThucXetTuyen.id'), nullable=False)
    nam = Column(Integer, nullable=False, index=True)
    diemChuan = Column(Float, nullable=False)
    chiTieu = Column(Integer, default=100)

    truong = relationship('TruongDaiHoc', back_populates='danhSachDiemChuan')
    nganh = relationship('NganhHoc', back_populates='danhSachDiemChuan')
    toHop = relationship('ToHopMon', back_populates='danhSachDiemChuan')
    phuongThuc = relationship('PhuongThucXetTuyen', back_populates='danhSachDiemChuan')

# 8. Bảng kết quả dự đoán
class KetQuaDuDoan(GocMoHinh):
    __tablename__ = 'ketQuaDuDoan'

    id = Column(Integer, primary_key=True, index=True)
    nguoiDungId = Column(Integer, ForeignKey('nguoiDung.id'), nullable=False)
    phienBanMoHinh = Column(String(50), default='RandomForest-v1.0')
    duLieuDauVao = Column(JSON)
    thoiGianTao = Column(DateTime, default=datetime.utcnow)

    nguoiDung = relationship('NguoiDung', back_populates='danhSachDuDoan')
    danhSachNguyenVong = relationship('GoiYNguyenVong', back_populates='ketQua', cascade='all, delete-orphan')

# 9. Bảng gợi ý nguyện vọng (Tên chính xác: goiYNguyenVong)
class GoiYNguyenVong(GocMoHinh):
    __tablename__ = 'goiYNguyenVong'

    id = Column(Integer, primary_key=True, index=True)
    ketQuaDuDoanId = Column(Integer, ForeignKey('ketQuaDuDoan.id'), nullable=False)
    truongDaiHocId = Column(Integer, ForeignKey('truongDaiHoc.id'), nullable=False)
    nganhHocId = Column(Integer, ForeignKey('nganhHoc.id'), nullable=False)
    toHopMonId = Column(Integer, ForeignKey('toHopMon.id'), nullable=False)
    phuongThucXetTuyenId = Column(Integer, ForeignKey('phuongThucXetTuyen.id'), nullable=False)
    doPhuHop = Column(Float, nullable=False)
    mucDoPhuHop = Column(String(50), nullable=False)
    mucDoRuiRo = Column(String(50), nullable=False)
    lyDo = Column(Text, nullable=False)
    thuTuNguyenVong = Column(Integer, nullable=False, index=True)

    ketQua = relationship('KetQuaDuDoan', back_populates='danhSachNguyenVong')
    truong = relationship('TruongDaiHoc')
    nganh = relationship('NganhHoc')
    toHop = relationship('ToHopMon')
    phuongThuc = relationship('PhuongThucXetTuyen')

# 10. Bảng yêu thích
class YeuThich(GocMoHinh):
    __tablename__ = 'yeuThich'

    id = Column(Integer, primary_key=True, index=True)
    nguoiDungId = Column(Integer, ForeignKey('nguoiDung.id'), nullable=False)
    truongDaiHocId = Column(Integer, ForeignKey('truongDaiHoc.id'), nullable=False)
    nganhHocId = Column(Integer, ForeignKey('nganhHoc.id'), nullable=True)
    thoiGianTao = Column(DateTime, default=datetime.utcnow)

    nguoiDung = relationship('NguoiDung', back_populates='danhSachYeuThich')
    truong = relationship('TruongDaiHoc')
    nganh = relationship('NganhHoc')
