from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from database.connection import CoSoDuLieu


class TaiKhoan(CoSoDuLieu):
    __tablename__ = "taiKhoan"

    maTaiKhoan = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(191), unique=True, nullable=False, index=True)
    matKhauHash = Column(String(255), nullable=False)
    vaiTro = Column(String(30), nullable=False, default="hocSinh")
    trangThai = Column(String(30), nullable=False, default="kichHoat")
    soLanDangNhapSai = Column(Integer, nullable=False, default=0)
    khoaDenThoiDiem = Column(DateTime, nullable=True)
    thoiDiemTao = Column(DateTime, nullable=False, default=datetime.utcnow)
    thoiDiemCapNhat = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    hocSinh = relationship("HocSinh", back_populates="taiKhoan", uselist=False, cascade="all, delete-orphan")
    phienDangNhap = relationship("PhienDangNhap", back_populates="taiKhoan", cascade="all, delete-orphan")


class PhienDangNhap(CoSoDuLieu):
    __tablename__ = "phienDangNhap"

    maPhien = Column(Integer, primary_key=True, autoincrement=True)
    maTaiKhoan = Column(Integer, ForeignKey("taiKhoan.maTaiKhoan", ondelete="CASCADE"), nullable=False, index=True)
    maBamToken = Column(String(64), unique=True, nullable=False, index=True)
    thoiHan = Column(DateTime, nullable=False, index=True)
    daThuHoi = Column(Boolean, nullable=False, default=False)
    diaChiIp = Column(String(45), nullable=True)
    tacNhanNguoiDung = Column(String(255), nullable=True)
    thoiDiemTao = Column(DateTime, nullable=False, default=datetime.utcnow)

    taiKhoan = relationship("TaiKhoan", back_populates="phienDangNhap")


class HocSinh(CoSoDuLieu):
    __tablename__ = "hocSinh"

    maHocSinh = Column(Integer, primary_key=True, autoincrement=True)
    maTaiKhoan = Column(Integer, ForeignKey("taiKhoan.maTaiKhoan", ondelete="CASCADE"), unique=True, nullable=False)
    hoTen = Column(String(100), nullable=False)
    soDienThoai = Column(String(20), nullable=True)
    namDuTuyen = Column(Integer, nullable=False, default=2026)
    nganSachToiDa = Column(Float, nullable=True)
    kyTinhNganSach = Column(String(20), nullable=False, default="nam")
    diaBanUuTien = Column(String(100), nullable=True)
    batBuocNganSach = Column(Boolean, nullable=False, default=False)
    batBuocDiaBan = Column(Boolean, nullable=False, default=False)
    mucTieuNgheNghiep = Column(Text, nullable=True)
    uuTienCaNhan = Column(Text, nullable=True)
    thoiDiemTao = Column(DateTime, nullable=False, default=datetime.utcnow)
    thoiDiemCapNhat = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    taiKhoan = relationship("TaiKhoan", back_populates="hocSinh")
    diemMonHoc = relationship("DiemMonHoc", back_populates="hocSinh", cascade="all, delete-orphan")
    soThichHocSinh = relationship("SoThichHocSinh", back_populates="hocSinh", cascade="all, delete-orphan")
    tuongTac = relationship("TuongTac", back_populates="hocSinh", cascade="all, delete-orphan")
    danhSachNguyenVong = relationship("DanhSachNguyenVong", back_populates="hocSinh", uselist=False, cascade="all, delete-orphan")
    phienKhuyenNghi = relationship("PhienKhuyenNghi", back_populates="hocSinh", cascade="all, delete-orphan")


class DiemMonHoc(CoSoDuLieu):
    __tablename__ = "diemMonHoc"

    maDiemMon = Column(Integer, primary_key=True, autoincrement=True)
    maHocSinh = Column(Integer, ForeignKey("hocSinh.maHocSinh", ondelete="CASCADE"), nullable=False, index=True)
    tenMon = Column(String(50), nullable=False)
    diemSo = Column(Float, nullable=False)
    thangDiem = Column(Float, nullable=False, default=10.0)
    loaiDiem = Column(String(30), nullable=False, default="thpt")
    namHocKy = Column(String(20), nullable=False, default="2026")
    thoiDiemTao = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("maHocSinh", "tenMon", "loaiDiem", "namHocKy", name="uqDiemMonHocSinh"),
    )

    hocSinh = relationship("HocSinh", back_populates="diemMonHoc")


