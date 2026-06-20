"""
Orchestrator Pipeline: Đọc Raw Data -> Dual-Stream Extraction -> Excel Validation
-> 2-Tier Fingerprint Filtering -> Build PDF -> Upload Drive -> Lưu DB (6 trường).
"""
import json
import os
import pandas as pd

from src.classifier import process_post_metadata
from src.pdf_builder import build_pdf_from_images
from src.drive_uploader import upload_pdf_to_drive
from config import DRIVE_FOLDER_ID

# Cấu hình đường dẫn
RAW_DATA_PATH = "output/raw_data.json"
DB_PATH = "output/database.json"
EXCEL_SUBJECT_PATH = "subject.xlsx"


def load_subject_dictionary(excel_path: str) -> dict:
    """Nạp danh mục chuẩn từ Excel để tạo Dictionary mapping Mã Môn -> Tên Môn"""
    subject_dict = {}
    if os.path.exists(excel_path):
        try:
            # Giả định: Cột 1 là Mã môn, Cột 2 là Tên môn
            df = pd.read_excel(excel_path)
            for _, row in df.iterrows():
                code = str(row.iloc[0]).strip().upper()
                name = str(row.iloc[1]).strip()
                if code and code != 'NAN':
                    subject_dict[code] = name
            print(f"📚 Đã nạp thành công {len(subject_dict)} danh mục môn học từ Excel.")
        except Exception as e:
            print(f"⚠️ Lỗi đọc file Excel {excel_path}: {e}")
    else:
        print(f"⚠️ Không tìm thấy file {excel_path}. Bỏ qua bước chuẩn hóa Excel.")
    
    return subject_dict


def get_core_fingerprint(metadata: dict) -> str:
    """Tạo Core Fingerprint từ 4 trường cốt lõi."""
    code = metadata.get("subject_code", "").strip().upper()
    name = metadata.get("subject_name", "").strip().upper()
    sem = metadata.get("semester", "").strip().upper()
    year = metadata.get("year", "").strip().upper()
    return f"{code}|{name}|{sem}|{year}"


