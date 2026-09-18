import os
import sys
import pytest

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from services.auth_service import DichVuXacThuc


def testHocSinhVaoTrangQuanTri(ungDungKiemThu, phienKiemThu):
    email = "hocsinh.test.rbac@dss.edu.vn"
    matKhau = "StudentPass@123"
    DichVuXacThuc.dangKy(email=email, matKhau=matKhau, hoTen="Học Sinh Phân Quyền")

    kqDn = DichVuXacThuc.dangNhap(email=email, matKhau=matKhau)
    token = kqDn["token"]

    ungDungKiemThu.set_cookie("tokenPhien", token)
    res = ungDungKiemThu.get("/quanTri", headers={"Accept": "application/json"})
    assert res.status_code == 403


def testQuanTriVaoTrangQuanTri(ungDungKiemThu, phienKiemThu):
    email = "admin.test.rbac@dss.edu.vn"
    matKhau = "AdminPass@123"
    DichVuXacThuc.dangKy(email=email, matKhau=matKhau, hoTen="Quản Trị Viên", vaiTro="quanTriVien")

    kqDn = DichVuXacThuc.dangNhap(email=email, matKhau=matKhau)
    token = kqDn["token"]

    ungDungKiemThu.set_cookie("tokenPhien", token)
    res = ungDungKiemThu.get("/quanTri", headers={"Accept": "application/json"})
    assert res.status_code == 200


def testHocSinhASuaNguyenVongB(phienKiemThu):
    kqA = DichVuXacThuc.dangKy("hocsinh.a@dss.edu.vn", "Pass@123456", "Học Sinh A")
    kqB = DichVuXacThuc.dangKy("hocsinh.b@dss.edu.vn", "Pass@123456", "Học Sinh B")

    dnA = DichVuXacThuc.dangNhap("hocsinh.a@dss.edu.vn", "Pass@123456")
    dnB = DichVuXacThuc.dangNhap("hocsinh.b@dss.edu.vn", "Pass@123456")

    userA = DichVuXacThuc.xacThucToken(dnA["token"])
    userB = DichVuXacThuc.xacThucToken(dnB["token"])

    assert userA["maHocSinh"] != userB["maHocSinh"]
    assert userA["email"] == "hocsinh.a@dss.edu.vn"
    assert userB["email"] == "hocsinh.b@dss.edu.vn"
