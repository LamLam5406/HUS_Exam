"""
TÊN FILE: main.py
CHỨC NĂNG: Orchestrator Pipeline.
Luồng xử lý: Đọc Raw Data -> Dual-Stream Extraction -> Excel Validation -> 
2-Tier Fingerprint Filtering -> Build PDF -> Upload Drive -> Lưu CSDL (6 trường).
"""
import json
import os
import pandas as pd

# [TỐI ƯU HÓA] Cấu hình cấp phát VRAM cho PyTorch trên môi trường Colab/Local
# Giúp tránh lỗi Out of Memory (OOM) khi nạp mô hình AI
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

from src.classifier import process_post_metadata
from src.pdf_builder import build_pdf_from_images
from src.drive_uploader import upload_pdf_to_drive
from config import DRIVE_FOLDER_ID

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN DỮ LIỆU
# ==========================================
RAW_DATA_PATH = "output/raw_data.json"
DB_PATH = "output/database.json"
EXCEL_SUBJECT_PATH = "subject.xlsx"
PROCESSED_IDS_PATH = "output/processed_ids.txt"  # Lưu lịch sử ID để không quét lại


def load_subject_dictionary(excel_path: str) -> dict:
    """
    Nạp danh mục môn học chuẩn từ file Excel.
    Trả về Dictionary mapping: Mã Môn -> Tên Môn.
    """
    subject_dict = {}
    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path)
            for _, row in df.iterrows():
                code = str(row.iloc[0]).strip().upper()
                name = str(row.iloc[1]).strip()
                # Loại bỏ các dòng trống (NaN)
                if code and code != 'NAN':
                    subject_dict[code] = name
            print(f"📚 Đã nạp thành công {len(subject_dict)} danh mục môn học từ Excel.")
        except Exception as e:
            print(f"⚠️ Lỗi đọc file Excel {excel_path}: {e}")
    else:
        print(f"⚠️ Không tìm thấy file {excel_path}. Bỏ qua bước chuẩn hóa Excel.")
    
    return subject_dict


def get_core_fingerprint(metadata: dict) -> str:
    """
    Tạo 'Vân tay' (Fingerprint) định danh duy nhất cho một đề thi 
    dựa trên 4 trường cốt lõi. Giúp phát hiện trùng lặp.
    """
    code = metadata.get("subject_code", "").strip().upper()
    name = metadata.get("subject_name", "").strip().upper()
    sem = metadata.get("semester", "").strip().upper()
    year = metadata.get("year", "").strip().upper()
    return f"{code}|{name}|{sem}|{year}"


