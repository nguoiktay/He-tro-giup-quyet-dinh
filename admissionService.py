import time
import unicodedata
from typing import Dict, List, Any, Optional
import pandas as pd

import config
from csvDatabase import CsvDatabase
from scoringService import ScoringService
from mlService import mlServiceInstance


class AdmissionService:
    _hoc_phi_by_prog: Optional[Dict[str, Any]] = None

    @classmethod
    def _ensure_hoc_phi_cache(cls) -> None:
        if cls._hoc_phi_by_prog is not None:
            return
        cls._hoc_phi_by_prog = {}
        for r in CsvDatabase.readAll("hocPhi"):
            pid = str(r.get("programId", "")).strip()
            if pid:
                cls._hoc_phi_by_prog[pid] = r

    @classmethod
    def traCuuHocPhi(
        cls,
        programId: Optional[str] = None,
        uni: Optional[Dict[str, Any]] = None,
        major: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cls._ensure_hoc_phi_cache()
        matched = None
        prog_key = str(programId or "").strip()
        if prog_key:
            matched = cls._hoc_phi_by_prog.get(prog_key)

        if not matched and uni and not prog_key:
            u_code = str(uni.get("maTruong", "")).strip().upper()
            if u_code:
                recs = [
                    r for r in cls._hoc_phi_by_prog.values()
                    if str(r.get("maTruong", "")).strip().upper() == u_code
                ]
                if recs and len({(r.get("hocPhiToiDa"), r.get("trangThaiHocPhi")) for r in recs}) == 1:
                    matched = recs[0]
                elif len(recs) == 1:
                    matched = recs[0]
            if not matched:
                u_name = str(uni.get("tenTruong", "")).strip().lower()
                if u_name:
                    recs = [
                        r for r in cls._hoc_phi_by_prog.values()
                        if str(r.get("tenTruong", "")).strip().lower() == u_name
                    ]
                    if recs and len({(r.get("hocPhiToiDa"), r.get("trangThaiHocPhi")) for r in recs}) == 1:
                        matched = recs[0]

        if not matched:
            web_url = uni.get("trangWeb", "") if uni else ""
            return {
                "hocPhiKy": None,
                "hocPhiNam": None,
                "hocPhiTrieuNam": None,
                "hocPhiToiThieu": None,
                "hocPhiToiDa": None,
                "hocPhiText": "Chưa có thông tin học phí đã xác minh",
                "trangThaiHocPhi": "UNVERIFIED",
                "loaiHocPhi": "CHUA_XAC_DINH",
                "nguonMinhChung": "Chưa có công bố chính thức hoặc đang cập nhật",
                "urlNguon": web_url,
                "ghiChu": "",
                "phuongPhapSoSanh": "CHUA_XAC_DINH",
                "phanLoai": "unverified",
                "namApDung": None,
                "khoaApDung": "",
                "apDungCho2027": False,
                "canCapNhat2027": False,
                "mienGiamCoDieuKien": False,
                "isOfficial": False,
                "canhBaoNamApDung": ""
            }

        def _safe_float(val: Any) -> Optional[float]:
            if val is None or str(val).strip() in ("", "none", "None"):
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        t_min = _safe_float(matched.get("hocPhiToiThieu"))
        t_max = _safe_float(matched.get("hocPhiToiDa"))
        t_year = t_max if t_max is not None else t_min
        t_ky = t_year if matched.get("donViTinh") == "VND_KY" else (0.0 if t_year == 0.0 else None)
        t_trieu = round(t_year / 1_000_000.0, 1) if t_year is not None else None

        status_hp = str(matched.get("trangThaiHocPhi") or "UNVERIFIED").strip().upper()
        loai_hp = str(matched.get("loaiHocPhi") or "CHUA_XAC_DINH").strip().upper()
        is_conditional = (loai_hp == "MIEN_GIAM_CO_DIEU_KIEN")
        is_official = (status_hp == "VERIFIED" and loai_hp == "CHINH_THUC")

        nam_val = matched.get("namApDung")
        nam_ap_dung = int(nam_val) if pd.notna(nam_val) and str(nam_val).strip().isdigit() else None
        khoa_ap_dung = str(matched.get("khoaApDung") or "").strip()
        can_cap_nhat_2027 = bool(nam_ap_dung is not None and nam_ap_dung < config.TARGET_YEAR)

        if t_trieu is None:
            phan_loai = "unverified"
        elif t_year == 0.0 and is_official and not is_conditional:
            phan_loai = "free_subsidized"
        elif t_trieu <= 20.0:
            phan_loai = "under_20m"
        elif t_trieu <= 35.0:
            phan_loai = "20m_35m"
        else:
            phan_loai = "over_35m"

        canh_bao_nam = f"Muc hoc phi theo nien khoa {nam_ap_dung} ({khoa_ap_dung or 'chua ro khoa'}), can luu y dieu chinh/truot gia cho nam tuyen sinh {config.TARGET_YEAR}." if can_cap_nhat_2027 else ""

        return {
            "hocPhiKy": t_ky,
            "hocPhiNam": t_year,
            "hocPhiTrieuNam": t_trieu,
            "hocPhiToiThieu": t_min,
            "hocPhiToiDa": t_max,
            "hocPhiText": matched.get("hocPhiDisplay") or "Chưa có thông tin học phí đã xác minh",
            "trangThaiHocPhi": status_hp,
            "loaiHocPhi": loai_hp,
            "nguonMinhChung": matched.get("nguonMinhChung") or "",
            "urlNguon": matched.get("urlNguon") or "",
            "ghiChu": matched.get("ghiChu") or "",
            "phuongPhapSoSanh": "TRUC_TIEP" if is_official else "NGUONG_TRAN_AN_TOAN",
            "phanLoai": phan_loai,
            "namApDung": nam_ap_dung,
            "khoaApDung": khoa_ap_dung,
            "apDungCho2027": (nam_ap_dung == config.TARGET_YEAR),
            "canCapNhat2027": can_cap_nhat_2027,
            "mienGiamCoDieuKien": is_conditional,
            "isOfficial": is_official,
            "canhBaoNamApDung": canh_bao_nam
        }

    @classmethod
    def _validate_input(cls, ho_so: Dict[str, Any]) -> Optional[str]:
        raw_pt = ho_so.get("phuongThucMongMuon") or ho_so.get("phuongThuc")
        if raw_pt:
            items = [m.strip().upper() for m in (raw_pt if isinstance(raw_pt, list) else str(raw_pt).split(",")) if m.strip()]
            if len(items) > 1:
                return "Chỉ hỗ trợ chọn đúng 1 phương thức xét tuyển (PT01 hoặc PT02) cho mỗi lần tư vấn."
            if items and items[0] not in ("PT01", "PT02"):
                return f"Phương thức '{items[0]}' không được hỗ trợ. Hiện chỉ hỗ trợ PT01 (THPT) và PT02 (Học bạ)."
        return None

    @classmethod
    def _parse_phuong_thuc(cls, raw: Any) -> tuple[str, Optional[str]]:
        if raw is None:
            return "PT01", None
        items = [m.strip().upper() for m in (raw if isinstance(raw, list) else str(raw).split(",")) if m.strip()]
        if not items:
            return "PT01", None
        if len(items) > 1:
            return items[0], "Chỉ hỗ trợ chọn đúng 1 phương thức xét tuyển (PT01 hoặc PT02) cho mỗi lần tư vấn."
        if items[0] not in ("PT01", "PT02"):
            return items[0], f"Phương thức '{items[0]}' không được hỗ trợ. Hiện chỉ hỗ trợ PT01 (THPT) và PT02 (Học bạ)."
        return items[0], None

    @classmethod
    def _parse_to_hop(cls, raw: Any) -> List[str]:
        if isinstance(raw, list):
            items = [t.strip().upper() for t in raw if t and str(t).strip()]
        else:
            items = [t.strip().upper() for t in str(raw or "").split(",") if t.strip()]
        return items if items else ["A00"]

    @classmethod
    def _collect_candidates(
        cls,
        ho_so: Dict[str, Any],
        ma_pt: str,
        pt_id: Optional[int],
        danh_sach_th: List[str],
        kv_target: Optional[str],
        nganh_target: str,
        all_combs: Dict,
        all_unis: Dict,
        all_majors: Dict,
        all_benchmarks: List,
        thong_tin_pt: Dict,
    ) -> tuple[List[Dict], List[Dict]]:
        hop_le = []
        can_kiem_tra = []

        for ma_th in danh_sach_th:
            th_id = all_combs.get(ma_th, {}).get("id")
            matched = [
                b for b in all_benchmarks
                if pt_id is not None and int(b.get("phuongThucXetTuyenId", -1)) == int(pt_id)
                and (th_id is None or int(b.get("toHopMonId", -1)) == int(th_id))
            ]

            latest_benchmarks = {}
            for b in sorted(matched, key=lambda x: int(x.get("nam", 0)), reverse=True):
                p_key = str(b.get("programId") or "").strip() or str(b.get("nganhHocId", ""))
                dedup_key = (
                    b.get("truongDaiHocId"),
                    p_key,
                    b.get("toHopMonId"),
                    b.get("phuongThucXetTuyenId"),
                )
                if dedup_key not in latest_benchmarks:
                    latest_benchmarks[dedup_key] = b

            for dc in latest_benchmarks.values():
                item = cls._score_one_benchmark(
                    ho_so, dc, ma_pt, ma_th, th_id, pt_id, thong_tin_pt,
                    kv_target, nganh_target, all_unis, all_majors, all_combs,
                )
                if item is None:
                    continue
                if item.get("_can_kiem_tra"):
                    item.pop("_can_kiem_tra")
                    can_kiem_tra.append(item)
                else:
                    hop_le.append(item)

        return hop_le, can_kiem_tra

    @classmethod
    def _score_one_benchmark(
        cls,
        ho_so: Dict[str, Any],
        dc: Dict,
        ma_pt: str,
        ma_th: str,
        th_id: Optional[int],
        pt_id: Optional[int],
        thong_tin_pt: Dict,
        kv_target: Optional[str],
        nganh_target: str,
        all_unis: Dict,
        all_majors: Dict,
        all_combs: Dict,
    ) -> Optional[Dict[str, Any]]:
        u_id = dc.get("truongDaiHocId")
        m_id = dc.get("nganhHocId")
        uni = all_unis.get(u_id, {"maTruong": "UNI", "tenTruong": "Đại học", "khuVuc": "Toàn quốc"})
        major = all_majors.get(m_id, {"maNganh": "UNKNOWN", "tenNganh": "Chưa phân loại", "nhomNganh": "Liên ngành"})

        uni_khu_vuc = uni.get("khuVuc", "")
        if kv_target and uni_khu_vuc != kv_target:
            return None

        if nganh_target:
            t_target = unicodedata.normalize("NFC", str(nganh_target or "")).strip().lower()
            t_nganh = unicodedata.normalize("NFC", str(major.get("tenNganh", "") or "")).strip().lower()
            t_prg = unicodedata.normalize("NFC", str(dc.get("tenChuongTrinh", "") or "")).strip().lower()
            t_nhom = unicodedata.normalize("NFC", str(major.get("nhomNganh", "") or "")).strip().lower()

            match_major = (
                (t_target in t_nganh)
                or (t_target in t_prg)
                or (t_target == t_nhom)
                or (bool(t_nhom) and t_nhom in t_target)
            )
            if not match_major:
                return None

        rule_id = dc.get("calculationRuleId", "RULE_THPT_STD_30" if ma_pt == "PT01" else "RULE_HB_STD_30")
        scale = dc.get("scoreScale", "SCALE_30")
        ket_qua = ScoringService.tinhDiemXetTuyenChuongTrinh(ho_so, ma_pt, ma_th, rule_id, scale)
        if not ket_qua.get("hopLe"):
            return None

        diem_xet_tuyen = ket_qua["diemXetTuyen"]
        diem_chuan_ls = float(dc.get("diemChuan", 24.0))
        prog_id = str(dc.get("programId", "")).strip()
        case_id = str(dc.get("admissionCaseId", "")).strip()
        nam_bc = dc.get("nam", config.REFERENCE_YEAR)

        fc_info = mlServiceInstance.getForecastInfo(
            universityCode=uni.get("maTruong", ""),
            programId=prog_id,
            admissionCaseId=case_id,
            methodCode=ma_pt,
            combinationCode=ma_th,
        )
        loai_du_bao = fc_info.get("forecastType") if fc_info else "HISTORICAL_ONLY"
        co_du_bao = bool(fc_info is not None and fc_info.get("predictedCutoff") is not None and loai_du_bao in ("HYBRID_RF", "BASELINE_LAG1"))
        diem_du_bao = fc_info.get("predictedCutoff") if co_du_bao else None
        diem_so_sanh = diem_du_bao if co_du_bao else diem_chuan_ls
        nhan_du_bao = (fc_info.get("displayLabel") or fc_info.get("forecastTypeLabel")) if fc_info else f"Điểm chuẩn năm {nam_bc}"
        u_radius = fc_info.get("uncertaintyRadius", 0.5) if fc_info else 0.5

        du_bao = mlServiceInstance.predictSuitability(
            studentScore=diem_xet_tuyen,
            benchmarkScore=diem_so_sanh,
            methodCode=ma_pt,
            combinationCode=ma_th,
            scoreScale=scale,
            namThamChieu=nam_bc,
            coDuBao=co_du_bao,
            uncertaintyRadius=u_radius,
            forecastType=loai_du_bao,
            uniTier=2,
        )
        diem_thuan_loi = du_bao["doPhuHop"]

        score_kv = 100.0 if (kv_target and uni_khu_vuc == kv_target) else (35.0 if kv_target else 80.0)
        score_nganh = cls._score_nganh(nganh_target, major, dc)

        hp_info = cls.traCuuHocPhi(programId=prog_id, uni=uni, major=major)
        hp_trieu = hp_info["hocPhiTrieuNam"]
        trang_thai_hp = hp_info["trangThaiHocPhi"]

        muc_filter = ho_so.get("filterTuition") or ho_so.get("mucHocPhi")
        ngan_sach = ho_so.get("nganSach") or ho_so.get("mucHocPhi")

        can_kt = False
        nhom_hp = None
        canh_bao = None

        if hp_trieu is None:
            nhom_hp = "CHUA_XAC_MINH"
            can_kt = True
        elif not cls._check_tuition_filter(muc_filter, ngan_sach, hp_trieu):
            return None
        else:
            if trang_thai_hp == "VERIFIED":
                nhom_hp = "XAC_MINH_PHU_HOP"
            elif trang_thai_hp == "PROJECTED":
                nhom_hp = "DU_KIEN_PHU_HOP"
                canh_bao = "Mức phí dự kiến dựa trên đề án, có thể thay đổi theo tín chỉ thực tế."
            else:
                nhom_hp = "CHUA_XAC_MINH"
                can_kt = True

        score_so_thich = round(0.5 * score_kv + 0.5 * score_nganh, 1)
        do_phu_hop = round(
            config.WEIGHT_DIEM_THUAN_LOI * diem_thuan_loi + config.WEIGHT_SO_THICH * score_so_thich, 1
        )

        ly_do_de_xuat = cls._build_ly_do_de_xuat(
            diem_xet_tuyen=diem_xet_tuyen,
            diem_so_sanh=diem_so_sanh,
            co_du_bao=co_du_bao,
            fc_info=fc_info,
            nam_bc=nam_bc,
            du_bao=du_bao,
            nganh_target=nganh_target,
            kv_target=kv_target,
            hp_text=hp_info["hocPhiText"],
            hp_trieu=hp_trieu,
            ngan_sach=ngan_sach,
        )

        chi_tieu_val = dc.get("chiTieu")
        chi_tieu_clean = int(chi_tieu_val) if chi_tieu_val not in (None, "", "None", "null") and not pd.isna(chi_tieu_val) else None

        return {
            "_can_kiem_tra": can_kt,
            "truongDaiHocId": u_id,
            "maTruong": uni["maTruong"],
            "tenTruong": uni["tenTruong"],
            "khuVuc": uni_khu_vuc,
            "khuVucTruong": uni_khu_vuc,
            "loaiTruong": uni.get("loaiTruong", "Công lập"),
            "hocPhiUocTinh": hp_info["hocPhiText"],
            "hocPhiNam": hp_info["hocPhiNam"],
            "hocPhiKy": hp_info["hocPhiKy"],
            "trangThaiHocPhi": trang_thai_hp,
            "trangThaiHocPhiPhuHop": nhom_hp,
            "loaiHocPhi": hp_info["loaiHocPhi"],
            "nguonMinhChung": hp_info["nguonMinhChung"],
            "urlNguon": hp_info.get("urlNguon", ""),
            "ghiChuHocPhi": hp_info.get("ghiChu", ""),
            "nhomHocPhi": nhom_hp,
            "phuongPhapSoSanh": hp_info.get("phuongPhapSoSanh", "NGUONG_TRAN_AN_TOAN"),
            "canhBaoTaiChinh": canh_bao,
            "chiTieu": chi_tieu_clean,
            "nganhHocId": m_id,
            "maNganh": major["maNganh"],
            "tenNganh": major["tenNganh"],
            "tenChuongTrinh": dc.get("tenChuongTrinh") or major["tenNganh"],
            "programId": prog_id,
            "admissionCaseId": case_id,
            "nhomNganh": major.get("nhomNganh", ""),
            "toHopMonId": th_id,
            "maToHop": ma_th,
            "tenToHop": all_combs.get(ma_th, {}).get("tenToHop", ma_th),
            "phuongThucXetTuyenId": pt_id,
            "maPhuongThuc": ma_pt,
            "tenPhuongThuc": thong_tin_pt.get("tenPhuongThuc", ""),
            "scoreScale": scale,
            "calculationRuleId": rule_id,
            "diemXetTuyen": diem_xet_tuyen,
            "diemChuanThamChieu": diem_chuan_ls,
            "namThamChieu": nam_bc,
            "coDuBao": co_du_bao,
            "diemChuanDuBao": diem_du_bao,
            "loaiDuBao": loai_du_bao,
            "nhanDuBao": nhan_du_bao,
            "namMucTieu": config.TARGET_YEAR,
            "phienBanMoHinh": fc_info.get("modelVersion") if co_du_bao else None,
            "khoangTinCay80": f"{fc_info['lowerBound80']} – {fc_info['upperBound80']}" if co_du_bao and fc_info.get("lowerBound80") else None,
            "lyDoChuaCoDuBao": None if co_du_bao else (
                "Phuong thuc hoc ba su dung diem chuan chinh thuc cong bo" if ma_pt == "PT02"
                else "Chuong trinh chua co du du lieu chuoi thoi gian de xay dung mo hinh du bao"
            ),
            "cachTinhDiem": ket_qua.get("cachTinh", ""),
            "delta": du_bao["delta"],
            "xacSuatDo": du_bao.get("xacSuatDo", diem_thuan_loi),
            "chiSoThuanLoi": diem_thuan_loi,
            "doPhuHop": do_phu_hop,
            "mucThuanLoiDiem": diem_thuan_loi,
            "doPhuHopSoThich": score_so_thich,
            "nhomNguyenVong": du_bao.get("nhomNguyenVong", "Vừa sức"),
            "mucDoPhuHop": du_bao["mucDoPhuHop"],
            "mucDoRuiRo": du_bao["mucDoRuiRo"],
            "lyDoDeXuat": ly_do_de_xuat,
        }

    @staticmethod
    def _build_ly_do_de_xuat(
        diem_xet_tuyen: float,
        diem_so_sanh: float,
        co_du_bao: bool,
        fc_info: Optional[Dict[str, Any]],
        nam_bc: Any,
        du_bao: Dict[str, Any],
        nganh_target: str,
        kv_target: Optional[str],
        hp_text: str,
        hp_trieu: Optional[float],
        ngan_sach: Any,
    ) -> str:
        delta = du_bao["delta"]
        if co_du_bao and fc_info:
            moc = f"điểm chuẩn dự báo {config.TARGET_YEAR} ({diem_so_sanh:.2f}, sai số ±{fc_info.get('uncertaintyRadius', 0.5)})"
        else:
            moc = f"điểm chuẩn năm {nam_bc} ({diem_so_sanh:.2f})"
        if delta > 0:
            so_sanh = f"cao hơn {moc} {delta:.2f} điểm"
        elif delta < 0:
            so_sanh = f"thấp hơn {moc} {abs(delta):.2f} điểm"
        else:
            so_sanh = f"bằng {moc}"

        phan = [
            f"Điểm xét tuyển {diem_xet_tuyen:.2f} {so_sanh}",
            f"chỉ số thuận lợi {du_bao['chiSoThuanLoi']:.1f}% nên xếp nhóm {du_bao['nhomNguyenVong']}",
        ]
        if nganh_target:
            phan.append(f"khớp ngành bạn quan tâm ('{nganh_target}')")
        if kv_target:
            phan.append(f"thuộc khu vực {kv_target}")
        if hp_trieu is not None:
            try:
                ns_val = float(ngan_sach) if ngan_sach not in (None, "") else 0.0
            except (ValueError, TypeError):
                ns_val = 0.0
            if ns_val > 0:
                phan.append(f"học phí {hp_text} nằm trong ngân sách {ns_val:g} triệu/năm")
        return "; ".join(phan) + "."

    @staticmethod
    def _score_nganh(nganh_target: str, major: Dict, dc: Dict) -> float:
        if not nganh_target:
            return 80.0
        ten_nganh = str(major.get("tenNganh", "")).lower()
        ten_prg = str(dc.get("tenChuongTrinh", "")).lower()
        if nganh_target in ten_nganh or nganh_target in ten_prg:
            return 100.0
        if nganh_target in str(major.get("nhomNganh", "")).lower():
            return 70.0
        return 40.0

    @staticmethod
    def _check_tuition_filter(muc_filter: Any, ngan_sach: Any, hp_trieu: float) -> bool:
        ok = True
        if muc_filter in ("mien_phi", "free_subsidized"):
            ok = (hp_trieu == 0.0)
        elif muc_filter == "under_20m":
            ok = (hp_trieu <= 20.0)
        elif muc_filter == "20m_35m":
            ok = (20.0 <= hp_trieu <= 35.0)
        elif muc_filter == "over_35m":
            ok = (hp_trieu >= 35.0)

        if ok and ngan_sach is not None and str(ngan_sach).strip() != "":
            try:
                ns_val = float(ngan_sach)
                if ns_val > 0:
                    ok = (hp_trieu <= ns_val)
            except (ValueError, TypeError):
                pass
        return ok

    @classmethod
    def _tier_sort_and_pick(cls, candidates: List[Dict]) -> tuple[Dict[str, List[Dict]], List[Dict]]:
        seen_pkeys = set()
        unique_candidates = []
        for c in candidates:
            pk = (c["truongDaiHocId"], c["programId"] or c["nganhHocId"], c["maToHop"])
            if pk not in seen_pkeys:
                seen_pkeys.add(pk)
                unique_candidates.append(c)

        raw_thu_suc = [c for c in unique_candidates if c.get("nhomNguyenVong") == "Thử sức"]
        raw_vua_suc = [c for c in unique_candidates if c.get("nhomNguyenVong") == "Vừa sức"]
        raw_an_toan = [c for c in unique_candidates if c.get("nhomNguyenVong") == "An toàn"]

        def _sort_thu_suc(x: Dict) -> float:
            d = x.get("delta", -1.0)
            return (abs(d) * -10.0) + (x.get("doPhuHopSoThich", 80.0) * 0.3)

        raw_thu_suc.sort(key=_sort_thu_suc, reverse=True)
        raw_vua_suc.sort(key=lambda x: x.get("doPhuHop", 50.0), reverse=True)

        def _sort_an_toan(x: Dict) -> float:
            d = x.get("delta", 2.0)
            scale_val = x.get("scoreScale", "SCALE_30")
            d_opt = 0.8 if scale_val in ("GPA_10", "THANG_10") else (2.8 if scale_val in ("SCALE_40", "THANG_40") else 2.2)
            dist_penalty = abs(d - d_opt) * 8.0
            return (x.get("doPhuHopSoThich", 80.0) * 0.4) + (x.get("diemChuanThamChieu", 20.0) * 1.5) - dist_penalty

        raw_an_toan.sort(key=_sort_an_toan, reverse=True)

        uni_count: Dict[int, int] = {}
        thu_suc_picks: List[Dict] = []
        vua_suc_picks: List[Dict] = []
        an_toan_picks: List[Dict] = []

        for c in raw_thu_suc:
            u_id = c["truongDaiHocId"]
            if uni_count.get(u_id, 0) < 3:
                thu_suc_picks.append(c)
                uni_count[u_id] = uni_count.get(u_id, 0) + 1
                if len(thu_suc_picks) >= 5:
                    break

        for c in raw_vua_suc:
            u_id = c["truongDaiHocId"]
            if uni_count.get(u_id, 0) < 3:
                vua_suc_picks.append(c)
                uni_count[u_id] = uni_count.get(u_id, 0) + 1
                if len(vua_suc_picks) >= 10:
                    break

        for c in raw_an_toan:
            u_id = c["truongDaiHocId"]
            if uni_count.get(u_id, 0) < 3:
                an_toan_picks.append(c)
                uni_count[u_id] = uni_count.get(u_id, 0) + 1
                if len(an_toan_picks) >= 5:
                    break

        selected = []
        selected.extend(thu_suc_picks)
        selected.extend(vua_suc_picks)
        selected.extend(an_toan_picks)

        if len(selected) < 20:
            picked_keys = {(w["truongDaiHocId"], w["programId"], w["maToHop"]) for w in selected}
            for pool in [raw_vua_suc, raw_an_toan, raw_thu_suc, unique_candidates]:
                for c in pool:
                    u_id = c["truongDaiHocId"]
                    ck = (u_id, c["programId"], c["maToHop"])
                    if ck not in picked_keys and uni_count.get(u_id, 0) < 3:
                        selected.append(c)
                        picked_keys.add(ck)
                        uni_count[u_id] = uni_count.get(u_id, 0) + 1
                        if len(selected) >= 20:
                            break
                if len(selected) >= 20:
                    break

        if len(selected) < 20:
            picked_keys = {(w["truongDaiHocId"], w["programId"], w["maToHop"]) for w in selected}
            for c in unique_candidates:
                ck = (c["truongDaiHocId"], c["programId"], c["maToHop"])
                if ck not in picked_keys:
                    selected.append(c)
                    picked_keys.add(ck)
                    if len(selected) >= 20:
                        break

        tier_order = {"Thử sức": 1, "Vừa sức": 2, "An toàn": 3, "Rủi ro cao": 4}
        selected.sort(key=lambda x: (tier_order.get(x.get("nhomNguyenVong", "Vừa sức"), 2), -x.get("doPhuHop", 50.0)))

        tong_hop = []
        for idx, item in enumerate(selected[:20], 1):
            cloned = dict(item)
            cloned["thuTuUuTien"] = f"NV{idx}"
            cloned["thuTuDeXuat"] = f"NV{idx}"
            cloned["stt"] = idx
            tong_hop.append(cloned)

        tier_map = {
            "danhSachAnToan": [w for w in tong_hop if w.get("nhomNguyenVong") == "An toàn"],
            "danhSachVuaSuc": [w for w in tong_hop if w.get("nhomNguyenVong") == "Vừa sức"],
            "danhSachThuSuc": [w for w in tong_hop if w.get("nhomNguyenVong") == "Thử sức"],
        }
        return tier_map, tong_hop

    @classmethod
    def _build_thong_bao(
        cls,
        tong_hop: List[Dict],
        can_kiem_tra: List[Dict],
        has_verified_under_budget: bool,
        ho_so: Optional[Dict] = None,
        all_benchmarks: Optional[List] = None,
        all_combs: Optional[Dict] = None,
        all_majors: Optional[Dict] = None,
        pt_id: Optional[int] = None,
        danh_sach_th: Optional[List[str]] = None,
    ) -> str:
        nganh_mong_muon = str((ho_so or {}).get("nganhMongMuon") or "").strip()
        if not tong_hop:
            if nganh_mong_muon:
                target_norm = unicodedata.normalize("NFC", nganh_mong_muon).strip().lower()
                avail_combs = set()
                if all_benchmarks and all_majors and all_combs:
                    combs_by_id = {c.get("id"): c.get("maToHop", "") for c in all_combs.values() if isinstance(c, dict)}
                    for b in all_benchmarks:
                        if pt_id is None or int(b.get("phuongThucXetTuyenId", -1)) == int(pt_id):
                            m = all_majors.get(b.get("nganhHocId"), {})
                            t_n = unicodedata.normalize("NFC", str(m.get("tenNganh", "") or "")).strip().lower()
                            t_p = unicodedata.normalize("NFC", str(b.get("tenChuongTrinh", "") or "")).strip().lower()
                            if target_norm in t_n or target_norm in t_p:
                                th_code = combs_by_id.get(b.get("toHopMonId"))
                                if th_code:
                                    avail_combs.add(th_code)

                comb_str = ", ".join(danh_sach_th) if danh_sach_th else "đã chọn"
                if avail_combs:
                    sorted_combs = ", ".join(sorted(list(avail_combs))[:6])
                    return (
                        f"Ngành '{nganh_mong_muon}' hiện không có chương trình tuyển sinh theo tổ hợp {comb_str}. "
                        f"Dữ liệu cho thấy ngành này đang xét tuyển qua các tổ hợp: {sorted_combs}. "
                        f"Gợi ý: Bạn có thể đổi sang một trong các tổ hợp trên nếu có điểm, hoặc chọn 'Bất kỳ ngành nào (Tất cả ngành)' để xem các ngành tuyển sinh theo tổ hợp {comb_str}."
                    )
                return (
                    f"Không tìm thấy chương trình đào tạo ngành '{nganh_mong_muon}' phù hợp với tổ hợp môn hoặc điều kiện điểm đã chọn. "
                    "Gợi ý: Thử chọn thêm tổ hợp xét tuyển khác phổ biến của ngành này hoặc chọn 'Bất kỳ ngành nào (Tất cả ngành)'."
                )
            return (
                "Chưa tìm thấy nguyện vọng phù hợp với điều kiện điểm hoặc tài chính. "
                "Vui lòng thử mở rộng vùng khu vực, nới lỏng ngân sách học phí hoặc chọn thêm tổ hợp môn."
            )

        an_toan_count = sum(1 for w in tong_hop if w.get("nhomNguyenVong") == "An toàn")
        high_risk_count = sum(1 for w in tong_hop if w.get("nhomNguyenVong") in ("Thử sức", "Rủi ro cao"))
        first_score = float(tong_hop[0].get("diemXetTuyen", 0.0))
        first_scale = tong_hop[0].get("scoreScale", "SCALE_30")
        min_safe = 5.0 if first_scale in ("GPA_10", "THANG_10") else (21.0 if first_scale in ("SCALE_40", "THANG_40") else 16.0)

        is_low_score = (an_toan_count == 0 or high_risk_count >= 10 or (first_score > 0 and first_score < min_safe))

        ts_count = sum(1 for w in tong_hop if w.get("nhomNguyenVong") == "Thử sức")
        vs_count = sum(1 for w in tong_hop if w.get("nhomNguyenVong") == "Vừa sức")
        at_count = sum(1 for w in tong_hop if w.get("nhomNguyenVong") == "An toàn")

        if is_low_score:
            avg_score = round(first_score, 2)
            thong_bao = (
                f"Điểm xét tuyển ({avg_score}) ở mức thấp so với ngưỡng điểm chuẩn đại học "
                "(danh sách không có hoặc rất ít nguyện vọng An toàn). Các nguyện vọng gợi ý tập trung ở mức Thử sức và Vừa sức sát ngưỡng. "
                "Thí sinh nên cân nhắc thêm các hệ cao đẳng, xét tuyển học bạ hoặc ngành đào tạo nghề."
            )
        elif ts_count >= 4 and vs_count >= 8 and at_count >= 4:
            thong_bao = f"Đã tìm thấy danh mục 20 nguyện vọng tối ưu phân tầng chuẩn 25% Thử sức ({ts_count}) - 50% Vừa sức ({vs_count}) - 25% An toàn ({at_count})."
        else:
            thong_bao = f"Đã đề xuất {len(tong_hop)} nguyện vọng phù hợp với phổ điểm ({ts_count} Thử sức, {vs_count} Vừa sức, {at_count} An toàn)."

        if nganh_mong_muon:
            thong_bao += f" (Hệ thống đã lọc chính xác theo ngành yêu thích: '{nganh_mong_muon}')."

        if can_kiem_tra and not has_verified_under_budget:
            thong_bao += f" Lưu ý: Có {len(can_kiem_tra)} chương trình chưa công bố biểu phí chính thức cần kiểm tra thêm."

        return thong_bao

    @classmethod
    def deXuatNguyenVong(cls, hoSoHocSinh: Dict[str, Any]) -> Dict[str, Any]:
        err = cls._validate_input(hoSoHocSinh)
        if err:
            return cls._empty_recommendation_result(err)

        ma_pt, err = cls._parse_phuong_thuc(hoSoHocSinh.get("phuongThucMongMuon", "PT01"))
        if err:
            return cls._empty_recommendation_result(err)

        danh_sach_th = cls._parse_to_hop(hoSoHocSinh.get("danhSachToHopDaChon", ["A00"]))

        all_methods = {m["maPhuongThuc"]: m for m in CsvDatabase.readAll("phuongThucXetTuyen")}
        all_combs = {c["maToHop"]: c for c in CsvDatabase.readAll("toHopMon")}
        all_unis = {u["id"]: u for u in CsvDatabase.readAll("truongDaiHoc")}
        all_majors = {m["id"]: m for m in CsvDatabase.readAll("nganhHoc")}
        thong_tin_pt = all_methods.get(ma_pt, {"id": 1, "maPhuongThuc": "PT01", "tenPhuongThuc": "Thi THPT"})
        pt_id = thong_tin_pt.get("id")
        all_benchmarks, nam_toi_thieu, so_ct_bo_qua = cls._loc_diem_chuan_gan_day(
            CsvDatabase.readAll("diemChuan"), pt_id
        )

        raw_kv = hoSoHocSinh.get("khuVucMongMuon")
        kv_target = str(raw_kv).strip() if (raw_kv and str(raw_kv).strip() != "Toàn quốc") else None
        nganh_target = str(hoSoHocSinh.get("nganhMongMuon") or "").strip().lower()

        hop_le, can_kiem_tra = cls._collect_candidates(
            hoSoHocSinh, ma_pt, pt_id, danh_sach_th,
            kv_target, nganh_target,
            all_combs, all_unis, all_majors, all_benchmarks, thong_tin_pt,
        )

        tiers, tong_hop = cls._tier_sort_and_pick(hop_le)

        has_verified = any(
            x.get("trangThaiHocPhi") == "VERIFIED" and x.get("hocPhiNam") is not None
            for x in tong_hop
        )
        thong_bao = cls._build_thong_bao(
            tong_hop, can_kiem_tra, has_verified, hoSoHocSinh,
            all_benchmarks=all_benchmarks, all_combs=all_combs, all_majors=all_majors,
            pt_id=pt_id, danh_sach_th=danh_sach_th,
        )
        if so_ct_bo_qua and tong_hop:
            thong_bao += (
                f" Đã bỏ qua {so_ct_bo_qua} chương trình chỉ có điểm chuẩn trước năm {nam_toi_thieu} "
                "vì không còn đủ tin cậy làm mốc."
            )

        seen_ck_keys = set()
        unique_ck = []
        for item in can_kiem_tra:
            ck_key = (item["truongDaiHocId"], item["programId"] or item["nganhHocId"], item["admissionCaseId"], item["maToHop"])
            if ck_key not in seen_ck_keys:
                seen_ck_keys.add(ck_key)
                unique_ck.append(item)

        ket_qua_tung_pt = {
            ma_pt: {
                "thongTinPhuongThuc": thong_tin_pt,
                "soLuong": len(tong_hop),
                "thongBao": thong_bao,
                "danhSach": tong_hop,
            }
        }

        return {
            "thanhCong": True,
            "thongBao": thong_bao,
            "phuongThuc": ma_pt,
            "tenPhuongThuc": thong_tin_pt.get("tenPhuongThuc"),
            "toHopMon": danh_sach_th,
            "danhSachTongHop": tong_hop,
            **tiers,
            "danhSachCanKiemTraHocPhi": unique_ck[:15],
            "tongSoGoiY": len(tong_hop),
            "ketQuaTungPhuongThuc": ket_qua_tung_pt,
            "phuongThucDangChon": ma_pt,
            "soLuongToHopDaChon": len(danh_sach_th),
            "namThamChieuToiThieu": nam_toi_thieu,
            "soChuongTrinhBoQuaDoDiemCu": so_ct_bo_qua,
        }

    @staticmethod
    def _loc_diem_chuan_gan_day(benchmarks: List[Dict], pt_id: Optional[int]) -> tuple[List[Dict], Optional[int], int]:
        if config.MAX_REFERENCE_AGE < 0:
            return benchmarks, None, 0
        nam_toi_thieu = config.REFERENCE_YEAR - config.MAX_REFERENCE_AGE
        giu, ct_cu, ct_moi = [], set(), set()
        for b in benchmarks:
            cung_pt = pt_id is not None and int(b.get("phuongThucXetTuyenId", -1)) == int(pt_id)
            key = (b.get("truongDaiHocId"), str(b.get("programId") or b.get("nganhHocId")))
            if int(b.get("nam", 0) or 0) >= nam_toi_thieu:
                giu.append(b)
                if cung_pt:
                    ct_moi.add(key)
            elif cung_pt:
                ct_cu.add(key)
        return giu, nam_toi_thieu, len(ct_cu - ct_moi)

    @staticmethod
    def _empty_recommendation_result(thong_bao: str) -> Dict[str, Any]:
        return {
            "thanhCong": False,
            "thongBao": thong_bao,
            "danhSachTongHop": [],
            "danhSachAnToan": [],
            "danhSachVuaSuc": [],
            "danhSachThuSuc": [],
            "danhSachCanKiemTraHocPhi": [],
            "tongSoGoiY": 0,
            "ketQuaTungPhuongThuc": {},
            "phuongThucDangChon": "PT01",
            "soLuongToHopDaChon": 0,
        }

    @classmethod
    def luuDanhSachNguyenVong(cls, nguoi_dung_id: int, wishlist_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not nguoi_dung_id:
            return {"thanhCong": False, "thongBao": "Yêu cầu đăng nhập để lưu danh sách nguyện vọng."}
        if not wishlist_items:
            return {"thanhCong": False, "thongBao": "Danh sách nguyện vọng lưu không được để trống."}

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        profiles = CsvDatabase.findWhere("hoSoHocSinh", {"nguoiDungId": nguoi_dung_id})
        if profiles:
            ho_so = profiles[0]
            ho_so_id = ho_so["id"]
        else:
            ho_so = CsvDatabase.insert("hoSoHocSinh", {"nguoiDungId": nguoi_dung_id, "ngayCapNhat": now_str})
            ho_so_id = ho_so["id"]

        prog_lookup = {
            str(r.get("programId", "")).strip(): r
            for r in CsvDatabase.readAll("diemChuan")
            if str(r.get("programId", "")).strip()
        }
        all_majors = {m["id"]: m for m in CsvDatabase.readAll("nganhHoc")}
        all_methods = {m["id"]: m for m in CsvDatabase.readAll("phuongThucXetTuyen")}
        all_combs = {c["id"]: c for c in CsvDatabase.readAll("toHopMon")}

        validated = []
        seen_keys = set()

        for item in wishlist_items:
            prog_id = str(item.get("programId") or "").strip()
            if not prog_id:
                return {"thanhCong": False, "thongBao": "Mỗi nguyện vọng lưu bắt buộc phải có mã chương trình chuẩn (programId)."}
            if prog_id not in prog_lookup:
                return {"thanhCong": False, "thongBao": f"Mã chương trình '{prog_id}' không tồn tại trong danh mục tuyển sinh chính thức của hệ thống."}

            wish_key = (
                prog_id,
                str(item.get("toHopMonId") or item.get("maToHop") or ""),
                str(item.get("phuongThucXetTuyenId") or item.get("maPhuongThuc") or "")
            )
            if wish_key in seen_keys:
                continue
            seen_keys.add(wish_key)

            matched = prog_lookup[prog_id]
            m_id = matched.get("nganhHocId")
            major_info = all_majors.get(m_id, {})
            ten_chuan = matched.get("tenChuongTrinh") or major_info.get("tenNganh") or "Chương trình đào tạo"

            pt_id = item.get("phuongThucXetTuyenId") or matched.get("phuongThucXetTuyenId")
            th_id = item.get("toHopMonId") or matched.get("toHopMonId")
            def _find_by_id(dct: Dict[Any, Any], target_id: Any) -> Dict[str, Any]:
                if target_id is None:
                    return {}
                if target_id in dct:
                    return dct[target_id]
                try:
                    int_id = int(float(target_id))
                    return dct.get(int_id, {})
                except (ValueError, TypeError):
                    return {}

            pt_rec = _find_by_id(all_methods, pt_id)
            th_rec = _find_by_id(all_combs, th_id)
            ma_pt = pt_rec.get("maPhuongThuc", "PT01")
            ma_th = th_rec.get("maToHop", "A00")
            rule_id = matched.get("calculationRuleId", "RULE_THPT_STD_30" if ma_pt == "PT01" else "RULE_HB_STD_30")
            scale = matched.get("scoreScale", "SCALE_30")

            server_score = None
            if ho_so and ma_pt and ma_th:
                calc = ScoringService.tinhDiemXetTuyenChuongTrinh(ho_so, ma_pt, ma_th, rule_id, scale)
                if calc.get("hopLe"):
                    server_score = calc.get("diemXetTuyen")

            max_scale = 10.0 if scale in ("GPA_10", "SCALE_10", "THANG_10") else (
                40.0 if scale in ("SCALE_40", "THANG_40") else (
                    100.0 if scale in ("SCALE_100", "THANG_100") else (
                        1200.0 if scale in ("SCALE_1200", "THANG_1200") else 30.0
                    )
                )
            )

            if server_score is not None:
                final_diem = server_score
            else:
                raw_diem = item.get("diemXetTuyen")
                try:
                    cand_diem = float(raw_diem) if raw_diem is not None else 0.0
                    final_diem = min(max(cand_diem, 0.0), max_scale)
                except (ValueError, TypeError):
                    final_diem = 0.0

            validated.append({
                "truongDaiHocId": matched.get("truongDaiHocId"),
                "nganhHocId": m_id,
                "toHopMonId": th_id,
                "phuongThucXetTuyenId": pt_id,
                "diemXetTuyen": final_diem,
                "diemChuanThamChieu": item.get("diemChuanThamChieu") or matched.get("diemChuan"),
                "doPhuHop": item.get("doPhuHop"),
                "mucDoPhuHop": item.get("mucDoPhuHop"),
                "mucDoRuiRo": item.get("mucDoRuiRo"),
                "programId": prog_id,
                "tenChuongTrinh": ten_chuan,
                "admissionCaseId": matched.get("admissionCaseId", ""),
            })

        all_wishes = CsvDatabase.readAll("goiYNguyenVong")
        remaining = [w for w in all_wishes if w.get("hoSoHocSinhId") != ho_so_id]
        max_id = max((int(float(w.get("id", 0))) for w in remaining), default=0)

        for idx, item in enumerate(validated, 1):
            max_id += 1
            remaining.append({
                "id": max_id,
                "hoSoHocSinhId": ho_so_id,
                **{k: item[k] for k in (
                    "truongDaiHocId", "nganhHocId", "toHopMonId",
                    "phuongThucXetTuyenId", "diemXetTuyen",
                    "diemChuanThamChieu", "doPhuHop",
                    "mucDoPhuHop", "mucDoRuiRo", "programId",
                    "tenChuongTrinh", "admissionCaseId"
                )},
                "thuTuUuTien": f"NV{idx}",
                "ngayTao": now_str,
            })

        df = pd.DataFrame(remaining)[CsvDatabase.COLUMNS["goiYNguyenVong"]]
        df.to_csv(CsvDatabase.FILE_PATHS["goiYNguyenVong"], index=False, encoding="utf-8-sig")
        CsvDatabase.clearCache("goiYNguyenVong")

        return {
            "thanhCong": True,
            "thongBao": f"Đã lưu thành công {len(validated)} nguyện vọng hợp lệ vào hệ thống.",
            "soLuongDaLuu": len(validated),
        }

    @classmethod
    def soSanhPhuongThucCuaNganh(cls, truong_id: int, nganh_id: int) -> List[Dict[str, Any]]:
        all_methods = {m["id"]: m for m in CsvDatabase.readAll("phuongThucXetTuyen")}
        all_combs = {c["id"]: c for c in CsvDatabase.readAll("toHopMon")}
        benchmarks = CsvDatabase.findWhere("diemChuan", {"truongDaiHocId": truong_id, "nganhHocId": nganh_id})
        results = []
        for b in benchmarks:
            pt = all_methods.get(b.get("phuongThucXetTuyenId"), {})
            th = all_combs.get(b.get("toHopMonId"), {})
            chi_tieu_val = b.get("chiTieu")
            chi_tieu_clean = int(chi_tieu_val) if chi_tieu_val not in (None, "", "None", "null") and not pd.isna(chi_tieu_val) else None
            results.append({
                "maPhuongThuc": pt.get("maPhuongThuc", "PT01"),
                "tenPhuongThuc": pt.get("tenPhuongThuc", "Xét tuyển"),
                "maToHop": th.get("maToHop", "A00"),
                "nam": b.get("nam", config.REFERENCE_YEAR),
                "diemChuan": b.get("diemChuan"),
                "chiTieu": chi_tieu_clean,
            })
        return results
