# Tuyển Sinh+ (Hệ Thống Hỗ Trợ Ra Quyết Định Tuyển Sinh Đại Học)

Tuyển Sinh+ là hệ thống hỗ trợ thí sinh và phụ huynh tra cứu điểm chuẩn, tính điểm xét tuyển chính xác theo quy chế, và xây dựng danh mục 20 nguyện vọng tham khảo theo mô hình phân tầng rủi ro (25% Thử sức / 50% Vừa sức / 25% An toàn).

---

## 1. Yêu Cầu Môi Trường
- **Python**: 3.10 trở lên
- **Hệ điều hành**: Windows / Linux / macOS
- **Trình duyệt**: Chrome, Edge, Firefox, Safari

---

## 2. Cài Đặt & Khởi Chạy

### Bước 1: Cài đặt các gói phụ thuộc
```bash
pip install -r requirements.txt
```

### Bước 2: Khởi chạy máy chủ Web
```bash
python app.py
```
Máy chủ sẽ khởi động tại: **`http://127.0.0.1:8000`** (mở trình duyệt để sử dụng giao diện).

---

## 3. Kiểm Thử & Đánh Giá Độc Lập

### Chạy toàn bộ Unit & Integration Tests (39 bài kiểm thử):
```bash
python -m pytest testApp.py
```

### Chạy Đánh giá Hệ thống Gợi ý (DSS RecSys Evaluation Benchmark):
```bash
python evaluate_recsys.py
```
Báo cáo đánh giá độc lập được xuất tại: `data/reports/recsys_evaluation_report.json`.

---

## 4. Cấu Trúc Mã Nguồn

```text
├── app.py                  # FastAPI Application: định tuyến API & phục vụ giao diện tĩnh
├── admissionService.py     # Nghiệp vụ phân tầng danh mục gợi ý (5 Thử sức / 10 Vừa sức / 5 An toàn)
├── scoringService.py       # Quy tắc tính điểm xét tuyển (THPT, Học bạ, điểm ưu tiên suy giảm)
├── mlService.py            # Mô hình Random Forest, dự báo điểm chuẩn và tính xác suất Gauss
├── csvDatabase.py          # Lớp truy xuất cơ sở dữ liệu CSV kèm bộ nhớ đệm tối ưu
├── authService.py          # Xác thực JWT với khóa bí mật lưu trữ an toàn
├── schemas.py              # Pydantic Schemas xác thực dữ liệu đầu vào
├── evaluate_recsys.py      # Benchmark đánh giá độc lập danh mục gợi ý
├── train.py                # Kịch bản tái tạo huấn luyện mô hình Machine Learning
├── testApp.py              # Bộ kiểm thử tự động (43 bài kiểm thử bao phủ toàn diện)
├── data/
│   ├── csv/                # Bảng dữ liệu vận hành hệ thống (chuẩn hóa quan hệ 3NF)
│   ├── metadata/           # Siêu dữ liệu chương trình đào tạo & trường ĐH
│   ├── models/             # Trọng số mô hình Random Forest (.joblib)
│   └── reports/            # Báo cáo đánh giá và dữ liệu kiểm toán
└── frontend/               # Giao diện người dùng web (HTML5, Vanilla CSS, JS)
```

---

## 5. Kiến Trúc Dữ Liệu Tuyển Sinh Đa Chiều & Chuẩn Hóa Quan Hệ (3NF)

Hệ thống Tuyển Sinh+ được xây dựng trên nền tảng mô hình dữ liệu tuyển sinh toàn quốc đa chiều, chuẩn hóa theo dạng chuẩn 3 (3NF) nhằm đảm bảo tính toàn vẹn và nhất quán trên toàn bộ 359 cơ sở đại học và học viện:

### Ba Trụ Cột Dữ Liệu Nền Tảng Thiết Kế Từ Ban Đầu:
1. **Trụ cột Điểm chuẩn Lịch sử & Chuỗi thời gian (`diemChuan.csv` - 26,474 bản ghi):**
   - Quản lý điểm trúng tuyển chính thức 2020–2026 cho 2 phương thức trọng yếu: Xét kết quả thi THPT (PT01) và Xét học bạ THPT (PT02).
   - Mỗi bản ghi xác định bởi: Cơ sở đào tạo, Mã chương trình (`programId`), Tổ hợp môn (`toHopMonId`), Phương thức xét tuyển (`phuongThucXetTuyenId`), Quy tắc tính điểm và Thang điểm chuẩn hóa (Thang 30 / Thang 40 / Thang 100).

