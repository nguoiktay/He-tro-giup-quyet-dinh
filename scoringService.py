from typing import Dict, List, Optional, Any
from csvDatabase import CsvDatabase


class ScoringService:

    DIEM_KHU_VUC = {
        "KV1": 0.75,
        "KV2_NT": 0.50,
        "KV2-NT": 0.50,
        "KV2": 0.25,
        "KV3": 0.00,
    }

    DIEM_DOI_TUONG = {
        "UT1": 2.00,
        "UT2": 1.00,
        "NONE": 0.00,
        "KHONG": 0.00,
    }

    TEN_MON = {
        "diemToan": "Toán", "diemVan": "Ngữ văn", "diemAnh": "Tiếng Anh",
        "diemLy": "Vật lý", "diemHoa": "Hóa học", "diemSinh": "Sinh học",
        "diemSu": "Lịch sử", "diemDia": "Địa lý", "diemGDCD": "GDCD",
        "diemTinHoc": "Tin học", "diemCongNghe": "Công nghệ",
    }

    TEN_DIEM_KHAC = {
        "diemDanhGiaNangLuc": "Đánh giá năng lực",
        "diemDanhGiaTuDuy": "Đánh giá tư duy",
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
        "IELTS 9.0": 10.0,
    }

    @classmethod
    def tinhDiemToHop(cls, diemMonHoc: Dict[str, Any], maToHop: str) -> Optional[float]:
        records = CsvDatabase.findWhere("toHopMon", {"maToHop": maToHop.strip().upper()})
        if not records:
            return None
        th = records[0]
        try:
            vals = [float(diemMonHoc.get(th[key])) for key in ("mon1", "mon2", "mon3")]
            return round(sum(vals), 2)
        except (ValueError, TypeError):
            return None

    @classmethod
    def timMonThieu(cls, diemMonHoc: Dict[str, Any], maToHop: str) -> Optional[List[str]]:
        records = CsvDatabase.findWhere("toHopMon", {"maToHop": maToHop.strip().upper()})
        if not records:
            return None
        thieu = []
        for key in ("mon1", "mon2", "mon3"):
            field = records[0][key]
            try:
                float(diemMonHoc.get(field))
            except (ValueError, TypeError):
                thieu.append(cls.TEN_MON.get(field) or cls.TEN_DIEM_KHAC.get(field, field))
        return thieu

    @classmethod
    def lyDoThieuMon(cls, diemMonHoc: Dict[str, Any], maToHop: str) -> str:
        thieu = cls.timMonThieu(diemMonHoc, maToHop)
        if thieu is None:
            return f"Tổ hợp {maToHop} không tồn tại trong danh mục"
        return f"Thiếu điểm môn {', '.join(thieu)} của tổ hợp {maToHop}"

    @classmethod
    def tinhDiemUuTien(
        cls,
        khuVuc: str = "KV3",
        doiTuong: str = "NONE",
        diemGoc: Optional[float] = None,
        thangDiem: str = "THANG_30",
    ) -> float:
        bonus = cls.DIEM_KHU_VUC.get(str(khuVuc).strip().upper(), 0.0) \
              + cls.DIEM_DOI_TUONG.get(str(doiTuong).strip().upper(), 0.0)
        if bonus <= 0.0:
            return 0.0

        if thangDiem == "THANG_10":
            raw = bonus / 3.0
            if diemGoc is not None and diemGoc >= 7.5:
                raw *= max((10.0 - min(diemGoc, 10.0)) / 2.5, 0.0)
            return round(raw, 2)

        if thangDiem == "THANG_40":
            raw = bonus * 4.0 / 3.0
            if diemGoc is not None and diemGoc >= 30.0:
                raw *= max((40.0 - min(diemGoc, 40.0)) / 10.0, 0.0)
            return round(raw, 2)

        if diemGoc is not None and diemGoc >= 22.5:
            bonus *= max((30.0 - min(diemGoc, 30.0)) / 7.5, 0.0)
        return round(bonus, 2)

    @classmethod
    def tinhDiemXetTuyen(cls, diemToHop: float, diemUuTien: float = 0.0) -> float:
        return round(float(diemToHop) + float(diemUuTien), 2)

    @classmethod
    def _extract_diem_mon_hoc(cls, hoSoHocSinh: Dict[str, Any]) -> Dict[str, Any]:
        diemMonHoc = {f: hoSoHocSinh.get(f) for f in cls.TEN_MON}
        chungChi = hoSoHocSinh.get("chungChiQuocTe")
        if chungChi and str(chungChi).strip() in cls.QUY_DOI_IELTS:
            mapped = cls.QUY_DOI_IELTS[str(chungChi).strip()]
            if diemMonHoc["diemAnh"] is None or mapped > float(diemMonHoc["diemAnh"]):
                diemMonHoc["diemAnh"] = mapped
        return diemMonHoc

    @classmethod
    def _build_score_result(
        cls,
        maPhuongThuc: str,
        tenPhuongThuc: str,
        maToHop: str,
        diemTho: float,
        diemUuTien: float,
        thangDiem: str,
        scoreScale: str,
        calculationRuleId: str,
        cachTinh: str,
        **extra,
    ) -> Dict[str, Any]:
        result = {
            "hopLe": True,
            "maPhuongThuc": maPhuongThuc,
            "tenPhuongThuc": tenPhuongThuc,
            "maToHop": maToHop,
            "diemTho": diemTho,
            "diemUuTien": diemUuTien,
            "diemXetTuyen": cls.tinhDiemXetTuyen(diemTho, diemUuTien),
            "thangDiem": thangDiem,
            "scoreScale": scoreScale,
            "calculationRuleId": calculationRuleId,
            "cachTinh": cachTinh,
        }
        result.update(extra)
        return result

    @classmethod
    def tinhDiemXetTuyenChuongTrinh(
        cls,
        hoSoHocSinh: Dict[str, Any],
        maPhuongThuc: str,
        maToHop: str,
        calculationRuleId: str = "RULE_THPT_STD_30",
        scoreScale: str = "SCALE_30",
    ) -> Dict[str, Any]:
        khuVuc = hoSoHocSinh.get("khuVucUuTien", "KV3")
        doiTuong = hoSoHocSinh.get("doiTuongUuTien", "NONE")
        diemMonHoc = cls._extract_diem_mon_hoc(hoSoHocSinh)
        ruleId = str(calculationRuleId).strip() if calculationRuleId else "RULE_THPT_STD_30"
        scale = str(scoreScale).strip() if scoreScale else "SCALE_30"

        if maPhuongThuc == "PT01":
            diemTho = cls.tinhDiemToHop(diemMonHoc, maToHop)
            if diemTho is None:
                return {"hopLe": False, "lyDo": cls.lyDoThieuMon(diemMonHoc, maToHop)}
            uuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho, "THANG_30")
            return cls._build_score_result(
                "PT01", "Xet theo diem thi tot nghiep THPT", maToHop,
                diemTho, uuTien, "THANG_30", "SCALE_30", ruleId,
                f"Tong diem 3 mon thi THPT theo to hop {maToHop}",
            )

        if maPhuongThuc == "PT02":
            return cls._tinh_diem_pt02(hoSoHocSinh, maToHop, khuVuc, doiTuong,
                                        diemMonHoc, ruleId, scale)

        return cls.tinhDiemTheoPhuongThuc(hoSoHocSinh, maPhuongThuc, maToHop)

    @classmethod
    def _tinh_diem_pt02(
        cls,
        hoSoHocSinh: Dict[str, Any],
        maToHop: str,
        khuVuc: str,
        doiTuong: str,
        diemMonHoc: Dict[str, Any],
        ruleId: str,
        scale: str,
    ) -> Dict[str, Any]:
        def _gpa_float(val) -> Optional[float]:
            if val is None:
                return None
            try:
                g = float(val)
                return g if 0.0 <= g <= 10.0 else None
            except (ValueError, TypeError):
                return None

        if ruleId == "RULE_HB_GPA10_YEAR12" and scale in ("GPA_10", "THANG_10"):
            gpa = _gpa_float(hoSoHocSinh.get("diemHocBa"))
            if gpa is None:
                return {"hopLe": False, "lyDo": "Quy tac RULE_HB_GPA10_YEAR12 yeu cau diem GPA hoc ba lop 12"}
            uuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, gpa, "THANG_10")
            return cls._build_score_result(
                "PT02", "Xet theo hoc ba THPT", maToHop,
                round(gpa, 2), uuTien, "THANG_10", "GPA_10", ruleId,
                f"Diem trung binh hoc ba lop 12 (thang 10: {gpa:.2f})",
            )

        if ruleId == "RULE_HB_GPA_X3" and scale in ("SCALE_30", "THANG_30"):
            gpa = _gpa_float(hoSoHocSinh.get("diemHocBa"))
            if gpa is None:
                return {"hopLe": False, "lyDo": "Quy tac RULE_HB_GPA_X3 yeu cau diem GPA lop 12"}
            diemTho = round(gpa * 3.0, 2)
            uuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho, "THANG_30")
            return cls._build_score_result(
                "PT02", "Xet theo hoc ba THPT", maToHop,
                diemTho, uuTien, "THANG_30", "SCALE_30", ruleId,
                f"Quy doi tu diem GPA hoc ba {gpa:.2f} sang thang 30 (GPA x 3)",
            )

        if ruleId == "RULE_HB_COEFF2_40" and scale in ("SCALE_40", "THANG_40"):
            records = CsvDatabase.findWhere("toHopMon", {"maToHop": maToHop.strip().upper()})
            if not records:
                return {"hopLe": False, "lyDo": f"Khong tim thay thong tin to hop {maToHop}"}
            th = records[0]
            try:
                m1, m2, m3 = float(diemMonHoc.get(th["mon1"])), float(diemMonHoc.get(th["mon2"])), float(diemMonHoc.get(th["mon3"]))
            except (ValueError, TypeError):
                return {"hopLe": False, "lyDo": f"Quy tac mon chinh thang 40: {cls.lyDoThieuMon(diemMonHoc, maToHop)}"}
            diemTho = round(m1 * 2.0 + m2 + m3, 2)
            uuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho, "THANG_40")
            return cls._build_score_result(
                "PT02", "Xet theo hoc ba THPT", maToHop,
                diemTho, uuTien, "THANG_40", "SCALE_40", ruleId,
                f"Diem hoc ba to hop {maToHop} (mon chinh {th['mon1']} he so 2, thang 40)",
            )

        if ruleId == "RULE_HB_STD_30" and scale in ("SCALE_30", "THANG_30"):
            diemTho = cls.tinhDiemToHop(diemMonHoc, maToHop)
            if diemTho is None:
                return {
                    "hopLe": False,
                    "lyDo": f"{cls.lyDoThieuMon(diemMonHoc, maToHop)} theo quy tac xet tuyen 3 mon hoc ba (yeu cau nhap diem chi tiet tung mon, khong suy dien tu GPA chung)"
                }
            uuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho, "THANG_30")
            cachTinh = f"Tong diem 3 mon hoc ba theo to hop {maToHop} (thang 30)"
            return cls._build_score_result(
                "PT02", "Xet theo hoc ba THPT", maToHop,
                diemTho, uuTien, "THANG_30", "SCALE_30", ruleId, cachTinh,
                uocTinhTuGpa=False,
            )

        return {
            "hopLe": False,
            "lyDo": f"Chua ho tro tinh diem cho truong hop quy tac '{ruleId}' voi thang diem '{scale}'",
        }

    @classmethod
    def tinhDiemTheoPhuongThuc(
        cls,
        hoSoHocSinh: Dict[str, Any],
        maPhuongThuc: str,
        maToHop: str = "A00",
    ) -> Dict[str, Any]:
        ruleId = hoSoHocSinh.get("calculationRuleId") or (
            "RULE_THPT_STD_30" if maPhuongThuc == "PT01" else "RULE_HB_STD_30"
        )
        scale = hoSoHocSinh.get("scoreScale") or "SCALE_30"

        if maPhuongThuc in ("PT01", "PT02"):
            return cls.tinhDiemXetTuyenChuongTrinh(hoSoHocSinh, maPhuongThuc, maToHop, ruleId, scale)

        khuVuc = hoSoHocSinh.get("khuVucUuTien", "KV3")
        doiTuong = hoSoHocSinh.get("doiTuongUuTien", "NONE")
        diemMonHoc = cls._extract_diem_mon_hoc(hoSoHocSinh)
        chungChi = hoSoHocSinh.get("chungChiQuocTe")

        if maPhuongThuc == "PT03":
            raw = hoSoHocSinh.get("diemDanhGiaNangLuc")
            if raw is None or str(raw).strip() == "":
                return {"hopLe": False, "lyDo": "Chua nhap diem thi Danh gia nang luc"}
            try:
                raw = float(raw)
                if raw <= 0:
                    return {"hopLe": False, "lyDo": "Diem thi Danh gia nang luc phai lon hon 0"}
            except (ValueError, TypeError):
                return {"hopLe": False, "lyDo": "Diem thi Danh gia nang luc khong dung dinh dang so"}
            diemTho = round(raw * 30.0 / (150.0 if raw <= 150.0 else 1200.0), 2)
            uuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho)
            return cls._build_score_result(
                "PT03", "Xet theo diem Danh gia nang luc", "DGNL",
                diemTho, uuTien, "THANG_30_QUY_DOI", "SCALE_30_QUY_DOI", "RULE_DGNL",
                f"Quy doi diem DGNL {raw} sang thang 30",
                diemGocDgnl=raw,
            )

        if maPhuongThuc == "PT04":
            raw = hoSoHocSinh.get("diemDanhGiaTuDuy") or hoSoHocSinh.get("diemTSA")
            if raw is None or str(raw).strip() == "":
                return {"hopLe": False, "lyDo": "Chua co diem thi Danh gia tu duy"}
            try:
                raw = float(raw)
                if raw <= 0:
                    return {"hopLe": False, "lyDo": "Diem thi Danh gia tu duy phai lon hon 0"}
            except (ValueError, TypeError):
                return {"hopLe": False, "lyDo": "Diem thi Danh gia tu duy khong dung dinh dang so"}
            raw = min(max(raw, 0.0), 100.0)
            diemTho = round(raw * 30.0 / 100.0, 2)
            uuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho)
            return cls._build_score_result(
                "PT04", "Xet theo diem Danh gia tu duy", "TSA",
                diemTho, uuTien, "THANG_30_QUY_DOI", "SCALE_30_QUY_DOI", "RULE_TSA",
                f"Quy doi diem TSA {raw} sang thang 30",
                diemGocDgtd=raw,
            )

        if maPhuongThuc == "PT06":
            if not chungChi:
                return {"hopLe": False, "lyDo": "Chua co chung chi quoc te (IELTS/SAT/ACT)"}
            diemTho = cls.tinhDiemToHop(diemMonHoc, maToHop)
            if diemTho is None:
                return {"hopLe": False, "lyDo": f"Thieu diem cac mon ket hop voi chung chi cho to hop {maToHop}"}
            uuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho)
            return cls._build_score_result(
                "PT06", "Xet tuyen ket hop chung chi quoc te", maToHop,
                diemTho, uuTien, "THANG_30", "SCALE_30", "RULE_PT06",
                f"Ket hop chung chi {chungChi} voi diem to hop {maToHop}",
                chungChi=chungChi,
            )

        diemTho = cls.tinhDiemToHop(diemMonHoc, maToHop)
        if diemTho is None:
            return {"hopLe": False, "lyDo": cls.lyDoThieuMon(diemMonHoc, maToHop)}
        uuTien = cls.tinhDiemUuTien(khuVuc, doiTuong, diemTho)
        return cls._build_score_result(
            maPhuongThuc, "Phuong thuc xet tuyen khac", maToHop,
            diemTho, uuTien, "THANG_30", "SCALE_30", f"RULE_{maPhuongThuc}",
            f"Xet tuyen theo phuong thuc {maPhuongThuc}",
        )
