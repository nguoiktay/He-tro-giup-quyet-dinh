import os
import sys

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

import logging
from database.connection import CoSoDuLieu, taoDongCo
from database.models import (
    TaiKhoan,
    PhienDangNhap,
    HocSinh,
    DiemMonHoc,
    SoThichHocSinh,
    TruongDaiHoc,
    NganhHoc,
    PhuongAn,
    ToHopXetTuyen,
    DiemChuan,
    NguonDuLieu,
    TuongTac,
    MauDanhGia,
    PhienBanDuLieu,
    PhienBanMoHinh,
    PhienKhuyenNghi,
    ChiTietKhuyenNghi,
    DanhSachNguyenVong,
    NguyenVong,
    PhanHoi,
    NhatKyQuanTri,
)
from config import CauHinh, CauHinhKiemThu

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def khoiTaoLuocDo(duongDanKetNoi=None):
    dongCo = taoDongCo(duongDanKetNoi)
    logging.info("Bắt đầu tạo lược đồ 21 bảng trong cơ sở dữ liệu MySQL...")
    CoSoDuLieu.metadata.create_all(dongCo)
    logging.info("Hoàn tất tạo cấu trúc bảng thành công!")

def xoaVaTaoLaiLuocDo(duongDanKetNoi=None):
    dongCo = taoDongCo(duongDanKetNoi)
    logging.info("Xóa toàn bộ các bảng cũ và tạo lại...")
    CoSoDuLieu.metadata.drop_all(dongCo)
    CoSoDuLieu.metadata.create_all(dongCo)
    logging.info("Lược đồ CSDL đã được thiết lập mới hoàn toàn!")

if __name__ == "__main__":
    duongDan = CauHinh.SQLALCHEMY_DATABASE_URI
    if len(sys.argv) > 1 and sys.argv[1] == "--kiemThu":
        duongDan = CauHinhKiemThu.SQLALCHEMY_DATABASE_URI
    khoiTaoLuocDo(duongDan)
