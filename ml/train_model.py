import os
import sys
import json
import hashlib
import logging
from datetime import datetime, timezone
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
import sklearn

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from config import CauHinh
from database.connection import layPhienKetNoi, dongPhienKetNoi
from database.models import PhienBanMoHinh
from ml.preprocessor import taoPipelineTienXuLy, DAC_TRUNG_SO, DAC_TRUNG_PHAN_LOAI
from ml.dataset import trichXuatTapDuLieu, chiaTapTheoHocSinh

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def tinhMaBamFile(duongDanFile):
    sha256 = hashlib.sha256()
    with open(duongDanFile, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def huanLuyenVaLuuPipeline(duongDanMoHinh=None, duongDanManifest=None):
    if duongDanMoHinh is None:
        duongDanMoHinh = CauHinh.DUONG_DAN_MO_HINH
    if duongDanManifest is None:
        duongDanManifest = CauHinh.DUONG_DAN_MANIFEST

    os.makedirs(os.path.dirname(duongDanMoHinh), exist_ok=True)

    logging.info("Bắt đầu nạp tập dữ liệu huấn luyện từ tệp CSV (data/dataset.csv)...")
    df = trichXuatTapDuLieu()
    if df.empty or len(df) < 20:
        logging.warning("Dữ liệu quá ít hoặc rỗng (%d dòng). Không thể huấn luyện mô hình.", len(df))
        return None

    logging.info("Tổng số mẫu đánh giá: %d, chia tập Train/Test theo nhóm học sinh...", len(df))
    dfTrain, dfTest = chiaTapTheoHocSinh(df, tiLeTrain=0.70, tiLeTest=0.30, random_state=42)
    logging.info("Tập Train: %d mẫu (%d học sinh), Tập Test: %d mẫu (%d học sinh)",
                 len(dfTrain), dfTrain["maHocSinh"].nunique(), len(dfTest), dfTest["maHocSinh"].nunique())

    cacCotDacTrung = DAC_TRUNG_SO + DAC_TRUNG_PHAN_LOAI
    xTrain = dfTrain[cacCotDacTrung]
    yTrain = dfTrain["nhanPhuHop"]
    xTest = dfTest[cacCotDacTrung]
    yTest = dfTest["nhanPhuHop"]

    baselineMean = Pipeline([
        ("tienXuLy", taoPipelineTienXuLy()),
        ("moHinh", DummyRegressor(strategy="mean")),
    ])
    baselineMean.fit(xTrain, yTrain)
    yDuDoanMean = baselineMean.predict(xTest)
    maeMean = mean_absolute_error(yTest, yDuDoanMean)
    rmseMean = np.sqrt(mean_squared_error(yTest, yDuDoanMean))

    treeDon = Pipeline([
        ("tienXuLy", taoPipelineTienXuLy()),
        ("moHinh", DecisionTreeRegressor(max_depth=6, random_state=42)),
    ])
    treeDon.fit(xTrain, yTrain)
    yDuDoanTree = treeDon.predict(xTest)
    maeTree = mean_absolute_error(yTest, yDuDoanTree)
    rmseTree = np.sqrt(mean_squared_error(yTest, yDuDoanTree))

    rfReg = RandomForestRegressor(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=2,
        min_samples_split=4,
        random_state=42,
        n_jobs=-1,
    )
    pipelineHoanChinh = Pipeline([
        ("tienXuLy", taoPipelineTienXuLy()),
        ("moHinh", rfReg),
    ])

    logging.info("Bắt đầu fit RandomForestRegressor...")
    pipelineHoanChinh.fit(xTrain, yTrain)
    yDuDoanRf = pipelineHoanChinh.predict(xTest)
    maeRf = mean_absolute_error(yTest, yDuDoanRf)
    rmseRf = np.sqrt(mean_squared_error(yTest, yDuDoanRf))
    r2Rf = r2_score(yTest, yDuDoanRf)

    logging.info("KẾT QUẢ ĐÁNH GIÁ TRÊN TẬP TEST:")
    logging.info("  * Baseline Mean: MAE=%.4f, RMSE=%.4f", maeMean, rmseMean)
    logging.info("  * Decision Tree: MAE=%.4f, RMSE=%.4f", maeTree, rmseTree)
    logging.info("  * Random Forest: MAE=%.4f, RMSE=%.4f, R2=%.4f", maeRf, rmseRf, r2Rf)

    joblib.dump(pipelineHoanChinh, duongDanMoHinh)
    maChecksum = tinhMaBamFile(duongDanMoHinh)
    logging.info("Đã lưu artifact pipeline tại: %s (Checksum: %s)", duongDanMoHinh, maChecksum)

    thoiDiemHienTai = datetime.now(timezone.utc).isoformat()
    thongTinManifest = {
        "tenMoHinh": "HeThongDeXuatNguyenVongRandomForest",
        "thuatToan": "RandomForestRegressor",
        "phienBan": "v1.0.0",
        "duLieuMoPhong": True,
        "thamSo": {
            "n_estimators": 300,
            "max_depth": 10,
            "min_samples_leaf": 2,
            "min_samples_split": 4,
            "random_state": 42,
        },
        "danhSachDacTrung": cacCotDacTrung,
        "thongTinTapChia": {
            "phuongPhap": "GroupShuffleSplit_TheoHocSinh",
            "tongMau": len(df),
            "mauTrain": len(dfTrain),
            "mauTest": len(dfTest),
            "soHocSinhTrain": int(dfTrain["maHocSinh"].nunique()),
            "soHocSinhTest": int(dfTest["maHocSinh"].nunique()),
        },
        "chiSoDanhGia": {
            "randomForest": {
                "MAE": round(float(maeRf), 4),
                "RMSE": round(float(rmseRf), 4),
                "R2": round(float(r2Rf), 4),
            },
            "baselineMean": {
                "MAE": round(float(maeMean), 4),
                "RMSE": round(float(rmseMean), 4),
            },
            "decisionTree": {
                "MAE": round(float(maeTree), 4),
                "RMSE": round(float(rmseTree), 4),
            },
        },
        "phienBanThuVien": {
            "scikit-learn": sklearn.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "joblib": joblib.__version__,
        },
        "thoiGianHuanLuyen": thoiDiemHienTai,
        "checksumSha256": maChecksum,
    }

    with open(duongDanManifest, "w", encoding="utf-8") as f:
        json.dump(thongTinManifest, f, indent=2, ensure_ascii=False)
    logging.info("Đã lưu manifest tại: %s", duongDanManifest)

    try:
        phien = layPhienKetNoi()
        try:
            phien.query(PhienBanMoHinh).update({"dangKichHoat": False})
            pbMoi = PhienBanMoHinh(
                tenPhienBan=f"RF_v1_{int(datetime.now().timestamp())}",
                thuatToan="RandomForestRegressor",
                thamSoJson=json.dumps(thongTinManifest["thamSo"]),
                danhSachDacTrungJson=json.dumps(cacCotDacTrung),
                chiSoDanhGiaJson=json.dumps(thongTinManifest["chiSoDanhGia"]),
                maBamChecksum=maChecksum,
                dangKichHoat=True,
            )
            phien.add(pbMoi)
            phien.commit()
            logging.info("Đã kích hoạt phiên bản mô hình trong cơ sở dữ liệu.")
        except Exception as e:
            phien.rollback()
            logging.info("Huấn luyện thành công qua CSV (bỏ qua cập nhật DB: %s)", e)
        finally:
            dongPhienKetNoi()
    except Exception as e:
        logging.info("Huấn luyện thành công qua CSV (không kết nối MySQL: %s)", e)

    moHinhNapLai = joblib.load(duongDanMoHinh)
    kiemThuDuDoan = moHinhNapLai.predict(xTest.iloc[:2])
    logging.info("Kiểm chứng dự đoán từ artifact nạp lại: %s", kiemThuDuDoan)

    return thongTinManifest


if __name__ == "__main__":
    huanLuyenVaLuuPipeline()
