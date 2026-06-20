/**
 * TÊN FILE: content.js
 * CHỨC NĂNG: Script chạy ngầm trên trang Facebook, tự động click chuyển ảnh, 
 * bóc tách dữ liệu (Caption, URL ảnh HD) và gửi về server nội bộ.
 */

let seenIds = new Set();
let currentPost = null;
let duplicateCount = 0;
const MAX_DUPLICATES = 3; 
let isScraping = false;

chrome.runtime.onMessage.addListener(async (request, sender, sendResponse) => {
    if (request.action === "START_SCRAPING" && !isScraping) {
        isScraping = true;
        console.log("▶️ Bắt đầu khởi chạy tiến trình thu thập...");
        startScraping();
    }
    
    if (request.action === "STOP_SCRAPING") {
        console.log("⏹️ Đã nhận lệnh dừng từ hệ thống!");
        isScraping = false; 
        
        if (currentPost) {
            await sendToFastAPI(currentPost);
            currentPost = null; 
        }
    }
});

async function startScraping() {
    try {
        const response = await fetch("http://localhost:8000/api/scraped-ids");
        const data = await response.json();
        seenIds = new Set(data.seen_ids);
    } catch (error) {
        console.warn("⚠️ Không thể kết nối tới Local API. Chạy với dữ liệu trắng.", error);
        seenIds = new Set();
    }

    const firstPhotoLink = document.querySelector('a[href*="/photo/"]');
    if (firstPhotoLink) {
        firstPhotoLink.click();
        setTimeout(scrapeCurrentModal, 3000);
    } else {
        console.error("❌ Không tìm thấy ảnh. Hãy cuộn trang để FB tải thêm DOM và thử lại.");
        isScraping = false;
    }
}

// ==========================================
// CÁC HÀM TIỆN ÍCH & DOM SELECTORS
// ==========================================

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

function extractPostId(url) {
    try {
        const urlObj = new URL(url);
        const setParam = urlObj.searchParams.get("set");
        if (setParam && setParam.includes("pcb.")) return setParam.split("pcb.")[1];
        return urlObj.searchParams.get("fbid") || "unknown_id";
    } catch (e) {
        return "unknown_id";
    }
}

function getHighResImage() {
    const images = Array.from(document.querySelectorAll('img[data-visualcompletion="media-vc-image"]'));
    return images.length > 0 ? images[images.length - 1].src : "";
}

/** * Hàm bóc tách text chuẩn, áp dụng cho cả Box bên phải và Modal 
 */
function extractCaptionFromNode(rootNode) {
    if (!rootNode) return "";

    // ==========================================
    // ƯU TIÊN 1: Tìm thẳng vào thẻ chứa nội dung chuẩn của Facebook
    // ==========================================
    const messageContainer = rootNode.querySelector('div[data-ad-comet-preview="message"]');
    if (messageContainer) {
        let text = messageContainer.innerText.trim();
        if (text) return text;
    }

    // ==========================================
    // ƯU TIÊN 2: Quét DOM dự phòng (Có bộ lọc chống text rác Obfuscated)
    // ==========================================
    const textElements = rootNode.querySelectorAll('span[dir="auto"], div[dir="auto"]');
    let validCaptions = [];

    const blacklist = [
        "hãy là người đầu tiên bình luận", "be the first to comment",
        "viết bình luận", "write a comment", "phù hợp nhất", "most relevant",
        "chưa có bình luận", "no comments yet", "đã trả lời", "phản hồi", 
        "tất cả bình luận", "chia sẻ", "share", "thành viên ẩn danh", "anonymous participant",
        "ảnh này nằm trong một bài viết", "xem bài viết"
    ];

    textElements.forEach(el => {
        // Bỏ qua khu vực bình luận
        if (el.closest('ul') || el.closest('[role="article"]') || 
            el.closest('[aria-label*="comment" i]') || el.closest('[aria-label*="Bình luận" i]')) return; 

        // Bỏ qua tên tác giả
        let isAuthorName = el.closest('a[href*="/user/"]') || el.closest('a[href*="/groups/"]') || 
                           el.querySelector('a[href*="/user/"]') || el.querySelector('a[href*="/groups/"]') ||
                           el.closest('h2, h3, h4');
        if (isAuthorName) return;

        let cleanText = (el.innerText || "").trim();
        let lowerText = cleanText.toLowerCase();
        
        // ----------------------------------------------------
        // [CẬP NHẬT]: BỘ LỌC CHỐNG CHUỖI MÃ HÓA (ANTI-SCRAPING)
        // ----------------------------------------------------
        // 1. Chặn đích danh chuỗi băm thường gặp của FB
        if (cleanText.includes("rdsSotepno") || cleanText.includes("Sponsor")) return;
        
        // 2. Chặn các chuỗi chứa một từ dính liền nhau quá dài (Caption thật thường có dấu cách giữa các từ)
        const longestWord = cleanText.split(/\s+/).reduce((max, word) => Math.max(max, word.length), 0);
        if (longestWord > 30) return; 
        // ----------------------------------------------------

        if (cleanText.length < 3) return;
        let newLineCount = (cleanText.match(/\n/g) || []).length;
        if (newLineCount > cleanText.length / 4) return; // Loại bỏ text chứa quá nhiều dòng trống (thường là menu UI)
        if (blacklist.some(phrase => lowerText.includes(phrase))) return;

        validCaptions.push(cleanText);
    });

    // Trả về đoạn văn bản hợp lệ dài nhất
    return validCaptions.length > 0 ? validCaptions.reduce((a, b) => a.length > b.length ? a : b, "") : "";
}

