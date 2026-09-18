import os
import sys
import time
import numpy as np
import pandas as pd

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from ml.model_manager import QuanLyMoHinh


def tinhPrecisionAtK(danhSachXepHang, tapRelevant, k=5):
    if not danhSachXepHang or not tapRelevant:
        return 0.0
    kHieuDung = min(k, len(danhSachXepHang))
    if kHieuDung == 0:
        return 0.0
    topK = danhSachXepHang[:kHieuDung]
    soLuongTrung = len(set(topK).intersection(set(tapRelevant)))
    return round(float(soLuongTrung) / float(kHieuDung), 4)


def tinhRecallAtK(danhSachXepHang, tapRelevant, k=5):
    if not danhSachXepHang or not tapRelevant:
        return 0.0
    kHieuDung = min(k, len(danhSachXepHang))
    topK = danhSachXepHang[:kHieuDung]
    soLuongTrung = len(set(topK).intersection(set(tapRelevant)))
    return round(float(soLuongTrung) / float(len(tapRelevant)), 4)


def tinhNdcgAtK(danhSachXepHang, banDoDiemThucTe, k=5):
    if not danhSachXepHang or not banDoDiemThucTe:
        return 0.0
    kHieuDung = min(k, len(danhSachXepHang))
    if kHieuDung == 0:
        return 0.0

    dcg = 0.0
    for i in range(kHieuDung):
        item = danhSachXepHang[i]
        rel = banDoDiemThucTe.get(item, 0.0)
        dcg += (2.0 ** rel - 1.0) / np.log2(i + 2)

    diemSapXep = sorted(banDoDiemThucTe.values(), reverse=True)
    idcg = 0.0
    for i in range(min(kHieuDung, len(diemSapXep))):
        rel = diemSapXep[i]
        idcg += (2.0 ** rel - 1.0) / np.log2(i + 2)

    if idcg == 0.0:
        return 0.0
    return round(float(dcg / idcg), 4)


def tinhDoDaDangNhomNganh(danhSachPhuongAn, k=5):
    if not danhSachPhuongAn:
        return 0.0
    kHieuDung = min(k, len(danhSachPhuongAn))
    nhomNganhSet = set(pa.get("nhomNganh", "Khac") for pa in danhSachPhuongAn[:kHieuDung])
    return round(float(len(nhomNganhSet)) / float(kHieuDung), 4)


def doDoTreSuyLuan(hoSoMau, danhSachPhuongAn, soLanLap=20):
    QuanLyMoHinh.khoiTao()
    if not QuanLyMoHinh.trangThaiSanSang:
        return {"loi": QuanLyMoHinh.thongBaoLoi}

    thoiGianChay = []
    for _ in range(2):
        QuanLyMoHinh.duDoan(hoSoMau, danhSachPhuongAn)

    for _ in range(soLanLap):
        tBatDau = time.perf_counter()
        QuanLyMoHinh.duDoan(hoSoMau, danhSachPhuongAn)
        tKetThuc = time.perf_counter()
        thoiGianChay.append((tKetThuc - tBatDau) * 1000.0)

    p50 = np.percentile(thoiGianChay, 50)
    p95 = np.percentile(thoiGianChay, 95)
    trungBinh = np.mean(thoiGianChay)

    return {
        "soUngVien": len(danhSachPhuongAn),
        "soLanLap": soLanLap,
        "p50_ms": round(float(p50), 2),
        "p95_ms": round(float(p95), 2),
        "trungBinh_ms": round(float(trungBinh), 2),
        "datMucTieuDuoi2s": bool(p95 < 2000.0),
    }