def run_pipeline():
    """Hàm chạy luồng xử lý chính của toàn bộ hệ thống."""
    print("🚀 Khởi động AI Data Pipeline...")
    
    if not os.path.exists(RAW_DATA_PATH):
        print("❌ Không tìm thấy file dữ liệu thô (raw_data.json)!")
        return

    # ---------------------------------------------------------
    # [GIAI ĐOẠN 1] NẠP DỮ LIỆU & TRẠNG THÁI HỆ THỐNG
    # ---------------------------------------------------------
    subject_dict = load_subject_dictionary(EXCEL_SUBJECT_PATH)

    with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Tạo bản đồ chứa URL ảnh gốc theo post_id để phục vụ việc gộp file (Case A)
    raw_images_map = {str(post.get("post_id")): post.get("image_urls", []) for post in raw_data}

    # Nạp cơ sở dữ liệu đã xử lý trước đó
    database = []
    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            try:
                database = json.load(f)
            except json.JSONDecodeError:
                database = []

    fingerprint_map = {}
    processed_ids = set()

    # Khôi phục danh sách các ID đã được xử lý để bỏ qua ở lần chạy này
    if os.path.exists(PROCESSED_IDS_PATH):
        with open(PROCESSED_IDS_PATH, "r", encoding="utf-8") as f:
            processed_ids = set(line.strip() for line in f if line.strip())

    # Đồng bộ thêm thông tin vân tay từ Database cũ vào bộ nhớ tạm
    for record in database:
        post_id_str = str(record.get("post_id"))
        processed_ids.add(post_id_str)
        fp = get_core_fingerprint(record)
        fingerprint_map[fp] = record

    # ---------------------------------------------------------
    # [GIAI ĐOẠN 2] DUYỆT VÀ XỬ LÝ TỪNG BÀI ĐĂNG
    # ---------------------------------------------------------
    for post in raw_data:
        post_id = str(post.get("post_id"))
        
        # Bỏ qua nếu bài đăng này đã được xử lý trước đó
        if post_id in processed_ids:
            continue

        caption = post.get("caption", "")
        image_urls = post.get("image_urls", [])

        # Bỏ qua bài đăng không có ảnh
        if not image_urls:
            continue

        print(f"\n⚙️ Đang xử lý Post ID: {post_id}...")

        # Gọi hàm bóc tách siêu dữ liệu (Metadata) thông minh
        metadata = process_post_metadata(
            image_url=image_urls[0],
            caption=caption,
            subject_dict=subject_dict
        )

        # Trích xuất 'vân tay' cho metadata mới nhận được
        current_fp = get_core_fingerprint(metadata)
        prefix_new = post_id[:7] # Lấy 7 ký tự đầu để so sánh sự tương đồng của ID
        
        # Kiểm tra tính hợp lệ của vân tay (loại bỏ dữ liệu rác không xác định)
        is_valid_fp = ("KHÔNG XÁC ĐỊNH" not in current_fp) or (metadata.get("subject_code") != "Không xác định")

        is_case_a, is_case_b, is_case_c = False, False, False

        # Phân loại kịch bản xử lý dựa vào việc trùng lặp vân tay
        if is_valid_fp and current_fp in fingerprint_map:
            existing_record = fingerprint_map[current_fp]
            existing_post_id = str(existing_record["post_id"])
            prefix_existing = existing_post_id[:7]

            if prefix_new == prefix_existing:
                is_case_a = True  # Cùng nguồn đăng, có thể là tiếp nối của bài cũ
            else:
                is_case_b = True  # Khác nguồn đăng, đây là bài bị trùng lặp nội dung
        else:
            is_case_c = True      # Dữ liệu hoàn toàn mới

        # --- TIẾN HÀNH XỬ LÝ THEO TỪNG KỊCH BẢN THỰC TẾ ---
        
        if is_case_a:
            # 🔴 TRƯỜNG HỢP A: Trùng khớp môn học + Cùng 1 đợt đăng -> Gộp ảnh
            print(f"🔴 [TRƯỜNG HỢP A] Phát hiện cụm đề thi ngắt quãng (Match ID: {existing_post_id}). Tiến hành gộp file...")
            
            old_images = raw_images_map.get(existing_post_id, [])
            _temp_image_urls = []
            seen = set()
            
            # Gộp URL ảnh cũ và mới, loại bỏ URL trùng lặp
            for url in old_images + image_urls:
                if url not in seen:
                    _temp_image_urls.append(url)
                    seen.add(url)

            # Xây dựng lại file PDF từ danh sách ảnh đã gộp
            pdf_filename = build_pdf_from_images(image_urls=_temp_image_urls, subject_name=metadata["subject_name"])
            
            if pdf_filename:
                local_path = f"output/pdfs/{pdf_filename}"
                drive_link = upload_pdf_to_drive(local_path, pdf_filename, DRIVE_FOLDER_ID)
                
                # Cập nhật link Drive mới cho bản ghi hiện có trong CSDL
                existing_record["pdf_drive_link"] = drive_link
                
                # Xóa file PDF local sau khi đã upload xong
                if os.path.exists(local_path):
                    os.remove(local_path)
            
            processed_ids.add(post_id)
            del _temp_image_urls
            
        elif is_case_b:
            # 🟡 TRƯỜNG HỢP B: Trùng đề thi nhưng khác nguồn -> Bỏ qua (chống rác)
            print("🟡 [TRƯỜNG HỢP B] Đề thi đã tồn tại từ một post khác. Loại bỏ dữ liệu rác.")
            processed_ids.add(post_id)

        elif is_case_c:
            # 🟢 TRƯỜNG HỢP C: Đề thi mới hoàn toàn -> Tạo PDF và lưu CSDL mới
            print("🟢 [TRƯỜNG HỢP C] Dữ liệu mới hoàn toàn. Tạo PDF độc lập...")
            pdf_filename = build_pdf_from_images(image_urls=image_urls, subject_name=metadata.get("subject_name", "Không xác định"))
            drive_link = ""
            
            if pdf_filename:
                local_path = f"output/pdfs/{pdf_filename}"
                drive_link = upload_pdf_to_drive(local_path, pdf_filename, DRIVE_FOLDER_ID)
                
                if drive_link and os.path.exists(local_path):
                    os.remove(local_path)

            # Chuẩn bị Record với đúng 6 trường dữ liệu cốt lõi
            final_record = {
                "post_id": post.get("post_id"),
                "subject_name": metadata.get("subject_name", ""),
                "subject_code": metadata.get("subject_code", ""),
                "year": metadata.get("year", ""),
                "semester": metadata.get("semester", ""),
                "pdf_drive_link": drive_link
            }
            
            # Cập nhật CSDL và bộ đệm trong RAM
            database.append(final_record)
            fingerprint_map[current_fp] = final_record
            processed_ids.add(post_id)
            
            print(f"🎯 LƯU HOÀN TẤT: {final_record['subject_name']} | {final_record['subject_code']} | Kỳ {final_record['semester']} | {final_record['year']}")

        # ---------------------------------------------------------
        # [GIAI ĐOẠN 3] ĐỒNG BỘ TRẠNG THÁI XUỐNG Ổ CỨNG
        # ---------------------------------------------------------
        # Ghi đè file DB.json ngay khi có sự thay đổi (tránh mất dữ liệu nếu bị ngắt ngang)
        if is_case_a or is_case_c:
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump(database, f, ensure_ascii=False, indent=4)
        
        # Ghi nhận ID vừa xử lý vào file text
        with open(PROCESSED_IDS_PATH, "w", encoding="utf-8") as f:
            for pid in processed_ids:
                f.write(f"{pid}\n")

    print("\n✅ Pipeline hoàn tất thành công!")

if __name__ == "__main__":
    run_pipeline()