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

### Chạy toàn bộ Unit & Integration Tests (37 bài kiểm thử):
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
├── testApp.py              # Bộ kiểm thử tự động
├── data/
│   ├── csv/                # Bảng dữ liệu vận hành hệ thống
│   ├── metadata/           # Siêu dữ liệu chương trình đào tạo & trường ĐH
│   ├── models/             # Trọng số mô hình Random Forest (.joblib)
│   └── reports/            # Báo cáo đánh giá và dữ liệu kiểm toán
└── frontend/               # Giao diện người dùng web (HTML5, Vanilla CSS, JS)
```

---

## 5. Lưu Ý Về Dữ Liệu & Phạm Vi Sử Dụng
- Danh sách nguyện vọng do hệ thống đề xuất mang tính chất **tham khảo** nhằm hỗ trợ ra quyết định.
- Thí sinh cần thực hiện đăng ký chính thức trên Cổng thông tin tuyển sinh của Bộ Giáo dục & Đào tạo theo đúng thời gian và quy chế hiện hành.
