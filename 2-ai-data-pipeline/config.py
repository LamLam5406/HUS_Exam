"""
TÊN FILE: config.py
CHỨC NĂNG: Tập trung toàn bộ các biến môi trường, đường dẫn và thiết lập 
để dễ dàng thay đổi mà không cần can thiệp vào logic code lõi.
"""
import os

# ==========================================
# 1. ĐƯỜNG DẪN HỆ THỐNG PHẦN MỀM LÕI
# ==========================================
# Sửa lại đường dẫn này nếu máy tính khác cài Tesseract ở ổ D hoặc thư mục khác
TESSERACT_CMD_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ==========================================
# 2. CẤU HÌNH API & GOOGLE DRIVE
# ==========================================
API_HOST = "0.0.0.0"
API_PORT = 8000

# ID Thư mục lưu trữ PDF trên Google Drive (Lấy từ URL của thư mục trên Web)
DRIVE_FOLDER_ID = "1_sJWdN0Mwus2bLAzTD1nJAlkBdjtzpTK"

# Quyền hạn Google Drive API
DRIVE_SCOPES = [
    'https://www.googleapis.com/auth/drive.file', 
    'https://www.googleapis.com/auth/drive.metadata'
]

# ==========================================
# 3. ĐƯỜNG DẪN LƯU TRỮ DỮ LIỆU LOCAL
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Các file JSON lưu database
RAW_DATA_PATH = os.path.join(BASE_DIR, "output", "raw_data.json")
DB_PATH = os.path.join(BASE_DIR, "output", "database.json")

# Nơi lưu file OAuth 2.0
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")

# ==========================================
# 4. NGƯỠNG CÀI ĐẶT (THRESHOLDS)
# ==========================================
MAX_RETRIES_DOWNLOAD = 3  # Số lần thử tải lại ảnh tối đa nếu mạng lỗi
OCR_THRESHOLD = 150       # Ngưỡng nhị phân hóa ảnh Trắng/Đen cho OpenCV