
from datetime import datetime, timedelta
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.cauHinh import caiDat
from app.models.coSoDuLieu import layPhienLamViecCSDL, NguoiDung

soDoXacThuc = OAuth2PasswordBearer(tokenUrl="/api/dangNhap")

def bamMatKhau(matKhauGoc: str) -> str:
    """
    Băm mật khẩu người dùng an toàn bằng bcrypt.
    """
    muoi = bcrypt.gensalt()
    return bcrypt.hashpw(matKhauGoc.encode('utf-8'), muoi).decode('utf-8')

def kiemTraMatKhau(matKhauNhap: str, matKhauDaBam: str) -> bool:
    """
    Kiểm tra mật khẩu nhập vào khớp với chuỗi bcrypt hash.
    """
    try:
        return bcrypt.checkpw(matKhauNhap.encode('utf-8'), matKhauDaBam.encode('utf-8'))
    except Exception:
        return False

def taoTokenTruyCap(duLieuPayload: dict) -> str:
    """
    Tạo JSON Web Token (JWT) có thời hạn hiệu lực.
    """
    duLieu = duLieuPayload.copy()
    thoiGianHetHan = datetime.utcnow() + timedelta(minutes=caiDat.thoiHanTokenPhut)
    duLieu.update({"exp": thoiGianHetHan})
    return jwt.encode(duLieu, caiDat.khoaBiMatJWT, algorithm=caiDat.thuatToanJWT)

def xacThucToken(chuoiToken: str) -> dict:
    """
    Giải mã và xác thực tính hợp lệ của token.
    """
    try:
        giaiMa = jwt.decode(chuoiToken, caiDat.khoaBiMatJWT, algorithms=[caiDat.thuatToanJWT])
        return giaiMa
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại!",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token xác thực không hợp lệ!",
            headers={"WWW-Authenticate": "Bearer"},
        )

def layNguoiDungHienTai(
    chuoiToken: str = Depends(soDoXacThuc),
    phienCSDL: Session = Depends(layPhienLamViecCSDL)
) -> NguoiDung:
    """
    Dependency lấy người dùng hiện tại từ Bearer Token.
    """
    payload = xacThucToken(chuoiToken)
    tenDangNhap = payload.get("sub")
    if not tenDangNhap:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token thiếu thông tin người dùng!")
        
    nguoiDung = phienCSDL.query(NguoiDung).filter(NguoiDung.tenDangNhap == tenDangNhap).first()
    if not nguoiDung:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại!")
        
    return nguoiDung

def kiemTraQuyenQuanTri(nguoiDungHienTai: NguoiDung = Depends(layNguoiDungHienTai)) -> NguoiDung:
    """
    Chỉ cho phép tài khoản có vai trò Quản trị viên (quanTri) truy cập.
    """
    if nguoiDungHienTai.vaiTro != "quanTri":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền quản trị để thực hiện chức năng này!"
        )
    return nguoiDungHienTai
