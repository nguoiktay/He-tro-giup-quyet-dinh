import os
import sys
from datetime import datetime, timezone
from sqlalchemy import func

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

from database.connection import layPhienKetNoi, dongPhienKetNoi
from database.models import PhanHoi, HocSinh, PhienKhuyenNghi


class DichVuDanhGia:

    @classmethod
    def guiPhanHoi(
        cls,
        maHocSinh,
        mucDoHaiLong,
        tiLeHoanThanh=1.0,
        thoiGianHoanThanhPhut=5.0,
        danhGiaGiaiThich=5,
        yKienDongGop=None,
        maPhienKhuyenNghi=None,
    ):
        try:
            mucDoHaiLongInt = int(mucDoHaiLong)
            if mucDoHaiLongInt < 1 or mucDoHaiLongInt > 5:
                return {"thanhCong": False, "thongBao": "Mức độ hài lòng phải từ 1 đến 5 sao."}
        except (ValueError, TypeError):
            return {"thanhCong": False, "thongBao": "Mức độ hài lòng không đúng định dạng."}

        phien = layPhienKetNoi()
        try:
            ph = PhanHoi(
                maHocSinh=maHocSinh,
                maPhienKhuyenNghi=maPhienKhuyenNghi,
                mucDoHaiLong=mucDoHaiLongInt,
                tiLeHoanThanh=float(tiLeHoanThanh) if tiLeHoanThanh is not None else 1.0,
                thoiGianHoanThanhPhut=float(thoiGianHoanThanhPhut) if thoiGianHoanThanhPhut is not None else 5.0,
                danhGiaGiaiThich=int(danhGiaGiaiThich) if danhGiaGiaiThich is not None else 5,
                yKienDongGop=yKienDongGop.strip() if yKienDongGop else None,
                thoiDiem=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            phien.add(ph)
            phien.commit()
            return {"thanhCong": True, "thongBao": "Cảm ơn bạn đã gửi đánh giá hệ thống DSS!"}
        except Exception as e:
            phien.rollback()
            return {"thanhCong": False, "thongBao": f"Lỗi khi gửi phản hồi: {str(e)}"}
        finally:
            dongPhienKetNoi()

    @classmethod
    def layThongKePhanHoi(cls):
        phien = layPhienKetNoi()
        try:
            tongSo = phien.query(PhanHoi).count()
            if tongSo == 0:
                return {
                    "tongSoPhanHoi": 0,
                    "haiLongTrungBinh": 0.0,
                    "tiLeHoanThanhTrungBinh": 0.0,
                    "thoiGianTrungBinhPhut": 0.0,
                    "giaiThichTrungBinh": 0.0,
                    "danhSachPhanHoiMoi": [],
                }

            haiLongTb = phien.query(func.avg(PhanHoi.mucDoHaiLong)).scalar() or 0.0
            tiLeTb = phien.query(func.avg(PhanHoi.tiLeHoanThanh)).scalar() or 0.0
            thoiGianTb = phien.query(func.avg(PhanHoi.thoiGianHoanThanhPhut)).scalar() or 0.0
            giaiThichTb = phien.query(func.avg(PhanHoi.danhGiaGiaiThich)).scalar() or 0.0

            danhSachMoi = (
                phien.query(PhanHoi)
                .order_by(PhanHoi.thoiDiem.desc())
                .limit(20)
                .all()
            )

            return {
                "tongSoPhanHoi": tongSo,
                "haiLongTrungBinh": round(float(haiLongTb), 2),
                "tiLeHoanThanhTrungBinh": round(float(tiLeTb) * 100, 1),
                "thoiGianTrungBinhPhut": round(float(thoiGianTb), 1),
                "giaiThichTrungBinh": round(float(giaiThichTb), 2),
                "danhSachPhanHoiMoi": [
                    {
                        "maPhanHoi": p.maPhanHoi,
                        "maHocSinh": p.maHocSinh,
                        "mucDoHaiLong": p.mucDoHaiLong,
                        "tiLeHoanThanh": p.tiLeHoanThanh,
                        "thoiGianHoanThanhPhut": p.thoiGianHoanThanhPhut,
                        "danhGiaGiaiThich": p.danhGiaGiaiThich,
                        "yKienDongGop": p.yKienDongGop,
                        "thoiDiem": p.thoiDiem.strftime("%Y-%m-%d %H:%M"),
                    }
                    for p in danhSachMoi
                ],
            }
        finally:
            dongPhienKetNoi()
