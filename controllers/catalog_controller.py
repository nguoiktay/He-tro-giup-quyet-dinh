import os
import sys
from flask import Blueprint, request, jsonify, render_template, g

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from controllers.auth_controller import layNguoiDungHienTai
from services.catalog_service import DichVuDanhMuc

dieuKhienDanhMuc = Blueprint("dieuKhienDanhMuc", __name__)


@dieuKhienDanhMuc.route("/danhMuc", methods=["GET"])
def trangDanhMuc():
    nguoiDung = layNguoiDungHienTai()
    vungMien = request.args.get("vungMien")
    khoiTruong = request.args.get("khoiTruong")
    nhomNganh = request.args.get("nhomNganh")
    tuKhoa = request.args.get("tuKhoa")
    trang = int(request.args.get("trang", 1))

    ketQuaPa = DichVuDanhMuc.layDanhSachPhuongAn(
        nhomNganh=nhomNganh,
        vungMien=vungMien,
        tuKhoa=tuKhoa,
        trang=trang,
        gioiHan=20,
    )
    danhSachToHop = DichVuDanhMuc.layDanhSachToHop()

    if request.is_json:
        return jsonify(ketQuaPa)

    return render_template(
        "university_catalog.html",
        duLieuPhuongAn=ketQuaPa,
        toHopMon=danhSachToHop,
        boLoc={"vungMien": vungMien, "khoiTruong": khoiTruong, "nhomNganh": nhomNganh, "tuKhoa": tuKhoa, "trang": trang},
        nguoiDung=nguoiDung,
    )


@dieuKhienDanhMuc.route("/danhMuc/phuongAn/<maPhuongAn>", methods=["GET"])
def chiTietPhuongAn(maPhuongAn):
    pa = DichVuDanhMuc.layChiTietPhuongAn(maPhuongAn)
    if not pa:
        return jsonify({"thanhCong": False, "thongBao": "Không tìm thấy phương án."}), 404
    return jsonify({"thanhCong": True, "phuongAn": pa})


@dieuKhienDanhMuc.route("/danhMuc/truong/<maTruong>", methods=["GET"])
def chiTietTruong(maTruong):
    truong = DichVuDanhMuc.layChiTietTruong(maTruong)
    if not truong:
        return jsonify({"thanhCong": False, "thongBao": "Không tìm thấy trường."}), 404
    return jsonify({"thanhCong": True, "truong": truong})
