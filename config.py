import os
import secrets
from typing import Dict, Any


def _load_dotenv(path: str) -> None:
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().removeprefix("export ").strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

ENV: str = os.environ.get("ENV", "development").lower()

TARGET_YEAR: int = int(os.environ.get("DSS_TARGET_YEAR", 2027))
REFERENCE_YEAR: int = int(os.environ.get("DSS_REFERENCE_YEAR", 2026))
MAX_REFERENCE_AGE: int = int(os.environ.get("DSS_MAX_REFERENCE_AGE", 1))

DSS_SECRET_KEY: str = os.environ.get("DSS_SECRET_KEY", "")
if not DSS_SECRET_KEY:
    if ENV == "production":
        raise RuntimeError("DSS_SECRET_KEY bat buoc phai duoc thiet lap qua bien moi truong trong moi truong production.")
    DSS_SECRET_KEY = secrets.token_hex(32)

PBKDF2_ITERATIONS: int = int(os.environ.get("DSS_PBKDF2_ITERS", 600000))
MAX_FAILED_LOGINS: int = 5
LOCKOUT_SECONDS: int = 900

WEIGHT_DIEM_THUAN_LOI: float = 0.70
WEIGHT_SO_THICH: float = 0.30

TIER_SAFE_THRESHOLD: float = 80.0
TIER_SUITABLE_THRESHOLD: float = 40.0
TIER_CHALLENGE_THRESHOLD: float = 15.0