// ==========================================
// VÒNG LẶP THU THẬP CỐT LÕI
// ==========================================

async function scrapeCurrentModal() {
    if (!isScraping) return;

    const currentUrl = window.location.href;
    const postId = extractPostId(currentUrl);
    const hdImageUrl = getHighResImage();
    
    const rightPanel = document.querySelector('div[role="complementary"]') || document.body;
    let captionText = extractCaptionFromNode(rightPanel);

    // =================================================================
    // XỬ LÝ CHÍNH XÁC: "ẢNH NẰM TRONG MỘT BÀI VIẾT"
    // =================================================================
    if (rightPanel.innerText.includes("Ảnh này nằm trong một bài viết")) {
        // [Cập nhật 1] Dùng TreeWalker lùng sục đúng phần tử text chứa chữ "Xem bài viết"
        let viewPostNode = null;
        const walker = document.createTreeWalker(rightPanel, NodeFilter.SHOW_TEXT, null, false);
        let node;
        while ((node = walker.nextNode())) {
            if (node.nodeValue.trim().toLowerCase() === "xem bài viết") {
                viewPostNode = node.parentElement;
                break;
            }
        }

        if (viewPostNode) {
            console.log("🔍 Click chuẩn xác nút 'Xem bài viết'...");
            const initialDialogCount = document.querySelectorAll('div[role="dialog"]').length;
            
            // Tìm nút có khả năng nhận click thực tế
            const clickable = viewPostNode.closest('a') || viewPostNode.closest('[role="button"]') || viewPostNode;
            clickable.click();

            // [Cập nhật 2] Chờ Modal bật lên một cách thông minh (tối đa 6 giây)
            let targetDialog = null;
            for (let i = 0; i < 15; i++) {
                await delay(400); 
                const currentDialogs = document.querySelectorAll('div[role="dialog"]');
                if (currentDialogs.length > initialDialogCount) {
                    targetDialog = currentDialogs[currentDialogs.length - 1]; // Bắt Modal vừa sinh ra
                    break;
                }
            }

            if (targetDialog) {
                console.log("✅ Đã bắt được Modal bài gốc. Trích xuất dữ liệu...");
                await delay(1000); // Chờ DOM trong Modal render text xong
                
                let realCaption = extractCaptionFromNode(targetDialog);
                captionText = realCaption ? `${realCaption}\n\nA` : "A";

                // [Cập nhật 3] Chỉ tìm nút Đóng ở BÊN TRONG Modal này
                const closeBtn = targetDialog.querySelector('[aria-label="Đóng"], [aria-label="Close"]');
                if (closeBtn) {
                    closeBtn.click();
                    console.log("✅ Đã đóng Modal.");
                } else {
                    console.warn("⚠️ Không tìm thấy nút Đóng, dùng ESC bảo vệ.");
                    document.dispatchEvent(new KeyboardEvent('keydown', { 'key': 'Escape', 'bubbles': true }));
                }
                
                await delay(1000); // Chờ Modal thu lại hoàn toàn
            } else {
                console.warn("❌ Lỗi mạng hoặc UI: Modal không hiện ra. Ghi nhận Fallback.");
                captionText = "A"; 
            }
        }
    }
    // =================================================================

    if (seenIds.has(postId)) {
        duplicateCount++;
        if (duplicateCount >= MAX_DUPLICATES) {
            console.log("✅ Đã chạm tới dữ liệu cũ. Hoàn tất tiến trình.");
            if (currentPost) await sendToFastAPI(currentPost);
            isScraping = false;
            return;
        }
    } else {
        duplicateCount = 0; 
    }

    if (!currentPost) {
        currentPost = { post_id: postId, caption: captionText, image_urls: [] };
        if (hdImageUrl) currentPost.image_urls.push(hdImageUrl);
    } else if (currentPost.post_id === postId) {
        if (!currentPost.caption && captionText) currentPost.caption = captionText;
        if (hdImageUrl && !currentPost.image_urls.includes(hdImageUrl)) {
            currentPost.image_urls.push(hdImageUrl);
        }
    } else {
        await sendToFastAPI(currentPost);
        seenIds.add(currentPost.post_id);
        
        currentPost = { post_id: postId, caption: captionText, image_urls: [] };
        if (hdImageUrl) currentPost.image_urls.push(hdImageUrl);
    }

    const nextButton = document.querySelector(
        '[aria-label*="Next"], [aria-label*="next"], [aria-label*="Tiếp"], [aria-label*="tiếp"]'
    );

    if (nextButton) {
        try {
            nextButton.click();
            setTimeout(scrapeCurrentModal, 2500); 
        } catch (error) {
            console.error("❌ Lỗi click nút Next:", error);
            isScraping = false;
        }
    } else {
        console.log("⏹️ Không tìm thấy nút Next. Đã đến cuối danh sách ảnh.");
        if (currentPost) await sendToFastAPI(currentPost);
        isScraping = false;
    }
}

async function sendToFastAPI(postData) {
    if (!postData.post_id || postData.post_id === "unknown_id" || postData.image_urls.length === 0) return;
    try {
        await fetch("http://localhost:8000/api/ingest", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(postData)
        });
        console.log(`📤 Đã gửi thành công: ${postData.post_id}`);
    } catch (error) {
        console.error(`❌ Lỗi kết nối gửi bài ${postData.post_id}:`, error);
    }
}