class SoThichHocSinh(CoSoDuLieu):
    __tablename__ = "soThichHocSinh"

    maSoThich = Column(Integer, primary_key=True, autoincrement=True)
    maHocSinh = Column(Integer, ForeignKey("hocSinh.maHocSinh", ondelete="CASCADE"), nullable=False, index=True)
    nhomNganh = Column(String(100), nullable=False)
    mucDoThich = Column(Integer, nullable=False, default=5)
    thoiDiemTao = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("maHocSinh", "nhomNganh", name="uqSoThichHocSinh"),
    )

    hocSinh = relationship("HocSinh", back_populates="soThichHocSinh")


class TruongDaiHoc(CoSoDuLieu):
    __tablename__ = "truongDaiHoc"

    maTruong = Column(String(30), primary_key=True)
    tenTruong = Column(String(255), nullable=False)
    khoiTruong = Column(String(50), nullable=False, default="CongLap")
    tinhThanh = Column(String(100), nullable=False, default="ToanQuoc")
    vungMien = Column(String(50), nullable=False, default="MienBac")
    website = Column(String(255), nullable=True)
    thoiDiemTao = Column(DateTime, nullable=False, default=datetime.utcnow)

    phuongAn = relationship("PhuongAn", back_populates="truongDaiHoc")


class NganhHoc(CoSoDuLieu):
    __tablename__ = "nganhHoc"

    maNganh = Column(String(50), primary_key=True)
    tenNganh = Column(String(255), nullable=False)
    nhomNganh = Column(String(100), nullable=False)
    moTa = Column(Text, nullable=True)
    thoiDiemTao = Column(DateTime, nullable=False, default=datetime.utcnow)

    phuongAn = relationship("PhuongAn", back_populates="nganhHoc")


class PhuongAn(CoSoDuLieu):
    __tablename__ = "phuongAn"

    maPhuongAn = Column(String(60), primary_key=True)
    maTruong = Column(String(30), ForeignKey("truongDaiHoc.maTruong", ondelete="CASCADE"), nullable=False, index=True)
    maNganh = Column(String(50), ForeignKey("nganhHoc.maNganh", ondelete="CASCADE"), nullable=False, index=True)
    tenChuongTrinh = Column(String(255), nullable=False)
    coSo = Column(String(100), nullable=False, default="Chinh")
    phuongThuc = Column(String(100), nullable=False, default="DiemThiTHPT")
    hocPhiKy = Column(Float, nullable=True)
    donViTien = Column(String(20), nullable=False, default="VND")
    namTuyenSinh = Column(Integer, nullable=False, default=2026)
    chiTieu = Column(Integer, nullable=True)
    dieuKienXetTuyen = Column(Text, nullable=True)
    thoiDiemTao = Column(DateTime, nullable=False, default=datetime.utcnow)

    truongDaiHoc = relationship("TruongDaiHoc", back_populates="phuongAn")
    nganhHoc = relationship("NganhHoc", back_populates="phuongAn")
    diemChuan = relationship("DiemChuan", back_populates="phuongAn", cascade="all, delete-orphan")
    tuongTac = relationship("TuongTac", back_populates="phuongAn")
    nguyenVong = relationship("NguyenVong", back_populates="phuongAn")


class ToHopXetTuyen(CoSoDuLieu):
    __tablename__ = "toHopXetTuyen"

    maToHop = Column(String(30), primary_key=True)
    tenToHop = Column(String(100), nullable=False)
    danhSachMon = Column(String(100), nullable=False)
    thoiDiemTao = Column(DateTime, nullable=False, default=datetime.utcnow)

    diemChuan = relationship("DiemChuan", back_populates="toHopXetTuyen")


class DiemChuan(CoSoDuLieu):
    __tablename__ = "diemChuan"

    maDiemChuan = Column(Integer, primary_key=True, autoincrement=True)
    maPhuongAn = Column(String(60), ForeignKey("phuongAn.maPhuongAn", ondelete="CASCADE"), nullable=False, index=True)
    maToHop = Column(String(30), ForeignKey("toHopXetTuyen.maToHop", ondelete="CASCADE"), nullable=False, index=True)
    nam = Column(Integer, nullable=False, index=True)
    diemTrungTuyen = Column(Float, nullable=False)
    thangDiem = Column(Float, nullable=False, default=30.0)
    nguonDuLieu = Column(String(100), nullable=False, default="DeAnTuyenSinh")
    ghiChu = Column(Text, nullable=True)
    thoiDiemTao = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("maPhuongAn", "maToHop", "nam", name="uqDiemChuanPhuongAnToHopNam"),
    )

    phuongAn = relationship("PhuongAn", back_populates="diemChuan")
    toHopXetTuyen = relationship("ToHopXetTuyen", back_populates="diemChuan")


