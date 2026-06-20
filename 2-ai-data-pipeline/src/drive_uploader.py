"""
Module quản lý kết nối Google Drive API (OAuth 2.0) và Upload file.
"""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import DRIVE_SCOPES

# Quyền hạn cần thiết: Tạo file mới và cấp quyền xem
SCOPES = DRIVE_SCOPES

def get_drive_service():
    """Khởi tạo và xác thực kết nối Google Drive."""
    creds = None
    base_dir = os.path.dirname(__file__)
    token_path = os.path.join(base_dir, '..', 'token.json')
    creds_path = os.path.join(base_dir, '..', 'credentials.json')

    # Nạp phiên đăng nhập cũ nếu có
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    # Làm mới token hoặc yêu cầu đăng nhập trình duyệt
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                print(f"❌ Không tìm thấy file OAuth credentials: {creds_path}")
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Lưu phiên đăng nhập
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ Lỗi khởi tạo Google Drive Service: {e}")
        return None

def upload_pdf_to_drive(local_file_path: str, filename: str, folder_id: str) -> str:
    """
    Upload file PDF lên thư mục cụ thể và cấp quyền Public (Reader).
    Trả về Web View Link.
    """
    service = get_drive_service()
    if not service:
        return ""

    try:
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(local_file_path, mimetype='application/pdf', resumable=True)
        
        print(f"☁️ Đang tải {filename} lên Google Drive...")
        file = service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id, webViewLink'
        ).execute()
        
        file_id = file.get('id')
        view_link = file.get('webViewLink')
        
        # Cấp quyền Public để ai có link cũng xem được (WebView)
        permission = {
            'type': 'anyone',
            'role': 'reader',
        }
        service.permissions().create(fileId=file_id, body=permission).execute()
        
        print("✅ Tải lên thành công!")
        return view_link
        
    except Exception as e:
        print(f"❌ Lỗi tải file lên Drive: {e}")
        return ""