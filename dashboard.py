import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials

# --- BƯỚC 1: KIỂM TRA KẾT NỐI ---
def check_connection():
    st.title("🧪 Kiểm tra kết nối & Cấu trúc")
    
    try:
        # Tự động tìm Key trong Secrets
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        if not k_name:
            st.error("❌ Bước 1 Thất bại: Không tìm thấy Key trong mục Secrets.")
            return
        
        # Giải mã Key
        info = json.loads(base64.b64decode(st.secrets[k_name]).decode())
        creds = Credentials.from_service_account_info(
            info, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)
        
        # Mở Sheet bằng ID (Lấy từ URL sếp gửi)
        SPREADSHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH"
        sh = client.open_by_key(SPREADSHEET_ID)
        worksheet = sh.get_worksheet(0)
        
        st.success("✅ Bước 1: Kết nối đến Google Sheet THÀNH CÔNG!")
        
        # --- BƯỚC 2: IN TÊN CỘT ---
        # Lấy duy nhất dòng 1
        headers = worksheet.row_values(1)
        
        if headers:
            st.write("### 📋 Bước 2: Danh sách các cột tìm thấy:")
            for i, name in enumerate(headers):
                st.info(f"Cột số {i+1}: **{name}**")
        else:
            st.warning("⚠️ Bước 2: Kết nối được nhưng không tìm thấy dữ liệu ở dòng 1.")

    except Exception as e:
        st.error(f"❌ Lỗi phát sinh: {str(e)}")
        st.info("Mẹo: Đảm bảo email Service Account đã được Share quyền Editor trong file Sheet.")

# Chạy kiểm tra
check_connection()
