import hashlib
import hmac
import time
import json
import base64
from typing import Dict, Optional, Any
from csvDatabase import CsvDatabase

import os
import re
import secrets

PBKDF2_ITERATIONS = int(os.environ.get("DSS_PBKDF2_ITERS", 600000))
SECRET_KEY = os.environ.get("DSS_SECRET_KEY") or secrets.token_hex(32)

def hashPassword(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt}${key.hex()}"

def verifyPassword(plainPassword: str, storedHash: str) -> bool:
    if not storedHash:
        return False
    if str(storedHash).startswith("pbkdf2:"):
        try:
            parts = storedHash.split("$")
            if len(parts) == 3:
                header, salt, keyHex = parts
                iters = int(header.split(":")[-1])
                calcKey = hashlib.pbkdf2_hmac("sha256", plainPassword.encode("utf-8"), salt.encode("utf-8"), iters)
                return hmac.compare_digest(keyHex, calcKey.hex())
        except Exception:
            return False
    legacySalt = "dss_salt_2026"
    legacyHash = hashlib.sha256(f"{plainPassword}:{legacySalt}".encode("utf-8")).hexdigest()
    return hmac.compare_digest(str(storedHash), legacyHash)

def createJwtToken(userData: Dict[str, Any], expireSeconds: int = 86400) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "userId": userData.get("id"),
        "username": userData.get("tenDangNhap"),
        "role": userData.get("vaiTro"),
        "exp": int(time.time()) + expireSeconds
    }

    hB64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    pB64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")

    signature = hmac.new(
        SECRET_KEY.encode(),
        f"{hB64}.{pB64}".encode(),
        hashlib.sha256
    ).digest()
    sB64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

    return f"{hB64}.{pB64}.{sB64}"

def verifyJwtToken(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.strip().split(".")
        if len(parts) != 3:
            return None
        hB64, pB64, sB64 = parts

        expectedSig = hmac.new(
            SECRET_KEY.encode(),
            f"{hB64}.{pB64}".encode(),
            hashlib.sha256
        ).digest()
        calcSigB64 = base64.urlsafe_b64encode(expectedSig).decode().rstrip("=")

        if not hmac.compare_digest(sB64, calcSigB64):
            return None

        rem = len(pB64) % 4
        if rem > 0:
            pB64 += "=" * (4 - rem)
        payloadJson = base64.urlsafe_b64decode(pB64).decode()
        payload = json.loads(payloadJson)

        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None

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
        emailClean = str(email or "").strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", emailClean):
            return {"thanhCong": False, "thongBao": "Địa chỉ email không đúng định dạng hợp lệ."}

        phoneClean = str(soDienThoai or "").strip()
        if phoneClean.endswith(".0"):
            phoneClean = phoneClean[:-2]
        if len(phoneClean) == 9 and not phoneClean.startswith("0"):
            phoneClean = "0" + phoneClean

        tenClean = tenDangNhap.strip().lower()
        existing = CsvDatabase.findWhere("nguoiDung", {"tenDangNhap": tenClean})
        if existing:
            return {"thanhCong": False, "thongBao": f"Tên đăng nhập '{tenClean}' đã tồn tại trên hệ thống."}

        hashedPw = hashPassword(matKhau)
        newUser = CsvDatabase.insert("nguoiDung", {
            "tenDangNhap": tenClean,
            "matKhau": hashedPw,
            "hoTen": hoTen.strip(),
            "email": emailClean,
            "soDienThoai": phoneClean,
            "vaiTro": vaiTro,
            "ngayTao": time.strftime("%Y-%m-%d %H:%M:%S")
        })

        token = createJwtToken(newUser)
        return {
            "thanhCong": True,
            "thongBao": "Đăng ký tài khoản thành công.",
            "token": token,
            "nguoiDung": {
                "id": newUser["id"],
                "tenDangNhap": newUser["tenDangNhap"],
                "hoTen": newUser["hoTen"],
                "email": newUser["email"],
                "vaiTro": newUser["vaiTro"]
            }
        }

    @classmethod
    def dangNhap(cls, tenDangNhap: str, matKhau: str) -> Dict[str, Any]:
        tenClean = tenDangNhap.strip().lower()
        users = CsvDatabase.findWhere("nguoiDung", {"tenDangNhap": tenClean})
        if not users:
            return {"thanhCong": False, "thongBao": "Tên đăng nhập hoặc mật khẩu không chính xác."}

        user = users[0]
        storedHash = str(user.get("matKhau", ""))
        if not verifyPassword(matKhau, storedHash):
            return {"thanhCong": False, "thongBao": "Tên đăng nhập hoặc mật khẩu không chính xác."}

        needsUpgrade = False
        if not storedHash.startswith("pbkdf2:"):
            needsUpgrade = True
        else:
            try:
                parts = storedHash.split("$")
                iters = int(parts[0].split(":")[-1])
                if iters < PBKDF2_ITERATIONS:
                    needsUpgrade = True
            except Exception:
                needsUpgrade = True

        if needsUpgrade:
            newHash = hashPassword(matKhau)
            user["matKhau"] = newHash
            CsvDatabase.update("nguoiDung", user["id"], {"matKhau": newHash})

        token = createJwtToken(user)
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
    def layThongTinNguoiDung(cls, token: str) -> Optional[Dict[str, Any]]:
        payload = verifyJwtToken(token)
        if not payload:
            return None
        userId = payload.get("userId")
        user = CsvDatabase.findById("nguoiDung", userId)
        if not user:
            return None
        return {
            "id": user["id"],
            "tenDangNhap": user["tenDangNhap"],
            "hoTen": user["hoTen"],
            "email": user["email"],
            "vaiTro": user["vaiTro"]
        }