def run_pipeline():
    print("🚀 Khởi động AI Data Pipeline...")
    
    if not os.path.exists(RAW_DATA_PATH):
        print("❌ Không tìm thấy file dữ liệu thô (raw_data.json)!")
        return

    # [Giai đoạn 1] Nạp Nguồn Chân Lý & Đọc Data
    subject_dict = load_subject_dictionary(EXCEL_SUBJECT_PATH)

    with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Bản đồ lưu URL ảnh gốc trong bộ nhớ để tái tạo PDF cho Case A
    raw_images_map = {str(post.get("post_id")): post.get("image_urls", []) for post in raw_data}

    # Nạp Cơ sở dữ liệu hiện hành
    database = []
    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            try:
                database = json.load(f)
            except json.JSONDecodeError:
                database = []

    # Xây dựng Core Fingerprint Map & Lọc ID đã xử lý
    fingerprint_map = {}
    processed_ids = set()

    for record in database:
        post_id_str = str(record.get("post_id"))
        processed_ids.add(post_id_str)
        fp = get_core_fingerprint(record)
        fingerprint_map[fp] = record

    # [Giai đoạn 2] Xử lý từng bài đăng
    for post in raw_data:
        post_id = str(post.get("post_id"))
        
        if post_id in processed_ids:
            continue

        caption = post.get("caption", "")
        image_urls = post.get("image_urls", [])

        if not image_urls:
            continue

        print(f"\n⚙️ Đang xử lý Post ID: {post_id}...")

        # [Bước 2.1 & 2.2] Dual-Stream Extraction + Excel Validation
        metadata = process_post_metadata(
            image_url=image_urls[0],
            caption=caption,
            subject_dict=subject_dict
        )

        # [Bước 2.3] Bộ lọc Vân tay 2 Tầng (2-Tier Fingerprint Filtering)
        current_fp = get_core_fingerprint(metadata)
        prefix_new = post_id[:7]
        
        # Bỏ qua Vân tay hoàn toàn không chứa dữ liệu hữu ích
        is_valid_fp = ("KHÔNG XÁC ĐỊNH" not in current_fp) or (metadata.get("subject_code") != "Không xác định")

        if is_valid_fp and current_fp in fingerprint_map:
            existing_record = fingerprint_map[current_fp]
            existing_post_id = str(existing_record["post_id"])
            prefix_existing = existing_post_id[:7]

            if prefix_new == prefix_existing:
                # 🔴 TRƯỜNG HỢP A: Trùng khớp 100% -> Gộp ảnh
                print(f"🔴 [TRƯỜNG HỢP A] Phát hiện cụm đề thi ngắt quãng (Match ID: {existing_post_id}). Tiến hành gộp file...")
                
                old_images = raw_images_map.get(existing_post_id, [])
                _temp_image_urls = []
                seen = set()
                
                # Nối ảnh bài cũ và mới, có lọc trùng lặp tuyệt đối
                for url in old_images + image_urls:
                    if url not in seen:
                        _temp_image_urls.append(url)
                        seen.add(url)

                pdf_filename = build_pdf_from_images(image_urls=_temp_image_urls, subject_name=metadata["subject_name"])
                
                if pdf_filename:
                    local_path = f"output/pdfs/{pdf_filename}"
                    drive_link = upload_pdf_to_drive(local_path, pdf_filename, DRIVE_FOLDER_ID)
                    
                    # Cập nhật link drive mới cho Record cũ trong CSDL
                    existing_record["pdf_drive_link"] = drive_link
                    
                    if os.path.exists(local_path):
                        os.remove(local_path)
                
                processed_ids.add(post_id)
                
                # Giai đoạn 3: Làm sạch biến tạm để giải phóng RAM
                del _temp_image_urls
                continue
                
            else:
                # 🟡 TRƯỜNG HỢP B: Trùng đề thi nhưng khác nguồn -> Loại bỏ hoàn toàn
                print("🟡 [TRƯỜNG HỢP B] Đề thi đã tồn tại từ một post khác. Loại bỏ dữ liệu rác.")
                processed_ids.add(post_id)
                continue

        # 🟢 TRƯỜNG HỢP C: Đề thi mới hoàn toàn (Vân tay chưa từng tồn tại)
        print("🟢 [TRƯỜNG HỢP C] Dữ liệu mới hoàn toàn. Tạo PDF độc lập...")
        pdf_filename = build_pdf_from_images(image_urls=image_urls, subject_name=metadata.get("subject_name", "Không xác định"))
        drive_link = ""
        
        if pdf_filename:
            local_path = f"output/pdfs/{pdf_filename}"
            drive_link = upload_pdf_to_drive(local_path, pdf_filename, DRIVE_FOLDER_ID)
            
            if drive_link and os.path.exists(local_path):
                os.remove(local_path)

        # [Giai đoạn 3] Đóng gói & Lưu trữ (Chính xác 6 trường)
        final_record = {
            "post_id": post.get("post_id"),  # Giữ nguyên type gốc của raw_data
            "subject_name": metadata.get("subject_name", ""),
            "subject_code": metadata.get("subject_code", ""),
            "year": metadata.get("year", ""),
            "semester": metadata.get("semester", ""),
            "pdf_drive_link": drive_link
        }
        
        database.append(final_record)
        fingerprint_map[current_fp] = final_record
        processed_ids.add(post_id)
        
        print(f"🎯 LƯU HOÀN TẤT: {final_record['subject_name']} | {final_record['subject_code']} | Kỳ {final_record['semester']} | {final_record['year']}")
        
        # Ghi đè cập nhật vào file DB liên tục để giữ state
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(database, f, ensure_ascii=False, indent=4)

    print("\n✅ Pipeline hoàn tất thành công!")

if __name__ == "__main__":
    run_pipeline()