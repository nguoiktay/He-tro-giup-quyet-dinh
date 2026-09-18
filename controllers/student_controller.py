import os
import sys
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, g

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from controllers.auth_controller import yeuCauHocSinh
from services.student_service import DichVuHocSinh

dieuKhienHocSinh = Blueprint("dieuKhienHocSinh", __name__)


@dieuKhienHocSinh.route("/hoSo", methods=["GET"])
@yeuCauHocSinh
def trangHoSo():
    maHs = g.nguoiDung.get("maHocSinh")
    hoSo = DichVuHocSinh.layHoSoChiTiet(maHs)
    if request.is_json:
        return jsonify({"thanhCong": True, "hoSo": hoSo})
    return render_template("student_profile.html", hoSo=hoSo, nguoiDung=g.nguoiDung)


@dieuKhienHocSinh.route("/hoSo/thongTin", methods=["POST"])
@yeuCauHocSinh
def capNhatThongTin():
    maHs = g.nguoiDung.get("maHocSinh")
    duLieu = request.get_json() if request.is_json else request.form

    hoTen = duLieu.get("hoTen")
    soDienThoai = duLieu.get("soDienThoai")
    namDuTuyen = duLieu.get("namDuTuyen", 2026)
    nganSachToiDa = duLieu.get("nganSachToiDa")
    kyTinhNganSach = duLieu.get("kyTinhNganSach", "nam")
    diaBanUuTien = duLieu.get("diaBanUuTien")
    batBuocNganSach = duLieu.get("batBuocNganSach") in [True, "true", "True", "1", "on"]
    batBuocDiaBan = duLieu.get("batBuocDiaBan") in [True, "true", "True", "1", "on"]
    mucTieuNgheNghiep = duLieu.get("mucTieuNgheNghiep")
    uuTienCaNhan = duLieu.get("uuTienCaNhan")

    ketQua = DichVuHocSinh.capNhatThongTinChung(
        maHocSinh=maHs,
        hoTen=hoTen,
        soDienThoai=soDienThoai,
        namDuTuyen=namDuTuyen,
        nganSachToiDa=nganSachToiDa if nganSachToiDa not in [None, ""] else None,
        kyTinhNganSach=kyTinhNganSach,
        diaBanUuTien=diaBanUuTien if diaBanUuTien not in [None, ""] else None,
        batBuocNganSach=batBuocNganSach,
        batBuocDiaBan=batBuocDiaBan,
        mucTieuNgheNghiep=mucTieuNgheNghiep,
        uuTienCaNhan=uuTienCaNhan,
    )

    if request.is_json:
        status_code = 200 if ketQua["thanhCong"] else 400
        return jsonify(ketQua), status_code
    return redirect(url_for("dieuKhienHocSinh.trangHoSo"))


@dieuKhienHocSinh.route("/hoSo/diemMon", methods=["POST"])
@yeuCauHocSinh
def capNhatDiem():
    maHs = g.nguoiDung.get("maHocSinh")
    duLieu = request.get_json() if request.is_json else request.form

    cacMon = ["Toan", "Van", "NgoaiNgu", "VatLy", "HoaHoc", "SinhHoc", "LichSu", "DiaLy", "GDCD"]
    bangDiem = {}
    for mon in cacMon:
        if mon in duLieu and duLieu.get(mon) not in [None, ""]:
            bangDiem[mon] = duLieu.get(mon)

    ketQua = DichVuHocSinh.capNhatDiemMon(maHs, bangDiem)
    if request.is_json:
        status_code = 200 if ketQua["thanhCong"] else 400
        return jsonify(ketQua), status_code
    return redirect(url_for("dieuKhienHocSinh.trangHoSo"))


@dieuKhienHocSinh.route("/hoSo/soThich", methods=["POST"])
@yeuCauHocSinh
def capNhatSoThich():
    maHs = g.nguoiDung.get("maHocSinh")
    duLieu = request.get_json() if request.is_json else request.form

    cacNhom = [
        "CongNgheThongTin",
        "KinhTeQuanTri",
        "KyThuatCongNghe",
        "YDuoc",
        "SuPhamNhanVan",
        "LuatNgoaiGiao",
        "NongLamThuySan",
    ]
    bangSoThich = {}
    for nhom in cacNhom:
        if nhom in duLieu and duLieu.get(nhom) not in [None, ""]:
            bangSoThich[nhom] = duLieu.get(nhom)

    ketQua = DichVuHocSinh.capNhatSoThich(maHs, bangSoThich)
    if request.is_json:
        status_code = 200 if ketQua["thanhCong"] else 400
        return jsonify(ketQua), status_code
    return redirect(url_for("dieuKhienHocSinh.trangHoSo"))


@dieuKhienHocSinh.route("/tuongTac/ghiNhan", methods=["POST"])
@yeuCauHocSinh
def ghiNhanTuongTac():
    maHs = g.nguoiDung.get("maHocSinh")
    duLieu = request.get_json() if request.is_json else request.form

    maPhuongAn = duLieu.get("maPhuongAn")
    loaiTuongTac = duLieu.get("loaiTuongTac", "xem")
    maPhienKn = duLieu.get("maPhienKhuyenNghi")
    viTri = duLieu.get("viTriHienThi")

    ketQua = DichVuHocSinh.ghiNhanTuongTac(
        maHocSinh=maHs,
        maPhuongAn=maPhuongAn,
        loaiTuongTac=loaiTuongTac,
        maPhienKhuyenNghi=maPhienKn,
        viTriHienThi=viTri,
    )
    return jsonify(ketQua)
