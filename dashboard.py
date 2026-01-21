import streamlit as st
import json
import gspread
import base64
import pandas as pd
from google.oauth2.service_account import Credentials

def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # 1. Giải mã Base64 sạch từ Secrets
        if "gcp_base64" not in st.secrets:
            st.error("❌ Thiếu 'gcp_base64' trong Secrets!")
            return None
            
        decoded_data = base64.b64decode(st.secrets["gcp_base64"]).decode('utf-8')
        info = json.loads(decoded_data)
        
        # 2. Nạp trực tiếp vào bộ nhớ - Phương pháp chuẩn Pro
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi xác thực JWT: {str(e)}")
        return None

# --- UI ĐIỀU HÀNH ---
client = get_gsheet_client()
if client:
    try:
        # ID Sheet của sếp
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet_obj = client.open_by_url(SHEET_URL).sheet1
        
        df = pd.DataFrame(sheet_obj.get_all_records())
        
        st.title("🛡️ 4Oranges AI Command Center")
        st.success("✅ Kết nối Google Cloud thành công!")
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"⚠️ Lỗi truy cập dữ liệu: {e}")
        st.info("Mẹo: Hãy kiểm tra xem Email trong file JSON đã được Share quyền Editor vào Sheet chưa.")
