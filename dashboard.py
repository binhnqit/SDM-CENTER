import streamlit as st
import json
import gspread
import base64 # Thư viện tiêu chuẩn để giải nén
import pandas as pd
from google.oauth2.service_account import Credentials

def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    try:
        # 1. Lấy chuỗi nén từ Secrets
        if "gcp_base64" not in st.secrets:
            st.error("❌ Thiếu 'gcp_base64' trong Secrets!")
            return None
            
        # 2. Giải mã ngược về JSON gốc ngay trong RAM
        base64_str = st.secrets["gcp_base64"]
        decoded_bytes = base64.b64decode(base64_str)
        info = json.loads(decoded_bytes)
        
        # 3. Nạp bảo mật - Chống mọi lỗi substrate/padding
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
        
    except Exception as e:
        st.error(f"❌ Lỗi xác thực: {str(e)}")
        return None

# --- LUỒNG HIỂN THỊ ---
client = get_gsheet_client()
if client:
    try:
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet_obj = client.open_by_url(SHEET_URL).sheet1
        df = pd.DataFrame(sheet_obj.get_all_records())
        
        st.success("✅ HỆ THỐNG 4ORANGES TRỰC TUYẾN")
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"⚠️ Lỗi Sheet: {e}")
