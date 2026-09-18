import os
import sys
import pytest

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from services.auth_service import DichVuXacThuc
from services.wishlist_service import DichVuNguyenVong, khuKhaiThacCongThucCsv
from database.connection import layPhienKetNoi
from database.models import PhuongAn


def testNguyenVongKhongTrungLap(phienKiemThu):
    kq = DichVuXacThuc.dangKy("hocsinh.nv.trung@dss.edu.vn", "Pass@123456", "Học Sinh Trùng NV")
    dn = DichVuXacThuc.dangNhap("hocsinh.nv.trung@dss.edu.vn", "Pass@123456")
    maHs = dn["hocSinh"]["maHocSinh"]

    pa = phienKiemThu.query(PhuongAn).first()
    assert pa is not None

    kq1 = DichVuNguyenVong.themNguyenVong(maHs, pa.maPhuongAn)
    assert kq1["thanhCong"] is True

    kq2 = DichVuNguyenVong.themNguyenVong(maHs, pa.maPhuongAn)
    assert kq2["thanhCong"] is False
    assert "đã có trong danh sách" in kq2["thongBao"]


def testXungDotHaiTabOptimisticLock(phienKiemThu):
    kq = DichVuXacThuc.dangKy("hocsinh.concurrency@dss.edu.vn", "Pass@123456", "Học Sinh Đồng Thời")
    dn = DichVuXacThuc.dangNhap("hocsinh.concurrency@dss.edu.vn", "Pass@123456")
    maHs = dn["hocSinh"]["maHocSinh"]

    cacPa = phienKiemThu.query(PhuongAn).limit(3).all()
    for pa in cacPa:
        DichVuNguyenVong.themNguyenVong(maHs, pa.maPhuongAn)

    dsBanDau = DichVuNguyenVong.layDanhSachNguyenVong(maHs)
    phienBanHienTai = dsBanDau["phienBan"]

    danhSachPaMoi = [pa.maPhuongAn for pa in reversed(cacPa)]
    kqTab1 = DichVuNguyenVong.capNhatThuTuHangLoat(
        maHocSinh=maHs,
        danhSachMaPhuongAnMoi=danhSachPaMoi,
        phienBanClient=phienBanHienTai,
    )
    assert kqTab1["thanhCong"] is True
    assert kqTab1["phienBanMoi"] > phienBanHienTai

    kqTab2 = DichVuNguyenVong.capNhatThuTuHangLoat(
        maHocSinh=maHs,
        danhSachMaPhuongAnMoi=danhSachPaMoi,
        phienBanClient=phienBanHienTai,
    )
    assert kqTab2["thanhCong"] is False
    assert kqTab2.get("xungDot") is True
    assert "thay đổi từ một tab hoặc thiết bị khác" in kqTab2["thongBao"]


def testXuatCsvAnToanVaBOM(phienKiemThu):
    assert khuKhaiThacCongThucCsv("=SUM(A1:A10)") == "'=SUM(A1:A10)"
    assert khuKhaiThacCongThucCsv("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert khuKhaiThacCongThucCsv("-123") == "'-123"
    assert khuKhaiThacCongThucCsv("@test") == "'@test"
    assert khuKhaiThacCongThucCsv("Đại học Bách Khoa") == "Đại học Bách Khoa"

    kq = DichVuXacThuc.dangKy("hocsinh.csv@dss.edu.vn", "Pass@123456", "Học Sinh CSV")
    dn = DichVuXacThuc.dangNhap("hocsinh.csv@dss.edu.vn", "Pass@123456")
    maHs = dn["hocSinh"]["maHocSinh"]

    pa = phienKiemThu.query(PhuongAn).first()
    DichVuNguyenVong.themNguyenVong(maHs, pa.maPhuongAn)

    csvText = DichVuNguyenVong.xuatCsvNguyenVong(maHs)
    assert csvText.startswith("\ufeff")
    assert "Thứ tự nguyện vọng" in csvText
    assert pa.maPhuongAn in csvText


def testSoSanhPhuongAn(phienKiemThu):
    cacPa = phienKiemThu.query(PhuongAn).limit(3).all()
    danhSachMaPa = [pa.maPhuongAn for pa in cacPa]

    kq = DichVuNguyenVong.layChiTietSoSanh(danhSachMaPa)
    assert kq["thanhCong"] is True
    assert kq["soLuong"] == len(cacPa)
    assert len(kq["danhSachSoSanh"]) == len(cacPa)
