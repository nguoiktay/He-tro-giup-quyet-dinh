import os
import sys
import pytest

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from config import CauHinhKiemThu
from app import app
from database.connection import taoDongCo, PhienKetNoi
from database.migrations import khoiTaoLuocDo, xoaVaTaoLaiLuocDo


from database.models import (
    TruongDaiHoc,
    NganhHoc,
    PhuongAn,
    ToHopXetTuyen,
    DiemChuan,
)
from ml.model_manager import QuanLyMoHinh


@pytest.fixture(scope="session")
def thietLapDatabaseKiemThu():
    dongCoTest = taoDongCo(CauHinhKiemThu.SQLALCHEMY_DATABASE_URI)
    xoaVaTaoLaiLuocDo(CauHinhKiemThu.SQLALCHEMY_DATABASE_URI)

    PhienKetNoi.configure(bind=dongCoTest)
    phien = PhienKetNoi()
    try:
        t1 = TruongDaiHoc(maTruong="BKA", tenTruong="Đại học Bách Khoa Hà Nội", khoiTruong="CongLap", vungMien="MienBac")
        t2 = TruongDaiHoc(maTruong="KHA", tenTruong="Đại học Kinh tế Quốc dân", khoiTruong="CongLap", vungMien="MienBac")
        t3 = TruongDaiHoc(maTruong="QST", tenTruong="Đại học Khoa học Tự nhiên TPHCM", khoiTruong="CongLap", vungMien="MienNam")
        phien.add_all([t1, t2, t3])

        th1 = ToHopXetTuyen(maToHop="A00", tenToHop="Toán, Lý, Hóa", danhSachMon="Toan, VatLy, HoaHoc")
        th2 = ToHopXetTuyen(maToHop="A01", tenToHop="Toán, Lý, Anh", danhSachMon="Toan, VatLy, NgoaiNgu")
        th3 = ToHopXetTuyen(maToHop="D01", tenToHop="Toán, Văn, Anh", danhSachMon="Toan, Van, NgoaiNgu")
        phien.add_all([th1, th2, th3])

        n1 = NganhHoc(maNganh="7480201", tenNganh="Công nghệ Thông tin", nhomNganh="CongNgheThongTin")
        n2 = NganhHoc(maNganh="7340101", tenNganh="Quản trị Kinh doanh", nhomNganh="KinhTeQuanTri")
        n3 = NganhHoc(maNganh="7520101", tenNganh="Kỹ thuật Cơ khí", nhomNganh="KyThuatCongNghe")
        phien.add_all([n1, n2, n3])
        phien.flush()

        pa0 = PhuongAn(
            maPhuongAn="BKA_QS_DiemThiTHPT",
            maTruong="BKA",
            maNganh="7480201",
            tenChuongTrinh="Chương trình Tài năng",
            phuongThuc="DiemThiTHPT",
            hocPhiKy=0.0,
            namTuyenSinh=2026,
            chiTieu=50,
        )
        pa1 = PhuongAn(
            maPhuongAn="BKA_IT1_DiemThiTHPT",
            maTruong="BKA",
            maNganh="7480201",
            tenChuongTrinh="Khoa học Máy tính",
            phuongThuc="DiemThiTHPT",
            hocPhiKy=15000000.0,
            namTuyenSinh=2026,
            chiTieu=200,
        )
        pa2 = PhuongAn(
            maPhuongAn="KHA_KT1_DiemThiTHPT",
            maTruong="KHA",
            maNganh="7340101",
            tenChuongTrinh="Quản trị Kinh doanh Quốc tế",
            phuongThuc="DiemThiTHPT",
            hocPhiKy=14000000.0,
            namTuyenSinh=2026,
            chiTieu=150,
        )
        pa3 = PhuongAn(
            maPhuongAn="QST_TN1_DiemThiTHPT",
            maTruong="QST",
            maNganh="7520101",
            tenChuongTrinh="Kỹ thuật Công nghệ",
            phuongThuc="DiemThiTHPT",
            hocPhiKy=12000000.0,
            namTuyenSinh=2026,
            chiTieu=100,
        )
        pa4 = PhuongAn(
            maPhuongAn="BKA_CK_DiemThiTHPT",
            maTruong="BKA",
            maNganh="7520101",
            tenChuongTrinh="Cơ điện tử tiên tiến",
            phuongThuc="DiemThiTHPT",
            hocPhiKy=16000000.0,
            namTuyenSinh=2026,
            chiTieu=100,
        )
        phien.add_all([pa0, pa1, pa2, pa3, pa4])
        phien.flush()

        phien.add(DiemChuan(maPhuongAn=pa1.maPhuongAn, maToHop="A00", nam=2025, diemTrungTuyen=28.5))
        phien.add(DiemChuan(maPhuongAn=pa2.maPhuongAn, maToHop="D01", nam=2025, diemTrungTuyen=27.2))
        phien.add(DiemChuan(maPhuongAn=pa3.maPhuongAn, maToHop="A00", nam=2025, diemTrungTuyen=24.5))
        phien.add(DiemChuan(maPhuongAn=pa4.maPhuongAn, maToHop="A01", nam=2025, diemTrungTuyen=26.8))

        phien.commit()
    finally:
        PhienKetNoi.remove()

    QuanLyMoHinh.khoiTao()

    yield dongCoTest


@pytest.fixture
def phienKiemThu(thietLapDatabaseKiemThu):
    PhienKetNoi.configure(bind=thietLapDatabaseKiemThu)
    phien = PhienKetNoi()
    yield phien
    phien.rollback()
    PhienKetNoi.remove()


@pytest.fixture
def ungDungKiemThu(thietLapDatabaseKiemThu):
    app.config.from_object(CauHinhKiemThu)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
