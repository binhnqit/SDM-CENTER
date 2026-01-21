import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd

# 1. Kết nối (Dùng phương thức trực tiếp nhất)
def get_client():
    try:
        # Lấy Key từ bất kỳ biến nào sếp đã lưu trong Secrets
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        info = json.loads(base64.b64decode(st.secrets[k_name]).decode())
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except: return None

st.set_page_config(page_title="4Oranges SDM", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

client = get_client()

if client:
    try:
        # Mở đúng file Sheet của sếp
        url = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sh = client.open_by_url(url).sheet1
        
        # Đọc toàn bộ dữ liệu dưới dạng bảng thô
        rows = sh.get_all_values()
        
        if len(rows) > 0:
            # Ép đúng 5 tên cột theo ảnh sếp gửi
            cols = ["MACHINE_ID", "STATUS", "COMMAND", "LAST_SEEN", "HISTORY"]
            
            # Chỉ lấy dữ liệu từ dòng 2, và chỉ lấy đúng 5 cột đầu tiên
            data = [r[:5] for r in rows[1:]]
            
            # Tạo bảng hiển thị
            df = pd.DataFrame(data, columns=cols)
            
            # HIỂN THỊ NGAY LẬP TỨC
            st.success("✅ KẾT NỐI THÀNH CÔNG")
            
            # Hiển thị bảng dữ liệu sếp cần
            st.table(df) # Dùng st.table để hiện dữ liệu thô, rõ ràng nhất
            
        else:
            st.warning("Sheet đang trống.")
    except Exception as e:
        st.error(f"Lỗi: {e}")
else:
    st.error("Chưa kết nối được Google Cloud. Kiểm tra lại mục Secrets.")
