"""
TÊN FILE: classifier.py
CHỨC NĂNG: Bóc tách siêu dữ liệu (Metadata) từ văn bản và ảnh.
Phương pháp: Sử dụng Regex để quét nội dung text trước, nếu thiếu sẽ gọi Local Vision-Language Model.
Kết thúc bằng việc chuẩn hóa (Fuzzy Matching) qua danh mục Excel.
"""
import re
import json
import requests
import torch
import difflib
import unicodedata
from io import BytesIO
from PIL import Image
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

# =========================================================================
# [QUẢN LÝ TRẠNG THÁI AI] - Kỹ thuật Lazy Loading
# Tránh việc nạp Model nặng vào VRAM khi chưa cần thiết (VD: Regex đã bóc tách đủ)
# =========================================================================
_model = None
_processor = None
_ai_load_failed = False

def get_ai_model():
    """Khởi tạo và nạp mô hình Qwen2-VL vào GPU chỉ khi được gọi lần đầu."""
    global _model, _processor, _ai_load_failed
    
    if _model is not None:
        return _model, _processor
    if _ai_load_failed:
        return None, None
        
    print("⏳ Đang nạp mô hình Qwen2-VL-2B vào GPU (Lazy Load)...")
    try:
        _model = Qwen2VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2-VL-2B-Instruct", 
            torch_dtype=torch.bfloat16, 
            device_map="auto"
        )
        _processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")
        print("✅ Đã nạp AI thành công!")
        return _model, _processor
    except Exception as e:
        print(f"❌ Lỗi khi nạp mô hình: {e}")
        _ai_load_failed = True
        return None, None

# =========================================================================
# [CÁC HÀM XỬ LÝ & BÓC TÁCH]
# =========================================================================

def remove_accents(input_str: str) -> str:
    """Hỗ trợ: Loại bỏ dấu tiếng Việt để so sánh chuỗi tương đối (Fuzzy Matching)."""
    if not input_str:
        return ""
    # Chuẩn hóa Unicode NFKD tách dấu ra khỏi ký tự, sau đó loại bỏ các ký tự dấu
    s = unicodedata.normalize('NFKD', input_str).encode('ASCII', 'ignore').decode('utf-8')
    return s.lower().strip()

def extract_metadata_from_text(text: str, subject_dict: dict = None) -> dict:
    """
    Sử dụng Regex và Keyword Matching để quét nội dung caption.
    Phương pháp này nhanh và ít tốn kém tài nguyên máy tính.
    """
    metadata = {
        "subject_name": "Không xác định",
        "subject_code": "Không xác định",
        "year": "Không xác định",
        "semester": "Không xác định"
    }
    if not text: return metadata

    text_lower = text.lower()
    
    # 1. BẮT HASHTAG: Tìm các môn học được viết tắt phổ biến
    abbreviation_map = {
        "tthcm": "Tư tưởng Hồ Chí Minh",
        "lsd": "Lịch sử Đảng Cộng sản Việt Nam",
        "lsđ": "Lịch sử Đảng Cộng sản Việt Nam",
        "xstk": "Xác suất thống kê",
        "ptdl": "Nhập môn phân tích dữ liệu",
        "csvh": "Cơ sở văn hóa Việt Nam",
        "csvhvn": "Cơ sở văn hóa Việt Nam",
        "cnxh": "Chủ nghĩa xã hội khoa học",
        "cnxhkh": "Chủ nghĩa xã hội khoa học",
    }
    
    for abbr, full_name in abbreviation_map.items():
        if re.search(rf"(?:#| ){abbr} ", text_lower):
            metadata["subject_name"] = full_name
            break

    # 1.5. QUÉT TỪ KHÓA CHUẨN: Kiểm tra xem tên môn có xuất hiện trong Dict Excel không
    if metadata["subject_name"] == "Không xác định" and subject_dict:
        for code, name in subject_dict.items():
            if len(name) > 6:  # Tránh bắt các từ quá ngắn dễ gây nhầm lẫn
                # \b giới hạn ranh giới từ để quét nguyên cụm
                pattern = rf"\b{re.escape(name.lower())}\b"
                if re.search(pattern, text_lower):
                    metadata["subject_name"] = name
                    metadata["subject_code"] = code
                    break

    # 2. BẮT NĂM HỌC: Tìm định dạng 20xx hoặc 20xx-20xx, tránh bắt nhầm mã môn (Negative Lookbehind)
    year_match = re.search(r"(?<![a-zA-Z])(20[1-2]\d(?:\s*-\s*20[1-2]\d)?)", text)
    if year_match: 
        metadata["year"] = year_match.group(1).replace(" ", "")

    # 3. BẮT HỌC KỲ: Tìm số La Mã hoặc số thường đứng sau cụm từ mô tả Học kỳ
    sem_pattern = r"(?:H[OQ]C\s*K[YÝIÌ]|K[YÝIÌ]|CU[ỐO]I\s*K[YÝIÌ]|GI[ỮU]A\s*K[YÝIÌ]|HK|K|KI|KÌ)\s*([123IVXl]+)"
    semester_match = re.search(sem_pattern, text, re.IGNORECASE)
    if semester_match:
        sem_raw = semester_match.group(1).upper().replace('L', 'I')
        sem_map = {"I": "1", "1": "1", "II": "2", "2": "2", "III": "3", "3": "3"}
        metadata["semester"] = sem_map.get(sem_raw, sem_raw)

    # 4. BẮT MÁ MÔN: Mã có 3-4 chữ cái liền với 3-4 số (Có thể kèm hậu tố chữ cái)
    code_match = re.search(r"#?([A-Za-z]{3,4}\s*\d{3,4}[A-Za-z]?)", text)
    if code_match: 
        metadata["subject_code"] = code_match.group(1).replace(" ", "").upper()

    # 5. FALLBACK TÊN MÔN: Cố gắng lấy dòng đầu tiên của post nếu các bước trên thất bại
    if metadata["subject_name"] == "Không xác định":
        first_line = text.split('\n')[0].strip()
        # Loại bỏ các từ mào đầu
        first_line_clean = re.sub(r'^(Đề\s+thi|Đề\s+cuối\s+kì\s+\d|Đề\s+giữa\s+kì\s+\d|Đề)\s*(?:cuối\s+kì\s+\d|giữa\s+kì\s+\d)?\s*(?:môn)?', '', first_line, flags=re.IGNORECASE).strip()
        first_line_clean = re.sub(r'#.*', '', first_line_clean).strip()
        
        # Danh sách đen: Nếu dòng đầu chứa các từ này thì bỏ qua (Không phải tên môn học)
        blacklist = ["ảnh từ bài viết", "đề thi", "chúc các bạn", "đáp án", "kì", "kỳ", "test", "kiểm tra", "đề", "de thi"]
        is_garbage = any(trash in first_line_clean.lower() for trash in blacklist)
        
        # Lọc độ dài hợp lý cho một tên môn học
        if first_line_clean and not is_garbage and 5 <= len(first_line_clean) <= 60 and len(first_line_clean.split()) <= 12: 
            name = re.sub(r'[\:\-\,\.]+$', '', first_line_clean).strip()
            name = re.sub(r'(kì|kỳ|học kỳ)\s*\d.*|20\d{2}.*', '', name, flags=re.IGNORECASE).strip()
            
            if len(name) > 5:
                metadata["subject_name"] = name if name.isupper() else name.title()

    return metadata


