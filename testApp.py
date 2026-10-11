import os
import shutil
import tempfile
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from app import app
from csvDatabase import CsvDatabase
from scoringService import ScoringService
from mlService import mlServiceInstance
from authService import AuthService, createJwtToken, verifyJwtToken

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def isolate_test_database():
    original_dir = CsvDatabase.CSV_DIR if hasattr(CsvDatabase, "CSV_DIR") else os.path.join(os.path.dirname(__file__), "data", "csv")
    temp_dir = tempfile.mkdtemp(prefix="dss_test_csv_")
    for f in os.listdir(original_dir):
        src_path = os.path.join(original_dir, f)
        if os.path.isfile(src_path):
            shutil.copy2(src_path, os.path.join(temp_dir, f))
    CsvDatabase.setDatabaseDirectory(temp_dir)
    yield temp_dir
    CsvDatabase.setDatabaseDirectory(original_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_csv_database_tables_and_columns():
    for tableName, expectedCols in CsvDatabase.COLUMNS.items():
        records = CsvDatabase.readAll(tableName)
        assert isinstance(records, list)
        for col in expectedCols:
            assert "_" not in col, f"Phát hiện dấu '_' trong tên cột {col} của bảng {tableName}"
        assert "_" not in tableName, f"Phát hiện dấu '_' trong tên bảng {tableName}"


def test_combinations_catalog():
    combs = CsvDatabase.readAll("toHopMon")
    combCodes = [c["maToHop"] for c in combs]
    for requiredComb in ["A00", "A01", "B00", "C00", "D01", "D07"]:
        assert requiredComb in combCodes, f"Thiếu tổ hợp {requiredComb} trong danh mục chuẩn"


def test_methods_catalog():
    methods = CsvDatabase.readAll("phuongThucXetTuyen")
    methodCodes = [m["maPhuongThuc"] for m in methods]
    for pt in ["PT01", "PT02", "PT03", "PT04", "PT05", "PT06", "PT07"]:
        assert pt in methodCodes, f"Thiếu phương thức {pt} trong danh mục chuẩn"


def test_business_scoring_functions():
    diemMonHoc = {
        "diemToan": 9.0,
        "diemLy": 8.5,
        "diemHoa": 8.0,
        "diemAnh": 9.0,
        "diemVan": 8.0
    }

    sA00 = ScoringService.tinhDiemToHop(diemMonHoc, "A00")
    assert sA00 == 25.5, f"Điểm A00 tính được: {sA00}, mong đợi: 25.5"

    sD01 = ScoringService.tinhDiemToHop(diemMonHoc, "D01")
    assert sD01 == 26.0, f"Điểm D01 tính được: {sD01}, mong đợi: 26.0"

    sB00 = ScoringService.tinhDiemToHop(diemMonHoc, "B00")
    assert sB00 is None, "B00 thiếu môn Sinh học nhưng không trả về None"

    u1 = ScoringService.tinhDiemUuTien("KV1", "NONE", 20.0)
    assert u1 == 0.75

    uReduced = ScoringService.tinhDiemUuTien("KV1", "NONE", 25.5)
    expectedReduced = round(((30.0 - 25.5) / 7.5) * 0.75, 2)
    assert uReduced == expectedReduced
    assert uReduced < 0.75

    sFinal = ScoringService.tinhDiemXetTuyen(sA00, uReduced)
    assert sFinal == round(sA00 + uReduced, 2)


def test_scoring_gpa_and_rules():
    hoSoHbComb = {
        "diemToan": 8.0,
        "diemLy": 8.5,
        "diemAnh": 9.0,
        "khuVucUuTien": "KV3",
        "doiTuongUuTien": "NONE"
    }
    resHb1 = ScoringService.tinhDiemTheoPhuongThuc(hoSoHbComb, "PT02", "A01")
    assert resHb1["hopLe"] is True
    assert resHb1["diemTho"] == 25.5
    assert "tổ hợp A01" in resHb1["cachTinh"]

    hoSoHbGpa = {
        "diemHocBa": 8.5,
        "calculationRuleId": "RULE_HB_GPA_X3",
        "scoreScale": "SCALE_30",
        "khuVucUuTien": "KV3",
        "doiTuongUuTien": "NONE"
    }
    resHb2 = ScoringService.tinhDiemXetTuyenChuongTrinh(hoSoHbGpa, "PT02", "HB_GPA", "RULE_HB_GPA_X3", "SCALE_30")
    assert resHb2["hopLe"] is True
    assert resHb2["diemTho"] == round(8.5 * 3, 2)
    assert "GPA" in resHb2["cachTinh"]


def test_random_forest_prediction():
    res = mlServiceInstance.predictSuitability(
        studentScore=28.0,
        benchmarkScore=26.5,
        methodCode="PT01",
        combinationCode="A00"
    )
    assert "doPhuHop" in res
    assert 0.0 <= res["doPhuHop"] <= 100.0
    assert res["mucDoPhuHop"] in ["Rất phù hợp", "Phù hợp", "Cân nhắc", "Thử sức"]
    assert res["mucDoRuiRo"] in ["Thấp", "Trung bình", "Cao"]
    assert res["delta"] == 1.5


def test_ml_service_status():
    stThpt = mlServiceInstance.getModelStatus("PT01")
    assert "sanSang" in stThpt
    assert "phuongPhap" in stThpt

    stHb = mlServiceInstance.getModelStatus("PT02")
    assert stHb["sanSang"] is False
    assert "Tra cứu" in stHb["cheDo"]


def test_auth_system_and_security():
    loginRes = AuthService.dangNhap("hocsinh", "hocsinh123")
    assert loginRes["thanhCong"] is True
    token = loginRes["token"]

    payload = verifyJwtToken(token)
    assert payload is not None
    assert payload["username"] == "hocsinh"
    assert payload["role"] == "hocSinh"

    testUser = f"test_sec_{int(pd.Timestamp.now().timestamp())}"
    regResp = client.post("/api/auth/register", json={
        "tenDangNhap": testUser,
        "matKhau": "123456",
        "hoTen": "Người dùng Test Bảo Mật",
        "email": f"{testUser}@test.edu.vn",
        "vaiTro": "quanTriVien"
    })
    assert regResp.status_code == 200
    regData = regResp.json()
    assert regData["nguoiDung"]["vaiTro"] == "hocSinh", "Tài khoản đăng ký mới phải có vai trò hocSinh"


def test_recommendation_api_thpt():
    payload = {
        "diemToan": 9.0, "diemLy": 8.5, "diemHoa": 8.5, "diemAnh": 9.0, "diemVan": 8.0,
        "khuVucUuTien": "KV1", "doiTuongUuTien": "NONE",
        "phuongThucMongMuon": ["PT01"],
        "danhSachToHopDaChon": ["A00"]
    }
    resp = client.post("/api/recommend", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["thanhCong"] is True
    assert len(data["danhSachTongHop"]) > 0

    topItem = data["danhSachTongHop"][0]
    assert "thuTuUuTien" in topItem
    assert "tenTruong" in topItem
    assert "tenNganh" in topItem
    assert topItem["maPhuongThuc"] == "PT01"


def test_hoc_ba_does_not_return_thpt_records():
    payload = {
        "diemToan": 8.5, "diemLy": 8.0, "diemAnh": 8.5,
        "diemHocBa": 8.6,
        "khuVucUuTien": "KV3", "doiTuongUuTien": "NONE",
        "phuongThucMongMuon": ["PT02"],
        "danhSachToHopDaChon": ["A01"]
    }
    resp = client.post("/api/recommend", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    for item in data.get("danhSachTongHop", []):
        assert item["maPhuongThuc"] == "PT02", f"Dữ liệu trả về không đúng phương thức PT02: {item['maPhuongThuc']}"
        assert item["phuongThucXetTuyenId"] == 2


def test_wishlist_save_and_retrieve_history():
    loginRes = AuthService.dangNhap("hocsinh", "hocsinh123")
    token = loginRes["token"]

    sampleWishes = [
        {
            "truongDaiHocId": 42,
            "nganhHocId": 7,
            "programId": "PRG_BKA_0069",
            "admissionCaseId": "CASE_BKA_01",
            "toHopMonId": 1,
            "phuongThucXetTuyenId": 1,
            "diemXetTuyen": 27.5,
            "diemChuanThamChieu": 26.0,
            "doPhuHop": 85.5,
            "mucDoPhuHop": "Rất phù hợp",
            "mucDoRuiRo": "Thấp",
            "thuTuUuTien": "NV1"
        },
        {
            "truongDaiHocId": 42,
            "nganhHocId": 44,
            "programId": "PRG_BKA_0049",
            "admissionCaseId": "CASE_BKA_02",
            "toHopMonId": 1,
            "phuongThucXetTuyenId": 1,
            "diemXetTuyen": 27.5,
            "diemChuanThamChieu": 27.0,
            "doPhuHop": 72.0,
            "mucDoPhuHop": "Phù hợp",
            "mucDoRuiRo": "Trung bình",
            "thuTuUuTien": "NV2"
        }
    ]

    saveResp = client.post(
        "/api/wishlist/save",
        headers={"Authorization": f"Bearer {token}"},
        json={"danhSachNguyenVong": sampleWishes}
    )
    assert saveResp.status_code == 200
    saveData = saveResp.json()
    assert saveData["thanhCong"] is True
    assert saveData["soLuongDaLuu"] == 2

    histResp = client.get(
        "/api/wishlist-history",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert histResp.status_code == 200
    histData = histResp.json()
    assert len(histData) >= 2
    assert any(w.get("thuTuUuTien") == "NV1" for w in histData)
    assert any(w.get("thuTuUuTien") == "NV2" for w in histData)

    unauthResp = client.get("/api/wishlist-history")
    assert unauthResp.status_code == 401


def test_admin_add_combination_and_method_with_cleanup():
    adminLogin = AuthService.dangNhap("admin", "admin123")
    adminToken = adminLogin["token"]

    testCombCode = "TTEST"
    testMethodCode = "PTTEST"

    try:
        respComb = client.post(
            "/api/combinations",
            headers={"Authorization": f"Bearer {adminToken}"},
            json={
                "maToHop": testCombCode,
                "tenToHop": "Tổ hợp thử nghiệm tạm thời",
                "mon1": "diemToan",
                "mon2": "diemLy",
                "mon3": "diemAnh"
            }
        )
        assert respComb.status_code in [200, 400]

        allCombs = client.get("/api/combinations").json()
        assert any(c["maToHop"] == testCombCode for c in allCombs)

        respMethod = client.post(
            "/api/methods",
            headers={"Authorization": f"Bearer {adminToken}"},
            json={
                "maPhuongThuc": testMethodCode,
                "tenPhuongThuc": "Phương thức kiểm thử tạm thời",
                "moTa": "Mô tả kiểm thử"
            }
        )
        assert respMethod.status_code in [200, 400]

        allMethods = client.get("/api/methods").json()
        assert any(m["maPhuongThuc"] == testMethodCode for m in allMethods)

    finally:
        thPath = CsvDatabase.FILE_PATHS["toHopMon"]
        if os.path.exists(thPath):
            dfTh = pd.read_csv(thPath)
            dfTh = dfTh[dfTh["maToHop"] != testCombCode]
            dfTh.to_csv(thPath, index=False, encoding="utf-8-sig")

        ptPath = CsvDatabase.FILE_PATHS["phuongThucXetTuyen"]
        if os.path.exists(ptPath):
            dfPt = pd.read_csv(ptPath)
            dfPt = dfPt[dfPt["maPhuongThuc"] != testMethodCode]
            dfPt.to_csv(ptPath, index=False, encoding="utf-8-sig")


def test_forecast_distinction_by_program():
    fcNone = mlServiceInstance.getForecastInfo("BKA")
    assert fcNone is None

    fcIoT = mlServiceInstance.getForecastInfo("BKA", "PRG_BKA_0049", combinationCode="A00")
    assert fcIoT is not None
    assert fcIoT["predictedCutoff"] == 27.33

    fcSec = mlServiceInstance.getForecastInfo("BKA", "PRG_BKA_0069", combinationCode="A00")
    assert fcSec is not None
    assert fcSec["predictedCutoff"] == 27.26

    fcChem = mlServiceInstance.getForecastInfo("BKA", "PRG_BKA_0008", combinationCode="A00")
    assert fcChem is not None
    assert fcChem["predictedCutoff"] == 23.23

    fcInvalid = mlServiceInstance.getForecastInfo("BKA", "NON_EXISTENT_PROGRAM")
    assert fcInvalid is None


def test_input_validation_server_side():
    resInvalidScore = client.post("/api/recommend", json={
        "diemToan": 99.0,
        "diemLy": 8.0,
        "diemHoa": 8.0,
        "phuongThucMongMuon": ["PT01"],
        "danhSachToHopDaChon": ["A00"]
    })
    assert resInvalidScore.status_code in [400, 422]

    resNegativeScore = client.post("/api/recommend", json={
        "diemToan": -5.0,
        "diemLy": 8.0,
        "diemHoa": 8.0,
        "phuongThucMongMuon": ["PT01"],
        "danhSachToHopDaChon": ["A00"]
    })
    assert resNegativeScore.status_code in [400, 422]

    resMultiMethod = client.post("/api/recommend", json={
        "diemToan": 8.0,
        "diemLy": 8.0,
        "diemHoa": 8.0,
        "phuongThucMongMuon": ["PT01", "PT02"],
        "danhSachToHopDaChon": ["A00"]
    })
    assert resMultiMethod.status_code in [400, 422]

    resUnsupportedMethod = client.post("/api/recommend", json={
        "diemToan": 8.0,
        "diemLy": 8.0,
        "diemHoa": 8.0,
        "phuongThucMongMuon": ["PT99"],
        "danhSachToHopDaChon": ["A00"]
    })
    assert resUnsupportedMethod.status_code in [400, 422]


def test_auth_password_no_bypass():
    adminWithStudentPass = AuthService.dangNhap("admin", "hocsinh123")
    assert adminWithStudentPass["thanhCong"] is False

    adminCorrect = AuthService.dangNhap("admin", "admin123")
    assert adminCorrect["thanhCong"] is True

    studentCorrect = AuthService.dangNhap("hocsinh", "hocsinh123")
    assert studentCorrect["thanhCong"] is True


def test_profile_saving_ownership_security():
    resUnauth = client.post("/api/profile", json={
        "nguoiDungId": 1,
        "diemToan": 8.5,
        "diemVan": 8.0,
        "diemAnh": 8.5,
        "phuongThucMongMuon": "PT01"
    })
    assert resUnauth.status_code == 401

    loginRes = AuthService.dangNhap("hocsinh", "hocsinh123")
    token = loginRes["token"]
    headers = {"Authorization": f"Bearer {token}"}
    resAuth = client.post("/api/profile", json={
        "nguoiDungId": 999,
        "diemToan": 8.5,
        "diemVan": 8.0,
        "diemAnh": 8.5,
        "phuongThucMongMuon": "PT01"
    }, headers=headers)
    assert resAuth.status_code == 200
    saved = resAuth.json().get("hoSo", {})
    assert saved.get("nguoiDungId") == loginRes["nguoiDung"]["id"]


def test_region_preference_and_score_distinction():
    resSouth = client.post("/api/recommend", json={
        "diemToan": 8.5,
        "diemLy": 8.5,
        "diemHoa": 8.5,
        "khuVucMongMuon": "Miền Nam",
        "phuongThucMongMuon": ["PT01"],
        "danhSachToHopDaChon": ["A00"]
    })
    assert resSouth.status_code == 200
    southList = resSouth.json().get("danhSachTongHop", [])
    assert len(southList) > 0
    for item in southList:
        assert item["khuVuc"] == "Miền Nam"

    resNorth = client.post("/api/recommend", json={
        "diemToan": 8.5,
        "diemLy": 8.5,
        "diemHoa": 8.5,
        "khuVucMongMuon": "Miền Bắc",
        "phuongThucMongMuon": ["PT01"],
        "danhSachToHopDaChon": ["A00"]
    })
    assert resNorth.status_code == 200
    northList = resNorth.json().get("danhSachTongHop", [])
    assert len(northList) > 0
    for item in northList:
        assert item["khuVuc"] == "Miền Bắc"

    resHb = client.post("/api/recommend", json={
        "diemToan": 8.5,
        "diemLy": 8.0,
        "diemAnh": 8.5,
        "phuongThucMongMuon": ["PT02"],
        "danhSachToHopDaChon": ["A01"]
    })
    assert resHb.status_code == 200
    hbList = resHb.json().get("danhSachTongHop", [])
    assert len(hbList) > 0
    for item in hbList:
        assert item["coDuBao"] is False
        assert item["diemChuanDuBao"] is None
        assert item["diemChuanThamChieu"] is not None


def test_scoring_program_scale_gpa10_no_cross_scaling():
    hoSoHocSinh = {
        "diemHocBa": 8.0,
        "khuVucUuTien": "KV3",
        "doiTuongUuTien": "NONE"
    }
    kq = ScoringService.tinhDiemXetTuyenChuongTrinh(
        hoSoHocSinh=hoSoHocSinh,
        maPhuongThuc="PT02",
        maToHop="HB_GPA",
        calculationRuleId="RULE_HB_GPA10_YEAR12",
        scoreScale="GPA_10"
    )
    assert kq["hopLe"] is True
    assert kq["diemXetTuyen"] == 8.0
    assert kq["thangDiem"] in ["GPA_10", "THANG_10"]


def test_calculate_score_validation_out_of_range():
    res = client.post("/api/calculate-score", json={
        "maToHop": "A00",
        "diemMonHoc": {
            "diemToan": 99.0,
            "diemLy": 8.0,
            "diemHoa": 8.0
        }
    })
    assert res.status_code in [400, 422]


def test_wishlist_history_preserves_program_id_and_name():
    userLogin = AuthService.dangNhap("hocsinh", "hocsinh123")
    token = userLogin["token"]
    headers = {"Authorization": f"Bearer {token}"}

    saveRes = client.post("/api/wishlist/save", json={
        "danhSachNguyenVong": [
            {
                "truongDaiHocId": 1,
                "nganhHocId": 21,
                "programId": "PRG_BKA_0001",
                "tenChuongTrinh": "Kỹ thuật Thực phẩm",
                "admissionCaseId": "CASE_BKA_TP_2025",
                "toHopMonId": 1,
                "phuongThucXetTuyenId": 1,
                "diemXetTuyen": 26.5,
                "diemChuanThamChieu": 25.0,
                "doPhuHop": 85.0,
                "mucDoPhuHop": "Rất phù hợp",
                "mucDoRuiRo": "Thấp",
                "thuTuUuTien": "NV1"
            }
        ]
    }, headers=headers)
    assert saveRes.status_code == 200

    histRes = client.get("/api/wishlist-history", headers=headers)
    assert histRes.status_code == 200
    items = histRes.json()
    assert len(items) >= 1
    found = any(i.get("programId") == "PRG_BKA_0001" and i.get("tenChuongTrinh") == "Kỹ thuật Thực phẩm" for i in items)
    assert found is True


def test_forecast_info_rejection_on_mismatched_case():
    fc = mlServiceInstance.getForecastInfo(
        universityCode="BKA",
        programId="PRG_BKA_9999",
        admissionCaseId="CASE_NON_EXISTENT",
        methodCode="PT01",
        combinationCode="A00"
    )
    assert fc is None


def test_invalid_and_fake_program_id_rejected():
    loginRes = AuthService.dangNhap("hocsinh", "hocsinh123")
    token = loginRes["token"]
    headers = {"Authorization": f"Bearer {token}"}

    resFake = client.post("/api/wishlist/save", json={
        "danhSachNguyenVong": [{
            "truongDaiHocId": 42,
            "nganhHocId": 7,
            "programId": "PRG_NOT_REAL",
            "admissionCaseId": "CASE_NOT_REAL",
            "toHopMonId": 1,
            "phuongThucXetTuyenId": 1,
            "diemXetTuyen": 27.0,
            "diemChuanThamChieu": 26.0,
            "doPhuHop": 80.0,
            "mucDoPhuHop": "Phù hợp",
            "mucDoRuiRo": "Thấp",
            "thuTuUuTien": "NV1"
        }]
    }, headers=headers)
    assert resFake.status_code == 400
    assert "không tồn tại" in resFake.json().get("detail", "")

    resEmpty = client.post("/api/wishlist/save", json={
        "danhSachNguyenVong": [{
            "truongDaiHocId": 42,
            "nganhHocId": 7,
            "programId": "",
            "toHopMonId": 1,
            "phuongThucXetTuyenId": 1,
            "diemXetTuyen": 27.0,
            "diemChuanThamChieu": 26.0,
            "doPhuHop": 80.0,
            "mucDoPhuHop": "Phù hợp",
            "mucDoRuiRo": "Thấp",
            "thuTuUuTien": "NV1"
        }]
    }, headers=headers)
    assert resEmpty.status_code == 400


def test_wishlist_deduplicates_by_program():
    loginRes = AuthService.dangNhap("hocsinh", "hocsinh123")
    token = loginRes["token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/wishlist/save", json={
        "danhSachNguyenVong": [
            {
                "truongDaiHocId": 42,
                "nganhHocId": 7,
                "programId": "PRG_BKA_0069",
                "admissionCaseId": "CASE_01",
                "toHopMonId": 1,
                "phuongThucXetTuyenId": 1,
                "diemXetTuyen": 27.5,
                "diemChuanThamChieu": 26.0,
                "doPhuHop": 85.0,
                "mucDoPhuHop": "Phù hợp",
                "mucDoRuiRo": "Thấp",
                "thuTuUuTien": "NV1"
            },
            {
                "truongDaiHocId": 42,
                "nganhHocId": 7,
                "programId": "PRG_BKA_0069",
                "admissionCaseId": "CASE_02",
                "toHopMonId": 2,
                "phuongThucXetTuyenId": 1,
                "diemXetTuyen": 26.5,
                "diemChuanThamChieu": 26.0,
                "doPhuHop": 80.0,
                "mucDoPhuHop": "Phù hợp",
                "mucDoRuiRo": "Thấp",
                "thuTuUuTien": "NV2"
            }
        ]
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["soLuongDaLuu"] == 2


def test_hoc_ba_strict_rules_no_guessing():
    kq1 = ScoringService.tinhDiemXetTuyenChuongTrinh(
        {"diemHocBa": 8.0}, "PT02", "A00", "RULE_HB_COEFF2_40", "SCALE_40"
    )
    assert kq1["hopLe"] is False, "Không được tự ý nhân GPA * 4 khi thiếu điểm thành phần"

    kq2 = ScoringService.tinhDiemXetTuyenChuongTrinh(
        {"diemHocBa": 8.0}, "PT02", "A00", "RULE_NOT_EXIST", "SCALE_30"
    )
    assert kq2["hopLe"] is False, "Quy tắc không tồn tại phải bị từ chối"

    kq3 = ScoringService.tinhDiemXetTuyenChuongTrinh(
        {"diemToan": 9.0, "diemAnh": 7.0}, "PT02", "D01", "RULE_HB_GPA10_YEAR12", "GPA_10"
    )
    assert kq3["hopLe"] is False, "Không được tự tính trung bình 2 môn thành GPA"


def test_land_management_not_mapped_to_ai():
    from csvDatabase import inferNganhIdFromName
    inferred = inferNganhIdFromName("Quản lý đất đai")
    assert inferred != 6, "Quản lý đất đai không được gán nhầm vào ngành Trí tuệ nhân tạo (ID=6)"


def test_combination_matching_exact_token_only():
    fc = mlServiceInstance.getForecastInfo(
        universityCode="BKA",
        programId="PRG_BKA_0001",
        methodCode="PT01",
        combinationCode="A0"
    )
    assert fc is None, "Mã tổ hợp 'A0' không được khớp chuỗi con của 'A00'"


def test_calculate_score_nan_rejected():
    resStr = client.post("/api/calculate-score", json={
        "maToHop": "A00",
        "diemMonHoc": {"diemToan": "NaN", "diemLy": 8.0, "diemHoa": 8.0}
    })
    assert resStr.status_code in [400, 422], "API phải từ chối điểm 'NaN' bằng mã 4xx"


def test_portfolio_quota_and_diversity_constraints():
    res = client.post("/api/recommend", json={
        "diemToan": 9.0, "diemLy": 8.5, "diemHoa": 9.0,
        "khuVucUuTien": "KV3", "doiTuongUuTien": "NONE",
        "phuongThucMongMuon": ["PT01"],
        "danhSachToHopDaChon": ["A00"]
    })
    assert res.status_code == 200
    data = res.json()
    assert data["thanhCong"] is True
    wishes = data["danhSachTongHop"]
    assert len(wishes) == 20

    thuSuc = [w for w in wishes if w["nhomNguyenVong"] == "Thử sức"]
    vuaSuc = [w for w in wishes if w["nhomNguyenVong"] == "Vừa sức"]
    anToan = [w for w in wishes if w["nhomNguyenVong"] == "An toàn"]
    assert len(thuSuc) == 5, f"Số lượng Thử sức: {len(thuSuc)}, mong đợi 5"
    assert len(vuaSuc) == 10, f"Số lượng Vừa sức: {len(vuaSuc)}, mong đợi 10"
    assert len(anToan) == 5, f"Số lượng An toàn: {len(anToan)}, mong đợi 5"

    uniCounts = {}
    for w in wishes:
        uId = w.get("truongDaiHocId")
        uniCounts[uId] = uniCounts.get(uId, 0) + 1
    for uId, cnt in uniCounts.items():
        assert cnt <= 3, f"Trường ĐH {uId} có {cnt} chương trình, vượt trần đa dạng hóa (tối đa 3)"

    anToanDeltas = [w["delta"] for w in anToan]
    avgAnToanDelta = sum(anToanDeltas) / len(anToanDeltas)
    assert avgAnToanDelta < 4.0, f"Delta trung bình nhóm An toàn ({avgAnToanDelta}) quá cao, lãng phí điểm xét tuyển"


def test_low_score_candidacy_warning():
    res = client.post("/api/recommend", json={
        "diemToan": 4.5, "diemLy": 4.5, "diemHoa": 4.5,
        "khuVucUuTien": "KV3", "doiTuongUuTien": "NONE",
        "phuongThucMongMuon": ["PT01"],
        "danhSachToHopDaChon": ["A00"]
    })
    assert res.status_code == 200
    data = res.json()
    msg = data.get("thongBao", "")
    assert ("rủi ro" in msg.lower() or "thấp" in msg.lower() or "cân nhắc" in msg.lower() or "cẩn trọng" in msg.lower()), (
        f"Thông báo cho thí sinh điểm thấp không nêu rõ rủi ro: '{msg}'"
    )


def test_probability_based_grouping_logic():
    res10 = mlServiceInstance.predictSuitability(
        studentScore=8.4,
        benchmarkScore=7.0,
        scoreScale="GPA_10",
        coDuBao=False,
        namThamChieu=2025
    )
    assert res10["nhomNguyenVong"] == "An toàn", f"Delta 1.4 thang 10 có P > 99% phải là An toàn, thực tế: {res10['nhomNguyenVong']}"

    res40 = mlServiceInstance.predictSuitability(
        studentScore=31.5,
        benchmarkScore=30.0,
        scoreScale="SCALE_40",
        coDuBao=False,
        namThamChieu=2025
    )
    assert res40["nhomNguyenVong"] == "Vừa sức", f"P ~ 73% thang 40 phải là Vừa sức (chưa đạt ngưỡng An toàn 80%), thực tế: {res40['nhomNguyenVong']}"


def test_persistent_jwt_secret_file():
    secret_path = os.path.join(os.path.dirname(__file__), "data", ".jwt_secret")
    assert not os.path.exists(secret_path)
    assert len(AuthService.SECRET_KEY) >= 32


def test_auto_gpa_conversion_for_standard_hoc_ba():
    hoSoOnlyGpa = {
        "diemHocBa": 8.0,
        "khuVucUuTien": "KV3",
        "doiTuongUuTien": "NONE"
    }
    res = ScoringService.tinhDiemXetTuyenChuongTrinh(
        hoSoOnlyGpa,
        "PT02",
        "A00",
        "RULE_HB_STD_30",
        "SCALE_30"
    )
    assert res["hopLe"] is True, "Phải quy đổi ước tính từ GPA sang thang 30 cho phương thức học bạ chuẩn"
    assert res["diemTho"] == 24.0, f"Điểm thô mong đợi: 24.0, nhận được: {res['diemTho']}"
    assert res.get("uocTinhTuGpa") is True


def test_tuition_estimation_and_fields():
    from admissionService import AdmissionService
    hpMilitary = AdmissionService.traCuuHocPhi(uni={"maTruong": "STS", "tenTruong": "Trường Sĩ quan Kỹ thuật Quân sự (Vin-Hem Pich)"})
    assert hpMilitary["trangThaiHocPhi"] == "VERIFIED"
    assert hpMilitary["hocPhiKy"] == 0.0
    assert "Bao cấp" in hpMilitary["hocPhiText"]

    hpPrivate = AdmissionService.traCuuHocPhi(uni={"maTruong": "FPT", "tenTruong": "Trường Đại học FPT"})
    assert hpPrivate["hocPhiNam"] > 35000000.0

    hpPublic = AdmissionService.traCuuHocPhi(programId="PRG_BKA_0001", uni={"maTruong": "BKA", "tenTruong": "Đại học Bách Khoa"})
    assert hpPublic["hocPhiNam"] > 0.0

    hpMultiNoProg = AdmissionService.traCuuHocPhi(uni={"maTruong": "BKA", "tenTruong": "Đại học Bách Khoa"})
    assert hpMultiNoProg["trangThaiHocPhi"] == "UNVERIFIED"
    assert hpMultiNoProg["hocPhiNam"] is None

    hpUnknown = AdmissionService.traCuuHocPhi(uni={"maTruong": "UNKNOWN_UNI", "tenTruong": "Trường Không Xác Định"})
    assert hpUnknown["trangThaiHocPhi"] == "UNVERIFIED"
    assert hpUnknown["hocPhiNam"] is None
    assert "Chưa có thông tin" in hpUnknown["hocPhiText"]

    res = client.post("/api/recommend", json={
        "diemToan": 8.5, "diemLy": 8.0, "diemAnh": 8.0,
        "khuVucUuTien": "KV3", "doiTuongUuTien": "NONE",
        "phuongThucMongMuon": ["PT01"],
        "danhSachToHopDaChon": ["A01"]
    })
    assert res.status_code == 200
    data = res.json()
    firstWish = data["danhSachTongHop"][0]
    assert "hocPhiKy" in firstWish
    assert "hocPhiNam" in firstWish
    assert "hocPhiUocTinh" in firstWish
    assert "chiTieu" in firstWish
    assert "trangThaiHocPhi" in firstWish
    assert "nguonMinhChung" in firstWish


def test_hoc_ba_multiple_combinations():
    for comb in ["B00", "C00", "D07"]:
        res = client.post("/api/recommend", json={
            "diemHocBa": 8.8,
            "khuVucUuTien": "KV3",
            "doiTuongUuTien": "NONE",
            "phuongThucMongMuon": ["PT02"],
            "danhSachToHopDaChon": [comb]
        })
        assert res.status_code == 200
        data = res.json()
        assert data["thanhCong"] is True
        assert len(data["danhSachTongHop"]) > 0
        assert data["danhSachTongHop"][0]["maToHop"] == comb


def test_tuition_filters():
    resUnder20 = client.post("/api/recommend", json={
        "diemToan": 8.5, "diemLy": 8.0, "diemHoa": 8.0,
        "khuVucUuTien": "KV3", "doiTuongUuTien": "NONE",
        "phuongThucMongMuon": ["PT01"],
        "danhSachToHopDaChon": ["A00"],
        "mucHocPhi": "under_20m"
    })
    assert resUnder20.status_code == 200
    dataUnder = resUnder20.json()
    for item in dataUnder.get("danhSachTongHop", []):
        assert item["hocPhiNam"] <= 20000000.0
    assert "danhSachCanKiemTraHocPhi" in dataUnder
    for ckItem in dataUnder.get("danhSachCanKiemTraHocPhi", []):
        assert ckItem["trangThaiHocPhi"] == "UNVERIFIED" or ckItem["hocPhiNam"] is None


def test_tdtu_program_tuition_and_budget_separation():
    tdtuPrograms = CsvDatabase.findWhere("hocPhi", {"maTruong": "DTT"})
    assert len(tdtuPrograms) > 0
    stdProgs = [p for p in tdtuPrograms if "tiếng Anh" not in p["tenChuongTrinh"] and "song bằng" not in p["tenChuongTrinh"] and "Phân hiệu" not in p["tenChuongTrinh"]]
    engProgs = [p for p in tdtuPrograms if "tiếng Anh" in p["tenChuongTrinh"]]
    assert len(stdProgs) > 0
    assert len(engProgs) > 0
    assert any(float(p["hocPhiToiDa"]) <= 35000000.0 for p in stdProgs)
    assert any(float(p["hocPhiToiDa"]) >= 70000000.0 for p in engProgs)
    for p in tdtuPrograms:
        assert "tdtu.edu.vn" in p.get("urlNguon", "")


def test_cors_origin_security():
    resEvil = client.options("/api/combinations", headers={
        "Origin": "https://evil.example",
        "Access-Control-Request-Method": "GET"
    })
    allowOrigin = resEvil.headers.get("access-control-allow-origin")
    assert allowOrigin != "https://evil.example"
    assert allowOrigin != "*"


def test_user_registration_email_and_phone_validation():
    resBadEmail = client.post("/api/auth/register", json={
        "tenDangNhap": "testuser_bad",
        "matKhau": "password123",
        "hoTen": "Test User",
        "email": "not-an-email",
        "soDienThoai": "0988888888"
    })
    assert resBadEmail.status_code == 422 or (resBadEmail.status_code == 400 and not resBadEmail.json().get("thanhCong"))


def test_data_architecture_tuition_relational_integrity():
    diemChuanRecords = CsvDatabase.readAll("diemChuan")
    hocPhiRecords = CsvDatabase.readAll("hocPhi")
    assert len(hocPhiRecords) == 10979
    hpProgramIds = {r["programId"] for r in hocPhiRecords if r.get("programId")}
    assert len(hpProgramIds) == 10979
    dcProgramIds = {r["programId"] for r in diemChuanRecords if r.get("programId")}
    assert len(dcProgramIds) > 0
    assert dcProgramIds.issubset(hpProgramIds)


def test_distinct_programs_in_same_university_tuition():
    from admissionService import AdmissionService
    hpStd = AdmissionService.traCuuHocPhi(programId="PRG_BKA_0001", uni={"maTruong": "BKA"})
    hpAdv = AdmissionService.traCuuHocPhi(programId="PRG_BKA_0003", uni={"maTruong": "BKA"})
    assert hpStd["hocPhiToiDa"] <= 30000000.0
    assert hpAdv["hocPhiToiDa"] >= 35000000.0
    assert hpStd["hocPhiToiDa"] != hpAdv["hocPhiToiDa"]


def test_hoc_ba_exact_subject_scores_prioritization():
    from scoringService import ScoringService
    hoSoExact = {
        "diemToan": 9.0,
        "diemLy": 9.5,
        "diemHoa": 8.5,
        "diemHocBa": 8.0,
        "khuVucUuTien": "KV3",
        "doiTuongUuTien": "NONE"
    }
    res = ScoringService.tinhDiemXetTuyenChuongTrinh(
        hoSoExact,
        "PT02",
        "A00",
        "RULE_HB_STD_30",
        "SCALE_30"
    )
    assert res["hopLe"] is True
    assert res["diemTho"] == 27.0
    assert res.get("uocTinhTuGpa") is False


def test_tuition_budget_match_status_distinction():
    from admissionService import AdmissionService
    hoSo = {
        "diemToan": 9.0,
        "diemLy": 9.0,
        "diemAnh": 9.0,
        "phuongThuc": "PT01",
        "maToHop": "A01",
        "mucHocPhi": 35000000.0,
        "khuVucUuTien": "KV3",
        "doiTuongUuTien": "NONE"
    }
    res = AdmissionService.deXuatNguyenVong(hoSo)
    assert "danhSachCanKiemTraHocPhi" in res
    for item in res.get("danhSachTongHop", []):
        if item.get("trangThaiHocPhi") == "VERIFIED":
            assert item.get("trangThaiHocPhiPhuHop") == "XAC_MINH_PHU_HOP"
        elif item.get("trangThaiHocPhi") == "PROJECTED":
            assert item.get("trangThaiHocPhiPhuHop") == "DU_KIEN_PHU_HOP"
            assert item.get("canhBaoTaiChinh") is not None
            assert item.get("phuongPhapSoSanh") == "NGUONG_TRAN_AN_TOAN"


def test_no_cross_program_tuition_fallback():
    from admissionService import AdmissionService
    hpUnknown = AdmissionService.traCuuHocPhi(
        programId="PRG_BKA_NONEXISTENT",
        uni={"maTruong": "BKA"}
    )
    assert hpUnknown["trangThaiHocPhi"] == "UNVERIFIED"
    assert hpUnknown["hocPhiToiDa"] is None
