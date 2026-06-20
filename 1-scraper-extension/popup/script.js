/**
 * TÊN FILE: script.js
 * CHỨC NĂNG: Giao tiếp giữa giao diện người dùng (Popup) và content.js đang chạy trên Tab hiện tại.
 */

const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const statusDiv = document.getElementById('status');

// Lệnh: BẮT ĐẦU
startBtn.addEventListener('click', async () => {
    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    // Validate trang web đang đứng
    if (tab.url.includes("facebook.com/groups") && tab.url.includes("/media")) {
        statusDiv.innerText = "Trạng thái: Đang tiến hành quét...";
        statusDiv.style.color = "#333";
        
        // Khóa nút để tránh click nhiều lần
        startBtn.classList.add("btn-disabled");
        startBtn.disabled = true;

        chrome.tabs.sendMessage(tab.id, { action: "START_SCRAPING" });
    } else {
        statusDiv.innerText = "Lỗi: Vui lòng mở tab Group Facebook mục Media.";
        statusDiv.style.color = "red";
    }
});

// Lệnh: DỪNG
stopBtn.addEventListener('click', async () => {
    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    chrome.tabs.sendMessage(tab.id, { action: "STOP_SCRAPING" });
    
    statusDiv.innerText = "Trạng thái: Đã dừng bằng tay.";
    statusDiv.style.color = "#dc3545";
    
    // Mở khóa lại nút Bắt đầu
    startBtn.classList.remove("btn-disabled");
    startBtn.disabled = false;
});