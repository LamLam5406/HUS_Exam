"""
Module phân tích, bóc tách siêu dữ liệu (Metadata) từ văn bản sử dụng Regex và Local Vision-Language Model.
Tích hợp đối chiếu Nguồn Chân Lý (Excel) để chuẩn hóa tên môn học.
"""
import re
import json
import requests
import torch
from io import BytesIO
from PIL import Image
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

# -------------------------------------------------------------------------
# [KHỞI TẠO AI] - Load model 1 lần duy nhất vào bộ nhớ GPU khi import file
# -------------------------------------------------------------------------
print("⏳ Đang nạp mô hình Qwen2-VL-2B vào GPU (sẽ mất khoảng 1-2 phút lần đầu)...")
try:
    # Tự động chọn GPU nếu có, ép kiểu bfloat16 để tiết kiệm VRAM trên Colab
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        "Qwen/Qwen2-VL-2B-Instruct", 
        torch_dtype=torch.bfloat16, 
        device_map="auto"
    )
    processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")
    print("✅ Đã nạp AI thành công! Sẵn sàng xử lý ảnh.")
except Exception as e:
    print(f"❌ Lỗi khi nạp mô hình: {e}")
    model, processor = None, None
# -------------------------------------------------------------------------


def extract_metadata(text: str) -> dict:
    """Trích xuất Năm học, Học kỳ, Mã học phần và Tên học phần bằng Regex (Luồng 2 - Giữ nguyên gốc)"""
    metadata = {
        "subject_name": "Không xác định",
        "subject_code": "Không xác định",
        "year": "Không xác định",
        "semester": "Không xác định"
    }
    if not text: return metadata

    year_match = re.search(r"(20\d{2}\s*-\s*20\d{2})", text)
    if year_match: metadata["year"] = year_match.group(1).replace(" ", "")

    sem_pattern = r"(?:H[OQ]C\s*K[YÝIÌ]|K[YÝIÌ]|CU[ỐO]I\s*K[YÝIÌ]|GI[ỮU]A\s*K[YÝIÌ])\s*([I123IVXl]+)"
    semester_match = re.search(sem_pattern, text, re.IGNORECASE)
    if semester_match:
        metadata["semester"] = semester_match.group(1).upper().replace('L', 'I').replace('1', 'I')

    code_match = re.search(r"([A-Z]{3,4}\s*\d{3,4})", text, re.IGNORECASE)
    if code_match: metadata["subject_code"] = code_match.group(1).replace(" ", "").upper()

    pattern_tier1 = r"(?:M[ôoóée]n\s*thi|M[ôoóée]n|T[éen]+\s*h[oQ]c\s*ph[aá]n|H[oQ]c\s*ph[aá]n)[\s:]*(.+?)(?=\n|M[aã]|D[ée]\s*s[éo]|Th[oò]i|Cu[ốo]i\s*k[yýiì]|Gi[ữu]a\s*k[yýiì]|K[yýiì]\s*\d|20\d{2}|\(|$|#)"
    subject_match_1 = re.search(pattern_tier1, text, re.IGNORECASE)
    
    pattern_tier2 = r"^(.+?)(?=\s*(?:Cu[ốo]i\s*k[yýiì]|Gi[ữu]a\s*k[yýiì]|K[yýiì]\s*\d|H[oQ]c\s*K[yýiì]|N[ăa]m\s*h[oQ]c|20\d{2}|#|\())"
    subject_match_2 = re.search(pattern_tier2, text, re.IGNORECASE)

    name = ""
    if subject_match_1: name = subject_match_1.group(1).strip()
    elif subject_match_2: name = subject_match_2.group(1).strip()
    else:
        clean_text = re.sub(r'#.*', '', text).strip()
        if clean_text:
            first_line = clean_text.split('\n')[0].strip()
            first_line_clean = re.sub(r'^(Đề\s+thi|Đề\s+cuối\s+kì\s+\d|Đề\s+giữa\s+kì\s+\d|Đề)\s*(?:cuối\s+kì\s+\d|giữa\s+kì\s+\d)?\s*(?:môn)?', '', first_line, flags=re.IGNORECASE).strip()
            if first_line_clean and len(first_line_clean) < 100: name = first_line_clean
        
    if name:
        name = re.sub(r'[\:\-\,\.]+$', '', name).strip()
        name = re.sub(r'#.*', '', name).strip()
        if name: metadata["subject_name"] = name if name.isupper() else name.title()

    return metadata


def extract_metadata_from_image_llm(image_url: str) -> dict:
    """Trích xuất Metadata trực tiếp từ ảnh bằng AI chạy Local/Colab (Luồng 1)"""
    fallback_data = {
        "subject_name": "Không xác định",
        "subject_code": "Không xác định",
        "year": "Không xác định",
        "semester": "Không xác định"
    }
    
    if not image_url or model is None or processor is None:
        return fallback_data

    try:
        # 1. Tải ảnh từ URL (vẫn giữ header để bypass Facebook CDN)
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(image_url, headers=headers, timeout=10)
        response.raise_for_status() 
        image = Image.open(BytesIO(response.content)).convert("RGB")
        
        # 2. Xây dựng câu lệnh (Prompt) cho mô hình
        # Qwen2-VL sử dụng format cấu trúc tin nhắn
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": "Trích xuất thông tin từ tài liệu này và trả về JSON có chính xác 4 trường: 'subject_name' (Tên môn học), 'subject_code' (Mã môn học), 'year' (Năm học), 'semester' (Học kỳ). Trả về 'Không xác định' nếu thiếu. Chỉ xuất JSON, không giải thích."}
                ]
            }
        ]
        
        # 3. Tiền xử lý và đẩy vào mô hình
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = processor.image_processor(image), None # Trích xuất tensor ảnh
        
        inputs = processor(
            text=[text],
            images=image,
            padding=True,
            return_tensors="pt"
        ).to(model.device) # Đẩy dữ liệu vào GPU

        # 4. Sinh kết quả
        generated_ids = model.generate(**inputs, max_new_tokens=150)
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        response_text = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
        
        # 5. Làm sạch JSON
        response_text = response_text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].strip()
            
        llm_data = json.loads(response_text)
        
        for key in fallback_data.keys():
            if key in llm_data and llm_data[key] and str(llm_data[key]).strip() != "":
                fallback_data[key] = str(llm_data[key]).strip()
                
        return fallback_data
        
    except json.JSONDecodeError:
        print(f"⚠️ AI không trả về định dạng JSON chuẩn. Raw output: {response_text}")
        return fallback_data
    except Exception as e:
        print(f"❌ Lỗi khi chạy AI Vision cho ảnh: {e}")
        return fallback_data


def normalize_metadata_via_excel(extracted_data: dict, subject_dict: dict) -> dict:
    """Chuẩn hóa tên môn học thông qua Nguồn Chân Lý (Excel Validation)."""
    code = extracted_data.get("subject_code", "").upper().strip()
    if code != "KHÔNG XÁC ĐỊNH" and code in subject_dict:
        extracted_data["subject_name"] = subject_dict[code]
    return extracted_data


def process_post_metadata(image_url: str, caption: str, subject_dict: dict) -> dict:
    """Luồng xử lý Kép: 1. AI Vision Fallback -> 2. Caption Regex -> 3. Excel Validation"""
    final_data = extract_metadata_from_image_llm(image_url)

    if caption:
        text_data = extract_metadata(caption)
        for key in final_data.keys():
            if final_data[key] == "Không xác định" and text_data.get(key) != "Không xác định":
                final_data[key] = text_data[key]

    final_data = normalize_metadata_via_excel(final_data, subject_dict)
    return final_data