2. **Trụ cột Tài chính & Biểu phí Chương trình Đào tạo (`hocPhi.csv` - 10,979 chương trình):**
   - Quản lý biểu phí đại học toàn quốc phân cấp theo: `Trường / Cơ sở` → `Chương trình đào tạo` → `Năm / Khóa áp dụng` → `Biểu phí & Đơn vị tính`.
   - Ánh xạ trực tiếp 1-1 với toàn bộ 10,979 chương trình đào tạo (`programId`) trên hệ thống.
   - Thẩm định minh bạch 4 trạng thái pháp lý:
     + `VERIFIED`: Đã xác minh có nguồn đề án/công bố chính thức hoặc chính sách nhà nước (TDTU, BKA, NEU, FTU, UEH, FPT, RMIT, chính sách bao cấp học viên quân sự/công an, Nghị định 116 đào tạo giáo viên).
     + `PROJECTED`: Biểu phí dự kiến theo đề án tuyển sinh hoặc thông báo của trường (kèm cảnh báo tài chính và so sánh theo ngưỡng trần an toàn).
     + `PER_CREDIT`: Mức phí tính theo đơn giá tín chỉ đào tạo.
     + `UNVERIFIED`: Chưa có công bố xác minh từ đề án trường (hiển thị nhãn minh bạch, không tự ý gán số tiền 0đ hay số liệu giả lập, tự động đưa vào danh mục cần kiểm tra khi lọc ngân sách).

3. **Trụ cột Danh mục Chuẩn Quốc gia:**
   - `truongDaiHoc.csv`: 359 cơ sở đại học, học viện, phân hiệu đại học vùng và trường sĩ quan toàn quốc.
   - `nganhHoc.csv`: Danh mục 44 ngành/nhóm ngành đào tạo cấp IV theo quy chuẩn Bộ GD&ĐT.
   - `toHopMon.csv`: 14 tổ hợp môn chuẩn (A00, A01, A02, B00, B08, C00, C01, C02, C19, D01, D07, D09, D10, D14).
   - `phuongThucXetTuyen.csv`: Các phương thức tuyển sinh chính thức quy định.

### Lý Do Thiết Kế Phân Tách Thực Thể Học Phí (Relational Normalization Rationale):
- **Chuẩn hóa dạng 3 (3NF):** Trong nghiệp vụ tuyển sinh, học phí là thuộc tính phụ thuộc vào bản thân **Chương trình đào tạo và Khóa học** (`Program × Cohort`), chứ không phụ thuộc vào từng tổ hợp môn hay phương thức xét tuyển. Một chương trình đào tạo thường xét tuyển bằng 3–4 tổ hợp môn khác nhau nhưng có chung một biểu phí.
- **Tránh dư thừa và bất nhất dữ liệu (Zero Redundancy):** Việc chuẩn hóa biểu phí vào bảng thực thể `hocPhi` riêng biệt liên kết qua khóa ngoại `programId` giúp hệ thống không phải lặp lại dữ liệu học phí hàng chục nghìn lần, đồng thời đảm bảo mọi cập nhật từ đề án tài chính đều được đồng bộ tức thì trên cả trang tra cứu, thẻ gợi ý, và hộp thoại chi tiết.
- **Phân tách chính xác các phân hệ đào tạo cùng trường:** Cho phép quản lý độc lập các hệ đào tạo trong cùng một trường đại học (Điển hình ĐH Tôn Đức Thắng: hệ tiêu chuẩn 28–35 triệu, hệ bằng tiếng Anh 70–85 triệu, hệ liên kết quốc tế 80–100 triệu, phân hiệu Khánh Hòa 20–24 triệu).
- **Loại bỏ triệt để Fallback xuyên chương trình:** Truy vấn học phí bắt buộc căn cứ trên `programId`. Tuyệt đối không lấy dòng đầu tiên của trường để gán cho chương trình khác khi thiếu dữ liệu riêng.

### Kiểm Toán Quy Trình Thu Thập Dữ Liệu (Data Collection & Audit Pipeline):
- **Theo dõi tiến độ 3 trụ cột đồng thời (`data/metadata/collection_status_verified.csv`):** Bảng kiểm toán quản lý song song 3 trạng thái thu thập (`thpt_collection_status`, `hoc_ba_collection_status`, `tuition_collection_status`) và số lượng bản ghi của 258 cơ sở cốt lõi.
- **Truy xuất nguồn gốc minh chứng (`data/metadata/sources_verified.csv` - 254 nguồn):** Toàn bộ các đề án tài chính, quyết định học phí và văn bản quy phạm pháp luật đều được lưu trữ URL chính thức, cơ quan ban hành, thời điểm thu thập và mã băm SHA-256.
- **Toàn vẹn khóa ngoại 100%:** 10,979/10,979 mã chương trình (`programId`) trong `hocPhi.csv` khớp hoàn toàn với danh mục chương trình quốc gia và bao phủ 100% các chương trình có điểm chuẩn trong `diemChuan.csv`.

---

## 6. Lưu Ý Về Dữ Liệu & Phạm Vi Sử Dụng
- Danh sách nguyện vọng do hệ thống đề xuất mang tính chất **tham khảo** nhằm hỗ trợ ra quyết định.
- Thí sinh cần thực hiện đăng ký chính thức trên Cổng thông tin tuyển sinh của Bộ Giáo dục & Đào tạo theo đúng thời gian và quy chế hiện hành.
