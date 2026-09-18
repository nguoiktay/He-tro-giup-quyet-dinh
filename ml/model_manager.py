import os
import sys
import json
import hashlib
import logging
import joblib
import pandas as pd
import numpy as np

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from config import CauHinh
from ml.preprocessor import DAC_TRUNG_SO, DAC_TRUNG_PHAN_LOAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def tinhMaBamSha256(duongDan):
    sha256 = hashlib.sha256()
    with open(duongDan, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


class QuanLyMoHinh:
    _instance = None
    pipelineMoHinh = None
    manifest = None
    trangThaiSanSang = False
    thongBaoLoi = "Mô hình chưa được nạp."

    @classmethod
    def khoiTao(cls, duongDanMoHinh=None, duongDanManifest=None):
        if duongDanMoHinh is None:
            duongDanMoHinh = CauHinh.DUONG_DAN_MO_HINH
        if duongDanManifest is None:
            duongDanManifest = CauHinh.DUONG_DAN_MANIFEST

        if not os.path.exists(duongDanMoHinh) or not os.path.exists(duongDanManifest):
            cls.trangThaiSanSang = False
            cls.thongBaoLoi = "Mô hình chưa sẵn sàng: Không tìm thấy tệp artifact hoặc manifest."
            logging.warning(cls.thongBaoLoi)
            return False

        try:
            with open(duongDanManifest, "r", encoding="utf-8") as f:
                cls.manifest = json.load(f)

            maBamLuu = cls.manifest.get("checksumSha256")
            maBamThucTe = tinhMaBamSha256(duongDanMoHinh)
            if maBamLuu != maBamThucTe:
                cls.trangThaiSanSang = False
                cls.thongBaoLoi = "Mô hình chưa sẵn sàng: Mã băm checksum của artifact không khớp với manifest (nghi ngờ tệp bị sửa đổi trái phép)."
                logging.error(cls.thongBaoLoi)
                return False

            cls.pipelineMoHinh = joblib.load(duongDanMoHinh)
            cls.trangThaiSanSang = True
            cls.thongBaoLoi = "Sẵn sàng"
            logging.info("Nạp mô hình RandomForest thành công (Phiên bản: %s).", cls.manifest.get("phienBan", "1.0"))
            return True
        except Exception as e:
            cls.trangThaiSanSang = False
            cls.thongBaoLoi = f"Mô hình chưa sẵn sàng: Lỗi khi nạp artifact ({str(e)})."
            logging.error(cls.thongBaoLoi)
            return False

    @classmethod
    def layTrangThai(cls):
        return {
            "sanSang": cls.trangThaiSanSang,
            "thongBao": cls.thongBaoLoi,
            "manifest": cls.manifest,
        }

    @classmethod
    def duDoan(cls, hoSoHocSinh, danhSachPhuongAn, banDoTuongTac=None):
        if not cls.trangThaiSanSang or cls.pipelineMoHinh is None:
            raise RuntimeError(f"Không thể dự đoán: {cls.thongBaoLoi}")

        if not danhSachPhuongAn:
            return {}

        if banDoTuongTac is None:
            banDoTuongTac = {}

        diemMon = hoSoHocSinh.get("diemMonHoc", {})
        dToan = diemMon.get("Toan", 7.0)
        dVan = diemMon.get("Van", 7.0)
        dAnh = diemMon.get("NgoaiNgu", 7.0)
        dVatLy = diemMon.get("VatLy", 7.0)
        dHoaHoc = diemMon.get("HoaHoc", 7.0)
        dSinhHoc = diemMon.get("SinhHoc", 7.0)
        dTrungBinh = float(np.mean([dToan, dVan, dAnh, dVatLy, dHoaHoc, dSinhHoc]))

        soThich = hoSoHocSinh.get("soThich", {})
        nganSach = hoSoHocSinh.get("nganSachToiDa")
        kyNganSach = hoSoHocSinh.get("kyTinhNganSach", "nam")
        diaBanUuTien = hoSoHocSinh.get("diaBanUuTien")

        danhSachDong = []
        maPhuongAnList = []
        for pa in danhSachPhuongAn:
            nhomNganh = pa.get("nhomNganh", "Khac")
            mucKhop = soThich.get(nhomNganh, 3) / 5.0

            chiPhi = pa.get("hocPhiKy")
            if chiPhi is None:
                chiPhi = 12500000.0

            if kyNganSach == "nam":
                chiPhiSoSanh = chiPhi * 2
            else:
                chiPhiSoSanh = chiPhi

            if nganSach and nganSach > 0 and chiPhiSoSanh > 0:
                tiLeTaiChinh = min(1.0, float(nganSach) / float(chiPhiSoSanh))
            else:
                tiLeTaiChinh = 1.0

            vungMienPa = pa.get("vungMien", "MienBac")
            if not diaBanUuTien or diaBanUuTien == vungMienPa:
                khopDiaBan = 1.0
            else:
                khopDiaBan = 0.0

            diemChuan = pa.get("diemChuanGanNhat")
            diemChuanQuyDoi = (diemChuan / 3.0) if diemChuan else 7.5

            maPa = pa.get("maPhuongAn")
            maPhuongAnList.append(maPa)
            soTuongTac = banDoTuongTac.get(maPa, 0)

            danhSachDong.append({
                "diemToan": dToan,
                "diemVan": dVan,
                "diemNgoaiNgu": dAnh,
                "diemVatLy": dVatLy,
                "diemHoaHoc": dHoaHoc,
                "diemSinhHoc": dSinhHoc,
                "diemTrungBinh": dTrungBinh,
                "mucKhopSoThich": mucKhop,
                "tiLeTaiChinh": tiLeTaiChinh,
                "khopDiaBan": khopDiaBan,
                "diemChuanThamKhao": diemChuanQuyDoi,
                "soLuotTuongTacTruoc": float(soTuongTac),
                "khoiTruong": pa.get("khoiTruong", "CongLap"),
                "vungMien": vungMienPa,
                "nhomNganh": nhomNganh,
                "phuongThuc": pa.get("phuongThuc", "DiemThiTHPT"),
            })

        cacCotDacTrung = DAC_TRUNG_SO + DAC_TRUNG_PHAN_LOAI
        dfFeatures = pd.DataFrame(danhSachDong)[cacCotDacTrung]
        ketQuaDuDoan = cls.pipelineMoHinh.predict(dfFeatures)

        ketQuaDuDoan = np.clip(ketQuaDuDoan, 1.0, 5.0)

        ketQuaMap = {}
        for maPa, diem in zip(maPhuongAnList, ketQuaDuDoan):
            ketQuaMap[maPa] = round(float(diem), 2)

        return ketQuaMap
