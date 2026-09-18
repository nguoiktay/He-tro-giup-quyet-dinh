
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Enum, ForeignKey,
    UniqueConstraint, Text
)
from sqlalchemy.orm import relationship
from backend.core.database import Base


class Truong(Base):
    __tablename__ = "TRUONG"

    id_truong = Column(Integer, primary_key=True, autoincrement=True)
    ma_truong = Column(String(20), unique=True, nullable=False)
    ten_truong = Column(String(255), nullable=False)
    khu_vuc = Column(String(100))
    loai_hinh = Column(String(50))

    nganhs = relationship("Nganh", back_populates="truong")


class Nganh(Base):
    __tablename__ = "NGANH"

    id_nganh = Column(Integer, primary_key=True, autoincrement=True)
    id_truong = Column(Integer, ForeignKey("TRUONG.id_truong"), nullable=False)
    ma_nganh = Column(String(20), nullable=False)
    ten_nganh = Column(String(255), nullable=False)
    to_hop_mon = Column(String(100))
    chi_tieu = Column(Integer)

    truong = relationship("Truong", back_populates="nganhs")
    diem_chuan_ls = relationship("DiemChuanLichSu", back_populates="nganh")
    nguyen_vongs = relationship("NguyenVong", back_populates="nganh")


class DiemChuanLichSu(Base):
    __tablename__ = "DIEM_CHUAN_LICH_SU"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_nganh = Column(Integer, ForeignKey("NGANH.id_nganh"), nullable=False)
    nam = Column(Integer, nullable=False)
    diem_chuan = Column(Float, nullable=False)
    chi_tieu_nam = Column(Integer)
    so_ho_so_dang_ky = Column(Integer)

    __table_args__ = (UniqueConstraint("id_nganh", "nam", name="uq_nganh_nam"),)

    nganh = relationship("Nganh", back_populates="diem_chuan_ls")


class HocSinh(Base):
    __tablename__ = "HOC_SINH"

    id_hoc_sinh = Column(Integer, primary_key=True, autoincrement=True)
    ho_ten = Column(String(255), nullable=False)
    truong_thpt = Column(String(255))
    nam_tot_nghiep = Column(Integer)

    tai_khoan = relationship("TaiKhoan", back_populates="hoc_sinh", uselist=False)
    diem_hoc_sinh = relationship("DiemHocSinh", back_populates="hoc_sinh")
    nguyen_vongs = relationship("NguyenVong", back_populates="hoc_sinh")


class TaiKhoan(Base):
    __tablename__ = "TAI_KHOAN"

    id_tai_khoan = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum("hoc_sinh", "admin"), nullable=False, default="hoc_sinh")
    id_hoc_sinh = Column(Integer, ForeignKey("HOC_SINH.id_hoc_sinh"), nullable=True)

    hoc_sinh = relationship("HocSinh", back_populates="tai_khoan")


class DiemHocSinh(Base):
    __tablename__ = "DIEM_HOC_SINH"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_hoc_sinh = Column(Integer, ForeignKey("HOC_SINH.id_hoc_sinh"), nullable=False)
    mon_hoc = Column(String(50), nullable=False)
    diem = Column(Float, nullable=False)
    loai_diem = Column(Enum("thi_thpt", "hoc_ba"), nullable=False)

    hoc_sinh = relationship("HocSinh", back_populates="diem_hoc_sinh")


class NguyenVong(Base):
    __tablename__ = "NGUYEN_VONG"

    id_nguyen_vong = Column(Integer, primary_key=True, autoincrement=True)
    id_hoc_sinh = Column(Integer, ForeignKey("HOC_SINH.id_hoc_sinh"), nullable=False)
    id_nganh = Column(Integer, ForeignKey("NGANH.id_nganh"), nullable=False)
    thu_tu_uu_tien = Column(Integer)
    trong_so_uu_thich = Column(Float, default=1.0)

    hoc_sinh = relationship("HocSinh", back_populates="nguyen_vongs")
    nganh = relationship("Nganh", back_populates="nguyen_vongs")
    ket_qua_du_doan = relationship("KetQuaDuDoan", back_populates="nguyen_vong",
                                    cascade="all, delete-orphan")


class KetQuaDuDoan(Base):
    __tablename__ = "KET_QUA_DU_DOAN"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_nguyen_vong = Column(Integer, ForeignKey("NGUYEN_VONG.id_nguyen_vong"), nullable=False)
    diem_chuan_du_doan = Column(Float)
    xac_suat_do = Column(Float)
    nhom_chien_luoc = Column(Enum("an_toan", "vua_suc", "thu_suc"))
    phien_ban_mo_hinh = Column(String(20))
    ngay_du_doan = Column(DateTime, default=datetime.utcnow)

    nguyen_vong = relationship("NguyenVong", back_populates="ket_qua_du_doan")
