import os
import sys
from functools import wraps
from flask import (
    Blueprint,
    request,
    jsonify,
    render_template,
    redirect,
    url_for,
    make_response,
    g,
)

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from services.auth_service import DichVuXacThuc

dieuKhienXacThuc = Blueprint("dieuKhienXacThuc", __name__)


def layTokenHienTai():
    token = request.cookies.get("tokenPhien")
    if not token:
        authHeader = request.headers.get("Authorization")
        if authHeader and authHeader.startswith("Bearer "):
            token = authHeader[7:].strip()
    return token


def layNguoiDungHienTai():
    token = layTokenHienTai()
    if not token:
        return None
    return DichVuXacThuc.xacThucToken(token)


def yeuCauDangNhap(f):
    @wraps(f)
    def hamBoc(*args, **kwargs):
        nguoiDung = layNguoiDungHienTai()
        if not nguoiDung:
            if request.is_json or request.path.startswith("/api/") or "application/json" in request.headers.get("Accept", ""):
                return jsonify({"thanhCong": False, "thongBao": "Yêu cầu đăng nhập."}), 401
            return redirect(url_for("dieuKhienXacThuc.trangDangNhap"))
        g.nguoiDung = nguoiDung
        return f(*args, **kwargs)

    return hamBoc


def yeuCauQuanTri(f):
    @wraps(f)
    def hamBoc(*args, **kwargs):
        nguoiDung = layNguoiDungHienTai()
        if not nguoiDung or nguoiDung.get("vaiTro") != "quanTriVien":
            if request.is_json or request.path.startswith("/api/") or "application/json" in request.headers.get("Accept", ""):
                return jsonify({"thanhCong": False, "thongBao": "Truy cập bị từ chối: Quyền quản trị viên."}), 403
            return redirect(url_for("dieuKhienXacThuc.trangDangNhap"))
        g.nguoiDung = nguoiDung
        return f(*args, **kwargs)

    return hamBoc


def yeuCauHocSinh(f):
    @wraps(f)
    def hamBoc(*args, **kwargs):
        nguoiDung = layNguoiDungHienTai()
        if not nguoiDung or nguoiDung.get("vaiTro") != "hocSinh":
            if request.is_json or request.path.startswith("/api/") or "application/json" in request.headers.get("Accept", ""):
                return jsonify({"thanhCong": False, "thongBao": "Yêu cầu quyền học sinh."}), 403
            return redirect(url_for("dieuKhienXacThuc.trangDangNhap"))
        g.nguoiDung = nguoiDung
        return f(*args, **kwargs)

    return hamBoc


@dieuKhienXacThuc.route("/dangKy", methods=["GET", "POST"])
def trangDangKy():
    if request.method == "GET":
        if layNguoiDungHienTai():
            return redirect(url_for("dieuKhienKhuyenNghi.trangKhuyenNghi"))
        return render_template("register.html")

    duLieu = request.get_json() if request.is_json else request.form
    email = duLieu.get("email")
    matKhau = duLieu.get("matKhau")
    hoTen = duLieu.get("hoTen")
    soDienThoai = duLieu.get("soDienThoai")

    ketQua = DichVuXacThuc.dangKy(email=email, matKhau=matKhau, hoTen=hoTen, soDienThoai=soDienThoai)
    if not ketQua["thanhCong"]:
        if request.is_json:
            return jsonify(ketQua), 400
        return render_template("register.html", thongBaoLoi=ketQua["thongBao"])

    if request.is_json:
        return jsonify(ketQua), 200
    return redirect(url_for("dieuKhienXacThuc.trangDangNhap", thongBao="Đăng ký thành công, vui lòng đăng nhập."))


@dieuKhienXacThuc.route("/dangNhap", methods=["GET", "POST"])
def trangDangNhap():
    if request.method == "GET":
        nguoiDung = layNguoiDungHienTai()
        if nguoiDung:
            if nguoiDung.get("vaiTro") == "quanTriVien":
                return redirect(url_for("dieuKhienQuanTri.trangQuanTri"))
            return redirect(url_for("dieuKhienKhuyenNghi.trangKhuyenNghi"))
        thongBao = request.args.get("thongBao")
        return render_template("login.html", thongBao=thongBao)

    duLieu = request.get_json() if request.is_json else request.form
    email = duLieu.get("email")
    matKhau = duLieu.get("matKhau")

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    userAgent = request.headers.get("User-Agent")

    ketQua = DichVuXacThuc.dangNhap(email=email, matKhau=matKhau, diaChiIp=ip, tacNhanNguoiDung=userAgent)
    if not ketQua["thanhCong"]:
        if request.is_json:
            return jsonify(ketQua), 401
        return render_template("login.html", thongBaoLoi=ketQua["thongBao"])

    rawToken = ketQua["token"]
    if request.is_json:
        phanHoi = make_response(jsonify(ketQua))
    else:
        if ketQua["taiKhoan"]["vaiTro"] == "quanTriVien":
            phanHoi = make_response(redirect(url_for("dieuKhienQuanTri.trangQuanTri")))
        else:
            phanHoi = make_response(redirect(url_for("dieuKhienKhuyenNghi.trangKhuyenNghi")))

    phanHoi.set_cookie(
        "tokenPhien",
        rawToken,
        httponly=True,
        samesite="Lax",
        secure=False,
        max_age=86400,
    )
    phanHoi.set_cookie("csrfToken", ketQua["csrfToken"], httponly=False, samesite="Lax", max_age=86400)
    return phanHoi


@dieuKhienXacThuc.route("/dangXuat", methods=["POST", "GET"])
def dangXuat():
    token = layTokenHienTai()
    if token:
        DichVuXacThuc.dangXuat(token)

    if request.is_json:
        phanHoi = make_response(jsonify({"thanhCong": True, "thongBao": "Đăng xuất thành công."}))
    else:
        phanHoi = make_response(redirect(url_for("dieuKhienKhuyenNghi.trangChonTruong")))

    phanHoi.delete_cookie("tokenPhien")
    phanHoi.delete_cookie("csrfToken")
    return phanHoi


@dieuKhienXacThuc.route("/doiMatKhau", methods=["GET", "POST"])
@yeuCauDangNhap
def trangDoiMatKhau():
    if request.method == "GET":
        return render_template("change_password.html", nguoiDung=g.nguoiDung)

    duLieu = request.get_json() if request.is_json else request.form
    matKhauCu = duLieu.get("matKhauCu")
    matKhauMoi = duLieu.get("matKhauMoi")

    ketQua = DichVuXacThuc.doiMatKhau(
        maTaiKhoan=g.nguoiDung["maTaiKhoan"],
        matKhauCu=matKhauCu,
        matKhauMoi=matKhauMoi,
    )
    if not ketQua["thanhCong"]:
        if request.is_json:
            return jsonify(ketQua), 400
        return render_template("change_password.html", thongBaoLoi=ketQua["thongBao"], nguoiDung=g.nguoiDung)

    if request.is_json:
        phanHoi = make_response(jsonify(ketQua))
    else:
        phanHoi = make_response(
            redirect(url_for("dieuKhienXacThuc.trangDangNhap", thongBao="Đổi mật khẩu thành công. Vui lòng đăng nhập lại."))
        )

    phanHoi.delete_cookie("tokenPhien")
    phanHoi.delete_cookie("csrfToken")
    return phanHoi
