"""
TÊN FILE: pdf_builder.py
CHỨC NĂNG: Module tải ảnh và biên dịch thành tài liệu PDF.
"""
import fitz  # Thư viện PyMuPDF
import requests
import os

def build_pdf_from_images(image_urls: list, subject_name: str) -> str | None:
    """
    Tải ảnh qua mạng và trực tiếp render thành 1 file PDF.
    Trả về tên file PDF đã khởi tạo thành công trên hệ thống.
    """
    if not image_urls:
        return None

    # Khởi tạo một đối tượng PDF trống
    doc = fitz.open()

    for url in image_urls:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                img_bytes = response.content
                
                # Mở dòng bytes của ảnh dưới dạng một doc ảo (Memory-based)
                img_doc = fitz.open(stream=img_bytes, filetype="jpg")
                
                # Chuyển đổi doc ảnh đó sang định dạng PDF stream
                pdf_bytes = img_doc.convert_to_pdf()
                img_pdf = fitz.open("pdf", pdf_bytes)
                
                # Ghép page ảnh vừa tạo vào file PDF tổng
                doc.insert_pdf(img_pdf)
        except Exception as e:
            print(f"⚠️ Lỗi khi convert ảnh sang PDF: {str(e)}")
            
    # Hủy bỏ quá trình nếu file PDF không có trang nào (Lỗi mạng tải ảnh toàn bộ)
    if doc.page_count == 0:
        return None

    # Xử lý tên file an toàn để tránh lỗi hệ điều hành
    safe_name = subject_name.replace(" ", "_").replace(":", "").replace("/", "_")
    if not safe_name:
        safe_name = "Unknown_Subject"
        
    filename = f"{safe_name}.pdf"
    
    # Thiết lập đường dẫn tương đối để lưu PDF vào thư mục output/pdfs
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'pdfs')
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, filename)
    doc.save(file_path)
    doc.close()
    
    return filename