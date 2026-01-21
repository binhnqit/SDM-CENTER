import streamlit as st
import json
import gspread
import base64
import pandas as pd
from google.oauth2.service_account import Credentials

# Sử dụng tên biến mới để ép Streamlit xóa cache cũ
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # Kiểm tra biến mới
        if "GCP_KEY_FINAL" not in st.secrets:
            st.error("❌ Chưa tìm thấy biến 'GCP_KEY_FINAL' trong Secrets!")
            return None
            
        # Giải mã Base64
        b64_str = st.secrets["GCP_KEY_FINAL"]
        decoded_data = base64.b64decode(b64_str).decode('utf-8')
        info = json.loads(decoded_data)
        
        # Nạp bảo mật - Dùng library mới nhất
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi xác thực hệ thống: {str(e)}")
        return None

# --- CHƯƠNG TRÌNH CHÍNH ---
st.title("🛡️ 4Oranges SDM - AI Command Center")

client = get_gsheet_client()

if client:
    try:
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        # Mở Sheet và ép làm mới dữ liệu
        sheet_obj = client.open_by_url(SHEET_URL).sheet1
        data = sheet_obj.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            st.success("✅ ĐÃ THÔNG SUỐT HỆ THỐNG VỚI KEY MỚI!")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("💡 Kết nối thành công nhưng Sheet chưa có dữ liệu.")
            
    except Exception as e:
        st.error(f"⚠️ Lỗi truy cập: {str(e)}")
