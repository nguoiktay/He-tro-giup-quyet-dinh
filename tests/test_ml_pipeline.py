import os
import sys
import pytest
import pandas as pd
import numpy as np

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from ml.dataset import chiaTapTheoHocSinh
from ml.model_manager import QuanLyMoHinh
from config import CauHinh


def testKhongRoRiHocSinh():
    duLieuMau = []
    for hs in range(1, 11):
        for pa in range(1, 6):
            duLieuMau.append({
                "maHocSinh": hs,
                "maPhuongAn": f"PA_{pa}",
                "nhanPhuHop": 4.0,
            })
    df = pd.DataFrame(duLieuMau)

    dfTrain, dfTest = chiaTapTheoHocSinh(df, tiLeTrain=0.70, tiLeTest=0.30, random_state=42)

    hsTrain = set(dfTrain["maHocSinh"])
    hsTest = set(dfTest["maHocSinh"])

    giaoNhau = hsTrain.intersection(hsTest)
    assert len(giaoNhau) == 0
    assert len(hsTrain) + len(hsTest) == 10


def testKiemTraChecksumVaNapArtifact():
    thanhCong = QuanLyMoHinh.khoiTao()
    assert thanhCong is True
    assert QuanLyMoHinh.trangThaiSanSang is True

    trangThai = QuanLyMoHinh.layTrangThai()
    assert trangThai["sanSang"] is True
    assert trangThai["manifest"] is not None
    assert "checksumSha256" in trangThai["manifest"]


def testDuDoanNhatQuan():
    QuanLyMoHinh.khoiTao()
    hoSo = {
        "diemMonHoc": {"Toan": 8.5, "Van": 7.5, "NgoaiNgu": 8.0, "VatLy": 8.2, "HoaHoc": 7.8, "SinhHoc": 6.5},
        "soThich": {"CongNgheThongTin": 5},
        "nganSachToiDa": 30000000.0,
        "kyTinhNganSach": "nam",
        "diaBanUuTien": "MienBac",
    }
    paList = [{
        "maPhuongAn": "TEST_PA_1",
        "khoiTruong": "CongLap",
        "vungMien": "MienBac",
        "nhomNganh": "CongNgheThongTin",
        "phuongThuc": "DiemThiTHPT",
        "hocPhiKy": 15000000.0,
        "diemChuanGanNhat": 26.5,
    }]

    kq1 = QuanLyMoHinh.duDoan(hoSo, paList)
    QuanLyMoHinh.khoiTao()
    kq2 = QuanLyMoHinh.duDoan(hoSo, paList)

    assert kq1["TEST_PA_1"] == kq2["TEST_PA_1"]
    assert 1.0 <= kq1["TEST_PA_1"] <= 5.0
