import time
from typing import Dict, List, Any, Optional
from csvDatabase import CsvDatabase
from scoringService import ScoringService
from mlService import mlServiceInstance


class AdmissionService:

    _hocPhiByProg = None
    _hocPhiByUni = None
    _hocPhiByName = None

    @classmethod
    def _ensureHocPhiCache(cls):
        if cls._hocPhiByProg is not None:
            return
        records = CsvDatabase.readAll("hocPhi")
        cls._hocPhiByProg = {}
        cls._hocPhiByUni = {}
        cls._hocPhiByName = {}
        for r in records:
            pid = str(r.get("programId", "")).strip()
            if pid:
                cls._hocPhiByProg[pid] = r
            uCode = str(r.get("maTruong", "")).strip().upper()
            if uCode and uCode not in cls._hocPhiByUni:
                cls._hocPhiByUni[uCode] = r
            uName = str(r.get("tenTruong", "")).strip().lower()
            if uName and uName not in cls._hocPhiByName:
                cls._hocPhiByName[uName] = r

    @classmethod
    def traCuuHocPhi(
        cls,
        programId: Optional[str] = None,
        uni: Optional[Dict[str, Any]] = None,
        major: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        cls._ensureHocPhiCache()
        progKey = str(programId or "").strip()
        matched = cls._hocPhiByProg.get(progKey)
        if not matched and uni:
            uCode = str(uni.get("maTruong", "")).strip().upper()
            if uCode:
                matched = cls._hocPhiByUni.get(uCode)
            if not matched:
                uName = str(uni.get("tenTruong", "")).strip().lower()
                matched = cls._hocPhiByName.get(uName)
                if not matched and uName:
                    for kName, r in cls._hocPhiByName.items():
                        if uName in kName or kName in uName:
                            matched = r
                            break

        if matched:
            tMin = matched.get("hocPhiToiThieu")
            tMax = matched.get("hocPhiToiDa")
            tMinFloat = float(tMin) if tMin is not None and str(tMin).strip() != "" and str(tMin).lower() != "none" else None
            tMaxFloat = float(tMax) if tMax is not None and str(tMax).strip() != "" and str(tMax).lower() != "none" else None

            tYear = tMaxFloat if tMaxFloat is not None else tMinFloat
            tKy = round(tYear / 2.0, 1) if tYear is not None else None
            tTrieu = round(tYear / 1000000.0, 1) if tYear is not None else None

            phanLoai = "under_20m"
            if tTrieu is not None:
                if tTrieu <= 20.0:
                    phanLoai = "under_20m"
                elif tTrieu <= 35.0:
                    phanLoai = "20m_35m"
                else:
                    phanLoai = "over_35m"
            else:
                phanLoai = "unverified"

            return {
                "hocPhiKy": tKy,
                "hocPhiNam": tYear,
                "hocPhiTrieuNam": tTrieu,
                "hocPhiToiThieu": tMinFloat,
                "hocPhiToiDa": tMaxFloat,
                "hocPhiText": matched.get("hocPhiDisplay") or "Chưa có thông tin học phí đã xác minh",
                "trangThaiHocPhi": matched.get("trangThaiHocPhi", "UNVERIFIED"),
                "loaiHocPhi": matched.get("loaiHocPhi", "CHUA_XAC_DINH"),
                "nguonMinhChung": matched.get("nguonMinhChung", "Chưa có công bố chính thức"),
                "urlNguon": matched.get("urlNguon", ""),
                "ghiChu": matched.get("ghiChu", ""),
                "phanLoai": phanLoai
            }

        webUrl = uni.get("trangWeb", "") if uni else ""
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
            "urlNguon": webUrl,
            "ghiChu": "Cần tra cứu trực tiếp tại đề án tuyển sinh hoặc thông báo của trường",
            "phanLoai": "unverified"
        }

    @classmethod
    def uocLuongHocPhi(cls, uni: Dict[str, Any], major: Dict[str, Any]) -> Dict[str, Any]:
        return cls.traCuuHocPhi(programId=None, uni=uni, major=major)

    @classmethod
    def deXuatNguyenVong(cls, hoSoHocSinh: Dict[str, Any]) -> Dict[str, Any]:
        scoreFields = ["diemToan", "diemVan", "diemAnh", "diemLy", "diemHoa", "diemSinh", "diemSu", "diemDia", "diemGDCD", "diemHocBa"]
        for sf in scoreFields:
            val = hoSoHocSinh.get(sf)
            if val is not None:
                try:
                    fVal = float(val)
                    if fVal < 0.0 or fVal > 10.0:
                        return {"thanhCong": False, "thongBao": f"Điểm môn học {sf} ({fVal}) không hợp lệ! Điểm phải từ 0.0 đến 10.0.", "danhSachTongHop": []}
                except (ValueError, TypeError):
                    return {"thanhCong": False, "thongBao": f"Điểm môn học {sf} không hợp lệ!", "danhSachTongHop": []}

        rawPt = hoSoHocSinh.get("phuongThucMongMuon", "PT01")
        if isinstance(rawPt, list):
            danhSachPt = [p.strip().upper() for p in rawPt if p.strip()]
        else:
            danhSachPt = [p.strip().upper() for p in str(rawPt).split(",") if p.strip()]

        if not danhSachPt:
            return {"thanhCong": False, "thongBao": "Vui lòng chọn 1 phương thức xét tuyển.", "danhSachTongHop": []}
        if len(danhSachPt) > 1:
            return {"thanhCong": False, "thongBao": "Hệ thống chỉ hỗ trợ tư vấn 1 phương thức xét tuyển tại một thời điểm (PT01 hoặc PT02).", "danhSachTongHop": []}

        maPt = danhSachPt[0]
        if maPt not in ["PT01", "PT02"]:
            return {"thanhCong": False, "thongBao": f"Phương thức '{maPt}' chưa được hỗ trợ. Hiện chỉ hỗ trợ PT01 (THPT) và PT02 (Học bạ).", "danhSachTongHop": []}

        rawTh = hoSoHocSinh.get("danhSachToHopDaChon", ["A00"])
        if isinstance(rawTh, list):
            danhSachTh = [t.strip().upper() for t in rawTh if t.strip()]
        else:
            danhSachTh = [t.strip().upper() for t in str(rawTh).split(",") if t.strip()]

        if not danhSachTh:
            danhSachTh = ["A00"]

        allMethods = {m["maPhuongThuc"]: m for m in CsvDatabase.readAll("phuongThucXetTuyen")}
        allCombs = {c["maToHop"]: c for c in CsvDatabase.readAll("toHopMon")}
        allUnis = {u["id"]: u for u in CsvDatabase.readAll("truongDaiHoc")}
        allMajors = {m["id"]: m for m in CsvDatabase.readAll("nganhHoc")}
        allBenchmarks = CsvDatabase.readAll("diemChuan")

        thongTinPt = allMethods.get(maPt, {"maPhuongThuc": maPt, "tenPhuongThuc": f"Phương thức {maPt}"})
        ptId = thongTinPt.get("id")

        khuVucMongMuon = hoSoHocSinh.get("khuVucMongMuon")
        kvTarget = khuVucMongMuon.strip() if khuVucMongMuon and khuVucMongMuon.strip() not in ["Tất cả", "Toàn quốc", ""] else None
        nganhTarget = str(hoSoHocSinh.get("nganhMongMuon") or "").strip().lower()

        ungVienHopLe = []
        ungVienCanKiemTra = []

        for maTh in danhSachTh:
            thId = allCombs.get(maTh, {}).get("id")

            matchedBenchmarks = [
                b for b in allBenchmarks
                if ptId is not None and int(b.get("phuongThucXetTuyenId", -1)) == int(ptId)
                and (thId is None or int(b.get("toHopMonId", -1)) == int(thId))
            ]

            if not matchedBenchmarks:
                continue

            for dc in matchedBenchmarks:
                uId = dc.get("truongDaiHocId")
                mId = dc.get("nganhHocId")
                uni = allUnis.get(uId, {"maTruong": "UNI", "tenTruong": "Đại học", "khuVuc": "Toàn quốc"})
                major = allMajors.get(mId, {"maNganh": "UNKNOWN", "tenNganh": "Chưa phân loại", "nhomNganh": "Liên ngành"})

                uniKhuVuc = uni.get("khuVuc", "")
                if kvTarget and uniKhuVuc != kvTarget:
                    continue

                ruleId = dc.get("calculationRuleId", "RULE_THPT_STD_30" if maPt == "PT01" else "RULE_HB_STD_30")
                scale = dc.get("scoreScale", "SCALE_30")

                ketQuaDiem = ScoringService.tinhDiemXetTuyenChuongTrinh(hoSoHocSinh, maPt, maTh, ruleId, scale)
                if not ketQuaDiem.get("hopLe"):
                    continue

                diemXetTuyen = ketQuaDiem["diemXetTuyen"]
                diemChuanLichSu = float(dc.get("diemChuan", 24.0))
                progId = str(dc.get("programId", "")).strip()
                caseId = str(dc.get("admissionCaseId", "")).strip()

                fcInfo = mlServiceInstance.getForecastInfo(
                    universityCode=uni.get("maTruong", ""),
                    programId=progId,
                    admissionCaseId=caseId,
                    methodCode=maPt,
                    combinationCode=maTh
                )

                coDuBao = (fcInfo is not None and fcInfo.get("predictedCutoff") is not None)
                diemDuBao = fcInfo.get("predictedCutoff") if coDuBao else None
                diemSoSanh = diemDuBao if coDuBao else diemChuanLichSu
                loaiDuBao = fcInfo.get("forecastType") if fcInfo else "HISTORICAL_ONLY"
                nhanDuBao = (fcInfo.get("displayLabel") or fcInfo.get("forecastTypeLabel")) if fcInfo else f"Điểm chuẩn năm {dc.get('nam', 2025)}"

                namBc = dc.get("nam", 2025)
                uRadius = fcInfo.get("uncertaintyRadius", 0.5) if fcInfo else 0.5

                duBao = mlServiceInstance.predictSuitability(
                    studentScore=diemXetTuyen,
                    benchmarkScore=diemSoSanh,
                    methodCode=maPt,
                    combinationCode=maTh,
                    scoreScale=scale,
                    namThamChieu=namBc,
                    coDuBao=coDuBao,
                    uncertaintyRadius=uRadius,
                    forecastType=loaiDuBao,
                    uniTier=2
                )

                diemThuanLoi = duBao["doPhuHop"]
                
                scoreKv = 80.0
                if kvTarget:
                    scoreKv = 100.0 if uniKhuVuc == kvTarget else 35.0

                scoreNganh = 80.0
                if nganhTarget:
                    tenNganhStr = str(major.get("tenNganh", "")).lower()
                    tenPrgStr = str(dc.get("tenChuongTrinh", "")).lower()
                    if nganhTarget in tenNganhStr or nganhTarget in tenPrgStr:
                        scoreNganh = 100.0
                    elif nganhTarget in str(major.get("nhomNganh", "")).lower():
                        scoreNganh = 70.0
                    else:
                        scoreNganh = 40.0

                hpInfo = cls.traCuuHocPhi(programId=progId, uni=uni, major=major)
                hocPhiUocTinhTrieu = hpInfo["hocPhiTrieuNam"]
                trangThaiHp = hpInfo["trangThaiHocPhi"]
                
                mucHocPhiFilter = hoSoHocSinh.get("mucHocPhi") or hoSoHocSinh.get("filterTuition") or hoSoHocSinh.get("hocPhiFilter")
                nganSachVal = hoSoHocSinh.get("nganSach")

                scoreHocPhi = 80.0
                nhomHocPhi = "KHONG_LOC"
                laCanKiemTra = False

                coLocNganSach = bool(mucHocPhiFilter or (nganSachVal is not None and str(nganSachVal).strip() != "" and float(nganSachVal) > 0))

                if coLocNganSach:
                    if trangThaiHp == "UNVERIFIED" or hocPhiUocTinhTrieu is None:
                        nhomHocPhi = "CAN_KIEM_TRA"
                        laCanKiemTra = True
                    else:
                        isMatch = True
                        if mucHocPhiFilter == "under_20m":
                            isMatch = (hocPhiUocTinhTrieu <= 20.0)
                        elif mucHocPhiFilter == "20m_35m":
                            isMatch = (20.0 <= hocPhiUocTinhTrieu <= 35.0)
                        elif mucHocPhiFilter == "over_35m":
                            isMatch = (hocPhiUocTinhTrieu >= 35.0)

                        if nganSachVal is not None and str(nganSachVal).strip() != "" and float(nganSachVal) > 0:
                            isMatch = isMatch and (hocPhiUocTinhTrieu <= float(nganSachVal))

                        if not isMatch:
                            continue
                        nhomHocPhi = "PHU_HOP"
                        scoreHocPhi = 100.0

                scoreSoThich = round(0.40 * scoreKv + 0.40 * scoreNganh + 0.20 * scoreHocPhi, 1)
                doPhuHopTongThe = round(0.70 * diemThuanLoi + 0.30 * scoreSoThich, 1)

                mucItem = {
                    "truongDaiHocId": uId,
                    "maTruong": uni["maTruong"],
                    "tenTruong": uni["tenTruong"],
                    "diaChi": uni.get("diaChi", ""),
                    "khuVuc": uniKhuVuc,
                    "loaiTruong": uni.get("loaiTruong", "Đại học"),
                    "hocPhiKy": hpInfo["hocPhiKy"],
                    "hocPhiNam": hpInfo["hocPhiNam"],
                    "hocPhiUocTinh": hpInfo["hocPhiText"],
                    "hocPhiPhanLoai": hpInfo["phanLoai"],
                    "trangThaiHocPhi": trangThaiHp,
                    "loaiHocPhi": hpInfo["loaiHocPhi"],
                    "nguonMinhChung": hpInfo["nguonMinhChung"],
                    "urlNguon": hpInfo.get("urlNguon", ""),
                    "ghiChuHocPhi": hpInfo.get("ghiChu", ""),
                    "nhomHocPhi": nhomHocPhi,
                    "chiTieu": int(dc.get("chiTieu") or 100),
                    "nganhHocId": mId,
                    "maNganh": major["maNganh"],
                    "tenNganh": major["tenNganh"],
                    "tenChuongTrinh": dc.get("tenChuongTrinh") or major["tenNganh"],
                    "programId": progId,
                    "admissionCaseId": caseId,
                    "nhomNganh": major.get("nhomNganh", ""),
                    "toHopMonId": thId,
                    "maToHop": maTh,
                    "tenToHop": allCombs.get(maTh, {}).get("tenToHop", maTh),
                    "phuongThucXetTuyenId": ptId,
                    "maPhuongThuc": maPt,
                    "tenPhuongThuc": thongTinPt.get("tenPhuongThuc", ""),
                    "scoreScale": scale,
                    "calculationRuleId": ruleId,
                    "diemXetTuyen": diemXetTuyen,
                    "diemChuanThamChieu": diemChuanLichSu,
                    "namThamChieu": namBc,
                    "coDuBao": coDuBao,
                    "diemChuanDuBao": diemDuBao,
                    "loaiDuBao": loaiDuBao,
                    "nhanDuBao": nhanDuBao,
                    "namMucTieu": fcInfo.get("targetYear") if coDuBao else None,
                    "phienBanMoHinh": fcInfo.get("modelVersion") if coDuBao else None,
                    "khoangTinCay80": f"{fcInfo['lowerBound80']} – {fcInfo['upperBound80']}" if coDuBao and fcInfo.get("lowerBound80") else None,
                    "lyDoChuaCoDuBao": None if coDuBao else ("Phương thức học bạ sử dụng điểm chuẩn chính thức công bố" if maPt == "PT02" else "Chương trình chưa có đủ dữ liệu chuỗi thời gian để xây dựng mô hình dự báo"),
                    "cachTinhDiem": ketQuaDiem.get("cachTinh", ""),
                    "delta": duBao["delta"],
                    "xacSuatDo": duBao.get("xacSuatDo", diemThuanLoi),
                    "doPhuHop": doPhuHopTongThe,
                    "mucThuanLoiDiem": diemThuanLoi,
                    "doPhuHopSoThich": scoreSoThich,
                    "nhomNguyenVong": duBao.get("nhomNguyenVong", "Vừa sức"),
                    "mucDoPhuHop": duBao["mucDoPhuHop"],
                    "mucDoRuiRo": duBao["mucDoRuiRo"]
                }
                if laCanKiemTra:
                    ungVienCanKiemTra.append(mucItem)
                else:
                    ungVienHopLe.append(mucItem)

        seenProgKeys = set()
        uniqueCandidates = []
        for item in ungVienHopLe:
            pKey = (item["truongDaiHocId"], item["programId"] or item["nganhHocId"], item["admissionCaseId"], item["maToHop"])
            if pKey not in seenProgKeys:
                seenProgKeys.add(pKey)
                uniqueCandidates.append(item)

        
        rawThuSuc = [c for c in uniqueCandidates if c.get("nhomNguyenVong") == "Thử sức"]
        rawVuaSuc = [c for c in uniqueCandidates if c.get("nhomNguyenVong") == "Vừa sức"]
        rawAnToan = [c for c in uniqueCandidates if c.get("nhomNguyenVong") == "An toàn"]


        def _sort_thu_suc(x):
            d = x.get("delta", -1.0)
            return (abs(d) * -10.0) + (x.get("doPhuHopSoThich", 80.0) * 0.3)

        rawThuSuc.sort(key=_sort_thu_suc, reverse=True)

        rawVuaSuc.sort(key=lambda x: x.get("doPhuHop", 50.0), reverse=True)

        def _sort_an_toan(x):
            d = x.get("delta", 2.0)
            scaleVal = x.get("scoreScale", "SCALE_30")
            dOpt = 0.8 if scaleVal == "GPA_10" else (2.8 if scaleVal == "SCALE_40" else 2.2)
            distPenalty = abs(d - dOpt) * 8.0
            return (x.get("doPhuHopSoThich", 80.0) * 0.4) + (x.get("diemChuanThamChieu", 20.0) * 1.5) - distPenalty

        rawAnToan.sort(key=_sort_an_toan, reverse=True)

        uniCount = {}
        thuSucPicks = []
        vuaSucPicks = []
        anToanPicks = []

        for c in rawThuSuc:
            uId = c["truongDaiHocId"]
            if uniCount.get(uId, 0) < 3:
                thuSucPicks.append(c)
                uniCount[uId] = uniCount.get(uId, 0) + 1
                if len(thuSucPicks) >= 5:
                    break

        for c in rawVuaSuc:
            uId = c["truongDaiHocId"]
            if uniCount.get(uId, 0) < 3:
                vuaSucPicks.append(c)
                uniCount[uId] = uniCount.get(uId, 0) + 1
                if len(vuaSucPicks) >= 10:
                    break

        for c in rawAnToan:
            uId = c["truongDaiHocId"]
            if uniCount.get(uId, 0) < 3:
                anToanPicks.append(c)
                uniCount[uId] = uniCount.get(uId, 0) + 1
                if len(anToanPicks) >= 5:
                    break

        selectedWishes = []
        selectedWishes.extend(thuSucPicks)
        selectedWishes.extend(vuaSucPicks)
        selectedWishes.extend(anToanPicks)

        if len(selectedWishes) < 20:
            pickedKeys = {(w["truongDaiHocId"], w["programId"], w["maToHop"]) for w in selectedWishes}
            for pool in [rawVuaSuc, rawAnToan, rawThuSuc, uniqueCandidates]:
                for c in pool:
                    uId = c["truongDaiHocId"]
                    ck = (uId, c["programId"], c["maToHop"])
                    if ck not in pickedKeys and uniCount.get(uId, 0) < 3:
                        selectedWishes.append(c)
                        pickedKeys.add(ck)
                        uniCount[uId] = uniCount.get(uId, 0) + 1
                        if len(selectedWishes) >= 20:
                            break
                if len(selectedWishes) >= 20:
                    break

        if len(selectedWishes) < 20:
            pickedKeys = {(w["truongDaiHocId"], w["programId"], w["maToHop"]) for w in selectedWishes}
            for c in uniqueCandidates:
                ck = (c["truongDaiHocId"], c["programId"], c["maToHop"])
                if ck not in pickedKeys:
                    selectedWishes.append(c)
                    pickedKeys.add(ck)
                    if len(selectedWishes) >= 20:
                        break

        tierOrder = {"Thử sức": 1, "Vừa sức": 2, "An toàn": 3, "Rủi ro cao": 4}
        selectedWishes.sort(key=lambda x: (tierOrder.get(x.get("nhomNguyenVong", "Vừa sức"), 2), -x.get("doPhuHop", 50.0)))

        danhSachTongHop = []
        for idx, item in enumerate(selectedWishes[:20], 1):
            itemCopy = dict(item)
            itemCopy["thuTuUuTien"] = f"NV{idx}"
            itemCopy["stt"] = idx
            danhSachTongHop.append(itemCopy)

        anToanCount = sum(1 for w in danhSachTongHop if w.get("nhomNguyenVong") == "An toàn")
        highRiskCount = sum(1 for w in danhSachTongHop if w.get("nhomNguyenVong") in ["Thử sức", "Rủi ro cao"])
        firstScore = float(danhSachTongHop[0].get("diemXetTuyen", 0.0)) if danhSachTongHop else 0.0
        
        firstItem = danhSachTongHop[0] if danhSachTongHop else {}
        firstScale = firstItem.get("scoreScale", "SCALE_30")
        minSafeScore = 5.0 if firstScale in ["GPA_10", "THANG_10"] else (21.0 if firstScale in ["SCALE_40", "THANG_40"] else 16.0)
        isLowScoreAlert = (anToanCount == 0 or highRiskCount >= 10 or (firstScore > 0 and firstScore < minSafeScore))

        tsCount = sum(1 for w in danhSachTongHop if w.get("nhomNguyenVong") == "Thử sức")
        vsCount = sum(1 for w in danhSachTongHop if w.get("nhomNguyenVong") == "Vừa sức")
        atCount = sum(1 for w in danhSachTongHop if w.get("nhomNguyenVong") == "An toàn")

        if not danhSachTongHop:
            thongBao = "Không tìm thấy chương trình phù hợp với thông tin đã nhập."
        elif isLowScoreAlert:
            avgScore = round(firstScore, 2)
            thongBao = f"Điểm xét tuyển ({avgScore}) ở mức thấp so với ngưỡng điểm chuẩn đại học (danh sách không có hoặc rất ít nguyện vọng An toàn). Các nguyện vọng gợi ý tập trung ở mức Thử sức và Vừa sức sát ngưỡng. Thí sinh nên cân nhắc thêm các hệ cao đẳng, xét tuyển học bạ hoặc ngành đào tạo nghề."
        elif tsCount >= 4 and vsCount >= 8 and atCount >= 4:
            thongBao = f"Đã tìm thấy danh mục 20 nguyện vọng tối ưu phân tầng chuẩn 25% Thử sức ({tsCount}) - 50% Vừa sức ({vsCount}) - 25% An toàn ({atCount})."
        else:
            thongBao = f"Đã đề xuất {len(danhSachTongHop)} nguyện vọng phù hợp với phổ điểm ({tsCount} Thử sức, {vsCount} Vừa sức, {atCount} An toàn)."

        ketQuaMoiPhuongThuc = {
            maPt: {
                "thongTinPhuongThuc": thongTinPt,
                "soLuong": len(danhSachTongHop),
                "thongBao": thongBao,
                "danhSach": danhSachTongHop
            }
        }

        seenCkKeys = set()
        uniqueCanKiemTra = []
        for item in ungVienCanKiemTra:
            pKey = (item["truongDaiHocId"], item["programId"] or item["nganhHocId"], item["admissionCaseId"], item["maToHop"])
            if pKey not in seenCkKeys:
                seenCkKeys.add(pKey)
                uniqueCanKiemTra.append(item)

        return {
            "thanhCong": True,
            "thongBao": thongBao,
            "danhSachTongHop": danhSachTongHop,
            "danhSachCanKiemTraHocPhi": uniqueCanKiemTra[:15],
            "ketQuaTungPhuongThuc": ketQuaMoiPhuongThuc,
            "phuongThucDangChon": maPt,
            "soLuongToHopDaChon": len(danhSachTh)
        }

    @classmethod
    def luuDanhSachNguyenVong(cls, nguoiDungId: int, danhSachNguyenVong: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not nguoiDungId:
            return {"thanhCong": False, "thongBao": "Yêu cầu đăng nhập để lưu danh sách nguyện vọng."}

        if not danhSachNguyenVong:
            return {"thanhCong": False, "thongBao": "Danh sách nguyện vọng lưu không được để trống."}

        userProfiles = CsvDatabase.findWhere("hoSoHocSinh", {"nguoiDungId": nguoiDungId})
        nowStr = time.strftime("%Y-%m-%d %H:%M:%S")

        if userProfiles:
            hoSoId = userProfiles[0]["id"]
        else:
            newProfile = CsvDatabase.insert("hoSoHocSinh", {
                "nguoiDungId": nguoiDungId,
                "ngayCapNhat": nowStr
            })
            hoSoId = newProfile["id"]

        allBenchmarks = CsvDatabase.readAll("diemChuan")
        allMajors = {m["id"]: m for m in CsvDatabase.readAll("nganhHoc")}
        progLookup = {}
        for b in allBenchmarks:
            pid = str(b.get("programId", "")).strip()
            if pid and pid not in progLookup:
                progLookup[pid] = b

        validatedWishes = []
        seenProgIds = set()

        for idx, item in enumerate(danhSachNguyenVong, 1):
            progId = str(item.get("programId") or "").strip()
            if not progId:
                return {
                    "thanhCong": False,
                    "thongBao": f"Nguyện vọng thứ {idx} thiếu mã chương trình đào tạo (programId)."
                }

            if progId not in progLookup:
                return {
                    "thanhCong": False,
                    "thongBao": f"Mã chương trình '{progId}' không tồn tại trong danh mục tuyển sinh chính thức của hệ thống."
                }

            toHopKey = str(item.get("toHopMonId") or item.get("maToHop") or "")
            ptKey = str(item.get("phuongThucXetTuyenId") or item.get("maPhuongThuc") or "")
            wishKey = (progId, toHopKey, ptKey)

            if wishKey in seenProgIds:
                continue
            seenProgIds.add(wishKey)

            matchedProg = progLookup[progId]
            mId = matchedProg.get("nganhHocId")
            majorInfo = allMajors.get(mId, {})
            tenChuan = matchedProg.get("tenChuongTrinh") or majorInfo.get("tenNganh") or "Chương trình đào tạo"
            uId = matchedProg.get("truongDaiHocId")
            caseId = matchedProg.get("admissionCaseId", "")

            validatedWishes.append({
                "truongDaiHocId": uId,
                "nganhHocId": mId,
                "toHopMonId": item.get("toHopMonId") or matchedProg.get("toHopMonId"),
                "phuongThucXetTuyenId": item.get("phuongThucXetTuyenId") or matchedProg.get("phuongThucXetTuyenId"),
                "diemXetTuyen": item.get("diemXetTuyen"),
                "diemChuanThamChieu": item.get("diemChuanThamChieu") or matchedProg.get("diemChuan"),
                "doPhuHop": item.get("doPhuHop"),
                "mucDoPhuHop": item.get("mucDoPhuHop"),
                "mucDoRuiRo": item.get("mucDoRuiRo"),
                "programId": progId,
                "tenChuongTrinh": tenChuan,
                "admissionCaseId": caseId
            })

        allWishes = CsvDatabase.readAll("goiYNguyenVong")
        remainingWishes = [w for w in allWishes if w.get("hoSoHocSinhId") != hoSoId]

        maxId = 0
        for w in remainingWishes:
            try:
                maxId = max(maxId, int(float(w.get("id", 0))))
            except (ValueError, TypeError):
                pass

        soLuongDaLuu = 0
        for idx, item in enumerate(validatedWishes, 1):
            maxId += 1
            newWish = {
                "id": maxId,
                "hoSoHocSinhId": hoSoId,
                "truongDaiHocId": item["truongDaiHocId"],
                "nganhHocId": item["nganhHocId"],
                "toHopMonId": item["toHopMonId"],
                "phuongThucXetTuyenId": item["phuongThucXetTuyenId"],
                "diemXetTuyen": item["diemXetTuyen"],
                "diemChuanThamChieu": item["diemChuanThamChieu"],
                "doPhuHop": item["doPhuHop"],
                "mucDoPhuHop": item["mucDoPhuHop"],
                "mucDoRuiRo": item["mucDoRuiRo"],
                "thuTuUuTien": f"NV{idx}",
                "ngayTao": nowStr,
                "programId": item["programId"],
                "tenChuongTrinh": item["tenChuongTrinh"],
                "admissionCaseId": item["admissionCaseId"]
            }
            remainingWishes.append(newWish)
            soLuongDaLuu += 1

        import pandas as pd
        dfWishes = pd.DataFrame(remainingWishes)[CsvDatabase.COLUMNS["goiYNguyenVong"]]
        dfWishes.to_csv(CsvDatabase.FILE_PATHS["goiYNguyenVong"], index=False, encoding="utf-8-sig")
        CsvDatabase.clearCache("goiYNguyenVong")

        return {
            "thanhCong": True,
            "thongBao": f"Đã lưu thành công {soLuongDaLuu} nguyện vọng hợp lệ vào hệ thống.",
            "soLuongDaLuu": soLuongDaLuu
        }

    @classmethod
    def soSanhPhuongThucCuaNganh(cls, truongDaiHocId: int, nganhHocId: int) -> List[Dict[str, Any]]:
        allMethods = {m["id"]: m for m in CsvDatabase.readAll("phuongThucXetTuyen")}
        allCombs = {c["id"]: c for c in CsvDatabase.readAll("toHopMon")}
        benchmarks = CsvDatabase.findWhere("diemChuan", {"truongDaiHocId": truongDaiHocId, "nganhHocId": nganhHocId})

        results = []
        for b in benchmarks:
            pt = allMethods.get(b.get("phuongThucXetTuyenId"), {})
            th = allCombs.get(b.get("toHopMonId"), {})
            results.append({
                "maPhuongThuc": pt.get("maPhuongThuc", "PT01"),
                "tenPhuongThuc": pt.get("tenPhuongThuc", "Xét tuyển"),
                "maToHop": th.get("maToHop", "A00"),
                "nam": b.get("nam", 2025),
                "diemChuan": b.get("diemChuan"),
                "chiTieu": b.get("chiTieu", 100)
            })
        return results
