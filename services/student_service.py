import os
import sys
from datetime import datetime, timedelta, timezone

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from database.connection import layPhienKetNoi, dongPhienKetNoi
from database.models import (
    HocSinh,
    DiemMonHoc,
    SoThichHocSinh,
    TuongTac,
    PhuongAn,
    TruongDaiHoc,
    NganhHoc,
)


class DichVuHocSinh:

    @classmethod
    def layHoSoChiTiet(cls, maHocSinh):
        phien = layPhienKetNoi()
        try:
            hs = phien.query(HocSinh).filter_by(maHocSinh=maHocSinh).first()
            if not hs:
                return None

            diemSo = {}
            for d in hs.diemMonHoc:
                diemSo[d.tenMon] = d.diemSo

            soThich = {}
            for st in hs.soThichHocSinh:
                soThich[st.nhomNganh] = st.mucDoThich

            return {
                "maHocSinh": hs.maHocSinh,
                "hoTen": hs.hoTen,
                "soDienThoai": hs.soDienThoai,
                "namDuTuyen": hs.namDuTuyen,
                "nganSachToiDa": hs.nganSachToiDa,
                "kyTinhNganSach": hs.kyTinhNganSach,
                "diaBanUuTien": hs.diaBanUuTien,
                "batBuocNganSach": hs.batBuocNganSach,
                "batBuocDiaBan": hs.batBuocDiaBan,
                "mucTieuNgheNghiep": hs.mucTieuNgheNghiep,
                "uuTienCaNhan": hs.uuTienCaNhan,
                "diemMonHoc": diemSo,
                "soThich": soThich,
            }
        finally:
            dongPhienKetNoi()

    @classmethod
    def capNhatThongTinChung(
        cls,
        maHocSinh,
        hoTen,
        soDienThoai=None,
        namDuTuyen=2026,
        nganSachToiDa=None,
        kyTinhNganSach="nam",
        diaBanUuTien=None,
        batBuocNganSach=False,
        batBuocDiaBan=False,
        mucTieuNgheNghiep=None,
        uuTienCaNhan=None,
    ):
        if not hoTen or not hoTen.strip():
            return {"thanhCong": False, "thongBao": "Họ và tên không được để trống."}

        if nganSachToiDa is not None:
            try:
                nganSachVal = float(nganSachToiDa)
                if nganSachVal < 0:
                    return {"thanhCong": False, "thongBao": "Ngân sách không được là số âm."}
                nganSachToiDa = nganSachVal
            except ValueError:
                return {"thanhCong": False, "thongBao": "Ngân sách phải là một số hợp lệ."}

        phien = layPhienKetNoi()
        try:
            hs = phien.query(HocSinh).filter_by(maHocSinh=maHocSinh).first()
            if not hs:
                return {"thanhCong": False, "thongBao": "Hồ sơ học sinh không tồn tại."}

            hs.hoTen = hoTen.strip()
            hs.soDienThoai = soDienThoai.strip() if soDienThoai else None
            hs.namDuTuyen = int(namDuTuyen) if namDuTuyen else 2026
            hs.nganSachToiDa = nganSachToiDa
            hs.kyTinhNganSach = kyTinhNganSach if kyTinhNganSach in ["nam", "ky"] else "nam"
            hs.diaBanUuTien = diaBanUuTien
            hs.batBuocNganSach = bool(batBuocNganSach)
            hs.batBuocDiaBan = bool(batBuocDiaBan)
            hs.mucTieuNgheNghiep = mucTieuNgheNghiep.strip() if mucTieuNgheNghiep else None
            hs.uuTienCaNhan = uuTienCaNhan.strip() if uuTienCaNhan else None

            phien.commit()
            return {"thanhCong": True, "thongBao": "Cập nhật hồ sơ thành công."}
        except Exception as e:
            phien.rollback()
            return {"thanhCong": False, "thongBao": f"Lỗi cập nhật hồ sơ: {str(e)}"}
        finally:
            dongPhienKetNoi()

    @classmethod
    def capNhatDiemMon(cls, maHocSinh, bangDiem):
        phien = layPhienKetNoi()
        try:
            hs = phien.query(HocSinh).filter_by(maHocSinh=maHocSinh).first()
            if not hs:
                return {"thanhCong": False, "thongBao": "Học sinh không tồn tại."}

            for tenMon, diemSo in bangDiem.items():
                if diemSo is None or diemSo == "":
                    continue
                try:
                    diemFloat = float(diemSo)
                except ValueError:
                    return {"thanhCong": False, "thongBao": f"Điểm môn {tenMon} không đúng định dạng số."}

                if diemFloat < 0.0 or diemFloat > 10.0:
                    return {
                        "thanhCong": False,
                        "thongBao": f"Điểm môn {tenMon} ({diemFloat}) nằm ngoài thang điểm 0 - 10 hợp lệ.",
                    }

                diemHienTai = (
                    phien.query(DiemMonHoc)
                    .filter_by(maHocSinh=maHocSinh, tenMon=tenMon, loaiDiem="thpt", namHocKy="2026")
                    .first()
                )
                if diemHienTai:
                    diemHienTai.diemSo = diemFloat
                else:
                    phien.add(
                        DiemMonHoc(
                            maHocSinh=maHocSinh,
                            tenMon=tenMon,
                            diemSo=diemFloat,
                            thangDiem=10.0,
                            loaiDiem="thpt",
                            namHocKy="2026",
                        )
                    )

            phien.commit()
            return {"thanhCong": True, "thongBao": "Lưu điểm môn học thành công."}
        except Exception as e:
            phien.rollback()
            return {"thanhCong": False, "thongBao": f"Lỗi lưu điểm môn học: {str(e)}"}
        finally:
            dongPhienKetNoi()

    @classmethod
    def capNhatSoThich(cls, maHocSinh, bangSoThich):
        phien = layPhienKetNoi()
        try:
            hs = phien.query(HocSinh).filter_by(maHocSinh=maHocSinh).first()
            if not hs:
                return {"thanhCong": False, "thongBao": "Học sinh không tồn tại."}

            for nhomNganh, mucDo in bangSoThich.items():
                try:
                    mucDoInt = int(mucDo)
                    if mucDoInt < 1 or mucDoInt > 5:
                        continue
                except (ValueError, TypeError):
                    continue

                st = phien.query(SoThichHocSinh).filter_by(maHocSinh=maHocSinh, nhomNganh=nhomNganh).first()
                if st:
                    st.mucDoThich = mucDoInt
                else:
                    phien.add(SoThichHocSinh(maHocSinh=maHocSinh, nhomNganh=nhomNganh, mucDoThich=mucDoInt))

            phien.commit()
            return {"thanhCong": True, "thongBao": "Cập nhật sở thích thành công."}
        except Exception as e:
            phien.rollback()
            return {"thanhCong": False, "thongBao": f"Lỗi cập nhật sở thích: {str(e)}"}
        finally:
            dongPhienKetNoi()

    @classmethod
    def ghiNhanTuongTac(cls, maHocSinh, maPhuongAn, loaiTuongTac, maPhienKhuyenNghi=None, viTriHienThi=None):
        if loaiTuongTac not in ["xem", "soSanh", "luu", "boLuu"]:
            return {"thanhCong": False, "thongBao": "Loại tương tác không hợp lệ."}

        phien = layPhienKetNoi()
        try:
            bayGio = datetime.now(timezone.utc).replace(tzinfo=None)
            khoangCachDebounce = bayGio - timedelta(seconds=30)
            tuongTacGan = (
                phien.query(TuongTac)
                .filter(
                    TuongTac.maHocSinh == maHocSinh,
                    TuongTac.maPhuongAn == maPhuongAn,
                    TuongTac.loaiTuongTac == loaiTuongTac,
                    TuongTac.thoiDiem >= khoangCachDebounce,
                )
                .first()
            )
            if tuongTacGan:
                return {"thanhCong": True, "thongBao": "Đã ghi nhận tương tác (bỏ qua do lặp trong cửa sổ thời gian)."}

            tt = TuongTac(
                maHocSinh=maHocSinh,
                maPhuongAn=maPhuongAn,
                loaiTuongTac=loaiTuongTac,
                thoiDiem=bayGio,
                maPhienKhuyenNghi=maPhienKhuyenNghi,
                viTriHienThi=viTriHienThi,
            )
            phien.add(tt)
            phien.commit()
            return {"thanhCong": True, "thongBao": "Ghi nhận tương tác thành công."}
        except Exception as e:
            phien.rollback()
            return {"thanhCong": False, "thongBao": f"Lỗi ghi nhận tương tác: {str(e)}"}
        finally:
            dongPhienKetNoi()
