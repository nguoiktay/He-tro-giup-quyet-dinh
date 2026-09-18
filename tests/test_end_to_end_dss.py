import os
import sys
import pytest

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from services.auth_service import DichVuXacThuc
from services.student_service import DichVuHocSinh
from services.recommendation_service import DichVuKhuyenNghi
from services.wishlist_service import DichVuNguyenVong
from services.evaluation_service import DichVuDanhGia
from ml.model_manager import QuanLyMoHinh


def testQuyTrinhXuyenSuotBayBuoc(phienKiemThu):
    QuanLyMoHinh.khoiTao()
    assert QuanLyMoHinh.trangThaiSanSang is True

    email = "thi.sinh.quytrinh@dss.edu.vn"
    matKhau = "MatKhauChuan@2026"
    hoTen = "Trần Thị Mai"

    kqDk = DichVuXacThuc.dangKy(email=email, matKhau=matKhau, hoTen=hoTen)
    assert kqDk["thanhCong"] is True

    kqDn = DichVuXacThuc.dangNhap(email=email, matKhau=matKhau)
    assert kqDn["thanhCong"] is True
    token = kqDn["token"]
    maHs = kqDn["hocSinh"]["maHocSinh"]

    kqDiem = DichVuHocSinh.capNhatDiemMon(maHs, {
        "Toan": 8.8,
        "VatLy": 8.6,
        "HoaHoc": 8.2,
        "NgoaiNgu": 8.5,
        "Van": 7.5,
    })
    assert kqDiem["thanhCong"] is True

    kqSt = DichVuHocSinh.capNhatSoThich(maHs, {
        "CongNgheThongTin": 5,
        "KyThuatCongNghe": 4,
        "KinhTeQuanTri": 3,
    })
    assert kqSt["thanhCong"] is True

    kqTtChung = DichVuHocSinh.capNhatThongTinChung(
        maHocSinh=maHs,
        hoTen=hoTen,
        namDuTuyen=2026,
        nganSachToiDa=30000000.0,
        kyTinhNganSach="nam",
        diaBanUuTien="MienBac",
    )
    assert kqTtChung["thanhCong"] is True

    hoSo = DichVuHocSinh.layHoSoChiTiet(maHs)
    assert hoSo["diemMonHoc"]["Toan"] == 8.8

    kqKn = DichVuKhuyenNghi.locUngVienVaXepHang(
        hoSoHocSinh=hoSo,
        trongSoTuyChinh={"moHinh": 0.70, "taiChinh": 0.20, "khuVuc": 0.10},
        gioiHanTopK=10,
        luuPhien=True,
    )
    assert kqKn["thanhCong"] is True
    danhSachKn = kqKn["danhSachKhuyenNghi"]
    assert len(danhSachKn) > 0

    top1 = danhSachKn[0]
    assert 1.0 <= top1["diemDuDoan"] <= 5.0
    assert 0.0 <= top1["diemXepHang"] <= 1.0
    assert len(top1["lyDo"]) > 0

    maPa1 = danhSachKn[0]["maPhuongAn"]
    maPa2 = danhSachKn[1]["maPhuongAn"]
    kqSs = DichVuNguyenVong.layChiTietSoSanh([maPa1, maPa2])
    assert kqSs["thanhCong"] is True
    assert kqSs["soLuong"] == 2

    kqWhatIf = DichVuKhuyenNghi.chayThuKichBanGiaDinh(
        hoSoGoc=hoSo,
        diemGiaDinh={"Toan": 9.8, "VatLy": 9.6},
        gioiHanTopK=5,
    )
    assert kqWhatIf["thanhCong"] is True

    kqThem1 = DichVuNguyenVong.themNguyenVong(maHs, maPa1)
    kqThem2 = DichVuNguyenVong.themNguyenVong(maHs, maPa2)
    assert kqThem1["thanhCong"] is True
    assert kqThem2["thanhCong"] is True

    dsnv = DichVuNguyenVong.layDanhSachNguyenVong(maHs)
    assert dsnv["soLuong"] == 2

    phienBanHienTai = dsnv["phienBan"]
    kqDoiTt = DichVuNguyenVong.capNhatThuTuHangLoat(
        maHocSinh=maHs,
        danhSachMaPhuongAnMoi=[maPa2, maPa1],
        phienBanClient=phienBanHienTai,
    )
    assert kqDoiTt["thanhCong"] is True

    DichVuXacThuc.dangXuat(token)
    assert DichVuXacThuc.xacThucToken(token) is None

    dnLai = DichVuXacThuc.dangNhap(email=email, matKhau=matKhau)
    assert dnLai["thanhCong"] is True

    dsnvLai = DichVuNguyenVong.layDanhSachNguyenVong(maHs)
    assert dsnvLai["soLuong"] == 2
    assert dsnvLai["danhSach"][0]["maPhuongAn"] == maPa2
    assert dsnvLai["danhSach"][1]["maPhuongAn"] == maPa1

    csvXuat = DichVuNguyenVong.xuatCsvNguyenVong(maHs)
    assert csvXuat.startswith("\ufeff")
    assert maPa2 in csvXuat

    kqPh = DichVuDanhGia.guiPhanHoi(
        maHocSinh=maHs,
        mucDoHaiLong=5,
        tiLeHoanThanh=1.0,
        thoiGianHoanThanhPhut=4.5,
        danhGiaGiaiThich=5,
        yKienDongGop="Hệ thống đề xuất rất chuẩn xác và giải thích rõ ràng!",
        maPhienKhuyenNghi=kqKn.get("maPhienKhuyenNghi"),
    )
    assert kqPh["thanhCong"] is True

    thongKePh = DichVuDanhGia.layThongKePhanHoi()
    assert thongKePh["tongSoPhanHoi"] >= 1
    assert thongKePh["haiLongTrungBinh"] >= 4.0