class NguonDuLieu(CoSoDuLieu):
    __tablename__ = "nguonDuLieu"

    maNguon = Column(Integer, primary_key=True, autoincrement=True)
    tenNguon = Column(String(100), nullable=False)
    loaiNguon = Column(String(50), nullable=False)
    duongDan = Column(String(255), nullable=True)
    moTa = Column(Text, nullable=True)
    thoiDiemTao = Column(DateTime, nullable=False, default=datetime.utcnow)


class TuongTac(CoSoDuLieu):
    __tablename__ = "tuongTac"

    maTuongTac = Column(Integer, primary_key=True, autoincrement=True)
    maHocSinh = Column(Integer, ForeignKey("hocSinh.maHocSinh", ondelete="CASCADE"), nullable=False, index=True)
    maPhuongAn = Column(String(60), ForeignKey("phuongAn.maPhuongAn", ondelete="CASCADE"), nullable=False, index=True)
    loaiTuongTac = Column(String(30), nullable=False)
    thoiDiem = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    maPhienKhuyenNghi = Column(Integer, nullable=True)
    viTriHienThi = Column(Integer, nullable=True)

    hocSinh = relationship("HocSinh", back_populates="tuongTac")
    phuongAn = relationship("PhuongAn", back_populates="tuongTac")


class MauDanhGia(CoSoDuLieu):
    __tablename__ = "mauDanhGia"

    maDanhGia = Column(Integer, primary_key=True, autoincrement=True)
    maHocSinh = Column(Integer, ForeignKey("hocSinh.maHocSinh", ondelete="CASCADE"), nullable=False, index=True)
    maPhuongAn = Column(String(60), ForeignKey("phuongAn.maPhuongAn", ondelete="CASCADE"), nullable=False, index=True)
    nhanPhuHop = Column(Float, nullable=False)
    nguonNhan = Column(String(50), nullable=False)
    duLieuMoPhong = Column(Boolean, nullable=False, default=False)
    thoiDiemGanNhan = Column(DateTime, nullable=False, default=datetime.utcnow)


class PhienBanDuLieu(CoSoDuLieu):
    __tablename__ = "phienBanDuLieu"

    maPhienBanDuLieu = Column(Integer, primary_key=True, autoincrement=True)
    tenPhienBan = Column(String(100), nullable=False, unique=True)
    moTa = Column(Text, nullable=True)
    soLuongBanGhi = Column(Integer, nullable=False, default=0)
    duLieuMoPhong = Column(Boolean, nullable=False, default=False)
    thoiDiemTao = Column(DateTime, nullable=False, default=datetime.utcnow)


class PhienBanMoHinh(CoSoDuLieu):
    __tablename__ = "phienBanMoHinh"

    maPhienBanMoHinh = Column(Integer, primary_key=True, autoincrement=True)
    tenPhienBan = Column(String(100), nullable=False, unique=True)
    thuatToan = Column(String(100), nullable=False, default="RandomForestRegressor")
    thamSoJson = Column(Text, nullable=False)
    danhSachDacTrungJson = Column(Text, nullable=False)
    chiSoDanhGiaJson = Column(Text, nullable=False)
    maBamChecksum = Column(String(64), nullable=False)
    dangKichHoat = Column(Boolean, nullable=False, default=False)
    thoiDiemTao = Column(DateTime, nullable=False, default=datetime.utcnow)


class PhienKhuyenNghi(CoSoDuLieu):
    __tablename__ = "phienKhuyenNghi"

    maPhienKhuyenNghi = Column(Integer, primary_key=True, autoincrement=True)
    maHocSinh = Column(Integer, ForeignKey("hocSinh.maHocSinh", ondelete="CASCADE"), nullable=False, index=True)
    thoiDiem = Column(DateTime, nullable=False, default=datetime.utcnow)
    anhXaHoSoJson = Column(Text, nullable=False)
    trongSoJson = Column(Text, nullable=False)
    phienBanMoHinh = Column(String(100), nullable=False)
    phienBanLuat = Column(String(50), nullable=False, default="v1.0")

    hocSinh = relationship("HocSinh", back_populates="phienKhuyenNghi")
    chiTietKhuyenNghi = relationship("ChiTietKhuyenNghi", back_populates="phienKhuyenNghi", cascade="all, delete-orphan")


