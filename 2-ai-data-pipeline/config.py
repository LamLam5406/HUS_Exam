"""
TÊN FILE: config.py
CHỨC NĂNG: Tập trung toàn bộ các biến môi trường, đường dẫn và thiết lập 
để dễ dàng thay đổi mà không cần can thiệp vào logic code lõi.
"""
import os

# ==========================================
# 1. CẤU HÌNH API SERVER
# ==========================================
API_HOST = "0.0.0.0"  # Lắng nghe trên mọi IP
API_PORT = 8000       # Cổng chạy FastAPI

# ==========================================
# 2. CẤU HÌNH GOOGLE DRIVE
# ==========================================
# ID Thư mục lưu trữ PDF trên Google Drive (Lấy từ URL của thư mục trên Web)
DRIVE_FOLDER_ID = "16Ogo1UsEtyhml-9thA8jSVpk02MJXtqT"

# Quyền hạn Google Drive API (Chỉ yêu cầu quyền quản lý file do app tạo ra)
DRIVE_SCOPES = [
    'https://www.googleapis.com/auth/drive.file', 
    'https://www.googleapis.com/auth/drive.metadata'
]

# ==========================================
# 3. ĐƯỜNG DẪN LƯU TRỮ DỮ LIỆU LOCAL
# ==========================================
# Lấy đường dẫn thư mục gốc chứa file config.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Các file JSON lưu database (đặt trong thư mục output)
RAW_DATA_PATH = os.path.join(BASE_DIR, "output", "raw_data.json")
DB_PATH = os.path.join(BASE_DIR, "output", "database.json")

# Nơi lưu file thông tin xác thực OAuth 2.0 của Google API
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")

# ==========================================
# 4. NGƯỠNG CÀI ĐẶT (THRESHOLDS)
# ==========================================
MAX_RETRIES_DOWNLOAD = 3  # Số lần thử tải lại ảnh tối đa nếu mạng bị lỗi
OCR_THRESHOLD = 150       # Ngưỡng nhị phân hóa ảnh (Trắng/Đen) áp dụng cho OpenCV