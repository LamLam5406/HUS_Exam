"""
TÊN FILE: image_processor.py
CHỨC NĂNG: Xử lý làm nét, phóng to và khử nhiễu ảnh từ URL.
Tối ưu hóa hình ảnh để OCR hoặc model Vision làm việc dễ dàng hơn.
"""
import cv2
import numpy as np
import requests

def download_and_preprocess_image(image_url: str) -> np.ndarray | None:
    """
    Tải ảnh từ mạng, phóng to, khử nhiễu và nhị phân hóa (chuyển Trắng/Đen).
    """
    try:
        response = requests.get(image_url)
        if response.status_code != 200:
            print(f"⚠️ Lỗi tải ảnh: {image_url}")
            return None
        
        # Decode mảng bytes tải được thành một ma trận ảnh lưu trực tiếp trên RAM (tránh lưu file nháp)
        image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        if img is None:
            return None

        # BƯỚC 1: Phóng to ảnh 2x bằng thuật toán nội suy Cubic 
        # (Giúp OCR nhận diện dấu tiếng Việt bị mờ tốt hơn)
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # BƯỚC 2: Chuyển màu sang dải xám (Grayscale)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # BƯỚC 3: Làm mịn bằng Gaussian Blur (Khử độ nhiễu pixel vuông khi ảnh bị Facebook nén)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # BƯỚC 4: Nhị phân hóa bằng thuật toán Otsu
        # Tự động tìm ngưỡng cắt thích hợp để phân rạch ròi vùng Trắng (nền) và Đen (chữ)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return thresh
        
    except Exception as e:
        print(f"⚠️ Lỗi tiền xử lý ảnh: {str(e)}")
        return None