import os
import sys
import pandas as pd
import numpy as np
from sklearn.model_selection import GroupShuffleSplit

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from database.connection import layPhienKetNoi, dongPhienKetNoi
from database.models import (
    HocSinh,
    DiemMonHoc,
    SoThichHocSinh,
    PhuongAn,
    TruongDaiHoc,
    NganhHoc,
    DiemChuan,
    TuongTac,
    MauDanhGia,
)
from config import CauHinh

def trichXuatTapDuLieu(duongDanCsv=None):
    """
    Trích xuất tập dữ liệu phục vụ huấn luyện mô hình.
    Ưu tiên đọc trực tiếp từ tệp CSV (data/dataset.csv) mà không cần kết nối MySQL.
    """
    if duongDanCsv is None:
        duongDanCsv = CauHinh.DUONG_DAN_DATASET_CSV

    if duongDanCsv and os.path.exists(duongDanCsv):
        df = pd.read_csv(duongDanCsv, encoding="utf-8")
        if not df.empty:
            return df

    duongDanMl = os.path.join(thuMucGoc, "ml", "dataset.csv")
    if os.path.exists(duongDanMl):
        df = pd.read_csv(duongDanMl, encoding="utf-8")
        if not df.empty:
            return df

    # Fallback dự phòng: Truy vấn từ CSDL nếu có kết nối
    try:
        phien = layPhienKetNoi()
    except Exception:
        return pd.DataFrame()

    try:
        mauDanhGia = phien.query(MauDanhGia).all()
        if not mauDanhGia:
            return pd.DataFrame()

        tatCaHocSinh = phien.query(HocSinh).all()
        banDoHocSinh = {hs.maHocSinh: hs for hs in tatCaHocSinh}

        tatCaDiem = phien.query(DiemMonHoc).all()
        banDoDiem = {}
        for d in tatCaDiem:
            if d.maHocSinh not in banDoDiem:
                banDoDiem[d.maHocSinh] = {}
            banDoDiem[d.maHocSinh][d.tenMon] = d.diemSo

        tatCaSoThich = phien.query(SoThichHocSinh).all()
        banDoSoThich = {}
        for st in tatCaSoThich:
            if st.maHocSinh not in banDoSoThich:
                banDoSoThich[st.maHocSinh] = {}
            banDoSoThich[st.maHocSinh][st.nhomNganh] = st.mucDoThich

        tatCaPhuongAn = phien.query(PhuongAn).join(TruongDaiHoc).join(NganhHoc).all()
        banDoPhuongAn = {pa.maPhuongAn: pa for pa in tatCaPhuongAn}

        tatCaDiemChuan = phien.query(DiemChuan).all()
        banDoDiemChuan = {}
        for dc in tatCaDiemChuan:
            if dc.maPhuongAn not in banDoDiemChuan or dc.nam > banDoDiemChuan[dc.maPhuongAn]["nam"]:
                banDoDiemChuan[dc.maPhuongAn] = {"nam": dc.nam, "diem": dc.diemTrungTuyen}

        tatCaTuongTac = phien.query(TuongTac).all()
        banDoTuongTac = {}
        for tt in tatCaTuongTac:
            cap = (tt.maHocSinh, tt.maPhuongAn)
            banDoTuongTac[cap] = banDoTuongTac.get(cap, 0) + 1

        duLieu = []
        for m in mauDanhGia:
            hs = banDoHocSinh.get(m.maHocSinh)
            pa = banDoPhuongAn.get(m.maPhuongAn)
            if not hs or not pa:
                continue

            diemHs = banDoDiem.get(m.maHocSinh, {})
            dToan = diemHs.get("Toan", 7.0)
            dVan = diemHs.get("Van", 7.0)
            dAnh = diemHs.get("NgoaiNgu", 7.0)
            dVatLy = diemHs.get("VatLy", 7.0)
            dHoaHoc = diemHs.get("HoaHoc", 7.0)
            dSinhHoc = diemHs.get("SinhHoc", 7.0)
            dTrungBinh = float(np.mean([dToan, dVan, dAnh, dVatLy, dHoaHoc, dSinhHoc]))

            soThichHs = banDoSoThich.get(m.maHocSinh, {})
            mucKhop = soThichHs.get(pa.nganhHoc.nhomNganh, 3) / 5.0

            chiPhi = pa.hocPhiKy if pa.hocPhiKy is not None else 12500000.0
            if hs.kyTinhNganSach == "nam":
                chiPhiTheoKyHs = chiPhi * 2
            else:
                chiPhiTheoKyHs = chiPhi

            if hs.nganSachToiDa and hs.nganSachToiDa > 0 and chiPhiTheoKyHs > 0:
                tiLeTaiChinh = min(1.0, float(hs.nganSachToiDa) / float(chiPhiTheoKyHs))
            else:
                tiLeTaiChinh = 1.0

            if not hs.diaBanUuTien or hs.diaBanUuTien == pa.truongDaiHoc.vungMien:
                khopDiaBan = 1.0
            else:
                khopDiaBan = 0.0

            diemChuanThongTin = banDoDiemChuan.get(pa.maPhuongAn)
            diemChuanQuyDoi = (diemChuanThongTin["diem"] / 3.0) if diemChuanThongTin else 7.5

            soTuongTac = banDoTuongTac.get((m.maHocSinh, m.maPhuongAn), 0)

            duLieu.append({
                "maHocSinh": m.maHocSinh,
                "maPhuongAn": m.maPhuongAn,
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
                "khoiTruong": pa.truongDaiHoc.khoiTruong,
                "vungMien": pa.truongDaiHoc.vungMien,
                "nhomNganh": pa.nganhHoc.nhomNganh,
                "phuongThuc": pa.phuongThuc,
                "nhanPhuHop": float(m.nhanPhuHop),
            })

        df = pd.DataFrame(duLieu)
        return df
    finally:
        dongPhienKetNoi()


def chiaTapTheoHocSinh(df, tiLeTrain=0.70, tiLeTest=0.30, random_state=42):
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    gss = GroupShuffleSplit(n_splits=1, train_size=tiLeTrain, random_state=random_state)
    trainIdx, testIdx = next(gss.split(df, groups=df["maHocSinh"]))

    dfTrain = df.iloc[trainIdx].copy().reset_index(drop=True)
    dfTest = df.iloc[testIdx].copy().reset_index(drop=True)

    giaoHocSinh = set(dfTrain["maHocSinh"]).intersection(set(dfTest["maHocSinh"]))
    if len(giaoHocSinh) > 0:
        raise ValueError(f"Rò rỉ dữ liệu phát hiện: {len(giaoHocSinh)} học sinh xuất hiện ở cả train và test!")

    return dfTrain, dfTest
