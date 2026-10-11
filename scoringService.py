from typing import Dict, Optional, Any
from csvDatabase import CsvDatabase

class ScoringService:

    DIEM_KHU_VUC = {
        "KV1": 0.75,
        "KV2_NT": 0.50,
        "KV2-NT": 0.50,
        "KV2": 0.25,
        "KV3": 0.00
    }

    DIEM_DOI_TUONG = {
        "UT1": 2.00,
        "UT2": 1.00,
        "NONE": 0.00,
        "KHONG": 0.00
    }

    QUY_DOI_IELTS = {
        "IELTS 5.0": 7.0,
        "IELTS 5.5": 7.5,
        "IELTS 6.0": 8.0,
        "IELTS 6.5": 9.0,
        "IELTS 7.0": 9.5,
        "IELTS 7.5": 10.0,
        "IELTS 8.0": 10.0,
        "IELTS 8.5": 10.0,
        "IELTS 9.0": 10.0
    }

    @classmethod
    def tinhDiemToHop(cls, diemMonHoc: Dict[str, Any], maToHop: str) -> Optional[float]:
        toHopRecords = CsvDatabase.findWhere("toHopMon", {"maToHop": maToHop.strip().upper()})
        if not toHopRecords:
            return None

        th = toHopRecords[0]
        m1Key = th["mon1"]
        m2Key = th["mon2"]
        m3Key = th["mon3"]

        s1 = diemMonHoc.get(m1Key)
        s2 = diemMonHoc.get(m2Key)
        s3 = diemMonHoc.get(m3Key)

        if s1 is None or s2 is None or s3 is None:
            return None

        try:
            val1 = float(s1)
            val2 = float(s2)
            val3 = float(s3)
            return round(val1 + val2 + val3, 2)
        except (ValueError, TypeError):
            return None

    @classmethod
    def tinhDiemUuTien(
        cls,
        khuVuc: str = "KV3",
        doiTuong: str = "NONE",
        diemGoc: Optional[float] = None,
        thangDiem: str = "THANG_30"
    ) -> float:
        kvCode = str(khuVuc).strip().upper()
        dtCode = str(doiTuong).strip().upper()

        bonusKv = cls.DIEM_KHU_VUC.get(kvCode, 0.0)
        bonusDt = cls.DIEM_DOI_TUONG.get(dtCode, 0.0)
        tongUuTienGoc = bonusKv + bonusDt

        if tongUuTienGoc <= 0.0:
            return 0.0

        if thangDiem == "THANG_10":
            bonus10 = tongUuTienGoc / 3.0
            if diemGoc is not None and diemGoc >= 7.5:
                heSoGiam = (10.0 - min(diemGoc, 10.0)) / 2.5
                return round(bonus10 * max(heSoGiam, 0.0), 2)
            return round(bonus10, 2)

        elif thangDiem == "THANG_40":
            bonus40 = tongUuTienGoc * 4.0 / 3.0
            if diemGoc is not None and diemGoc >= 30.0:
                heSoGiam = (40.0 - min(diemGoc, 40.0)) / 10.0
                return round(bonus40 * max(heSoGiam, 0.0), 2)
            return round(bonus40, 2)

        else:
            if diemGoc is not None and diemGoc >= 22.5:
                heSoGiam = (30.0 - min(diemGoc, 30.0)) / 7.5
                return round(tongUuTienGoc * max(heSoGiam, 0.0), 2)
            return round(tongUuTienGoc, 2)

    @classmethod
    def tinhDiemXetTuyen(cls, diemToHop: float, diemUuTien: float = 0.0) -> float:
        return round(float(diemToHop) + float(diemUuTien), 2)

    @classmethod
    def tinhDiemXetTuyenChuongTrinh(
        cls,
        hoSoHocSinh: Dict[str, Any],
        maPhuongThuc: str,
        maToHop: str,
        calculationRuleId: str = "RULE_THPT_STD_30",
        scoreScale: str = "SCALE_30"
    ) -> Dict[str, Any]:
        khuVuc = hoSoHocSinh.get("khuVucUuTien", "KV3")
        doiTuong = hoSoHocSinh.get("doiTuongUuTien", "NONE")

        scoreFields = ["diemToan", "diemVan", "diemAnh", "diemLy", "diemHoa", "diemSinh", "diemSu", "diemDia", "diemGDCD"]
        diemMonHoc = {sf: hoSoHocSinh.get(sf) for sf in scoreFields}

        chungChi = hoSoHocSinh.get("chungChiQuocTe")
        if chungChi and str(chungChi).strip() in cls.QUY_DOI_IELTS:
            diemQuyDoiAnh = cls.QUY_DOI_IELTS[str(chungChi).strip()]
            if diemMonHoc["diemAnh"] is None or diemQuyDoiAnh > float(diemMonHoc["diemAnh"]):
                diemMonHoc["diemAnh"] = diemQuyDoiAnh

        ruleId = str(calculationRuleId).strip() if calculationRuleId else "RULE_THPT_STD_30"
        scale = str(scoreScale).strip() if scoreScale else "SCALE_30"

        if maPhuongThuc == "PT01":
            diemTho = cls.tinhDiemToHop(diemMonHoc, maToHop)
            if diemTho is None:
                return {"hopLe": False, "lyDo": f"Thiếu điểm các môn thuộc tổ hợp {maToHop}"}
            diemUuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho, "THANG_30")
            diemXetTuyen = cls.tinhDiemXetTuyen(diemTho, diemUuTien)
            return {
                "hopLe": True,
                "maPhuongThuc": "PT01",
                "tenPhuongThuc": "Xét theo điểm thi tốt nghiệp THPT",
                "maToHop": maToHop,
                "diemTho": diemTho,
                "diemUuTien": diemUuTien,
                "diemXetTuyen": diemXetTuyen,
                "thangDiem": "THANG_30",
                "scoreScale": "SCALE_30",
                "calculationRuleId": ruleId,
                "cachTinh": f"Tổng điểm 3 môn thi THPT theo tổ hợp {maToHop}"
            }

        elif maPhuongThuc == "PT02":
            if ruleId == "RULE_HB_GPA10_YEAR12" and scale in ["GPA_10", "THANG_10"]:
                diemHb = hoSoHocSinh.get("diemHocBa")
                if diemHb is None:
                    return {"hopLe": False, "lyDo": "Quy tắc RULE_HB_GPA10_YEAR12 yêu cầu điểm GPA học bạ lớp 12, thí sinh chưa nhập điểm GPA"}
                try:
                    gpaVal = float(diemHb)
                    if not (0.0 <= gpaVal <= 10.0):
                        return {"hopLe": False, "lyDo": "Điểm GPA học bạ không hợp lệ (phải từ 0.0 đến 10.0)"}
                except (ValueError, TypeError):
                    return {"hopLe": False, "lyDo": "Điểm GPA học bạ không đúng định dạng số"}

                diemTho = round(gpaVal, 2)
                diemUuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho, "THANG_10")
                diemXetTuyen = cls.tinhDiemXetTuyen(diemTho, diemUuTien)
                return {
                    "hopLe": True,
                    "maPhuongThuc": "PT02",
                    "tenPhuongThuc": "Xét theo học bạ THPT",
                    "maToHop": maToHop,
                    "diemTho": diemTho,
                    "diemUuTien": diemUuTien,
                    "diemXetTuyen": diemXetTuyen,
                    "thangDiem": "THANG_10",
                    "scoreScale": "GPA_10",
                    "calculationRuleId": ruleId,
                    "cachTinh": f"Điểm trung bình học bạ lớp 12 (thang 10: {diemTho:.2f})"
                }

            elif ruleId == "RULE_HB_STD_30" and scale in ["SCALE_30", "THANG_30"]:
                diemTho = cls.tinhDiemToHop(diemMonHoc, maToHop)
                uocTinh = False
                if diemTho is None:
                    diemHb = hoSoHocSinh.get("diemHocBa")
                    if diemHb is not None and str(diemHb).strip() != "":
                        try:
                            gpaVal = float(diemHb)
                            if 0.0 <= gpaVal <= 10.0:
                                diemTho = round(gpaVal * 3.0, 2)
                                uocTinh = True
                        except Exception:
                            pass
                if diemTho is None:
                    return {"hopLe": False, "lyDo": f"Thiếu điểm các môn bắt buộc của tổ hợp {maToHop} theo quy tắc xét tuyển 3 môn học bạ"}

                diemUuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho, "THANG_30")
                diemXetTuyen = cls.tinhDiemXetTuyen(diemTho, diemUuTien)
                cachTinhStr = f"Tổng điểm 3 môn học bạ theo tổ hợp {maToHop} (thang 30)" if not uocTinh else f"Ước lượng tham khảo từ GPA học bạ lớp 12 ({float(hoSoHocSinh.get('diemHocBa', 0.0)):.2f} x 3 = {diemTho:.2f}) do chưa nhập điểm chi tiết 3 môn"
                return {
                    "hopLe": True,
                    "maPhuongThuc": "PT02",
                    "tenPhuongThuc": "Xét theo học bạ THPT",
                    "maToHop": maToHop,
                    "diemTho": diemTho,
                    "diemUuTien": diemUuTien,
                    "diemXetTuyen": diemXetTuyen,
                    "thangDiem": "THANG_30",
                    "scoreScale": "SCALE_30",
                    "calculationRuleId": ruleId,
                    "cachTinh": cachTinhStr,
                    "uocTinhTuGpa": uocTinh
                }

            elif ruleId == "RULE_HB_GPA_X3" and scale in ["SCALE_30", "THANG_30"]:
                diemHb = hoSoHocSinh.get("diemHocBa")
                if diemHb is None:
                    return {"hopLe": False, "lyDo": "Quy tắc RULE_HB_GPA_X3 yêu cầu điểm GPA lớp 12 quy đổi thang 30, thí sinh chưa nhập điểm GPA"}
                try:
                    gpaVal = float(diemHb)
                    if not (0.0 <= gpaVal <= 10.0):
                        return {"hopLe": False, "lyDo": "Điểm GPA học bạ không hợp lệ"}
                except (ValueError, TypeError):
                    return {"hopLe": False, "lyDo": "Điểm GPA học bạ không đúng định dạng số"}

                diemTho = round(gpaVal * 3.0, 2)
                diemUuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho, "THANG_30")
                diemXetTuyen = cls.tinhDiemXetTuyen(diemTho, diemUuTien)
                return {
                    "hopLe": True,
                    "maPhuongThuc": "PT02",
                    "tenPhuongThuc": "Xét theo học bạ THPT",
                    "maToHop": maToHop,
                    "diemTho": diemTho,
                    "diemUuTien": diemUuTien,
                    "diemXetTuyen": diemXetTuyen,
                    "thangDiem": "THANG_30",
                    "scoreScale": "SCALE_30",
                    "calculationRuleId": ruleId,
                    "cachTinh": f"Quy đổi từ điểm GPA học bạ {gpaVal:.2f} sang thang 30 (GPA x 3)"
                }

            elif ruleId == "RULE_HB_COEFF2_40" and scale in ["SCALE_40", "THANG_40"]:
                toHopRecords = CsvDatabase.findWhere("toHopMon", {"maToHop": maToHop.strip().upper()})
                if not toHopRecords:
                    return {"hopLe": False, "lyDo": f"Không tìm thấy thông tin tổ hợp {maToHop}"}
                th = toHopRecords[0]
                m1 = diemMonHoc.get(th["mon1"])
                m2 = diemMonHoc.get(th["mon2"])
                m3 = diemMonHoc.get(th["mon3"])
                if m1 is None or m2 is None or m3 is None:
                    return {"hopLe": False, "lyDo": f"Quy tắc môn chính thang 40 yêu cầu đủ điểm các môn trong tổ hợp {maToHop}"}
                try:
                    diemTho = round(float(m1) * 2.0 + float(m2) + float(m3), 2)
                    cachTinh = f"Điểm học bạ tổ hợp {maToHop} (môn chính {th['mon1']} hệ số 2, thang 40)"
                except (ValueError, TypeError):
                    return {"hopLe": False, "lyDo": "Lỗi định dạng điểm các môn tổ hợp"}

                diemUuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho, "THANG_40")
                diemXetTuyen = cls.tinhDiemXetTuyen(diemTho, diemUuTien)
                return {
                    "hopLe": True,
                    "maPhuongThuc": "PT02",
                    "tenPhuongThuc": "Xét theo học bạ THPT",
                    "maToHop": maToHop,
                    "diemTho": diemTho,
                    "diemUuTien": diemUuTien,
                    "diemXetTuyen": diemXetTuyen,
                    "thangDiem": "THANG_40",
                    "scoreScale": "SCALE_40",
                    "calculationRuleId": ruleId,
                    "cachTinh": cachTinh
                }

            else:
                return {
                    "hopLe": False,
                    "lyDo": f"Chưa hỗ trợ tính điểm cho trường hợp quy tắc '{ruleId}' với thang điểm '{scale}'"
                }

        else:
            return cls.tinhDiemTheoPhuongThuc(hoSoHocSinh, maPhuongThuc, maToHop)

    @classmethod
    def tinhDiemTheoPhuongThuc(
        cls,
        hoSoHocSinh: Dict[str, Any],
        maPhuongThuc: str,
        maToHop: str = "A00"
    ) -> Dict[str, Any]:
        ruleId = hoSoHocSinh.get("calculationRuleId")
        scale = hoSoHocSinh.get("scoreScale")
        if not ruleId:
            ruleId = "RULE_THPT_STD_30" if maPhuongThuc == "PT01" else "RULE_HB_STD_30"
        if not scale:
            scale = "SCALE_30"

        if maPhuongThuc in ["PT01", "PT02"]:
            return cls.tinhDiemXetTuyenChuongTrinh(hoSoHocSinh, maPhuongThuc, maToHop, ruleId, scale)

        khuVuc = hoSoHocSinh.get("khuVucUuTien", "KV3")
        doiTuong = hoSoHocSinh.get("doiTuongUuTien", "NONE")
        scoreFields = ["diemToan", "diemVan", "diemAnh", "diemLy", "diemHoa", "diemSinh", "diemSu", "diemDia", "diemGDCD"]
        diemMonHoc = {sf: hoSoHocSinh.get(sf) for sf in scoreFields}
        chungChi = hoSoHocSinh.get("chungChiQuocTe")

        if maPhuongThuc == "PT03":
            diemDgnl = hoSoHocSinh.get("diemDanhGiaNangLuc")
            if diemDgnl is None or str(diemDgnl).strip() == "":
                return {"hopLe": False, "lyDo": "Chưa nhập điểm thi Đánh giá năng lực"}
            try:
                rawVal = float(diemDgnl)
                if rawVal <= 0:
                    return {"hopLe": False, "lyDo": "Điểm thi Đánh giá năng lực phải lớn hơn 0"}
            except (ValueError, TypeError):
                return {"hopLe": False, "lyDo": "Điểm thi Đánh giá năng lực không đúng định dạng số"}

            if rawVal <= 150.0:
                diemTho = round(rawVal * 30.0 / 150.0, 2)
            else:
                diemTho = round(rawVal * 30.0 / 1200.0, 2)
            diemUuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho)
            diemXetTuyen = cls.tinhDiemXetTuyen(diemTho, diemUuTien)
            return {
                "hopLe": True,
                "maPhuongThuc": "PT03",
                "tenPhuongThuc": "Xét theo điểm Đánh giá năng lực",
                "maToHop": "DGNL",
                "diemGocDgnl": rawVal,
                "diemTho": diemTho,
                "diemUuTien": diemUuTien,
                "diemXetTuyen": diemXetTuyen,
                "thangDiem": "THANG_30_QUY_DOI"
            }

        elif maPhuongThuc == "PT04":
            diemDgtd = hoSoHocSinh.get("diemDanhGiaTuDuy") or hoSoHocSinh.get("diemTSA")
            if diemDgtd is None or str(diemDgtd).strip() == "":
                return {"hopLe": False, "lyDo": "Chưa có điểm thi Đánh giá tư duy"}
            try:
                rawVal = float(diemDgtd)
                if rawVal <= 0:
                    return {"hopLe": False, "lyDo": "Điểm thi Đánh giá tư duy phải lớn hơn 0"}
            except (ValueError, TypeError):
                return {"hopLe": False, "lyDo": "Điểm thi Đánh giá tư duy không đúng định dạng số"}

            rawVal = min(max(rawVal, 0.0), 100.0)
            diemTho = round(rawVal * 30.0 / 100.0, 2)
            diemUuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho)
            diemXetTuyen = cls.tinhDiemXetTuyen(diemTho, diemUuTien)
            return {
                "hopLe": True,
                "maPhuongThuc": "PT04",
                "tenPhuongThuc": "Xét theo điểm Đánh giá tư duy",
                "maToHop": "TSA",
                "diemGocDgtd": rawVal,
                "diemTho": diemTho,
                "diemUuTien": diemUuTien,
                "diemXetTuyen": diemXetTuyen,
                "thangDiem": "THANG_30_QUY_DOI"
            }

        elif maPhuongThuc == "PT06":
            if not chungChi:
                return {"hopLe": False, "lyDo": "Chưa có chứng chỉ quốc tế (IELTS/SAT/ACT)"}
            diemTho = cls.tinhDiemToHop(diemMonHoc, maToHop)
            if diemTho is None:
                return {"hopLe": False, "lyDo": f"Thiếu điểm các môn kết hợp với chứng chỉ cho tổ hợp {maToHop}"}
            diemUuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho)
            diemXetTuyen = cls.tinhDiemXetTuyen(diemTho, diemUuTien)
            return {
                "hopLe": True,
                "maPhuongThuc": "PT06",
                "tenPhuongThuc": "Xét tuyển kết hợp chứng chỉ quốc tế",
                "maToHop": maToHop,
                "chungChi": chungChi,
                "diemTho": diemTho,
                "diemUuTien": diemUuTien,
                "diemXetTuyen": diemXetTuyen,
                "thangDiem": "THANG_30"
            }

        else:
            diemTho = cls.tinhDiemToHop(diemMonHoc, maToHop)
            if diemTho is None:
                return {"hopLe": False, "lyDo": f"Thiếu điểm các môn thuộc tổ hợp {maToHop}"}
            diemUuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho)
            diemXetTuyen = cls.tinhDiemXetTuyen(diemTho, diemUuTien)
            return {
                "hopLe": True,
                "maPhuongThuc": maPhuongThuc,
                "tenPhuongThuc": "Phương thức xét tuyển khác",
                "maToHop": maToHop,
                "diemTho": diemTho,
                "diemUuTien": diemUuTien,
                "diemXetTuyen": diemXetTuyen,
                "thangDiem": "THANG_30"
            }
