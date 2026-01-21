import time
import requests
import os
import uuid

# Lấy ID duy nhất của phần cứng
def get_hwid():
    return str(uuid.getnode())

def check_for_commands():
    # Giả lập đọc lệnh từ Google Sheet/Server
    # Nếu lệnh là "Update_v12" -> Tải file từ GitHub đẩy vào thư mục C:\ProgramData\...
    # Nếu lệnh là "Lock" -> Khóa máy
    pass

def heartbeat():
    print(f"[{get_hwid()}] Đang báo cáo trạng thái Online...")
    # Gửi tín hiệu về Database

if __name__ == "__main__":
    print("Agent SDM đang khởi động...")
    while True:
        heartbeat()
        check_for_commands()
        time.sleep(60) # Gửi tín hiệu mỗi 1 phút