class ChiTietKhuyenNghi(CoSoDuLieu):
    __tablename__ = "chiTietKhuyenNghi"

    maChiTietKhuyenNghi = Column(Integer, primary_key=True, autoincrement=True)
    maPhienKhuyenNghi = Column(Integer, ForeignKey("phienKhuyenNghi.maPhienKhuyenNghi", ondelete="CASCADE"), nullable=False, index=True)
    maPhuongAn = Column(String(60), ForeignKey("phuongAn.maPhuongAn", ondelete="CASCADE"), nullable=False)
    thuHang = Column(Integer, nullable=False)
    diemDuDoan = Column(Float, nullable=False)
    diemMoHinh = Column(Float, nullable=False)
    diemTaiChinh = Column(Float, nullable=False)
    diemKhuVuc = Column(Float, nullable=False)
    diemXepHang = Column(Float, nullable=False)
    lyDoJson = Column(Text, nullable=True)
    canKiemTraJson = Column(Text, nullable=True)

    phienKhuyenNghi = relationship("PhienKhuyenNghi", back_populates="chiTietKhuyenNghi")


class DanhSachNguyenVong(CoSoDuLieu):
    __tablename__ = "danhSachNguyenVong"

    maDanhSach = Column(Integer, primary_key=True, autoincrement=True)
    maHocSinh = Column(Integer, ForeignKey("hocSinh.maHocSinh", ondelete="CASCADE"), unique=True, nullable=False)
    tenDanhSach = Column(String(100), nullable=False, default="Danh sách nguyện vọng chính thức")
    phienBan = Column(Integer, nullable=False, default=1)
    thoiDiemTao = Column(DateTime, nullable=False, default=datetime.utcnow)
    thoiDiemCapNhat = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    hocSinh = relationship("HocSinh", back_populates="danhSachNguyenVong")
    nguyenVong = relationship("NguyenVong", back_populates="danhSachNguyenVong", cascade="all, delete-orphan", order_by="NguyenVong.thuTu")


class NguyenVong(CoSoDuLieu):
    __tablename__ = "nguyenVong"

    maNguyenVong = Column(Integer, primary_key=True, autoincrement=True)
    maDanhSach = Column(Integer, ForeignKey("danhSachNguyenVong.maDanhSach", ondelete="CASCADE"), nullable=False, index=True)
    maPhuongAn = Column(String(60), ForeignKey("phuongAn.maPhuongAn", ondelete="CASCADE"), nullable=False)
    thuTu = Column(Integer, nullable=False)
    ghiChu = Column(Text, nullable=True)
    thoiDiemTao = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("maDanhSach", "thuTu", name="uqNguyenVongDanhSachThuTu"),
        UniqueConstraint("maDanhSach", "maPhuongAn", name="uqNguyenVongDanhSachPhuongAn"),
    )

    danhSachNguyenVong = relationship("DanhSachNguyenVong", back_populates="nguyenVong")
    phuongAn = relationship("PhuongAn", back_populates="nguyenVong")


class PhanHoi(CoSoDuLieu):
    __tablename__ = "phanHoi"

    maPhanHoi = Column(Integer, primary_key=True, autoincrement=True)
    maHocSinh = Column(Integer, ForeignKey("hocSinh.maHocSinh", ondelete="CASCADE"), nullable=False, index=True)
    maPhienKhuyenNghi = Column(Integer, nullable=True)
    mucDoHaiLong = Column(Integer, nullable=False)
    tiLeHoanThanh = Column(Float, nullable=False, default=1.0)
    thoiGianHoanThanhPhut = Column(Float, nullable=False, default=5.0)
    danhGiaGiaiThich = Column(Integer, nullable=False, default=5)
    yKienDongGop = Column(Text, nullable=True)
    thoiDiem = Column(DateTime, nullable=False, default=datetime.utcnow)


class NhatKyQuanTri(CoSoDuLieu):
    __tablename__ = "nhatKyQuanTri"

    maNhatKy = Column(Integer, primary_key=True, autoincrement=True)
    maTaiKhoan = Column(Integer, nullable=True)
    hanhDong = Column(String(100), nullable=False)
    chiTiet = Column(Text, nullable=True)
    diaChiIp = Column(String(45), nullable=True)
    thoiDiem = Column(DateTime, nullable=False, default=datetime.utcnow)