def extract_metadata_from_image_llm(image_url: str) -> dict:
    """
    Sử dụng AI Vision (Qwen2-VL) để đọc và phân tích nội dung hình ảnh.
    Có đi kèm các bước lọc kết quả (Post-Processing) để tránh tình trạng AI bị ảo giác (Hallucination).
    """
    fallback_data = {
        "subject_name": "Không xác định", "subject_code": "Không xác định",
        "year": "Không xác định", "semester": "Không xác định"
    }
    
    if not image_url: return fallback_data
    
    model, processor = get_ai_model()
    if model is None or processor is None:
        return fallback_data

    response_text = "" 
    
    try:
        # Tải ảnh từ URL để nạp cho mô hình
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(image_url, headers=headers, timeout=10)
        response.raise_for_status() 
        image = Image.open(BytesIO(response.content)).convert("RGB")
        
        # Giảm dung lượng ảnh để không làm tràn VRAM GPU
        image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        
        # System Prompt được thiết kế chặt chẽ, ép AI trả về chuẩn JSON
        system_prompt = (
            "Trích xuất thông tin từ tài liệu và trả về ĐÚNG định dạng JSON với 4 trường: "
            "'subject_name', 'subject_code', 'year', 'semester'.\n"
            "QUY TẮC:\n"
            "- 'year': Bắt buộc định dạng YYYY-YYYY hoặc YYYY (VD: 2023-2024 hoặc 2024).\n"
            "- 'semester': CHỈ trả về giá trị '1', '2', '3'. KHÔNG trả về chữ (VD: 'Trung học', 'Tuyển sinh'). "
            "Nếu không có hoặc không chắc chắn, trả về ''.\n"
            "Nếu không tìm thấy bất kỳ trường nào, điền 'Không xác định'."
        )

        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": system_prompt}
            ]
        }]
        
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=[text], images=image, padding=True, return_tensors="pt").to(model.device) 

        # Đẩy qua Model để Inference (Tạo text)
        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=150)
            
        generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
        response_text = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True)[0]
        
        # Cắt lấy chuỗi JSON từ Output của AI
        json_match = re.search(r'\{.*\}', response_text.replace('\n', ''), re.DOTALL)
        if json_match:
            llm_data = json.loads(json_match.group(0))
            
            # --- BỘ LỌC CHỐNG ẢO GIÁC (POST-PROCESSING) ---
            
            # 1. Lọc Kỳ học
            sem_raw = str(llm_data.get("semester", "")).upper()
            valid_sem = re.search(r'([123I]+)', sem_raw)
            if valid_sem:
                sem_map = {"I": "1", "1": "1", "II": "2", "2": "2", "III": "3", "3": "3"}
                fallback_data["semester"] = sem_map.get(valid_sem.group(1), "Không xác định")
            else:
                fallback_data["semester"] = "Không xác định"

            # 2. Lọc Năm học
            year_raw = str(llm_data.get("year", ""))
            valid_year = re.search(r'(?<![a-zA-Z])(20[1-2]\d(?:\s*-\s*20[1-2]\d)?)', year_raw)
            if valid_year:
                fallback_data["year"] = valid_year.group(1).replace(" ", "")
            else:
                fallback_data["year"] = "Không xác định"

            # 3. Lọc Mã Môn
            code_raw = str(llm_data.get("subject_code", "")).strip().upper()
            if re.match(r'^[A-Z]{3,4}\s*\d{3,4}[A-Z]?$', code_raw):
                fallback_data["subject_code"] = code_raw

            # 4. Lọc Tên Môn
            if llm_data.get("subject_name") and str(llm_data["subject_name"]).strip() not in ["", "Không xác định"]: 
                fallback_data["subject_name"] = str(llm_data["subject_name"]).strip()
                    
        return fallback_data
        
    except json.JSONDecodeError:
        print(f"⚠️ AI trả về lỗi JSON. Raw output: {response_text}")
        return fallback_data
    except Exception as e:
        print(f"❌ Lỗi AI Vision: {e}")
        return fallback_data


