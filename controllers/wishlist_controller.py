import os
import sys
from flask import (
    Blueprint,
    request,
    jsonify,
    render_template,
    Response,
    g,
)

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from controllers.auth_controller import yeuCauHocSinh
from services.wishlist_service import DichVuNguyenVong
from services.student_service import DichVuHocSinh

dieuKhienNguyenVong = Blueprint("dieuKhienNguyenVong", __name__)


@dieuKhienNguyenVong.route("/nguyenVong", methods=["GET"])
@yeuCauHocSinh
def trangDanhSachNguyenVong():
    maHs = g.nguoiDung.get("maHocSinh")
    ds = DichVuNguyenVong.layDanhSachNguyenVong(maHs)
    if request.is_json:
        return jsonify(ds)
    return render_template("wishlist.html", danhSachNguyenVong=ds, nguoiDung=g.nguoiDung)


@dieuKhienNguyenVong.route("/nguyenVong/them", methods=["POST"])
@yeuCauHocSinh
def themVaoNguyenVong():
    maHs = g.nguoiDung.get("maHocSinh")
    duLieu = request.get_json() if request.is_json else request.form
    maPa = duLieu.get("maPhuongAn")
    ghiChu = duLieu.get("ghiChu")

    if not maPa:
        return jsonify({"thanhCong": False, "thongBao": "Thiếu mã phương án."}), 400

    ketQua = DichVuNguyenVong.themNguyenVong(maHs, maPa, ghiChu)
    if ketQua["thanhCong"]:
        DichVuHocSinh.ghiNhanTuongTac(maHs, maPa, "luu")

    status_code = 200 if ketQua["thanhCong"] else 400
    return jsonify(ketQua), status_code


@dieuKhienNguyenVong.route("/nguyenVong/xoa", methods=["POST"])
@yeuCauHocSinh
def xoaKhoiNguyenVong():
    maHs = g.nguoiDung.get("maHocSinh")
    duLieu = request.get_json() if request.is_json else request.form
    maPa = duLieu.get("maPhuongAn")

    if not maPa:
        return jsonify({"thanhCong": False, "thongBao": "Thiếu mã phương án."}), 400

    ketQua = DichVuNguyenVong.xoaNguyenVong(maHs, maPa)
    if ketQua["thanhCong"]:
        DichVuHocSinh.ghiNhanTuongTac(maHs, maPa, "boLuu")

    status_code = 200 if ketQua["thanhCong"] else 400
    return jsonify(ketQua), status_code


@dieuKhienNguyenVong.route("/nguyenVong/capNhatThuTu", methods=["POST"])
@yeuCauHocSinh
def capNhatThuTu():
    maHs = g.nguoiDung.get("maHocSinh")
    duLieu = request.get_json() if request.is_json else request.form

    danhSachMoi = duLieu.get("danhSachMaPhuongAn", [])
    phienBanClient = duLieu.get("phienBan")

    if not isinstance(danhSachMoi, list):
        return jsonify({"thanhCong": False, "thongBao": "Danh sách phương án không đúng định dạng."}), 400

    ketQua = DichVuNguyenVong.capNhatThuTuHangLoat(maHs, danhSachMoi, phienBanClient)
    if ketQua.get("xungDot"):
        return jsonify(ketQua), 409

    status_code = 200 if ketQua["thanhCong"] else 400
    return jsonify(ketQua), status_code


@dieuKhienNguyenVong.route("/soSanh", methods=["GET"])
@yeuCauHocSinh
def trangSoSanh():
    maPaStr = request.args.get("danhSachMaPhuongAn", "")
    danhSachMaPa = [p.strip() for p in maPaStr.split(",") if p.strip()]

    duLieuSoSanh = None
    if danhSachMaPa:
        duLieuSoSanh = DichVuNguyenVong.layChiTietSoSanh(danhSachMaPa)
        maHs = g.nguoiDung.get("maHocSinh")
        for p in danhSachMaPa:
            DichVuHocSinh.ghiNhanTuongTac(maHs, p, "soSanh")

    if request.is_json:
        return jsonify(duLieuSoSanh or {"thanhCong": False, "thongBao": "Chưa chọn phương án để so sánh."})

    hoSo = DichVuHocSinh.layHoSoChiTiet(g.nguoiDung.get("maHocSinh"))
    return render_template(
        "scenario_comparison.html",
        duLieuSoSanh=duLieuSoSanh,
        danhSachMaPa=danhSachMaPa,
        hoSo=hoSo,
        nguoiDung=g.nguoiDung,
    )


@dieuKhienNguyenVong.route("/nguyenVong/xuatCsv", methods=["GET"])
@yeuCauHocSinh
def xuatCsv():
    maHs = g.nguoiDung.get("maHocSinh")
    noiDungCsv = DichVuNguyenVong.xuatCsvNguyenVong(maHs)

    return Response(
        noiDungCsv,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=danhSachNguyenVong_DH2026.csv",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
