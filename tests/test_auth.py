import os
import sys
import pytest

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from services.auth_service import DichVuXacThuc


def testDangKyHopLe(phienKiemThu):
    email = "test.dangky@dss.edu.vn"
    matKhau = "MatKhauChuan@123"
    hoTen = "Lê Hoàng Nam"

    kq = DichVuXacThuc.dangKy(email=email, matKhau=matKhau, hoTen=hoTen)
    assert kq["thanhCong"] is True
    assert "maTaiKhoan" in kq


def testEmailTrung(phienKiemThu):
    email = "test.trung@dss.edu.vn"
    kq1 = DichVuXacThuc.dangKy(email=email, matKhau="MatKhau1@123", hoTen="Học Sinh 1")
    assert kq1["thanhCong"] is True

    kq2 = DichVuXacThuc.dangKy(email=email.upper(), matKhau="MatKhau2@123", hoTen="Học Sinh 2")
    assert kq2["thanhCong"] is False
    assert "đã được sử dụng" in kq2["thongBao"]


def testSaiMatKhau(phienKiemThu):
    email = "test.saimatkhau@dss.edu.vn"
    matKhau = "MatKhauDung@123"
    DichVuXacThuc.dangKy(email=email, matKhau=matKhau, hoTen="Học Sinh Test")

    kqSai = DichVuXacThuc.dangNhap(email=email, matKhau="MatKhauSai@999")
    assert kqSai["thanhCong"] is False
    assert "không chính xác" in kqSai["thongBao"]

    kqDung = DichVuXacThuc.dangNhap(email=email, matKhau=matKhau)
    assert kqDung["thanhCong"] is True
    assert "token" in kqDung


def testDangXuatVoHieuHoaPhien(phienKiemThu):
    email = "test.dangxuat@dss.edu.vn"
    matKhau = "MatKhauChuan@123"
    DichVuXacThuc.dangKy(email=email, matKhau=matKhau, hoTen="Học Sinh Đăng Xuất")

    kqDn = DichVuXacThuc.dangNhap(email=email, matKhau=matKhau)
    token = kqDn["token"]

    xacThuc1 = DichVuXacThuc.xacThucToken(token)
    assert xacThuc1 is not None

    DichVuXacThuc.dangXuat(token)

    xacThuc2 = DichVuXacThuc.xacThucToken(token)
    assert xacThuc2 is None


def testDoiMatKhauThuHoiPhien(phienKiemThu):
    email = "test.doimk@dss.edu.vn"
    matKhauCu = "MatKhauCu@123"
    matKhauMoi = "MatKhauMoi@456"
    DichVuXacThuc.dangKy(email=email, matKhau=matKhauCu, hoTen="Học Sinh Đổi MK")

    kqDn = DichVuXacThuc.dangNhap(email=email, matKhau=matKhauCu)
    tokenCu = kqDn["token"]
    maTk = kqDn["taiKhoan"]["maTaiKhoan"]

    kqDoi = DichVuXacThuc.doiMatKhau(maTaiKhoan=maTk, matKhauCu=matKhauCu, matKhauMoi=matKhauMoi)
    assert kqDoi["thanhCong"] is True

    assert DichVuXacThuc.xacThucToken(tokenCu) is None

    kqDnMoi = DichVuXacThuc.dangNhap(email=email, matKhau=matKhauMoi)
    assert kqDnMoi["thanhCong"] is True
