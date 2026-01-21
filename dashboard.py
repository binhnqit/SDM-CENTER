import streamlit as st
import json
import gspread
import base64
import pandas as pd
from google.oauth2.service_account import Credentials

# 1. ÉP LÀM SẠCH BỘ NHỚ
st.cache_resource.clear()

def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # Sử dụng biến V3 mới để ép hệ thống thoát khỏi lỗi cũ
        if "GCP_KEY_V3" not in st.secrets:
            st.error("❌ Chưa cấu hình 'GCP_KEY_V3' trong Secrets!")
            return None
            
        # Giải mã và nạp trực tiếp vào RAM
        decoded_data = base64.b64decode(st.secrets["GCP_KEY_V3"]).decode('utf-8')
        info = json.loads(decoded_data)
        
        # Nạp bảo mật chuẩn Google
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi mổ xẻ hệ thống: {str(e)}")
        return None

# --- GIAO DIỆN ĐIỀU HÀNH ---
st.title("🛡️ 4Oranges SDM - AI Command Center")

client = get_gsheet_client()

if client:
    try:
        # ID Sheet chuẩn từ ảnh của sếp
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet_obj = client.open_by_url(SHEET_URL).sheet1
        
        # Đọc dữ liệu thô
        data = sheet_obj.get_all_records()
        if data:
            df = pd.DataFrame(data)
            st.success("✅ ĐÃ THÔNG SUỐT! CHÀO MỪNG SẾP TRỞ LẠI HỆ THỐNG.")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("💡 Kết nối thành công nhưng Sheet đang trống.")
            
    except Exception as e:
        st.error(f"⚠️ Lỗi Sheet: {str(e)}")
