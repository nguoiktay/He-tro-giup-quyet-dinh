import os
import sys
import json
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, g

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from controllers.auth_controller import yeuCauQuanTri
from database.connection import layPhienKetNoi, dongPhienKetNoi
from database.models import (
    TaiKhoan,
    HocSinh,
    TruongDaiHoc,
    NganhHoc,
    PhuongAn,
    DiemChuan,
    PhienBanMoHinh,
    MauDanhGia,
)
from services.evaluation_service import DichVuDanhGia
from ml.model_manager import QuanLyMoHinh
from ml.evaluate_model import doDoTreSuyLuan
from services.student_service import DichVuHocSinh
from services.catalog_service import DichVuDanhMuc

dieuKhienQuanTri = Blueprint("dieuKhienQuanTri", __name__)


@dieuKhienQuanTri.route("/quanTri", methods=["GET"])
@yeuCauQuanTri
def trangQuanTri():
    phien = layPhienKetNoi()
    try:
        soTaiKhoan = phien.query(TaiKhoan).count()
        soHocSinh = phien.query(HocSinh).count()
        soTruong = phien.query(TruongDaiHoc).count()
        soNganh = phien.query(NganhHoc).count()
        soPhuongAn = phien.query(PhuongAn).count()
        soDiemChuan = phien.query(DiemChuan).count()
        soMauDanhGia = phien.query(MauDanhGia).count()

        cacPhienBanMoHinh = (
            phien.query(PhienBanMoHinh)
            .order_by(PhienBanMoHinh.thoiDiemTao.desc())
            .all()
        )
        dsPhienBan = [
            {
                "maPhienBanMoHinh": pb.maPhienBanMoHinh,
                "tenPhienBan": pb.tenPhienBan,
                "thuatToan": pb.thuatToan,
                "maBamChecksum": pb.maBamChecksum[:12] + "...",
                "dangKichHoat": pb.dangKichHoat,
                "thoiDiemTao": pb.thoiDiemTao.strftime("%Y-%m-%d %H:%M"),
            }
            for pb in cacPhienBanMoHinh
        ]

        thongKePhanHoi = DichVuDanhGia.layThongKePhanHoi()
        trangThaiMoHinh = QuanLyMoHinh.layTrangThai()

        thongKe = {
            "soTaiKhoan": soTaiKhoan,
            "soHocSinh": soHocSinh,
            "soTruong": soTruong,
            "soNganh": soNganh,
            "soPhuongAn": soPhuongAn,
            "soDiemChuan": soDiemChuan,
            "soMauDanhGia": soMauDanhGia,
            "phienBanMoHinh": dsPhienBan,
            "trangThaiMoHinh": trangThaiMoHinh,
            "thongKePhanHoi": thongKePhanHoi,
        }

        if request.is_json or "application/json" in request.headers.get("Accept", ""):
            return jsonify(thongKe)

        return render_template("admin_dashboard.html", thongKe=thongKe, nguoiDung=g.nguoiDung)
    finally:
        dongPhienKetNoi()


@dieuKhienQuanTri.route("/quanTri/kichHoatMoHinh", methods=["POST"])
@yeuCauQuanTri
def kichHoatMoHinh():
    duLieu = request.get_json() if request.is_json else request.form
    maPb = duLieu.get("maPhienBanMoHinh")
    if not maPb:
        return jsonify({"thanhCong": False, "thongBao": "Thiếu mã phiên bản mô hình."}), 400

    phien = layPhienKetNoi()
    try:
        phien.query(PhienBanMoHinh).update({"dangKichHoat": False})
        pb = phien.query(PhienBanMoHinh).filter_by(maPhienBanMoHinh=int(maPb)).first()
        if not pb:
            return jsonify({"thanhCong": False, "thongBao": "Không tìm thấy phiên bản mô hình."}), 404
        pb.dangKichHoat = True
        phien.commit()

        QuanLyMoHinh.khoiTao()
        return jsonify({"thanhCong": True, "thongBao": f"Đã kích hoạt phiên bản {pb.tenPhienBan} thành công."})
    except Exception as e:
        phien.rollback()
        return jsonify({"thanhCong": False, "thongBao": f"Lỗi kích hoạt: {str(e)}"}), 500
    finally:
        dongPhienKetNoi()


@dieuKhienQuanTri.route("/quanTri/kiemTraDoTre", methods=["POST"])
@yeuCauQuanTri
def kiemTraDoTre():
    hoSoMau = {
        "maHocSinh": 1,
        "diemMonHoc": {"Toan": 8.5, "Van": 7.5, "NgoaiNgu": 8.0, "VatLy": 8.2, "HoaHoc": 7.8, "SinhHoc": 6.5},
        "soThich": {"CongNgheThongTin": 5, "KyThuatCongNghe": 4},
        "nganSachToiDa": 25000000.0,
        "kyTinhNganSach": "nam",
        "diaBanUuTien": "MienBac",
    }
    paData = DichVuDanhMuc.layDanhSachPhuongAn(gioiHan=500)
    danhSachPa = paData.get("danhSach", [])
    if not danhSachPa:
        return jsonify({"thanhCong": False, "thongBao": "Không có ứng viên để đo độ trễ."}), 400

    ketQuaDoTre = doDoTreSuyLuan(hoSoMau, danhSachPa, soLanLap=10)
    return jsonify({"thanhCong": True, "ketQuaDoTre": ketQuaDoTre})
