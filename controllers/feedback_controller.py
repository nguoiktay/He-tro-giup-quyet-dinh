import os
import sys
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, g

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from controllers.auth_controller import yeuCauHocSinh
from services.evaluation_service import DichVuDanhGia

dieuKhienPhanHoi = Blueprint("dieuKhienPhanHoi", __name__)


@dieuKhienPhanHoi.route("/phanHoi", methods=["GET", "POST"])
@yeuCauHocSinh
def trangPhanHoi():
    maHs = g.nguoiDung.get("maHocSinh")
    if request.method == "GET":
        thongBao = request.args.get("thongBao")
        return render_template("system_feedback.html", thongBao=thongBao, nguoiDung=g.nguoiDung)

    duLieu = request.get_json() if request.is_json else request.form
    mucDoHaiLong = duLieu.get("mucDoHaiLong", 5)
    tiLeHoanThanh = duLieu.get("tiLeHoanThanh", 1.0)
    thoiGianHoanThanhPhut = duLieu.get("thoiGianHoanThanhPhut", 5.0)
    danhGiaGiaiThich = duLieu.get("danhGiaGiaiThich", 5)
    yKienDongGop = duLieu.get("yKienDongGop")
    maPhienKn = duLieu.get("maPhienKhuyenNghi")

    ketQua = DichVuDanhGia.guiPhanHoi(
        maHocSinh=maHs,
        mucDoHaiLong=mucDoHaiLong,
        tiLeHoanThanh=tiLeHoanThanh,
        thoiGianHoanThanhPhut=thoiGianHoanThanhPhut,
        danhGiaGiaiThich=danhGiaGiaiThich,
        yKienDongGop=yKienDongGop,
        maPhienKhuyenNghi=maPhienKn,
    )

    if request.is_json:
        status_code = 200 if ketQua["thanhCong"] else 400
        return jsonify(ketQua), status_code

    if ketQua["thanhCong"]:
        return redirect(url_for("dieuKhienPhanHoi.trangPhanHoi", thongBao="Cảm ơn bạn đã gửi đánh giá hệ thống!"))
    return render_template("system_feedback.html", thongBaoLoi=ketQua["thongBao"], nguoiDung=g.nguoiDung)
