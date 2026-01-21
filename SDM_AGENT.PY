import os
import time
import requests
import tkinter as tk
from threading import Thread
import uuid

# --- CẤU HÌNH ---
SERVER_API = "URL_CUA_DASHBOARD_STREAMLIT_HOAC_SHEET" # Trạm điều khiển
UPDATE_PATH = r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Updates"
MACHINE_ID = str(uuid.getnode()) # ID duy nhất theo phần cứng

class LockScreen:
    """Module khóa cứng màn hình"""
    def __init__(self):
        self.root = None

    def start(self, message="THIẾT BỊ ĐÃ BỊ KHÓA TỪ XA. VUI LÒNG LIÊN HỆ QUẢN TRỊ VIÊN."):
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True) # Luôn nằm trên cùng
        self.root.configure(bg='red')
        
        label = tk.Label(self.root, text=message, font=("Arial", 30, "bold"), fg="white", bg="red")
        label.pack(expand=True)
        
        # Chặn nút đóng (X) và phím tắt cơ bản
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self.root.mainloop()

    def stop(self):
        if self.root:
            self.root.destroy()

lock_system = LockScreen()

def handle_commands():
    """Kiểm tra và thực thi lệnh từ sếp"""
    while True:
        try:
            # Giả lập đọc lệnh từ Dashboard (Sếp có thể thay bằng API thật)
            response = requests.get(f"{SERVER_API}/get_cmd?id={MACHINE_ID}").json()
            cmd = response.get("cmd")

            if cmd == "LOCK":
                if not lock_system.root: # Nếu chưa khóa thì mới kích hoạt
                    Thread(target=lock_system.start).start()
            
            elif cmd == "UNLOCK":
                lock_system.stop()

            elif cmd == "UPDATE":
                file_url = response.get("url")
                filename = file_url.split("/")[-1]
                r = requests.get(file_url)
                with open(os.path.join(UPDATE_PATH, filename), 'wb') as f:
                    f.write(r.content)
                print(f"Đã đẩy file {filename} vào thư mục Updates.")

        except:
            pass
        time.sleep(10) # 10 giây kiểm tra lệnh 1 lần

if __name__ == "__main__":
    if not os.path.exists(UPDATE_PATH):
        os.makedirs(UPDATE_PATH)
    
    print(f"Agent đang chạy ngầm trên máy: {MACHINE_ID}")
    handle_commands()
