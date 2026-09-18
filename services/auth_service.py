import os
import sys
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
import bcrypt

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from database.connection import layPhienKetNoi, dongPhienKetNoi
from database.models import TaiKhoan, PhienDangNhap, HocSinh, DanhSachNguyenVong
from config import CauHinh


def bămMatKhau(matKhauRõ):
    matKhauBytes = matKhauRõ.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(matKhauBytes, salt).decode("utf-8")


def kiemTraMatKhau(matKhauRõ, matKhauHash):
    try:
        return bcrypt.checkpw(matKhauRõ.encode("utf-8"), matKhauHash.encode("utf-8"))
    except Exception:
        return False


def bamTokenPhien(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class DichVuXacThuc:

    @staticmethod
    def chuanHoaEmail(email):
        if not email:
            return ""
        return email.strip().lower()

    @classmethod
    def dangKy(cls, email, matKhau, hoTen, vaiTro="hocSinh", soDienThoai=None):
        emailChuan = cls.chuanHoaEmail(email)
        if not emailChuan or "@" not in emailChuan:
            return {"thanhCong": False, "thongBao": "Email không hợp lệ."}
        if len(matKhau) < 8:
            return {"thanhCong": False, "thongBao": "Mật khẩu phải có ít nhất 8 ký tự."}
        if not hoTen or not hoTen.strip():
            return {"thanhCong": False, "thongBao": "Họ và tên không được để trống."}

        phien = layPhienKetNoi()
        try:
            taiKhoanTonTai = phien.query(TaiKhoan).filter_by(email=emailChuan).first()
            if taiKhoanTonTai:
                return {"thanhCong": False, "thongBao": "Email đã được sử dụng trong hệ thống."}

            matKhauHash = bămMatKhau(matKhau)
            taiKhoanMoi = TaiKhoan(
                email=emailChuan,
                matKhauHash=matKhauHash,
                vaiTro=vaiTro if vaiTro in ["hocSinh", "quanTriVien"] else "hocSinh",
                trangThai="kichHoat",
                soLanDangNhapSai=0,
            )
            phien.add(taiKhoanMoi)
            phien.flush()

            if taiKhoanMoi.vaiTro == "hocSinh":
                hocSinhMoi = HocSinh(
                    maTaiKhoan=taiKhoanMoi.maTaiKhoan,
                    hoTen=hoTen.strip(),
                    soDienThoai=soDienThoai.strip() if soDienThoai else None,
                    namDuTuyen=2026,
                    kyTinhNganSach="nam",
                    batBuocNganSach=False,
                    batBuocDiaBan=False,
                )
                phien.add(hocSinhMoi)
                phien.flush()

                dsnv = DanhSachNguyenVong(
                    maHocSinh=hocSinhMoi.maHocSinh,
                    tenDanhSach="Danh sách nguyện vọng chính thức",
                    phienBan=1,
                )
                phien.add(dsnv)

            phien.commit()
            return {
                "thanhCong": True,
                "thongBao": "Đăng ký tài khoản thành công.",
                "maTaiKhoan": taiKhoanMoi.maTaiKhoan,
            }
        except Exception as e:
            phien.rollback()
            return {"thanhCong": False, "thongBao": f"Lỗi hệ thống khi đăng ký: {str(e)}"}
        finally:
            dongPhienKetNoi()

    @classmethod
    def dangNhap(cls, email, matKhau, diaChiIp=None, tacNhanNguoiDung=None):
        emailChuan = cls.chuanHoaEmail(email)
        if not emailChuan or not matKhau:
            return {"thanhCong": False, "thongBao": "Vui lòng nhập đầy đủ email và mật khẩu."}

        phien = layPhienKetNoi()
        try:
            taiKhoan = phien.query(TaiKhoan).filter_by(email=emailChuan).first()
            if not taiKhoan:
                return {"thanhCong": False, "thongBao": "Tài khoản hoặc mật khẩu không chính xác."}

            bayGio = datetime.now(timezone.utc).replace(tzinfo=None)
            if taiKhoan.khoaDenThoiDiem and taiKhoan.khoaDenThoiDiem > bayGio:
                soPhutConLai = int((taiKhoan.khoaDenThoiDiem - bayGio).total_seconds() / 60) + 1
                return {
                    "thanhCong": False,
                    "thongBao": f"Tài khoản đang bị tạm khóa do thử sai nhiều lần. Vui lòng thử lại sau {soPhutConLai} phút.",
                }

            if not kiemTraMatKhau(matKhau, taiKhoan.matKhauHash):
                taiKhoan.soLanDangNhapSai += 1
                if taiKhoan.soLanDangNhapSai >= CauHinh.SO_LAN_DANG_NHAP_SAI_TOI_DA:
                    taiKhoan.khoaDenThoiDiem = bayGio + timedelta(minutes=CauHinh.THOI_GIAN_KHOA_TAI_KHOAN_PHUT)
                    phien.commit()
                    return {
                        "thanhCong": False,
                        "thongBao": f"Đăng nhập sai quá {CauHinh.SO_LAN_DANG_NHAP_SAI_TOI_DA} lần. Tài khoản bị tạm khóa 15 phút.",
                    }
                phien.commit()
                return {"thanhCong": False, "thongBao": "Tài khoản hoặc mật khẩu không chính xác."}

            taiKhoan.soLanDangNhapSai = 0
            taiKhoan.khoaDenThoiDiem = None

            rawToken = secrets.token_urlsafe(32)
            tokenHash = bamTokenPhien(rawToken)
            thoiHanPhien = bayGio + timedelta(hours=CauHinh.THOI_HAN_PHIEN_GIO)

            phienDangNhap = PhienDangNhap(
                maTaiKhoan=taiKhoan.maTaiKhoan,
                maBamToken=tokenHash,
                thoiHan=thoiHanPhien,
                daThuHoi=False,
                diaChiIp=diaChiIp,
                tacNhanNguoiDung=tacNhanNguoiDung[:255] if tacNhanNguoiDung else None,
            )
            phien.add(phienDangNhap)
            phien.commit()

            thongTinHs = None
            if taiKhoan.vaiTro == "hocSinh" and taiKhoan.hocSinh:
                thongTinHs = {
                    "maHocSinh": taiKhoan.hocSinh.maHocSinh,
                    "hoTen": taiKhoan.hocSinh.hoTen,
                }

            csrfToken = secrets.token_hex(16)

            return {
                "thanhCong": True,
                "thongBao": "Đăng nhập thành công.",
                "token": rawToken,
                "csrfToken": csrfToken,
                "taiKhoan": {
                    "maTaiKhoan": taiKhoan.maTaiKhoan,
                    "email": taiKhoan.email,
                    "vaiTro": taiKhoan.vaiTro,
                },
                "hocSinh": thongTinHs,
            }
        except Exception as e:
            phien.rollback()
            return {"thanhCong": False, "thongBao": f"Lỗi hệ thống khi đăng nhập: {str(e)}"}
        finally:
            dongPhienKetNoi()

    @classmethod
    def xacThucToken(cls, rawToken):
        if not rawToken:
            return None
        tokenHash = bamTokenPhien(rawToken)
        phien = layPhienKetNoi()
        try:
            bayGio = datetime.now(timezone.utc).replace(tzinfo=None)
            phienDn = (
                phien.query(PhienDangNhap)
                .filter(
                    PhienDangNhap.maBamToken == tokenHash,
                    PhienDangNhap.daThuHoi == False,
                    PhienDangNhap.thoiHan > bayGio,
                )
                .first()
            )
            if not phienDn:
                return None

            taiKhoan = phienDn.taiKhoan
            if not taiKhoan or taiKhoan.trangThai != "kichHoat":
                return None

            ketQua = {
                "maTaiKhoan": taiKhoan.maTaiKhoan,
                "email": taiKhoan.email,
                "vaiTro": taiKhoan.vaiTro,
                "maPhien": phienDn.maPhien,
            }
            if taiKhoan.vaiTro == "hocSinh" and taiKhoan.hocSinh:
                ketQua["maHocSinh"] = taiKhoan.hocSinh.maHocSinh
                ketQua["hoTen"] = taiKhoan.hocSinh.hoTen
            return ketQua
        finally:
            dongPhienKetNoi()

    @classmethod
    def dangXuat(cls, rawToken):
        if not rawToken:
            return True
        tokenHash = bamTokenPhien(rawToken)
        phien = layPhienKetNoi()
        try:
            phienDn = phien.query(PhienDangNhap).filter_by(maBamToken=tokenHash).first()
            if phienDn:
                phienDn.daThuHoi = True
                phien.commit()
            return True
        except Exception:
            phien.rollback()
            return False
        finally:
            dongPhienKetNoi()

    @classmethod
    def doiMatKhau(cls, maTaiKhoan, matKhauCu, matKhauMoi):
        if len(matKhauMoi) < 8:
            return {"thanhCong": False, "thongBao": "Mật khẩu mới phải có ít nhất 8 ký tự."}
        phien = layPhienKetNoi()
        try:
            taiKhoan = phien.query(TaiKhoan).filter_by(maTaiKhoan=maTaiKhoan).first()
            if not taiKhoan:
                return {"thanhCong": False, "thongBao": "Tài khoản không tồn tại."}
            if not kiemTraMatKhau(matKhauCu, taiKhoan.matKhauHash):
                return {"thanhCong": False, "thongBao": "Mật khẩu cũ không chính xác."}

            taiKhoan.matKhauHash = bămMatKhau(matKhauMoi)
            phien.query(PhienDangNhap).filter(
                PhienDangNhap.maTaiKhoan == maTaiKhoan,
                PhienDangNhap.daThuHoi == False,
            ).update({"daThuHoi": True})
            phien.commit()
            return {"thanhCong": True, "thongBao": "Đổi mật khẩu thành công. Các phiên trước đã bị thu hồi."}
        except Exception as e:
            phien.rollback()
            return {"thanhCong": False, "thongBao": f"Lỗi đổi mật khẩu: {str(e)}"}
        finally:
            dongPhienKetNoi()
