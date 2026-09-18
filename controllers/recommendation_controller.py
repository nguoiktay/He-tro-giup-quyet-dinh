import os
import sys
from flask import Blueprint, request, jsonify, render_template, g

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from controllers.auth_controller import yeuCauHocSinh, layNguoiDungHienTai
from services.student_service import DichVuHocSinh
from services.recommendation_service import DichVuKhuyenNghi
from services.wishlist_service import DichVuNguyenVong
from ml.model_manager import QuanLyMoHinh

dieuKhienKhuyenNghi = Blueprint("dieuKhienKhuyenNghi", __name__)


@dieuKhienKhuyenNghi.route("/chonTruong", methods=["GET"])
def trangChonTruong():
    nguoiDung = layNguoiDungHienTai()
    maHs = nguoiDung.get("maHocSinh") if nguoiDung else None
    hoSo = DichVuHocSinh.layHoSoChiTiet(maHs) if maHs else None
    dsNguyenVong = DichVuNguyenVong.layDanhSachNguyenVong(maHs) if maHs else {"danhSach": [], "phienBan": 1}
    trangThaiMoHinh = QuanLyMoHinh.layTrangThai()
    ketQuaKn = None
    if hoSo and trangThaiMoHinh["sanSang"]:
        ketQuaKn = DichVuKhuyenNghi.locUngVienVaXepHang(
            hoSoHocSinh=hoSo,
            trongSoTuyChinh={"moHinh": 0.70, "taiChinh": 0.20, "khuVuc": 0.10},
            gioiHanTopK=20,
            luuPhien=False,
        )

    return render_template(
        "chon_truong.html",
        hoSo=hoSo,
        trangThaiMoHinh=trangThaiMoHinh,
        ketQuaKhuyenNghi=ketQuaKn,
        nguoiDung=nguoiDung,
        dsNguyenVong=dsNguyenVong,
    )


@dieuKhienKhuyenNghi.route("/api/deXuatChonTruong", methods=["POST"])
def apiDeXuatChonTruong():
    nguoiDung = layNguoiDungHienTai()
    maHs = nguoiDung.get("maHocSinh") if nguoiDung else None
    hoSo = DichVuHocSinh.layHoSoChiTiet(maHs) if maHs else {}
    if hoSo is None:
        hoSo = {}

    duLieu = request.get_json() if request.is_json else request.form

    maToHop = duLieu.get("toHop", "A00")
    try:
        diemMon1 = float(duLieu.get("diemMon1", 8.0))
        diemMon2 = float(duLieu.get("diemMon2", 8.0))
        diemMon3 = float(duLieu.get("diemMon3", 8.0))
    except (ValueError, TypeError):
        diemMon1, diemMon2, diemMon3 = 8.0, 8.0, 8.0

    tongDiem = round(diemMon1 + diemMon2 + diemMon3, 2)
    nhomNganh = duLieu.get("nhomNganh", "tatCa")
    vungMien = duLieu.get("vungMien", "tatCa")
    nganSach = duLieu.get("nganSach")

    toHopMonMap = {
        "A00": ("Toan", "VatLy", "HoaHoc"),
        "A01": ("Toan", "VatLy", "NgoaiNgu"),
        "A02": ("Toan", "VatLy", "SinhHoc"),
        "B00": ("Toan", "HoaHoc", "SinhHoc"),
        "B08": ("Toan", "SinhHoc", "NgoaiNgu"),
        "C00": ("Van", "LichSu", "DiaLy"),
        "C01": ("Toan", "Van", "VatLy"),
        "C03": ("Van", "Toan", "LichSu"),
        "D01": ("Toan", "Van", "NgoaiNgu"),
        "D07": ("Toan", "HoaHoc", "NgoaiNgu"),
        "D08": ("Toan", "SinhHoc", "NgoaiNgu"),
        "D14": ("Van", "LichSu", "NgoaiNgu"),
        "D15": ("Van", "DiaLy", "NgoaiNgu"),
    }

    mon1, mon2, mon3 = toHopMonMap.get(maToHop, ("Toan", "VatLy", "HoaHoc"))
    diemMonDict = hoSo.get("diemMonHoc", {}).copy() if hoSo else {}
    diemMonDict[mon1] = diemMon1
    diemMonDict[mon2] = diemMon2
    diemMonDict[mon3] = diemMon3

    soThichDict = hoSo.get("soThich", {}).copy() if hoSo else {}
    if nhomNganh and nhomNganh != "tatCa":
        soThichDict[nhomNganh] = 5

    hoSoXuLy = {
        "maHocSinh": maHs,
        "hoTen": hoSo.get("hoTen", "Thí sinh") if hoSo else "Thí sinh",
        "diemMonHoc": diemMonDict,
        "soThich": soThichDict,
        "nganSachToiDa": float(nganSach) if nganSach not in [None, "", "tatCa"] else None,
        "kyTinhNganSach": "nam",
        "diaBanUuTien": vungMien if vungMien not in [None, "", "tatCa"] else None,
        "batBuocNganSach": False,
        "batBuocDiaBan": False,
        "tongDiemXetTuyen": tongDiem,
        "toHopChon": maToHop,
        "nhomNganhLoc": nhomNganh,
        "diaBanLoc": vungMien,
    }

    wMoHinh = float(duLieu.get("wMoHinh", 0.70))
    wTaiChinh = float(duLieu.get("wTaiChinh", 0.20))
    wKhuVuc = float(duLieu.get("wKhuVuc", 0.10))
    trongSo = {"moHinh": wMoHinh, "taiChinh": wTaiChinh, "khuVuc": wKhuVuc}

    ketQua = DichVuKhuyenNghi.locUngVienVaXepHang(
        hoSoHocSinh=hoSoXuLy,
        trongSoTuyChinh=trongSo,
        gioiHanTopK=25,
        luuPhien=(maHs is not None),
    )

    if maHs:
        DichVuHocSinh.capNhatDiemMon(maHs, diemMonDict)
        if nhomNganh and nhomNganh != "tatCa":
            DichVuHocSinh.capNhatSoThich(maHs, {nhomNganh: 5})

    return jsonify(ketQua)


