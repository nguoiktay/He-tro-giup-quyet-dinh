import os
import sys
from sqlalchemy import or_, desc

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from database.connection import layPhienKetNoi, dongPhienKetNoi
from database.models import (
    TruongDaiHoc,
    NganhHoc,
    PhuongAn,
    DiemChuan,
    ToHopXetTuyen,
)


class DichVuDanhMuc:

    @classmethod
    def layDanhSachTruong(cls, vungMien=None, khoiTruong=None, tuKhoa=None, trang=1, gioiHan=30):
        phien = layPhienKetNoi()
        try:
            truyVan = phien.query(TruongDaiHoc)
            if vungMien:
                truyVan = truyVan.filter(TruongDaiHoc.vungMien == vungMien)
            if khoiTruong:
                truyVan = truyVan.filter(TruongDaiHoc.khoiTruong == khoiTruong)
            if tuKhoa:
                tuKhoaLike = f"%{tuKhoa.strip()}%"
                truyVan = truyVan.filter(
                    or_(
                        TruongDaiHoc.maTruong.like(tuKhoaLike),
                        TruongDaiHoc.tenTruong.like(tuKhoaLike),
                        TruongDaiHoc.tinhThanh.like(tuKhoaLike),
                    )
                )
            tongSo = truyVan.count()
            danhSach = (
                truyVan.order_by(TruongDaiHoc.maTruong)
                .offset((trang - 1) * gioiHan)
                .limit(gioiHan)
                .all()
            )
            return {
                "tongSo": tongSo,
                "trang": trang,
                "gioiHan": gioiHan,
                "danhSach": [
                    {
                        "maTruong": t.maTruong,
                        "tenTruong": t.tenTruong,
                        "khoiTruong": t.khoiTruong,
                        "tinhThanh": t.tinhThanh,
                        "vungMien": t.vungMien,
                    }
                    for t in danhSach
                ],
            }
        finally:
            dongPhienKetNoi()

    @classmethod
    def layChiTietTruong(cls, maTruong):
        phien = layPhienKetNoi()
        try:
            t = phien.query(TruongDaiHoc).filter_by(maTruong=maTruong).first()
            if not t:
                return None
            cacPhuongAn = (
                phien.query(PhuongAn)
                .filter_by(maTruong=maTruong)
                .limit(50)
                .all()
            )
            return {
                "maTruong": t.maTruong,
                "tenTruong": t.tenTruong,
                "khoiTruong": t.khoiTruong,
                "tinhThanh": t.tinhThanh,
                "vungMien": t.vungMien,
                "website": t.website,
                "soLuongPhuongAn": len(cacPhuongAn),
                "phuongAnTieuBieu": [
                    {
                        "maPhuongAn": pa.maPhuongAn,
                        "tenChuongTrinh": pa.tenChuongTrinh,
                        "phuongThuc": pa.phuongThuc,
                        "hocPhiKy": pa.hocPhiKy,
                    }
                    for pa in cacPhuongAn[:10]
                ],
            }
        finally:
            dongPhienKetNoi()

    @classmethod
    def layDanhSachNganh(cls, nhomNganh=None, tuKhoa=None):
        phien = layPhienKetNoi()
        try:
            truyVan = phien.query(NganhHoc)
            if nhomNganh:
                truyVan = truyVan.filter(NganhHoc.nhomNganh == nhomNganh)
            if tuKhoa:
                tuKhoaLike = f"%{tuKhoa.strip()}%"
                truyVan = truyVan.filter(
                    or_(
                        NganhHoc.maNganh.like(tuKhoaLike),
                        NganhHoc.tenNganh.like(tuKhoaLike),
                    )
                )
            danhSach = truyVan.order_by(NganhHoc.tenNganh).limit(100).all()
            return [
                {
                    "maNganh": n.maNganh,
                    "tenNganh": n.tenNganh,
                    "nhomNganh": n.nhomNganh,
                    "moTa": n.moTa,
                }
                for n in danhSach
            ]
        finally:
            dongPhienKetNoi()

    @classmethod
    def layDanhSachPhuongAn(
        cls,
        maTruong=None,
        nhomNganh=None,
        phuongThuc=None,
        vungMien=None,
        tuKhoa=None,
        hocPhiToiDa=None,
        trang=1,
        gioiHan=25,
    ):
        phien = layPhienKetNoi()
        try:
            truyVan = phien.query(PhuongAn).join(TruongDaiHoc).join(NganhHoc)
            if maTruong:
                truyVan = truyVan.filter(PhuongAn.maTruong == maTruong)
            if nhomNganh:
                truyVan = truyVan.filter(NganhHoc.nhomNganh == nhomNganh)
            if phuongThuc:
                truyVan = truyVan.filter(PhuongAn.phuongThuc == phuongThuc)
            if vungMien:
                truyVan = truyVan.filter(TruongDaiHoc.vungMien == vungMien)
            if hocPhiToiDa is not None:
                truyVan = truyVan.filter(
                    or_(PhuongAn.hocPhiKy == None, PhuongAn.hocPhiKy <= float(hocPhiToiDa))
                )
            if tuKhoa:
                tuKhoaLike = f"%{tuKhoa.strip()}%"
                truyVan = truyVan.filter(
                    or_(
                        PhuongAn.tenChuongTrinh.like(tuKhoaLike),
                        TruongDaiHoc.tenTruong.like(tuKhoaLike),
                        TruongDaiHoc.maTruong.like(tuKhoaLike),
                    )
                )

            tongSo = truyVan.count()
            danhSach = (
                truyVan.order_by(TruongDaiHoc.maTruong, PhuongAn.tenChuongTrinh)
                .offset((trang - 1) * gioiHan)
                .limit(gioiHan)
                .all()
            )

            ketQua = []
            for pa in danhSach:
                diemGanNhat = (
                    phien.query(DiemChuan)
                    .filter_by(maPhuongAn=pa.maPhuongAn)
                    .order_by(desc(DiemChuan.nam))
                    .first()
                )
                ketQua.append(
                    {
                        "maPhuongAn": pa.maPhuongAn,
                        "maTruong": pa.maTruong,
                        "tenTruong": pa.truongDaiHoc.tenTruong,
                        "khoiTruong": pa.truongDaiHoc.khoiTruong,
                        "vungMien": pa.truongDaiHoc.vungMien,
                        "maNganh": pa.maNganh,
                        "tenNganh": pa.nganhHoc.tenNganh,
                        "nhomNganh": pa.nganhHoc.nhomNganh,
                        "tenChuongTrinh": pa.tenChuongTrinh,
                        "phuongThuc": pa.phuongThuc,
                        "hocPhiKy": pa.hocPhiKy,
                        "diemChuanGanNhat": diemGanNhat.diemTrungTuyen if diemGanNhat else None,
                        "namDiemChuan": diemGanNhat.nam if diemGanNhat else None,
                    }
                )

            return {
                "tongSo": tongSo,
                "trang": trang,
                "gioiHan": gioiHan,
                "danhSach": ketQua,
            }
        finally:
            dongPhienKetNoi()

    @classmethod
    def layChiTietPhuongAn(cls, maPhuongAn):
        phien = layPhienKetNoi()
        try:
            pa = phien.query(PhuongAn).filter_by(maPhuongAn=maPhuongAn).first()
            if not pa:
                return None

            diemCacNam = (
                phien.query(DiemChuan)
                .filter_by(maPhuongAn=maPhuongAn)
                .order_by(desc(DiemChuan.nam))
                .all()
            )
            lichSuDiem = [
                {
                    "nam": dc.nam,
                    "maToHop": dc.maToHop,
                    "diemTrungTuyen": dc.diemTrungTuyen,
                    "thangDiem": dc.thangDiem,
                }
                for dc in diemCacNam
            ]

            return {
                "maPhuongAn": pa.maPhuongAn,
                "maTruong": pa.maTruong,
                "tenTruong": pa.truongDaiHoc.tenTruong,
                "khoiTruong": pa.truongDaiHoc.khoiTruong,
                "vungMien": pa.truongDaiHoc.vungMien,
                "tinhThanh": pa.truongDaiHoc.tinhThanh,
                "maNganh": pa.maNganh,
                "tenNganh": pa.nganhHoc.tenNganh,
                "nhomNganh": pa.nganhHoc.nhomNganh,
                "tenChuongTrinh": pa.tenChuongTrinh,
                "coSo": pa.coSo,
                "phuongThuc": pa.phuongThuc,
                "hocPhiKy": pa.hocPhiKy,
                "donViTien": pa.donViTien,
                "chiTieu": pa.chiTieu,
                "dieuKienXetTuyen": pa.dieuKienXetTuyen,
                "lichSuDiemChuan": lichSuDiem,
            }
        finally:
            dongPhienKetNoi()

    @classmethod
    def layDanhSachToHop(cls):
        phien = layPhienKetNoi()
        try:
            danhSach = phien.query(ToHopXetTuyen).order_by(ToHopXetTuyen.maToHop).all()
            return [
                {
                    "maToHop": th.maToHop,
                    "tenToHop": th.tenToHop,
                    "danhSachMon": th.danhSachMon,
                }
                for th in danhSach
            ]
        finally:
            dongPhienKetNoi()
