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
│   │   ├── image_processor.py # OpenCV: Cắt góc, xoay, cân bằng sáng
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

#### Giai đoạn 2: Trích xuất và Số hóa (Tuần 3 - 5)
* **Mục tiêu:** Ảnh thô biến thành chữ.
* **Công việc:**
  * Sử dụng OpenCV viết hàm tiền xử lý: chuyển ảnh sang đen trắng, tăng độ tương phản.
  * Cài đặt Tesseract OCR và chạy thử nghiệm trên các ảnh đã làm sạch.
  * Tinh chỉnh các tham số cấu hình của Tesseract để nhận diện rõ nét các từ khóa đặc thù (VD: "Đề thi", "Môn", "Thời gian").
* **Nghiệm thu:** Đưa một ảnh chụp đề thi bất kỳ vào, script in ra được đoạn text rõ ràng.

---

#### Giai đoạn 3: Phân loại và Đóng gói (Tuần 6 - 8)
* **Mục tiêu:** Máy tính tự hiểu đây là môn gì và gộp file PDF.
* **Công việc:**
  * Xây dựng bộ quy tắc Regex để bắt số "Năm học".
  * Thu thập thủ công một tập dữ liệu nhỏ (khoảng 100 đề thi) để làm dữ liệu huấn luyện (Training data).
  * Huấn luyện mô hình SVM (Support Vector Machine) bằng thư viện scikit-learn để dự đoán "Môn học" dựa trên text OCR và caption.
  * Viết hàm nối các file ảnh đầu ra thành 1 file PDF duy nhất.
  * Viết hàm ghi thông tin tổng hợp vào tệp `database.json`.
* **Nghiệm thu:** Script tự động nhận 1 thư mục ảnh, xuất ra 1 file PDF và 1 file JSON chứa metadata chuẩn xác.

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