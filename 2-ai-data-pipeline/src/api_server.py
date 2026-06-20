"""
TÊN FILE: api_server.py
CHỨC NĂNG: API Server hứng dữ liệu tự động từ Chrome Extension (Scraper).
Dữ liệu nhận được sẽ lưu trực tiếp vào file /output/raw_data.json.
"""
import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Cấu hình CORS để cho phép Chrome Extension gọi API từ bất kỳ domain nào
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExamPost(BaseModel):
    """Định nghĩa cấu trúc dữ liệu JSON nhận được từ Scraper Extension"""
    post_id: str
    caption: str
    image_urls: list[str]

# ==========================================
# THIẾT LẬP ĐƯỜNG DẪN AN TOÀN
# ==========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.dirname(CURRENT_DIR)
OUTPUT_DIR = os.path.join(MODULE_DIR, "output")
DATA_FILE = os.path.join(OUTPUT_DIR, "raw_data.json")

def read_data() -> list:
    """Hàm phụ trợ: Đọc dữ liệu thô hiện có từ file JSON."""
    if not os.path.exists(DATA_FILE):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

@app.get("/api/scraped-ids")
async def get_scraped_ids():
    """API Endpoint: Trả về danh sách các Post ID đã lưu để Extension tránh thu thập lại."""
    data = read_data()
    seen_ids = [post["post_id"] for post in data]
    return {"seen_ids": seen_ids}

@app.post("/api/ingest")
async def ingest_data(post: ExamPost):
    """API Endpoint: Tiếp nhận và lưu trữ bài viết mới vào file raw_data.json."""
    data = read_data()
    
    # Kiểm tra để tránh lưu trùng lặp ID
    if not any(item["post_id"] == post.post_id for item in data):
        # Chuyển đối tượng Pydantic thành Dictionary (Hỗ trợ cả Pydantic V1 & V2)
        post_data = post.model_dump() if hasattr(post, "model_dump") else post.dict()
        data.append(post_data)
        
        # Ghi dữ liệu mới xuống file
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        print(f"✅ ĐÃ LƯU: {post.post_id} -> {DATA_FILE}")
        return {"status": "success", "message": "Đã lưu dữ liệu"}
    
    print(f"⚠️ BỎ QUA: {post.post_id} đã tồn tại trong file raw.")
    return {"status": "skipped", "message": "Dữ liệu đã tồn tại"}

if __name__ == "__main__":
    import uvicorn
    # Khởi chạy server trên cổng 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)