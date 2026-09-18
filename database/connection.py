from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from config import CauHinh

CoSoDuLieu = declarative_base()

def taoDongCo(duongDanKetNoi=None):
    if duongDanKetNoi is None:
        duongDanKetNoi = CauHinh.SQLALCHEMY_DATABASE_URI
    dongCo = create_engine(
        duongDanKetNoi,
        pool_recycle=CauHinh.SQLALCHEMY_ENGINE_OPTIONS["pool_recycle"],
        pool_pre_ping=CauHinh.SQLALCHEMY_ENGINE_OPTIONS["pool_pre_ping"],
        pool_size=CauHinh.SQLALCHEMY_ENGINE_OPTIONS["pool_size"],
        max_overflow=CauHinh.SQLALCHEMY_ENGINE_OPTIONS["max_overflow"],
    )
    return dongCo

dongCoMacDinh = taoDongCo()
PhienKetNoi = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=dongCoMacDinh))

def layPhienKetNoi():
    return PhienKetNoi()

def dongPhienKetNoi(ngoaiLe=None):
    PhienKetNoi.remove()
