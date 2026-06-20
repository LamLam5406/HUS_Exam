Dưới đây là tài liệu mô tả chi tiết quy trình xử lý của hệ thống (dựa trên mã nguồn `main.py` mới nhất), được trình bày dưới định dạng Markdown để bạn dễ dàng lưu trữ hoặc đưa vào file `README.md`.

---

# ⚙️ Mô tả Quy trình Hệ thống: AI Data Pipeline

Quy trình này chịu trách nhiệm tự động hóa việc đọc dữ liệu thô từ các bài đăng, bóc tách siêu dữ liệu (Metadata) thông qua 2 luồng (văn bản và hình ảnh), chuẩn hóa thông tin dựa trên danh mục gốc và đóng gói các hình ảnh thành tệp PDF lưu trữ trên Google Drive.

## 📦 1. Giai đoạn Khởi tạo & Chuẩn bị Dữ liệu

* **Nạp Danh mục Chuẩn (Excel):** Hệ thống đọc file `subject.xlsx` để tải lên bộ nhớ một từ điển ánh xạ (Dictionary) giữa **Mã môn học** và **Tên môn học chuẩn**. Đây là "nguồn chân lý" để sửa các lỗi chính tả hoặc viết tắt từ dữ liệu mạng xã hội.
* **Đọc Dữ liệu Đầu vào & Đầu ra:** Nạp tệp dữ liệu thô (`raw_data.json`) và cơ sở dữ liệu hiện tại (`database.json`).
* **Xây dựng Bản đồ Vân tay (Core Fingerprint Map):** Quét CSDL cũ để tạo một bản đồ tra cứu nhanh dựa trên 4 trường cốt lõi: `Mã Môn` + `Tên Môn` + `Học Kỳ` + `Năm Học`.
* **Lọc ID đã xử lý:** Ghi nhận các `post_id` đã tồn tại trong CSDL để bỏ qua ở lần chạy này, tránh xử lý dư thừa.

---

## 🔄 2. Giai đoạn Xử lý Dữ liệu (Duyệt từng Post)

Hệ thống duyệt qua từng bài đăng trong tệp dữ liệu thô. Nếu bài đăng không có ảnh (`image_urls` rỗng) hoặc đã được xử lý, nó sẽ bị bỏ qua. Nếu hợp lệ, hệ thống tiến hành các bước sau:

### Bước 2.1: Luồng Trích xuất Kép (Dual-Stream Extraction)

Để đảm bảo thu thập đầy đủ 4 trường thông tin (Tên môn, Mã môn, Năm học, Học kỳ), hệ thống chạy song song 2 luồng:

* **Luồng 1 (Caption - Regex):** Quét nội dung văn bản của bài đăng để bóc tách thông tin nhanh và tiết kiệm tài nguyên.
* **Luồng 2 (AI Vision Fallback):** Nếu Caption không đủ thông tin, hệ thống tự động tải bức ảnh đầu tiên và gửi đến Multimodal LLM (Google Gemini). AI sẽ đọc hiểu nội dung ảnh bất chấp format và trả về cấu trúc dữ liệu chuẩn (JSON).
* **Hợp nhất:** Hệ thống lấy dữ liệu từ AI làm ưu tiên(60%).

### Bước 2.2: Chuẩn hóa qua Nguồn Chân Lý (Excel Validation)

* Lấy **Mã môn** vừa trích xuất đem đối chiếu với Từ điển Excel.
* Nếu mã môn tồn tại trong file Excel, hệ thống tự động **ghi đè Tên môn** bằng tên chuẩn trong file Excel để loại bỏ sai sót bóc tách.

### Bước 2.3: Bộ lọc Vân tay 2 Tầng (2-Tier Fingerprint Filtering)

Hệ thống tính toán Vân tay cốt lõi (`Core Fingerprint`) từ 4 trường thông tin đã chuẩn hóa. Tùy thuộc vào việc đối chiếu với CSDL cũ, hệ thống rẽ nhánh theo 3 trường hợp:

* **🔴 Trường hợp A: Trùng khớp 100% (Khớp 4 trường + Khớp 7 số đầu Post ID)**
* *Nhận định:* Đây là các bài đăng thuộc cùng một cụm đề thi bị ngắt quãng.
* *Hành động:* Hệ thống tải lại mảng ảnh của bài cũ, nối với mảng ảnh của bài mới (có lọc trùng ảnh tuyệt đối). Dựng lại thành 1 file PDF tổng hợp duy nhất, upload đè lên Drive và cập nhật link Drive mới vào CSDL.


* **🟡 Trường hợp B: Trùng đề thi khác nguồn (Khớp 4 trường + KHÁC 7 số đầu Post ID)**
* *Nhận định:* Đề thi này đã có người đăng trước đó (đã tồn tại file PDF trong hệ thống).
* *Hành động:* Giữ nguyên file cũ. **Loại bỏ hoàn toàn bài đăng mới này**, không tạo PDF và không lưu vào CSDL để chống rác dữ liệu.


* **🟢 Trường hợp C: Đề thi mới hoàn toàn (Vân tay chưa từng tồn tại)**
* *Nhận định:* Đây là tài liệu mới.
* *Hành động:* Đóng gói danh sách ảnh của bài đăng thành một file PDF độc lập. Tải lên Google Drive để lấy link liên kết.



---

## 💾 3. Giai đoạn Đóng gói & Lưu trữ

* **Làm sạch Dữ liệu:** Định dạng lại kết quả đầu ra, loại bỏ toàn bộ các biến chạy tạm thời trong RAM (như mảng `_temp_image_urls` dùng để nối ảnh, đường dẫn file máy tính).
* **Chuẩn hóa Output:** Đảm bảo mỗi bản ghi (Record) lưu xuống CSDL chỉ chứa chính xác 6 trường thông tin:
1. `post_id`
2. `subject_name`
3. `subject_code`
4. `year`
5. `semester`
6. `pdf_drive_link`


* **Lưu File:** Ghi đè CSDL đã cập nhật xuống file `database.json` dưới định dạng UTF-8, hoàn tất vòng đời xử lý của một bài đăng.