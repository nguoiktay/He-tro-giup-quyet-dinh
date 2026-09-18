# -*- coding: utf-8 -*-
"""
Cấu hình hệ thống DSS (FastAPI / SQLAlchemy / JWT).
Quy tắc: Tiếng Việt không dấu, camelCase cho biến và thuộc tính, PascalCase cho Class.
"""

import os

class CaiDat:
    # Cấu hình JWT
    khoaBiMatJWT: str = os.environ.get("KHOA_BI_MAT_JWT", "khoaBiMatMacDinhChoHeThongDss2026")
    thuatToanJWT: str = os.environ.get("THUAT_TOAN_JWT", "HS256")
    thoiHanTokenPhut: int = int(os.environ.get("THOI_HAN_TOKEN_PHUT", 1440))  # 24 giờ

    # Cấu hình CSDL MySQL
    tenDangNhapCSDL: str = os.environ.get("MYSQL_USER", "root")
    matKhauCSDL: str = os.environ.get("MYSQL_PASSWORD", "")
    mayChuCSDL: str = os.environ.get("MYSQL_HOST", "127.0.0.1")
    congCSDL: int = int(os.environ.get("MYSQL_PORT", 3306))
    tenCSDL: str = os.environ.get("MYSQL_DB", "heTroGiupQuyetDinh")

    @property
    def duongDanKetNoiCSDL(self) -> str:
        duongDanEnv = os.environ.get("DATABASE_URL")
        if duongDanEnv:
            return duongDanEnv
        return f"mysql+pymysql://{self.tenDangNhapCSDL}:{self.matKhauCSDL}@{self.mayChuCSDL}:{self.congCSDL}/{self.tenCSDL}?charset=utf8mb4"

caiDat = CaiDat()
