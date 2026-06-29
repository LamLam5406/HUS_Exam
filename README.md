# HỆ THỐNG PHÂN LOẠI VÀ LƯU TRỮ ĐỀ THI (JAMSTACK ARCHITECTURE)

## I. TỔNG QUAN KIẾN TRÚC
Hệ thống sử dụng kiến trúc Web Tĩnh (Jamstack) kết hợp với đường ống dữ liệu AI tự động.
1. **Data Ingestion:** Chrome Extension cào dữ liệu từ Facebook.
2. **AI Processing:** Python (OpenCV + Tesseract + Sklearn) xử lý ảnh, phân loại văn bản, đóng gói PDF và xuất ra file `database.json`.
3. **Frontend Delivery:** React đọc trực tiếp file `database.json` để hiển thị và lọc kết quả siêu tốc trên trình duyệt.

---

## II. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
exam-classification-system/
│
├── 1-scraper-extension/       # MODULE 1: CHROME EXTENSION (Thu thập dữ liệu)
│   ├── manifest.json          # Cấu hình extension
│   ├── background.js          # Quản lý trạng thái tải (chống trùng lặp)
│   ├── content.js             # Nhúng vào DOM Facebook lấy post_id, caption, image_urls
│   └── popup/                 # Giao diện icon của extension
│       ├── index.html
│       └── script.js
│
├── 2-ai-data-pipeline/        # MODULE 2: AI WORKER (Xử lý & Xuất dữ liệu)
│   ├── requirements.txt       # Các thư viện Python (opencv-python, pytesseract, scikit-learn, pymupdf)
│   ├── main.py                # File khởi chạy luồng xử lý
│   ├── config.json            # Cấu hình đường dẫn, API keys (nếu có)
│   ├── src/
│   │   ├── api_server.py      # API nội bộ (FastAPI/Flask) nhận dữ liệu từ Extension
│   │   ├── drive_upload.py    # Đẩy các file PDF lên Drive
│   │   ├── ocr_engine.py      # Tesseract: Trích xuất chữ từ ảnh
│   │   ├── classifier.py      # Sklearn: Phân loại môn học, Regex lấy năm
│   │   └── pdf_builder.py     # Nối ảnh thành PDF
│   └── output/                # Thư mục chứa file PDF và file database.json xuất ra
│       └── database.json      # File lõi chứa toàn bộ dữ liệu metadata
│
├── 3-react-frontend/          # MODULE 3: WEB TĨNH (Hiển thị)
│   ├── package.json
│   ├── public/                
│   │   └── data/              
│   │       └── database.json  # File JSON được copy từ thư mục output của AI sang đây
│   └── src/
│       ├── components/        # UI: SearchBar, FilterSidebar, ExamCard, PDFViewer
│       ├── pages/             # Layout chính của trang web
│       ├── hooks/             # useExamData.js (đọc file JSON và xử lý mảng)
│       ├── utils/             # Các hàm lọc (filter), sắp xếp (sort)
│       └── App.jsx            
│
└── README.md                  # Hướng dẫn setup toàn dự án
```

---

### III. QUY TRÌNH THỰC HIỆN TỪNG BƯỚC

#### Giai đoạn 1: Thu thập Dữ liệu (Tuần 1 - 2)
* **Mục tiêu:** Lấy được dữ liệu thô bán tự động.
* **Công việc:**
  * Viết Chrome Extension đơn giản.
  * Lập trình `content.js` để tìm và bóc tách các thẻ chứa ảnh và caption trên group Facebook.
  * Xây dựng API nội bộ (Python FastAPI) để Extension gửi dữ liệu thô về.
* **Nghiệm thu:** Nhấn nút trên Extension, Terminal của Python in ra được thông tin bài đăng.

---

#### Giai đoạn 2: Bóc tách Siêu dữ liệu (Metadata) (Tuần 3 - 5)
* **Mục tiêu:** Trích xuất tự động và chuẩn hóa 4 trường thông tin cốt lõi (Tên môn, Mã môn, Học kỳ, Năm học) từ văn bản và hình ảnh.
* **Công việc:**
  * Xây dựng bộ quy tắc Regex và Keyword Matching để quét nhanh nội dung văn bản (caption), bắt các định dạng chuẩn của năm học, học kỳ, và hashtag môn học.
  * Tích hợp mô hình AI Vision (Qwen2-VL-2B-Instruct) kết hợp kỹ thuật Lazy Loading (chỉ nạp vào GPU khi cần) để đọc và trích xuất dữ liệu trực tiếp từ ảnh nếu phương pháp Regex chưa lấy đủ thông tin thiết yếu.
  * Viết bộ lọc chống ảo giác (Post-Processing) cho kết quả JSON trả về từ AI để đảm bảo định dạng các trường dữ liệu hợp lệ.
  * Sử dụng kỹ thuật Fuzzy Matching (thông qua thư viện difflib) để đối chiếu và chuẩn hóa tên môn, mã môn dựa trên danh mục từ điển chuẩn trong file Excel (subject.xlsx).
Nghiệm thu: Luồng xử lý kép (Dual-Stream: Regex -> AI Vision -> Excel Validation) hoạt động ổn định, trả về được một chuỗi Metadata chuẩn hóa khi đầu vào là văn bản và URL hình ảnh.

#### Giai đoạn 3: Phân loại kịch bản, Đóng gói và Lưu trữ (Tuần 6 - 8)
* **Mục tiêu:** Nhận diện dữ liệu trùng lặp, tự động gộp file PDF, tải lên Cloud và lưu vào Cơ sở dữ liệu (CSDL).
* **Công việc:**
  * Xây dựng thuật toán tạo "Vân tay" (Fingerprint định dạng: Mã Môn|Tên Môn|Học Kỳ|Năm Học) để định danh duy nhất cho từng đề thi, phục vụ việc phát hiện trùng lặp.
  * Thiết kế luồng phân loại 3 kịch bản xử lý thực tế:
    * Trường hợp A: Gộp ảnh và tạo lại PDF cho các bài đăng cùng nguồn (đề thi bị ngắt quãng).
    * Trường hợp B: Bỏ qua dữ liệu để chống rác nếu phát hiện đề thi trùng lặp nhưng khác nguồn đăng.
    * Trường hợp C: Tạo PDF mới hoàn toàn cho đề thi chưa từng xuất hiện.
  * Tích hợp module (pdf_builder) để chuyển đổi danh sách các URL ảnh thành một file PDF duy nhất.
  * Kết nối API (drive_uploader) để tải tự động các file PDF đã tạo lên Google Drive và lấy liên kết (URL) lưu trữ.
  * Xây dựng cơ chế cập nhật trạng thái liên tục xuống ổ cứng, lưu 6 trường thông tin vào CSDL (database.json) và ghi nhận lịch sử xử lý (processed_ids.txt) để tối ưu hiệu suất cho các lần chạy sau.
* **Nghiệm thu:** Script main.py (Orchestrator) tự động quét file dữ liệu thô, phân loại chính xác các kịch bản, xuất PDF thành công lên Google Drive và cập nhật đầy đủ thông tin vào CSDL.

---

#### Giai đoạn 4: Xây dựng Giao diện Web (Tuần 9 - 11)
* **Mục tiêu:** Sản phẩm hiển thị siêu tốc cho sinh viên sử dụng.
* **Công việc:**
  * Khởi tạo dự án React.
  * Viết logic (Custom Hook) để fetch tệp `database.json` vào bộ nhớ cục bộ ngay khi load trang.
  * Lập trình thanh tìm kiếm và bộ lọc mảng (Array Filter) hoạt động theo thời gian thực (Real-time).
  * Tích hợp thư viện xem PDF trên nền web (ví dụ: `react-pdf`).
* **Nghiệm thu:** Web chạy trên Localhost, tìm kiếm không có độ trễ, mở xem PDF trực tiếp không cần tải về.

---

#### Giai đoạn 5: Triển khai và Kiểm thử (Tuần 12)
* **Mục tiêu:** Đưa dự án lên môi trường thực tế.
* **Công việc:**
  * Kết nối kho lưu trữ GitHub của thư mục `3-react-frontend/` với nền tảng Vercel hoặc Netlify để tự động build Web Tĩnh.
  * Đẩy các file PDF lên Google Drive và thiết lập quyền "Bất kỳ ai có liên kết đều có thể xem".
  * Cập nhật link Drive vào file `database.json` và đồng bộ lại lên Web.
* **Nghiệm thu:** Có link domain thực tế gửi cho bạn bè dùng thử và truy cập mượt mà trên cả điện thoại lẫn máy tính.

* **Website**: https://lamlam5406.github.io/HUS_Exam/