def normalize_metadata_via_excel(extracted_data: dict, subject_dict: dict) -> dict:
    """
    Hàm chuẩn hóa cuối cùng: Ép các dữ liệu vừa lấy được qua lăng kính danh mục chuẩn (Excel).
    Sử dụng kỹ thuật Fuzzy Matching để tìm tên môn gần đúng nhất.
    """
    if not subject_dict:
        return extracted_data

    raw_code = extracted_data.get("subject_code", "").replace(" ", "").upper()
    raw_name = extracted_data.get("subject_name", "").strip()

    matched_code = "Không xác định"
    matched_name = "Không xác định"

    # ƯU TIÊN 1: Map chính xác hoàn toàn theo Mã môn
    if raw_code and raw_code != "KHÔNGXÁCĐỊNH" and raw_code in subject_dict:
        matched_code = raw_code
        matched_name = subject_dict[raw_code]
        
    # ƯU TIÊN 2: Nếu không có mã, tiến hành so sánh Tên môn học không dấu (Fuzzy Matching)
    elif raw_name and raw_name.lower() != "không xác định":
        name_clean = remove_accents(raw_name)
        standard_mapping = {remove_accents(v): k for k, v in subject_dict.items()}
        standard_names_clean = list(standard_mapping.keys())
        
        # Tìm danh từ gần giống nhất (Độ tương đồng >= 0.7)
        matches = difflib.get_close_matches(name_clean, standard_names_clean, n=1, cutoff=0.7)
        if matches:
            matched_code = standard_mapping[matches[0]]
            matched_name = subject_dict[matched_code]

    # Cập nhật lại kết quả (Nếu không khớp được bất kỳ cái gì thì sẽ là Không xác định)
    extracted_data["subject_code"] = matched_code
    extracted_data["subject_name"] = matched_name
        
    return extracted_data


def process_post_metadata(image_url: str, caption: str, subject_dict: dict) -> dict:
    """
    Hàm tổng hợp luồng xử lý kép:
    1. Chạy Regex trước (nhanh, rẻ).
    2. Nếu thiếu dữ liệu quan trọng -> Chạy AI Image (chậm, đắt) để bổ khuyết.
    3. Đẩy kết quả cuối qua màng lọc Excel.
    """
    # Bước 1: Quét chữ
    final_data = extract_metadata_from_text(caption, subject_dict)
    
    # Đánh giá xem có thiếu thông tin thiết yếu không
    is_missing_critical_data = (
        final_data["subject_code"] == "Không xác định" or 
        final_data["year"] == "Không xác định"
    )

    # Bước 2: Gọi AI Vision nếu cần
    if image_url and is_missing_critical_data:
        ai_data = extract_metadata_from_image_llm(image_url)
        # Bổ sung các giá trị còn thiếu bằng dữ liệu AI vừa bóc tách
        for key in final_data.keys():
            if final_data[key] == "Không xác định" and ai_data.get(key) != "Không xác định":
                final_data[key] = ai_data[key]

    # Bước 3: Chuẩn hóa qua Excel
    final_data = normalize_metadata_via_excel(final_data, subject_dict)
    
    return final_data