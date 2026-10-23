Hệ hỗ trợ quyết định gợi ý nguyện vọng đại học cho học sinh THPT dựa trên dự báo điểm chuẩn bằng Random Forest, triển khai qua REST API

Hệ thống tính điểm xét tuyển, tra cứu điểm chuẩn và gợi ý tối đa 20 nguyện vọng theo ba nhóm rủi ro: Thử sức, Vừa sức, An toàn. Dự báo điểm chuẩn 2027 bằng mô hình Random Forest kèm khoảng sai số hiệu chỉnh. Kết quả mang tính tham khảo, thí sinh đăng ký chính thức trên Cổng của Bộ GD&ĐT.

1. Môi trường

Python: 3.10 trở lên (đã kiểm thử trên 3.14.5).

scikit-learn: 1.9.0 (bắt buộc để đọc model data/models/rf_thpt_best.joblib).

Thư viện phụ trợ: FastAPI, Uvicorn, Pydantic 2, pandas, numpy, joblib, httpx.

Trình duyệt: Chrome, Edge, Firefox, Safari.

2. Cài đặt và vận hành

Cài đặt: pip install -r requirements.txt

Chạy hệ thống: python app.py (truy cập [http://127.0.0.1:8000](http://127.0.0.1:8000))

Tạo quản trị viên: python authService.py create-admin --username <ten> --password <mat-khau>

Biến môi trường chính (tùy chọn trong .env):

ENV: development / production.

DSS_SECRET_KEY: Khóa ký JWT.

DSS_TARGET_YEAR: 2027.

DSS_REFERENCE_YEAR: 2026.

DSS_MAX_REFERENCE_AGE: 1 (chỉ lấy mốc từ 2025 trở đi; đặt -1 để bỏ giới hạn).

GEMINI_API_KEY, GEMINI_MODEL (gemini-3.8-flash), GEMINI_TIMEOUT_SECONDS (15), GEMINI_RATE_LIMIT_PER_MINUTE (10).

Trợ lý Gemini (geminiService.py):

POST /api/explain: Diễn giải nguyện vọng bằng số liệu cho phép, có cache 512 mục và chế độ dự phòng.

POST /api/chat: Chatbot function calling qua 4 hàm nội bộ; tự động che email, số điện thoại. Giới hạn tần suất gọi theo IP (mã 429 khi vượt ngưỡng).

3. Kiểm thử, huấn luyện và đánh giá

Kiểm thử: thực hiện thủ công trên giao diện web và trang tài liệu API http://127.0.0.1:8000/docs.

Đánh giá hệ gợi ý: python evaluate_recsys.py

Backtest hệ gợi ý: python backtestRecsys.py (tùy chọn --max-age)

So sánh biến thể mô hình: python train.py --compare-only

Huấn luyện lại toàn bộ: python train.py

4. Kiến trúc hệ thống

Giao diện: HTML, CSS, JavaScript thuần (thư mục frontend/).

Backend (FastAPI):

scoringService.py: Tính điểm tổ hợp, điểm ưu tiên (giảm dần từ 22.5), quy đổi học bạ/ĐGNL/ĐGTD.

admissionService.py: Lọc, chấm điểm, phân nhóm rủi ro, chọn 20 nguyện vọng.

mlService.py: Tải model, nạp bảng dự báo 2027, tính chỉ số thuận lợi Φ(delta / σ) với khoảng tin cậy 80% (±2.2 điểm). Phân nhóm: An toàn (≥ 80%), Vừa sức (≥ 40%), Thử sức (≥ 15%).

authService.py: Xác thực PBKDF2, cấp JWT, khóa tài khoản sau 5 lần đăng nhập sai.

csvDatabase.py: Đọc ghi dữ liệu CSV có cache và khóa đồng thời.

Pipeline dữ liệu ngoại tuyến: build_dataset.py -> train.py -> evaluate_recsys.py.

5. Danh sách API chính

Xác thực: POST /api/auth/register, POST /api/auth/login, GET /api/auth/me.

Nghiệp vụ tuyển sinh: POST /api/calculate-score, POST /api/recommend, GET /api/model-info, POST /api/explain, POST /api/chat.

Hồ sơ: POST /api/profile, POST /api/wishlist/save, GET /api/wishlist-history.

Danh mục và tra cứu: GET /api/compare-methods/{truongId}/{nganhId}, GET /api/combinations, GET /api/methods, GET /api/regions, GET /api/university-types, GET /api/universities, GET /api/majors, GET /api/benchmarks, GET /api/explore-benchmarks.

Quản trị: Quản lý danh mục (POST/DELETE combinations, methods, benchmarks), thống kê hệ thống (GET /api/admin/stats), quản lý người dùng (GET/POST/PUT/DELETE /api/admin/users).

6. Dữ liệu

Dữ liệu CSV nội bộ: diemChuan.csv (26.474 bản ghi từ 2020–2026), truongDaiHoc.csv (359 trường), nganhHoc.csv (44 nhóm ngành), hocPhi.csv (11.054 chương trình), toHopMon.csv (33 tổ hợp).

Nguồn thu thập (254 nguồn xác thực): Tuyensinh247 (186 nguồn), VnExpress/Bộ GD&ĐT (53 nguồn), đề án trường và văn bản nhà nước (15 nguồn).

Phân chia tập dữ liệu: Huấn luyện ≤ 2024, Hiệu chỉnh (Validation) 2025, Kiểm thử (Test) 2026, Dự báo 2027.

7. Hiệu năng mô hình và Backtest

Kiểm thử 2026: Mô hình lai đạt MAE 1.041, RMSE 1.543, R² 0.872 (vượt nhẹ Lag-1 có MAE 1.056, nhưng không có ý nghĩa thống kê do khoảng tin cậy chứa 0). Khoảng tin cậy 80% đạt độ phủ thực tế 87.6%.

Dò tham số mô hình lai: w = 0.15, c = -0.18 chọn theo MAE validation 2025.

Backtest hệ gợi ý 2026 (với --max-age 0): Khớp điểm thật đạt 90.7%, Brier score đạt 0.132. Tỷ lệ đỗ thực tế: nhóm An toàn 96.5%, Vừa sức 82.3%, Thử sức 37.7%, Rủi ro cao 8.1%.

8. Giới hạn hệ thống

Dự báo chỉ áp dụng cho 1.113/3.972 bản ghi (42 trường); các bản ghi còn lại dùng điểm năm trước hoặc điểm đã công bố.

Khi giới hạn năm tham chiếu từ 2025, PT01 thu hẹp còn 45 trường (1.263 chương trình); PT02 còn 161 trường.

Chưa có dữ liệu điểm chuẩn để gợi ý cho phương thức ĐGNL/ĐGTD (mới hỗ trợ hàm quy đổi).

Chưa thể backtest phương thức học bạ (PT02) do sai lệch mã chương trình qua các năm.

Lưu trữ hoàn toàn trên file CSV, bộ nhớ đệm và giới hạn lượt gọi AI sẽ làm mới khi khởi động lại ứng dụng.