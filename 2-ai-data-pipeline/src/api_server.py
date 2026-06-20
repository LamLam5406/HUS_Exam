"""
API Server hứng dữ liệu từ Chrome Extension.
Lưu file vào /output/raw_data.json.
"""
import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Cấu hình CORS cho phép Extension gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExamPost(BaseModel):
    """Cấu trúc dữ liệu nhận từ Scraper"""
    post_id: str
    caption: str
    image_urls: list[str]

# Thiết lập đường dẫn tuyệt đối an toàn
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.dirname(CURRENT_DIR)
OUTPUT_DIR = os.path.join(MODULE_DIR, "output")
DATA_FILE = os.path.join(OUTPUT_DIR, "raw_data.json")

def read_data() -> list:
    """Đọc dữ liệu hiện có từ file JSON."""
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
    """Cấp phát danh sách ID đã lưu để Scraper tránh quét lại."""
    data = read_data()
    seen_ids = [post["post_id"] for post in data]
    return {"seen_ids": seen_ids}

@app.post("/api/ingest")
async def ingest_data(post: ExamPost):
    """Lưu bài viết mới vào hệ thống."""
    data = read_data()
    
    # Kiểm tra trùng lặp ID
    if not any(item["post_id"] == post.post_id for item in data):
        # Tương thích ngược Pydantic v1 và v2
        post_data = post.model_dump() if hasattr(post, "model_dump") else post.dict()
        data.append(post_data)
        
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        print(f"✅ ĐÃ LƯU: {post.post_id} -> {DATA_FILE}")
        return {"status": "success", "message": "Đã lưu dữ liệu"}
    
    print(f"⚠️ BỎ QUA: {post.post_id} đã tồn tại.")
    return {"status": "skipped", "message": "Dữ liệu đã tồn tại"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)