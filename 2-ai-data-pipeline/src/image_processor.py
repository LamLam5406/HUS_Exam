"""
Module tiền xử lý ảnh sử dụng OpenCV nhằm tối ưu hóa đầu vào cho mô hình OCR.
"""
import cv2
import numpy as np
import requests

def download_and_preprocess_image(image_url: str) -> np.ndarray | None:
    """
    Tải ảnh từ mạng, phóng to, khử nhiễu và nhị phân hóa (Trắng/Đen).
    """
    try:
        response = requests.get(image_url)
        if response.status_code != 200:
            print(f"⚠️ Lỗi tải ảnh: {image_url}")
            return None
        
        # Decode ảnh thẳng trên RAM
        image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        if img is None:
            return None

        # 1. Phóng to ảnh 2x (Giúp OCR nhận diện dấu tiếng Việt tốt hơn)
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # 2. Chuyển sang dải xám (Grayscale)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 3. Làm mịn (Gaussian Blur) để khử độ nhiễu khối của chuẩn nén JPEG từ Facebook
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 4. Nhị phân hóa Otsu (Tự động tìm ngưỡng cắt Trắng/Đen)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return thresh
        
    except Exception as e:
        print(f"⚠️ Lỗi tiền xử lý ảnh: {str(e)}")
        return None