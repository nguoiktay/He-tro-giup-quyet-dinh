import os
import sys
import pytest

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from services.auth_service import DichVuXacThuc
from services.student_service import DichVuHocSinh


def testDiemNgoaiThangBiChan(phienKiemThu):
    kq = DichVuXacThuc.dangKy("hocsinh.diem@dss.edu.vn", "Pass@123456", "Học Sinh Điểm")
    dn = DichVuXacThuc.dangNhap("hocsinh.diem@dss.edu.vn", "Pass@123456")
    maHs = dn["hocSinh"]["maHocSinh"]

    kqLoi = DichVuHocSinh.capNhatDiemMon(maHs, {"Toan": 11.5})
    assert kqLoi["thanhCong"] is False
    assert "nằm ngoài thang điểm 0 - 10" in kqLoi["thongBao"]

    kqLoiAm = DichVuHocSinh.capNhatDiemMon(maHs, {"Van": -1.0})
    assert kqLoiAm["thanhCong"] is False
    assert "nằm ngoài thang điểm 0 - 10" in kqLoiAm["thongBao"]


def testDiemHopLeLuuThanhCong(phienKiemThu):
    kq = DichVuXacThuc.dangKy("hocsinh.diem.hople@dss.edu.vn", "Pass@123456", "Học Sinh Điểm Chuẩn")
    dn = DichVuXacThuc.dangNhap("hocsinh.diem.hople@dss.edu.vn", "Pass@123456")
    maHs = dn["hocSinh"]["maHocSinh"]

    kqDung = DichVuHocSinh.capNhatDiemMon(maHs, {"Toan": 8.5, "Van": 7.8, "NgoaiNgu": 9.0})
    assert kqDung["thanhCong"] is True

    hoSo = DichVuHocSinh.layHoSoChiTiet(maHs)
    assert hoSo["diemMonHoc"]["Toan"] == 8.5
    assert hoSo["diemMonHoc"]["Van"] == 7.8
    assert hoSo["diemMonHoc"]["NgoaiNgu"] == 9.0


def testNganSachAmVaBoTrong(phienKiemThu):
    kq = DichVuXacThuc.dangKy("hocsinh.ngansach@dss.edu.vn", "Pass@123456", "Học Sinh Ngân Sách")
    dn = DichVuXacThuc.dangNhap("hocsinh.ngansach@dss.edu.vn", "Pass@123456")
    maHs = dn["hocSinh"]["maHocSinh"]

    kqAm = DichVuHocSinh.capNhatThongTinChung(maHs, hoTen="Học Sinh Ngân Sách", nganSachToiDa=-5000000)
    assert kqAm["thanhCong"] is False
    assert "không được là số âm" in kqAm["thongBao"]

    kqTrong = DichVuHocSinh.capNhatThongTinChung(maHs, hoTen="Học Sinh Ngân Sách", nganSachToiDa=None)
    assert kqTrong["thanhCong"] is True


def testGhiNhanTuongTac(phienKiemThu):
    kq = DichVuXacThuc.dangKy("hocsinh.tuongtac@dss.edu.vn", "Pass@123456", "Học Sinh Tương Tác")
    dn = DichVuXacThuc.dangNhap("hocsinh.tuongtac@dss.edu.vn", "Pass@123456")
    maHs = dn["hocSinh"]["maHocSinh"]

    kqTt = DichVuHocSinh.ghiNhanTuongTac(maHs, "BKA_IT1_DiemThiTHPT", "xem")
    assert kqTt["thanhCong"] is True