@dieuKhienKhuyenNghi.route("/khuyenNghi", methods=["GET"])
@yeuCauHocSinh
def trangKhuyenNghi():
    return trangChonTruong()


@dieuKhienKhuyenNghi.route("/khuyenNghi/tinhToan", methods=["POST"])
@yeuCauHocSinh
def tinhToanKhuyenNghi():
    maHs = g.nguoiDung.get("maHocSinh")
    hoSo = DichVuHocSinh.layHoSoChiTiet(maHs)
    if not hoSo:
        return jsonify({"thanhCong": False, "thongBao": "Chưa tìm thấy hồ sơ học sinh."}), 404

    duLieu = request.get_json() if request.is_json else request.form
    wMoHinh = float(duLieu.get("wMoHinh", 0.70))
    wTaiChinh = float(duLieu.get("wTaiChinh", 0.20))
    wKhuVuc = float(duLieu.get("wKhuVuc", 0.10))

    if wMoHinh <= 0:
        return jsonify({"thanhCong": False, "thongBao": "Trọng số mô hình Random Forest phải lớn hơn 0."}), 400

    trongSo = {"moHinh": wMoHinh, "taiChinh": wTaiChinh, "khuVuc": wKhuVuc}
    gioiHan = int(duLieu.get("gioiHan", 20))

    ketQua = DichVuKhuyenNghi.locUngVienVaXepHang(
        hoSoHocSinh=hoSo,
        trongSoTuyChinh=trongSo,
        gioiHanTopK=gioiHan,
        luuPhien=True,
    )
    status_code = 200 if ketQua["thanhCong"] else 400
    return jsonify(ketQua), status_code


@dieuKhienKhuyenNghi.route("/khuyenNghi/thuKichBan", methods=["POST"])
@yeuCauHocSinh
def thuKichBanGiaDinh():
    maHs = g.nguoiDung.get("maHocSinh")
    hoSo = DichVuHocSinh.layHoSoChiTiet(maHs)
    if not hoSo:
        return jsonify({"thanhCong": False, "thongBao": "Chưa tìm thấy hồ sơ học sinh."}), 404

    duLieu = request.get_json() if request.is_json else request.form

    diemGiaDinh = duLieu.get("diemGiaDinh", {})
    nganSachGiaDinh = duLieu.get("nganSachGiaDinh")

    wMoHinh = float(duLieu.get("wMoHinh", 0.70))
    wTaiChinh = float(duLieu.get("wTaiChinh", 0.20))
    wKhuVuc = float(duLieu.get("wKhuVuc", 0.10))
    trongSo = {"moHinh": wMoHinh, "taiChinh": wTaiChinh, "khuVuc": wKhuVuc}

    ketQua = DichVuKhuyenNghi.chayThuKichBanGiaDinh(
        hoSoGoc=hoSo,
        diemGiaDinh=diemGiaDinh,
        nganSachGiaDinh=nganSachGiaDinh,
        trongSoGiaDinh=trongSo,
        gioiHanTopK=20,
    )
    return jsonify(ketQua)
