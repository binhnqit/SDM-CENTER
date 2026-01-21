import requests
import time
import os
import re
import platform
import tkinter as tk
from threading import Thread

# --- 1. CẤU HÌNH HỆ THỐNG ---
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwTGw5t9QBUYL3MUdrfIH9OCV4hVEZ4I-No7sIofDetVj4Xg8r1synpvwkdbnLg8R-SJg/exec"

# PHƯƠNG ÁN KẾT HỢP: Tên PC và Tên User để dữ liệu chỉnh chu nhất
try:
    pc_name = platform.node().upper()  # Lấy tên máy tính (Ví dụ: 4ORANGES0001)
    user_name = os.getlogin().upper()  # Lấy tên User đang đăng nhập
    MACHINE_ID = f"{pc_name}-{user_name}"
except:
    MACHINE_ID = f"4ORANGES-UNKNOWN-{time.time_ns() % 1000}"

FDB_PATH = r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Db\History.fdb"

# Biến kiểm soát trạng thái
last_sent_color = ""
last_file_size = 0

class FullscreenLock:
    def __init__(self):
        self.root = None
    def start(self):
        if self.root: return
        try:
            self.root = tk.Tk()
            self.root.attributes("-fullscreen", True, "-topmost", True)
            self.root.configure(bg='black')
            self.root.overrideredirect(True)
            tk.Label(self.root, text="⚠️ THIẾT BỊ TẠM KHÓA ⚠️\n\nVui lòng liên hệ IT 4Oranges.", 
                     font=("Arial", 25, "bold"), fg="red", bg="black").pack(expand=True)
            self.root.mainloop()
        except: pass
    def stop(self):
        if self.root:
            try: self.root.destroy()
            except: pass
            self.root = None

locker = FullscreenLock()

def get_fdb_data_optimized():
    global last_file_size
    if not os.path.exists(FDB_PATH): return None
    
    try:
        current_size = os.path.getsize(FDB_PATH)
        if current_size == last_file_size: return None 
        
        last_file_size = current_size
        with open(FDB_PATH, "rb") as f:
            f.seek(0, 2)
            # Đọc 50KB cuối cùng để tìm dữ liệu màu mới nhất
            f.seek(max(0, f.tell() - 51200))
            chunk = f.read()

        matches = re.findall(b'[A-Z0-9\s\-\.]{6,30}', chunk)
        trash = [b'TABLE', b'INDEX', b'PRIMARY', b'HISTORY', b'SYSTEM']
        
        for m in reversed(matches):
            clean = m.strip().decode('ascii', errors='ignore')
            if len(clean) > 6 and not any(t in m for t in trash):
                if not clean.isdigit(): return clean
        return None
    except: return None

def sdm_worker():
    global last_sent_color
    print(f"--- SDM AGENT V4.1 ENTERPRISE STARTING ---")
    print(f"IDENTIFIER: {MACHINE_ID}") # Hiển thị ID mới để sếp kiểm tra
    
    retry_delay = 15

    while True:
        try:
            current_color = get_fdb_data_optimized()
            
            # Gửi Heartbeat mỗi 5 phút hoặc khi có màu mới
            is_heartbeat = (int(time.time()) % 300 < 25)
            
            if current_color or is_heartbeat:
                color_to_send = current_color if current_color else (last_sent_color if last_sent_color else "IDLE")
                
                params = {
                    'machine_id': MACHINE_ID,
                    'status': 'Online',
                    'history': color_to_send
                }
                
                response = requests.get(WEB_APP_URL, params=params, timeout=25)
                cmd = response.text.strip().upper()
                
                print(f"[{time.strftime('%H:%M:%S')}] {MACHINE_ID} | Color: {color_to_send} | Cmd: {cmd}")
                
                if current_color: last_sent_color = current_color
                retry_delay = 15

                # Điều khiển khóa từ xa
                if "LOCK" in cmd:
                    if not locker.root: Thread(target=locker.start, daemon=True).start()
                else:
                    if locker.root: locker.stop()
            
        except Exception as e:
            print(f"⚠️ Network Busy: Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 300) 
            continue 
            
        time.sleep(25) # Chu kỳ quét

if __name__ == "__main__":
    sdm_worker()