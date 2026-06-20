"""
TÊN FILE: drive_uploader.py
CHỨC NĂNG: Module quản lý kết nối Google Drive API và tải file.
Thực hiện quá trình OAuth 2.0, cấp quyền public và trả về link xem.
"""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import DRIVE_SCOPES

SCOPES = DRIVE_SCOPES

def get_drive_service():
    """Khởi tạo và xác thực kết nối Google Drive."""
    creds = None
    base_dir = os.path.dirname(__file__)
    
    # Các file lưu token và credentials phải nằm ở thư mục root
    token_path = os.path.join(base_dir, '..', 'token.json')
    creds_path = os.path.join(base_dir, '..', 'credentials.json')

    # Nạp phiên đăng nhập cũ nếu có (Tránh phải đăng nhập lại nhiều lần)
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    # Làm mới token hoặc yêu cầu đăng nhập qua trình duyệt (Lần đầu chạy)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                print(f"❌ Không tìm thấy file OAuth credentials tại: {creds_path}")
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Lưu phiên đăng nhập xuống ổ cứng để lần sau tái sử dụng
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        # Build API service phiên bản v3
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ Lỗi khởi tạo Google Drive Service: {e}")
        return None

def upload_pdf_to_drive(local_file_path: str, filename: str, folder_id: str) -> str:
    """
    Tải file PDF cục bộ lên Google Drive (có hỗ trợ Resume),
    Gán file vào ID thư mục đích và tự động cấp quyền View (Reader).
    """
    service = get_drive_service()
    if not service:
        return ""

    try:
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        # Khởi tạo đối tượng stream upload file
        media = MediaFileUpload(local_file_path, mimetype='application/pdf', resumable=True)
        
        print(f"☁️ Đang tải {filename} lên Google Drive...")
        
        # Thực thi tải lên và yêu cầu Google trả về ID file + Link xem
        file = service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id, webViewLink'
        ).execute()
        
        file_id = file.get('id')
        view_link = file.get('webViewLink')
        
        # Cấp quyền Public: Ai có link cũng được xem (Không cần đăng nhập Google)
        permission = {
            'type': 'anyone',
            'role': 'reader',
        }
        service.permissions().create(fileId=file_id, body=permission).execute()
        
        print("✅ Tải lên Drive thành công!")
        return view_link
        
    except Exception as e:
        print(f"❌ Lỗi tải file lên Drive: {e}")
        return ""