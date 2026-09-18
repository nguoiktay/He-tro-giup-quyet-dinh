import os
import sys
import secrets
from flask import Flask, request, jsonify, render_template, redirect, url_for, g

thuMucGoc = os.path.dirname(os.path.abspath(__file__))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from config import CauHinh
from database.connection import dongPhienKetNoi
from ml.model_manager import QuanLyMoHinh

app = Flask(
    __name__,
    template_folder=os.path.join(thuMucGoc, "templates"),
    static_folder=os.path.join(thuMucGoc, "static"),
)
app.config.from_object(CauHinh)

from controllers.auth_controller import dieuKhienXacThuc, layNguoiDungHienTai
from controllers.student_controller import dieuKhienHocSinh
from controllers.catalog_controller import dieuKhienDanhMuc
from controllers.recommendation_controller import dieuKhienKhuyenNghi
from controllers.wishlist_controller import dieuKhienNguyenVong
from controllers.feedback_controller import dieuKhienPhanHoi
from controllers.admin_controller import dieuKhienQuanTri

app.register_blueprint(dieuKhienXacThuc)
app.register_blueprint(dieuKhienHocSinh)
app.register_blueprint(dieuKhienDanhMuc)
app.register_blueprint(dieuKhienKhuyenNghi)
app.register_blueprint(dieuKhienNguyenVong)
app.register_blueprint(dieuKhienPhanHoi)
app.register_blueprint(dieuKhienQuanTri)


@app.before_request
def thietLapPhienVaCsrf():
    g.nguoiDung = layNguoiDungHienTai()

    cacDuongDanBoQuaCsrf = ["/dangNhap", "/dangKy", "/dangXuat", "/api/deXuatChonTruong"]
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        if request.path in cacDuongDanBoQuaCsrf or app.config.get("TESTING"):
            return None

        csrfHeader = request.headers.get("X-CSRF-Token")
        csrfCookie = request.cookies.get("csrfToken")
        csrfForm = request.form.get("_csrfToken") if request.form else None

        tokenGui = csrfHeader or csrfForm
        if not tokenGui or not csrfCookie or tokenGui != csrfCookie:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"thanhCong": False, "thongBao": "Yêu cầu bị từ chối: Mã CSRF token không hợp lệ hoặc bị thiếu."}), 403
            return render_template("login.html", thongBaoLoi="Phiên làm việc hoặc mã xác thực CSRF không hợp lệ, vui lòng đăng nhập lại."), 403


@app.context_processor
def truyenDuLieuGiaoDien():
    csrfToken = request.cookies.get("csrfToken")
    if not csrfToken:
        csrfToken = secrets.token_hex(16)
    return {
        "nguoiDungHienTai": g.get("nguoiDung"),
        "csrfToken": csrfToken,
    }


@app.teardown_appcontext
def giaiPhongKetNoi(ngoaiLe=None):
    dongPhienKetNoi(ngoaiLe)


@app.route("/")
def trangChu():
    return redirect(url_for("dieuKhienKhuyenNghi.trangChonTruong"))


with app.app_context():
    QuanLyMoHinh.khoiTao()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
