import os
import sys
import pytest

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from services.recommendation_service import DichVuKhuyenNghi


def testCongThucXepHang():
    diemMh = DichVuKhuyenNghi.tinhDiemMoHinh(4.2)
    assert diemMh == 0.8

    diemTc, thieu = DichVuKhuyenNghi.tinhDiemTaiChinh(20000000, 10000000, "nam")
    assert diemTc == 1.0
    assert thieu is False

    diemKv = DichVuKhuyenNghi.tinhDiemKhuVuc("MienBac", "MienBac")
    assert diemKv == 1.0

    diemXh = DichVuKhuyenNghi.tinhDiemXepHang(
        diemMoHinh=diemMh,
        diemTaiChinh=diemTc,
        diemKhuVuc=diemKv,
        wMoHinh=0.70,
        wTaiChinh=0.20,
        wKhuVuc=0.10,
    )
    assert diemXh == 0.86


def testXuLyThieuHocPhiHoacNganSach():
    diemTc, thieu = DichVuKhuyenNghi.tinhDiemTaiChinh(None, 15000000, "nam")
    assert diemTc is None
    assert thieu is False

    diemXh = DichVuKhuyenNghi.tinhDiemXepHang(
        diemMoHinh=0.8,
        diemTaiChinh=None,
        diemKhuVuc=1.0,
        wMoHinh=0.70,
        wTaiChinh=0.20,
        wKhuVuc=0.10,
    )
    assert diemXh == 0.825

    diemTc2, thieu2 = DichVuKhuyenNghi.tinhDiemTaiChinh(20000000, None, "nam")
    assert diemTc2 is None
    assert thieu2 is True


def testLocUngVienDieuKienCung():
    hoSoBatBuoc = {
        "maHocSinh": 999,
        "diemMonHoc": {"Toan": 8.0, "Van": 8.0, "NgoaiNgu": 8.0},
        "soThich": {},
        "nganSachToiDa": 10000000.0,
        "kyTinhNganSach": "nam",
        "batBuocNganSach": True,
        "diaBanUuTien": "MienBac",
        "batBuocDiaBan": False,
    }

    kq = DichVuKhuyenNghi.locUngVienVaXepHang(
        hoSoHocSinh=hoSoBatBuoc,
        gioiHanTopK=10,
        luuPhien=False,
    )
    assert kq["thanhCong"] is True
    for item in kq["danhSachKhuyenNghi"]:
        chiPhiKy = item["hocPhiKy"]
        if chiPhiKy is not None:
            assert chiPhiKy * 2 <= 10000000.0
