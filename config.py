import os

class CauHinh:
    SECRET_KEY = os.environ.get("KHOA_BI_MAT", "khoaBiMatMacDinhChoHeThongDss2026")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQL_DB", "heTroGiupQuyetDinh")
    
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 3600,
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    }
    
    THOI_HAN_PHIEN_GIO = 24
    SO_LAN_DANG_NHAP_SAI_TOI_DA = 5
    THOI_GIAN_KHOA_TAI_KHOAN_PHUT = 15
    
    THU_MUC_GOC = os.path.dirname(os.path.abspath(__file__))
    DUONG_DAN_DATASET_CSV = os.path.join(THU_MUC_GOC, "data", "dataset.csv")
    DUONG_DAN_MO_HINH = os.path.join(THU_MUC_GOC, "models", "pipeline_model.joblib")
    DUONG_DAN_MANIFEST = os.path.join(THU_MUC_GOC, "models", "model_manifest.json")
    DUONG_DAN_DU_LIEU_GOC = os.path.join(THU_MUC_GOC, "Du_Lieu_Tuyen_Sinh_Tong_Hop_2021_2026.xlsx")


class CauHinhKiemThu(CauHinh):
    MYSQL_DB = os.environ.get("MYSQL_TEST_DB", "heTroGiupQuyetDinhKiemThu")
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{CauHinh.MYSQL_USER}:{CauHinh.MYSQL_PASSWORD}@{CauHinh.MYSQL_HOST}:{CauHinh.MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    )
    TESTING = True
