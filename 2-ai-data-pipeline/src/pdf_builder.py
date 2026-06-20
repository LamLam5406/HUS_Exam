"""
Module ghép các URL ảnh tải về thành một tài liệu PDF duy nhất.
"""
import fitz  # PyMuPDF
import requests
import os

def build_pdf_from_images(image_urls: list, subject_name: str) -> str | None:
    """
    Tải ảnh và render trực tiếp thành 1 file PDF.
    Trả về tên file PDF đã tạo (đặt tên theo subject_name).
    """
    if not image_urls:
        return None

    # Khởi tạo PDF tổng
    doc = fitz.open()

    for url in image_urls:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                img_bytes = response.content
                
                # Mở stream byte của ảnh dưới dạng PDF doc, rồi ghép vào doc chính
                img_doc = fitz.open(stream=img_bytes, filetype="jpg")
                pdf_bytes = img_doc.convert_to_pdf()
                img_pdf = fitz.open("pdf", pdf_bytes)
                
                doc.insert_pdf(img_pdf)
        except Exception as e:
            print(f"⚠️ Lỗi khi convert ảnh sang PDF: {str(e)}")
            
    # Bỏ qua nếu quá trình tải ảnh lỗi toàn bộ
    if doc.page_count == 0:
        return None

    # Format tên file an toàn (Không chứa khoảng trắng/kí tự đặc biệt)
    safe_name = subject_name.replace(" ", "_").replace(":", "").replace("/", "_")
    if not safe_name:
        safe_name = "Unknown_Subject"
        
    filename = f"{safe_name}.pdf"
    
    # Thiết lập đường dẫn thư mục đầu ra
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'pdfs')
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, filename)
    doc.save(file_path)
    doc.close()
    
    return filename