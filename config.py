import os
import secrets
from typing import Dict, Any

ENV: str = os.environ.get("ENV", "development").lower()

TARGET_YEAR: int = int(os.environ.get("DSS_TARGET_YEAR", 2027))
REFERENCE_YEAR: int = int(os.environ.get("DSS_REFERENCE_YEAR", 2026))

DSS_SECRET_KEY: str = os.environ.get("DSS_SECRET_KEY", "")
if not DSS_SECRET_KEY:
    if ENV == "production":
        raise RuntimeError("DSS_SECRET_KEY bắt buộc phải được thiết lập qua biến môi trường trong môi trường production.")
    DSS_SECRET_KEY = secrets.token_hex(32)

PBKDF2_ITERATIONS: int = int(os.environ.get("DSS_PBKDF2_ITERS", 600000))
MAX_FAILED_LOGINS: int = 5
LOCKOUT_SECONDS: int = 900

WEIGHT_DIEM_THUAN_LOI: float = 0.70
WEIGHT_SO_THICH: float = 0.30

TIER_SAFE_THRESHOLD: float = 80.0
TIER_SUITABLE_THRESHOLD: float = 40.0
TIER_CHALLENGE_THRESHOLD: float = 15.0
