import argparse
import base64
import hashlib
import hmac
import json
import re
import secrets
import sys
import threading
import time
from typing import Dict, Optional, Any

import config
from csvDatabase import CsvDatabase

SECRET_KEY: str = config.DSS_SECRET_KEY
PBKDF2_ITERATIONS: int = config.PBKDF2_ITERATIONS

_auth_lock = threading.Lock()
_failed_attempts: Dict[str, Dict[str, Any]] = {}


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt}${key.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    if str(stored_hash).startswith("pbkdf2:"):
        try:
            parts = stored_hash.split("$")
            if len(parts) == 3:
                header, salt, key_hex = parts
                iters = int(header.split(":")[-1])
                calc_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iters)
                return hmac.compare_digest(key_hex, calc_key.hex())
        except Exception:
            return False

    legacy_salt = "dss_salt_2026"
    legacy_hash = hashlib.sha256(f"{plain_password}:{legacy_salt}".encode("utf-8")).hexdigest()
    if hmac.compare_digest(str(stored_hash), legacy_hash):
        return True

    raw_sha256 = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(str(stored_hash), raw_sha256)


def create_jwt_token(user_data: Dict[str, Any], expire_seconds: int = 86400) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "userId": user_data.get("id"),
        "username": user_data.get("tenDangNhap"),
        "role": user_data.get("vaiTro"),
        "exp": int(time.time()) + expire_seconds
    }

    h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    p_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")

    signature = hmac.new(
        SECRET_KEY.encode(),
        f"{h_b64}.{p_b64}".encode(),
        hashlib.sha256
    ).digest()
    s_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{h_b64}.{p_b64}.{s_b64}"


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.strip().split(".")
        if len(parts) != 3:
            return None
        h_b64, p_b64, s_b64 = parts

        expected_sig = hmac.new(
            SECRET_KEY.encode(),
            f"{h_b64}.{p_b64}".encode(),
            hashlib.sha256
        ).digest()
        calc_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")

        if not hmac.compare_digest(s_b64, calc_sig_b64):
            return None

        rem = len(p_b64) % 4
        if rem > 0:
            p_b64 += "=" * (4 - rem)
        payload = json.loads(base64.urlsafe_b64decode(p_b64).decode())

        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


hashPassword = hash_password
verifyPassword = verify_password
createJwtToken = create_jwt_token
verifyJwtToken = verify_jwt_token


