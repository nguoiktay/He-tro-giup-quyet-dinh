import os
import sys
import csv
import io
from datetime import datetime, timezone
from sqlalchemy import desc

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from database.connection import layPhienKetNoi, dongPhienKetNoi
from database.models import (
    DanhSachNguyenVong,
    NguyenVong,
    PhuongAn,
    TruongDaiHoc,
    NganhHoc,
    DiemChuan,
)


def khuKhaiThacCongThucCsv(giaTri):
    if giaTri is None:
        return ""
    chuoi = str(giaTri).strip()
    if chuoi and chuoi[0] in ["=", "+", "-", "@"]:
        return "'" + chuoi
    return chuoi


class DichVuNguyenVong:

    @classmethod
    def layDanhSachNguyenVong(cls, maHocSinh):
        phien = layPhienKetNoi()
        try:
            dsnv = phien.query(DanhSachNguyenVong).filter_by(maHocSinh=maHocSinh).first()
            if not dsnv:
                dsnv = DanhSachNguyenVong(
                    maHocSinh=maHocSinh,
                    tenDanhSach="Danh sách nguyện vọng chính thức",
                    phienBan=1,
                )
                phien.add(dsnv)
                phien.commit()

            danhSach = []
            for nv in dsnv.nguyenVong:
                pa = nv.phuongAn
                diemGanNhat = (
                    phien.query(DiemChuan)
                    .filter_by(maPhuongAn=pa.maPhuongAn)
                    .order_by(desc(DiemChuan.nam))
                    .first()
                )
                danhSach.append({
                    "maNguyenVong": nv.maNguyenVong,
                    "maPhuongAn": pa.maPhuongAn,
                    "thuTu": nv.thuTu,
                    "tenTruong": pa.truongDaiHoc.tenTruong,
                    "maTruong": pa.maTruong,
                    "tenNganh": pa.nganhHoc.tenNganh,
                    "tenChuongTrinh": pa.tenChuongTrinh,
                    "phuongThuc": pa.phuongThuc,
                    "hocPhiKy": pa.hocPhiKy,
                    "vungMien": pa.truongDaiHoc.vungMien,
                    "diemChuanGanNhat": diemGanNhat.diemTrungTuyen if diemGanNhat else None,
                    "ghiChu": nv.ghiChu,
                })

            danhSach.sort(key=lambda x: x["thuTu"])
            return {
                "maDanhSach": dsnv.maDanhSach,
                "tenDanhSach": dsnv.tenDanhSach,
                "phienBan": dsnv.phienBan,
                "soLuong": len(danhSach),
                "danhSach": danhSach,
            }
        finally:
            dongPhienKetNoi()

    @classmethod
    def themNguyenVong(cls, maHocSinh, maPhuongAn, ghiChu=None):
        phien = layPhienKetNoi()
        try:
            dsnv = phien.query(DanhSachNguyenVong).filter_by(maHocSinh=maHocSinh).first()
            if not dsnv:
                dsnv = DanhSachNguyenVong(maHocSinh=maHocSinh, phienBan=1)
                phien.add(dsnv)
                phien.flush()

            nvTonTai = (
                phien.query(NguyenVong)
                .filter_by(maDanhSach=dsnv.maDanhSach, maPhuongAn=maPhuongAn)
                .first()
            )
            if nvTonTai:
                return {
                    "thanhCong": False,
                    "thongBao": "Phương án này đã có trong danh sách nguyện vọng của bạn.",
                }

            soLuongHienCo = (
                phien.query(NguyenVong).filter_by(maDanhSach=dsnv.maDanhSach).count()
            )
            thuTuMoi = soLuongHienCo + 1

            nvMoi = NguyenVong(
                maDanhSach=dsnv.maDanhSach,
                maPhuongAn=maPhuongAn,
                thuTu=thuTuMoi,
                ghiChu=ghiChu,
            )
            phien.add(nvMoi)
            dsnv.phienBan += 1
            phien.commit()

            return {
                "thanhCong": True,
                "thongBao": f"Đã thêm vào nguyện vọng số {thuTuMoi}.",
                "phienBanMoi": dsnv.phienBan,
            }
        except Exception as e:
            phien.rollback()
            return {"thanhCong": False, "thongBao": f"Lỗi khi thêm nguyện vọng: {str(e)}"}
        finally:
            dongPhienKetNoi()

    @classmethod
    def xoaNguyenVong(cls, maHocSinh, maPhuongAn):
        phien = layPhienKetNoi()
        try:
            dsnv = phien.query(DanhSachNguyenVong).filter_by(maHocSinh=maHocSinh).first()
            if not dsnv:
                return {"thanhCong": False, "thongBao": "Không tìm thấy danh sách nguyện vọng."}

            nv = (
                phien.query(NguyenVong)
                .filter_by(maDanhSach=dsnv.maDanhSach, maPhuongAn=maPhuongAn)
                .first()
            )
            if not nv:
                return {"thanhCong": False, "thongBao": "Phương án không tồn tại trong danh sách."}

            phien.delete(nv)
            phien.flush()

            cacNvConLai = (
                phien.query(NguyenVong)
                .filter_by(maDanhSach=dsnv.maDanhSach)
                .order_by(NguyenVong.thuTu)
                .all()
            )
            for idx, item in enumerate(cacNvConLai, start=1):
                item.thuTu = idx

            dsnv.phienBan += 1
            phien.commit()
            return {"thanhCong": True, "thongBao": "Đã xóa nguyện vọng khỏi danh sách.", "phienBanMoi": dsnv.phienBan}
        except Exception as e:
            phien.rollback()
            return {"thanhCong": False, "thongBao": f"Lỗi khi xóa nguyện vọng: {str(e)}"}
        finally:
            dongPhienKetNoi()

    @classmethod
    def capNhatThuTuHangLoat(cls, maHocSinh, danhSachMaPhuongAnMoi, phienBanClient):
        phien = layPhienKetNoi()
        try:
            dsnv = phien.query(DanhSachNguyenVong).filter_by(maHocSinh=maHocSinh).first()
            if not dsnv:
                return {"thanhCong": False, "thongBao": "Không tìm thấy danh sách nguyện vọng."}

            if phienBanClient is not None and dsnv.phienBan != int(phienBanClient):
                return {
                    "thanhCong": False,
                    "xungDot": True,
                    "thongBao": "Danh sách nguyện vọng đã được thay đổi từ một tab hoặc thiết bị khác. Vui lòng tải lại trang để thấy dữ liệu mới nhất.",
                }

            if len(danhSachMaPhuongAnMoi) != len(set(danhSachMaPhuongAnMoi)):
                return {"thanhCong": False, "thongBao": "Danh sách nguyện vọng không được chứa phương án trùng lặp."}

            cacNvHienCo = {
                nv.maPhuongAn: nv
                for nv in phien.query(NguyenVong).filter_by(maDanhSach=dsnv.maDanhSach).all()
            }

            for nv in cacNvHienCo.values():
                nv.thuTu = -nv.thuTu
            phien.flush()

            for idx, maPa in enumerate(danhSachMaPhuongAnMoi, start=1):
                if maPa in cacNvHienCo:
                    cacNvHienCo[maPa].thuTu = idx

            dsnv.phienBan += 1
            phien.commit()
            return {
                "thanhCong": True,
                "thongBao": "Cập nhật thứ tự nguyện vọng thành công.",
                "phienBanMoi": dsnv.phienBan,
            }
        except Exception as e:
            phien.rollback()
            return {"thanhCong": False, "thongBao": f"Lỗi cập nhật thứ tự: {str(e)}"}
        finally:
            dongPhienKetNoi()

    @classmethod
    def layChiTietSoSanh(cls, danhSachMaPhuongAn):
        if not danhSachMaPhuongAn or len(danhSachMaPhuongAn) < 2 or len(danhSachMaPhuongAn) > 4:
            return {
                "thanhCong": False,
                "thongBao": "Chức năng so sánh yêu cầu chọn từ 2 đến 4 phương án.",
            }

        phien = layPhienKetNoi()
        try:
            danhSach = []
            for maPa in danhSachMaPhuongAn:
                pa = phien.query(PhuongAn).filter_by(maPhuongAn=maPa).first()
                if not pa:
                    continue
                diemCacNam = (
                    phien.query(DiemChuan)
                    .filter_by(maPhuongAn=maPa)
                    .order_by(desc(DiemChuan.nam))
                    .all()
                )
                lichSu = {dc.nam: dc.diemTrungTuyen for dc in diemCacNam}
                danhSach.append({
                    "maPhuongAn": pa.maPhuongAn,
                    "maTruong": pa.maTruong,
                    "tenTruong": pa.truongDaiHoc.tenTruong,
                    "khoiTruong": pa.truongDaiHoc.khoiTruong,
                    "vungMien": pa.truongDaiHoc.vungMien,
                    "tinhThanh": pa.truongDaiHoc.tinhThanh,
                    "tenNganh": pa.nganhHoc.tenNganh,
                    "nhomNganh": pa.nganhHoc.nhomNganh,
                    "tenChuongTrinh": pa.tenChuongTrinh,
                    "phuongThuc": pa.phuongThuc,
                    "hocPhiKy": pa.hocPhiKy,
                    "chiTieu": pa.chiTieu,
                    "dieuKienXetTuyen": pa.dieuKienXetTuyen,
                    "lichSuDiemChuan": lichSu,
                })

            return {
                "thanhCong": True,
                "soLuong": len(danhSach),
                "danhSachSoSanh": danhSach,
            }
        finally:
            dongPhienKetNoi()

    @classmethod
    def xuatCsvNguyenVong(cls, maHocSinh):
        phien = layPhienKetNoi()
        try:
            ds = cls.layDanhSachNguyenVong(maHocSinh)
            danhSach = ds.get("danhSach", [])

            output = io.StringIO()
            output.write("\ufeff")
            writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

            writer.writerow([
                "Thứ tự nguyện vọng",
                "Mã phương án",
                "Mã trường",
                "Tên trường đại học",
                "Tên ngành / Chương trình",
                "Phương thức xét tuyển",
                "Học phí kỳ (VND)",
                "Khu vực",
                "Điểm chuẩn tham khảo gần nhất",
                "Ghi chú",
            ])

            for nv in danhSach:
                writer.writerow([
                    khuKhaiThacCongThucCsv(nv.get("thuTu")),
                    khuKhaiThacCongThucCsv(nv.get("maPhuongAn")),
                    khuKhaiThacCongThucCsv(nv.get("maTruong")),
                    khuKhaiThacCongThucCsv(nv.get("tenTruong")),
                    khuKhaiThacCongThucCsv(nv.get("tenChuongTrinh")),
                    khuKhaiThacCongThucCsv(nv.get("phuongThuc")),
                    khuKhaiThacCongThucCsv(nv.get("hocPhiKy") or "Chưa công bố"),
                    khuKhaiThacCongThucCsv(nv.get("vungMien")),
                    khuKhaiThacCongThucCsv(nv.get("diemChuanGanNhat") or "Chưa có"),
                    khuKhaiThacCongThucCsv(nv.get("ghiChu") or ""),
                ])

            return output.getvalue()
        finally:
            dongPhienKetNoi()
