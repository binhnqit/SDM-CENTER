import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Chưa cấu hình Secrets!")
        return None
        
    try:
        # 1. Lấy dữ liệu thô từ Secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # 2. FIX LỖI PADDING: Quan trọng nhất
        # Chúng ta thay thế chuỗi '\\n' thành '\n' thực sự và đảm bảo không có khoảng trắng thừa
        raw_key = creds_dict["private_key"]
        fixed_key = raw_key.replace("\\n", "\n").strip()
        creds_dict["private_key"] = fixed_key
        
        # 3. Khởi tạo kết nối
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi nạp bảo mật chi tiết: {str(e)}")
        # In ra độ dài khóa để kiểm tra (không in ra khóa thật để bảo mật)
        if "private_key" in creds_dict:
            st.info(f"Độ dài khóa hiện tại: {len(creds_dict['private_key'])} ký tự.")
        return None

# --- TRIỂN KHAI GIAO DIỆN ---
client = get_gsheet_client()

if client:
    try:
        # Thay link sheet của sếp vào đây
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit").sheet1
        st.success("✅ AI Command Center: Kết nối bảo mật thành công!")
        
        # Đọc dữ liệu và hiển thị Dashboard
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
    except Exception as e:
        st.error(f"Lỗi truy cập dữ liệu: {e}")