class AuthService:
    SECRET_KEY = SECRET_KEY

    @classmethod
    def dangKy(
        cls,
        tenDangNhap: str,
        matKhau: str,
        hoTen: str,
        email: str,
        soDienThoai: str = "",
        vaiTro: str = "hocSinh"
    ) -> Dict[str, Any]:
        email_clean = str(email or "").strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_clean):
            return {"thanhCong": False, "thongBao": "Địa chỉ email không đúng định dạng hợp lệ."}

        ten_clean = str(tenDangNhap or "").strip().lower()
        if not ten_clean:
            return {"thanhCong": False, "thongBao": "Tên đăng nhập không được để trống."}

        existing_user = CsvDatabase.findWhere("nguoiDung", {"tenDangNhap": ten_clean})
        if existing_user:
            return {"thanhCong": False, "thongBao": f"Tên đăng nhập '{ten_clean}' đã tồn tại trên hệ thống."}

        existing_email = CsvDatabase.findWhere("nguoiDung", {"email": email_clean})
        if existing_email:
            return {"thanhCong": False, "thongBao": f"Địa chỉ email '{email_clean}' đã được sử dụng trên hệ thống."}

        hashed_pw = hash_password(matKhau)
        new_user = CsvDatabase.insert("nguoiDung", {
            "tenDangNhap": ten_clean,
            "matKhau": hashed_pw,
            "hoTen": hoTen.strip(),
            "email": email_clean,
            "soDienThoai": str(soDienThoai or "").strip(),
            "vaiTro": vaiTro,
            "ngayTao": time.strftime("%Y-%m-%d %H:%M:%S")
        })

        token = create_jwt_token(new_user)
        return {
            "thanhCong": True,
            "thongBao": "Đăng ký tài khoản thành công.",
            "token": token,
            "nguoiDung": {
                "id": new_user["id"],
                "tenDangNhap": new_user["tenDangNhap"],
                "hoTen": new_user["hoTen"],
                "email": new_user["email"],
                "vaiTro": new_user["vaiTro"]
            }
        }

    @classmethod
    def dangNhap(cls, tenDangNhap: str, matKhau: str) -> Dict[str, Any]:
        ten_clean = str(tenDangNhap or "").strip().lower()

        with _auth_lock:
            now = time.time()
            attempt = _failed_attempts.get(ten_clean, {})
            locked_until = attempt.get("locked_until", 0)
            if locked_until > now:
                remaining = int(locked_until - now)
                return {
                    "thanhCong": False,
                    "thongBao": f"Tài khoản bị tạm khóa do đăng nhập sai nhiều lần. Vui lòng thử lại sau {remaining} giây."
                }

        users = CsvDatabase.findWhere("nguoiDung", {"tenDangNhap": ten_clean})
        if not users:
            cls._record_failed_attempt(ten_clean)
            return {"thanhCong": False, "thongBao": "Tên đăng nhập hoặc mật khẩu không chính xác."}

        user = users[0]
        stored_hash = str(user.get("matKhau", ""))
        if not verify_password(matKhau, stored_hash):
            return cls._record_failed_attempt(ten_clean)

        with _auth_lock:
            _failed_attempts.pop(ten_clean, None)

        needs_upgrade = False
        if not stored_hash.startswith("pbkdf2:"):
            needs_upgrade = True
        else:
            try:
                parts = stored_hash.split("$")
                iters = int(parts[0].split(":")[-1])
                if iters < PBKDF2_ITERATIONS:
                    needs_upgrade = True
            except Exception:
                needs_upgrade = True

        if needs_upgrade:
            new_hash = hash_password(matKhau)
            user["matKhau"] = new_hash
            CsvDatabase.update("nguoiDung", user["id"], {"matKhau": new_hash})

        token = create_jwt_token(user)
        return {
            "thanhCong": True,
            "thongBao": "Đăng nhập thành công.",
            "token": token,
            "nguoiDung": {
                "id": user["id"],
                "tenDangNhap": user["tenDangNhap"],
                "hoTen": user["hoTen"],
                "email": user["email"],
                "vaiTro": user["vaiTro"]
            }
        }

    @classmethod
    def _record_failed_attempt(cls, username: str) -> Dict[str, Any]:
        with _auth_lock:
            now = time.time()
            entry = _failed_attempts.get(username, {"count": 0, "locked_until": 0})
            cnt = entry.get("count", 0) + 1
            if cnt >= config.MAX_FAILED_LOGINS:
                _failed_attempts[username] = {"count": 0, "locked_until": now + config.LOCKOUT_SECONDS}
                return {
                    "thanhCong": False,
                    "thongBao": f"Đăng nhập sai quá {config.MAX_FAILED_LOGINS} lần. Tài khoản bị tạm khóa 15 phút."
                }
            _failed_attempts[username] = {"count": cnt, "locked_until": 0}
            return {"thanhCong": False, "thongBao": "Tên đăng nhập hoặc mật khẩu không chính xác."}

    @classmethod
    def moKhoaTaiKhoan(cls, username: str) -> bool:
        with _auth_lock:
            cleaned = str(username or "").strip().lower()
            if cleaned in _failed_attempts:
                del _failed_attempts[cleaned]
                return True
            return False

    @classmethod
    def layThongTinNguoiDung(cls, token: str) -> Optional[Dict[str, Any]]:
        payload = verify_jwt_token(token)
        if not payload:
            return None
        user_id = payload.get("userId")
        user = CsvDatabase.findById("nguoiDung", user_id)
        if not user:
            return None
        return {
            "id": user["id"],
            "tenDangNhap": user["tenDangNhap"],
            "hoTen": user["hoTen"],
            "email": user["email"],
            "vaiTro": user["vaiTro"]
        }


def create_admin_account(
    tenDangNhap: str,
    matKhau: str,
    hoTen: str = "Quản Trị Viên Hệ Thống",
    email: str = "admin@dss-admission.edu.vn",
    soDienThoai: str = "0988888888"
) -> Dict[str, Any]:
    ten_clean = str(tenDangNhap).strip().lower()
    existing = CsvDatabase.findWhere("nguoiDung", {"tenDangNhap": ten_clean})
    if existing:
        new_hash = hash_password(matKhau)
        CsvDatabase.update("nguoiDung", existing[0]["id"], {
            "matKhau": new_hash,
            "vaiTro": "quanTriVien"
        })
        return {"thanhCong": True, "thongBao": f"Đã cập nhật mật khẩu cho quản trị viên '{ten_clean}'."}

    return AuthService.dangKy(
        tenDangNhap=ten_clean,
        matKhau=matKhau,
        hoTen=hoTen,
        email=email,
        soDienThoai=soDienThoai,
        vaiTro="quanTriVien"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quản lý tài khoản quản trị viên qua dòng lệnh CLI")
    subparsers = parser.add_subparsers(dest="command")

    admin_parser = subparsers.add_parser("create-admin", help="Tạo hoặc cập nhật tài khoản quản trị viên")
    admin_parser.add_argument("--username", required=True, help="Tên đăng nhập admin")
    admin_parser.add_argument("--password", required=True, help="Mật khẩu admin")
    admin_parser.add_argument("--name", default="Quản Trị Viên Hệ Thống", help="Họ và tên")
    admin_parser.add_argument("--email", default="admin@dss-admission.edu.vn", help="Email")

    args = parser.parse_args()
    if args.command == "create-admin":
        res = create_admin_account(args.username, args.password, hoTen=args.name, email=args.email)
        print(res.get("thongBao"))
    else:
        parser.print_help()
