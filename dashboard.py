import streamlit as st
import json
import gspread
import base64
import pandas as pd
from google.oauth2.service_account import Credentials

# Cấu hình trang
st.set_page_config(page_title="4Oranges AI Center", layout="wide")

def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # Kiểm tra biến mới để ép thoát khỏi Cache cũ
        if "GCP_KEY_FINAL" not in st.secrets:
            st.error("❌ Chưa cấu hình 'GCP_KEY_FINAL' trong Secrets!")
            return None
            
        # Giải mã và nạp thẳng vào RAM
        decoded_data = base64.b64decode(st.secrets["GCP_KEY_FINAL"]).decode('utf-8')
        info = json.loads(decoded_data)
        
        # Nạp bảo mật chuẩn Google - Chống lỗi Signature
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi xác thực hệ thống: {str(e)}")
        return None

# --- GIAO DIỆN ĐIỀU HÀNH ---
st.title("🛡️ 4Oranges SDM - AI Command Center")

client = get_gsheet_client()

if client:
    try:
        # URL Sheet sếp cung cấp
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet_obj = client.open_by_url(SHEET_URL).sheet1
        
        # Ép đọc dữ liệu mới nhất
        data = sheet_obj.get_all_records()
        if data:
            df = pd.DataFrame(data)
            st.success("✅ HỆ THỐNG ĐÃ THÔNG SUỐT!")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Kết nối thành công nhưng Sheet chưa có dữ liệu.")
            
    except Exception as e:
        st.error(f"⚠️ Lỗi truy cập: {str(e)}")
        st.info("Mẹo: Hãy chắc chắn Email 'sdm-manage@...' trong ảnh sếp gửi đã có quyền Editor.")
