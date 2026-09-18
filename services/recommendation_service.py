import os
import sys
import json
from datetime import datetime, timezone

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from database.connection import layPhienKetNoi, dongPhienKetNoi
from database.models import (
    HocSinh,
    PhuongAn,
    TruongDaiHoc,
    NganhHoc,
    DiemChuan,
    TuongTac,
    PhienKhuyenNghi,
    ChiTietKhuyenNghi,
)
from ml.model_manager import QuanLyMoHinh


class DichVuKhuyenNghi:

    @classmethod
    def tinhDiemMoHinh(cls, diemDuDoan):
        return round(float(max(0.0, min(1.0, (diemDuDoan - 1.0) / 4.0))), 4)

    @classmethod
    def tinhDiemTaiChinh(cls, nganSach, hocPhiKy, kyNganSach="nam"):
        if nganSach is None or nganSach == "":
            return None, False

        try:
            nganSachVal = float(nganSach)
        except (ValueError, TypeError):
            return None, False

        if hocPhiKy is None:
            return None, True

        chiPhiSoSanh = hocPhiKy * 2 if kyNganSach == "nam" else hocPhiKy

        if chiPhiSoSanh == 0.0 and nganSachVal >= 0.0:
            return 1.0, False
        if nganSachVal == 0.0 and chiPhiSoSanh > 0.0:
            return 0.0, False
        if nganSachVal > 0.0 and chiPhiSoSanh > 0.0:
            return round(min(1.0, nganSachVal / chiPhiSoSanh), 4), False
        return 0.0, False

    @classmethod
    def tinhDiemKhuVuc(cls, diaBanUuTien, vungMienTruong):
        if not diaBanUuTien:
            return None
        if diaBanUuTien == vungMienTruong:
            return 1.0
        return 0.0

    @classmethod
    def tinhDiemXepHang(cls, diemMoHinh, diemTaiChinh, diemKhuVuc, wMoHinh=0.70, wTaiChinh=0.20, wKhuVuc=0.10):
        cacThanhPhan = []
        trongSoThuc = []

        cacThanhPhan.append((wMoHinh, diemMoHinh))
        trongSoThuc.append(wMoHinh)

        if diemTaiChinh is not None:
            cacThanhPhan.append((wTaiChinh, diemTaiChinh))
            trongSoThuc.append(wTaiChinh)

        if diemKhuVuc is not None:
            cacThanhPhan.append((wKhuVuc, diemKhuVuc))
            trongSoThuc.append(wKhuVuc)

        tongTrongSo = sum(trongSoThuc)
        if tongTrongSo <= 0:
            return diemMoHinh

        diemTong = sum(w * d for w, d in cacThanhPhan) / tongTrongSo
        return round(float(max(0.0, min(1.0, diemTong))), 4)

    @classmethod
    def locUngVienVaXepHang(
        cls,
        hoSoHocSinh,
        trongSoTuyChinh=None,
        gioiHanTopK=20,
        luuPhien=True,
    ):
        if trongSoTuyChinh is None:
            trongSoTuyChinh = {"moHinh": 0.70, "taiChinh": 0.20, "khuVuc": 0.10}

        wMoHinh = float(trongSoTuyChinh.get("moHinh", 0.70))
        wTaiChinh = float(trongSoTuyChinh.get("taiChinh", 0.20))
        wKhuVuc = float(trongSoTuyChinh.get("khuVuc", 0.10))

        if not QuanLyMoHinh.trangThaiSanSang:
            QuanLyMoHinh.khoiTao()

        if not QuanLyMoHinh.trangThaiSanSang:
            return {
                "thanhCong": False,
                "thongBao": QuanLyMoHinh.thongBaoLoi,
                "danhSachKhuyenNghi": [],
            }

        phien = layPhienKetNoi()
        try:
            cacPhuongAn = phien.query(PhuongAn).join(TruongDaiHoc).join(NganhHoc).all()
            if not cacPhuongAn:
                return {
                    "thanhCong": False,
                    "thongBao": "Chưa có dữ liệu phương án tuyển sinh trong hệ thống.",
                    "danhSachKhuyenNghi": [],
                }

            maHs = hoSoHocSinh.get("maHocSinh")
            banDoTuongTac = {}
            if maHs:
                tuongTacRows = phien.query(TuongTac).filter_by(maHocSinh=maHs).all()
                for tt in tuongTacRows:
                    banDoTuongTac[tt.maPhuongAn] = banDoTuongTac.get(tt.maPhuongAn, 0) + 1

            tatCaDiemChuan = phien.query(DiemChuan).all()
            banDoDiemChuan = {}
            for dc in tatCaDiemChuan:
                if dc.maPhuongAn not in banDoDiemChuan or dc.nam > banDoDiemChuan[dc.maPhuongAn]["nam"]:
                    banDoDiemChuan[dc.maPhuongAn] = {
                        "nam": dc.nam,
                        "diem": dc.diemTrungTuyen,
                        "toHop": dc.maToHop,
                    }

            ungVienHopLe = []
            nganSach = hoSoHocSinh.get("nganSachToiDa")
            kyNganSach = hoSoHocSinh.get("kyTinhNganSach", "nam")
            batBuocNganSach = hoSoHocSinh.get("batBuocNganSach", False)
            diaBanUuTien = hoSoHocSinh.get("diaBanUuTien")
            batBuocDiaBan = hoSoHocSinh.get("batBuocDiaBan", False)

            nhomNganhLoc = hoSoHocSinh.get("nhomNganhLoc")
            diaBanLoc = hoSoHocSinh.get("diaBanLoc")

            for pa in cacPhuongAn:
                chiPhi = pa.hocPhiKy
                chiPhiSoSanh = (chiPhi * 2) if (chiPhi and kyNganSach == "nam") else chiPhi

                if batBuocNganSach and nganSach and chiPhiSoSanh is not None:
                    if chiPhiSoSanh > float(nganSach):
                        continue

                if batBuocDiaBan and diaBanUuTien:
                    if pa.truongDaiHoc.vungMien != diaBanUuTien:
                        continue

                if nhomNganhLoc and nhomNganhLoc not in ["", "tatCa"]:
                    if pa.nganhHoc.nhomNganh != nhomNganhLoc:
                        continue

                if diaBanLoc and diaBanLoc not in ["", "tatCa"]:
                    if pa.truongDaiHoc.vungMien != diaBanLoc:
                        continue

                ungVienHopLe.append(pa)

            if not ungVienHopLe:
                return {
                    "thanhCong": True,
                    "thongBao": "Không tìm thấy phương án nào thỏa mãn toàn bộ ràng buộc đã chọn. Vui lòng chọn Tất cả nhóm ngành hoặc nới lỏng tiêu chí.",
                    "danhSachKhuyenNghi": [],
                }

            dsPaDict = []
            for pa in ungVienHopLe:
                dcMoiNhat = banDoDiemChuan.get(pa.maPhuongAn)
                dsPaDict.append({
                    "maPhuongAn": pa.maPhuongAn,
                    "khoiTruong": pa.truongDaiHoc.khoiTruong,
                    "vungMien": pa.truongDaiHoc.vungMien,
                    "nhomNganh": pa.nganhHoc.nhomNganh,
                    "phuongThuc": pa.phuongThuc,
                    "hocPhiKy": pa.hocPhiKy,
                    "diemChuanGanNhat": dcMoiNhat["diem"] if dcMoiNhat else None,
                })

            banDoDiemDuDoan = QuanLyMoHinh.duDoan(hoSoHocSinh, dsPaDict, banDoTuongTac)

            danhSachXepHang = []
            soThich = hoSoHocSinh.get("soThich", {})
            tongDiemXetTuyen = hoSoHocSinh.get("tongDiemXetTuyen")

            for pa in ungVienHopLe:
                diemDuDoan = banDoDiemDuDoan.get(pa.maPhuongAn, 3.0)
                diemMh = cls.tinhDiemMoHinh(diemDuDoan)
                diemTc, thieuHocPhi = cls.tinhDiemTaiChinh(nganSach, pa.hocPhiKy, kyNganSach)
                diemKv = cls.tinhDiemKhuVuc(diaBanUuTien, pa.truongDaiHoc.vungMien)

                diemXh = cls.tinhDiemXepHang(
                    diemMoHinh=diemMh,
                    diemTaiChinh=diemTc,
                    diemKhuVuc=diemKv,
                    wMoHinh=wMoHinh,
                    wTaiChinh=wTaiChinh,
                    wKhuVuc=wKhuVuc,
                )

                lyDo = []
                nhomNganh = pa.nganhHoc.nhomNganh
                if nhomNganh in soThich and soThich[nhomNganh] >= 4:
                    lyDo.append(f"Khớp sở thích nhóm ngành {pa.nganhHoc.tenNganh} (mức ưu tiên {soThich[nhomNganh]}/5)")
                if diemTc is not None and diemTc >= 0.8:
                    lyDo.append("Học phí phù hợp với ngân sách dự kiến của bạn")
                if diemKv == 1.0:
                    lyDo.append(f"Trường nằm tại {pa.truongDaiHoc.vungMien} đúng khu vực địa bàn ưu tiên")
                if not lyDo:
                    lyDo.append("Phương án có điểm đánh giá tổng thể cao theo năng lực của bạn")

                canKiemTra = []
                if thieuHocPhi:
                    canKiemTra.append("Chưa có thông tin học phí chính thức từ đề án; cần đối chiếu thông báo của trường.")
                if pa.dieuKienXetTuyen:
                    canKiemTra.append(f"Điều kiện tuyển sinh: {pa.dieuKienXetTuyen}")
                dcMoiNhat = banDoDiemChuan.get(pa.maPhuongAn)
                toHopPa = dcMoiNhat["toHop"] if dcMoiNhat else "A00"
                diemChuanPa = dcMoiNhat["diem"] if dcMoiNhat else None
                if dcMoiNhat:
                    canKiemTra.append(f"Điểm chuẩn tham khảo năm {dcMoiNhat['nam']} (tổ hợp {dcMoiNhat['toHop']}): {dcMoiNhat['diem']} điểm.")

                delta = None
                if tongDiemXetTuyen is not None and diemChuanPa is not None:
                    try:
                        delta = round(float(tongDiemXetTuyen) - float(diemChuanPa), 2)
                    except (ValueError, TypeError):
                        delta = None

                if delta is not None:
                    if delta >= 0.5:
                        phanLoai = "doChac"
                    elif delta >= -0.5:
                        phanLoai = "coKhaNang"
                    else:
                        phanLoai = "thuThach"
                else:
                    if diemDuDoan >= 4.0:
                        phanLoai = "doChac"
                    elif diemDuDoan >= 3.2:
                        phanLoai = "coKhaNang"
                    else:
                        phanLoai = "thuThach"

                danhSachXepHang.append({
                    "maPhuongAn": pa.maPhuongAn,
                    "maTruong": pa.maTruong,
                    "tenTruong": pa.truongDaiHoc.tenTruong,
                    "khoiTruong": pa.truongDaiHoc.khoiTruong,
                    "vungMien": pa.truongDaiHoc.vungMien,
                    "tinhThanh": pa.truongDaiHoc.tinhThanh,
                    "maNganh": pa.maNganh,
                    "tenNganh": pa.nganhHoc.tenNganh,
                    "nhomNganh": pa.nganhHoc.nhomNganh,
                    "tenChuongTrinh": pa.tenChuongTrinh,
                    "phuongThuc": pa.phuongThuc,
                    "hocPhiKy": pa.hocPhiKy,
                    "diemDuDoan": diemDuDoan,
                    "diemMoHinh": diemMh,
                    "diemTaiChinh": diemTc if diemTc is not None else 1.0,
                    "diemKhuVuc": diemKv if diemKv is not None else 1.0,
                    "diemXepHang": diemXh,
                    "lyDo": lyDo,
                    "canKiemTra": canKiemTra,
                    "toHop": toHopPa,
                    "diemChuan": diemChuanPa,
                    "delta": delta,
                    "phanLoai": phanLoai,
                })

            danhSachXepHang.sort(key=lambda x: (-x["diemXepHang"], x["maPhuongAn"]))

            for idx, item in enumerate(danhSachXepHang, start=1):
                item["thuHang"] = idx

            topK = danhSachXepHang[:gioiHanTopK]

            maPhienLuu = None
            if luuPhien and maHs:
                try:
                    phienKn = PhienKhuyenNghi(
                        maHocSinh=maHs,
                        thoiDiem=datetime.now(timezone.utc).replace(tzinfo=None),
                        anhXaHoSoJson=json.dumps(hoSoHocSinh, ensure_ascii=False),
                        trongSoJson=json.dumps(trongSoTuyChinh),
                        phienBanMoHinh=QuanLyMoHinh.manifest.get("phienBan", "v1.0.0") if QuanLyMoHinh.manifest else "v1.0.0",
                        phienBanLuat="v1.0_chinhSachDSS",
                    )
                    phien.add(phienKn)
                    phien.flush()
                    maPhienLuu = phienKn.maPhienKhuyenNghi

                    chiTietList = []
                    for item in topK:
                        chiTietList.append(ChiTietKhuyenNghi(
                            maPhienKhuyenNghi=maPhienLuu,
                            maPhuongAn=item["maPhuongAn"],
                            thuHang=item["thuHang"],
                            diemDuDoan=item["diemDuDoan"],
                            diemMoHinh=item["diemMoHinh"],
                            diemTaiChinh=item["diemTaiChinh"],
                            diemKhuVuc=item["diemKhuVuc"],
                            diemXepHang=item["diemXepHang"],
                            lyDoJson=json.dumps(item["lyDo"], ensure_ascii=False),
                            canKiemTraJson=json.dumps(item["canKiemTra"], ensure_ascii=False),
                        ))
                    phien.bulk_save_objects(chiTietList)
                    phien.commit()
                except Exception as exSave:
                    phien.rollback()

            return {
                "thanhCong": True,
                "thongBao": "Sinh danh sách khuyến nghị thành công.",
                "maPhienKhuyenNghi": maPhienLuu,
                "danhSachKhuyenNghi": topK,
                "cheDoDemo": bool(QuanLyMoHinh.manifest.get("duLieuMoPhong", False)) if QuanLyMoHinh.manifest else True,
            }
        finally:
            dongPhienKetNoi()

    @classmethod
    def chayThuKichBanGiaDinh(cls, hoSoGoc, diemGiaDinh=None, nganSachGiaDinh=None, trongSoGiaDinh=None, gioiHanTopK=20):
        hoSoGiaDinh = dict(hoSoGoc)
        if diemGiaDinh:
            hoSoGiaDinh["diemMonHoc"] = dict(hoSoGoc.get("diemMonHoc", {}))
            hoSoGiaDinh["diemMonHoc"].update(diemGiaDinh)
        if nganSachGiaDinh is not None:
            hoSoGiaDinh["nganSachToiDa"] = float(nganSachGiaDinh)

        return cls.locUngVienVaXepHang(
            hoSoHocSinh=hoSoGiaDinh,
            trongSoTuyChinh=trongSoGiaDinh,
            gioiHanTopK=gioiHanTopK,
            luuPhien=False,
        )
