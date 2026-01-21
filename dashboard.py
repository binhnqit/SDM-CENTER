import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import pandas as pd
from datetime import datetime

def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Chưa cấu hình Secrets!")
        return None
        
    try:
        # 1. Lấy dữ liệu thô
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # 2. CHUYÊN GIA FIX: Loại bỏ hoàn toàn byte lạ (\xac) và rác Base64
        raw_key = creds_dict["private_key"]
        header = "-----BEGIN PRIVATE KEY-----"
        footer = "-----END PRIVATE KEY-----"
        
        # Tách lấy phần lõi mã hóa
        content = raw_key.replace(header, "").replace(footer, "")
        
        # CHỈ giữ lại các ký tự Base64 hợp lệ: A-Z, a-z, 0-9, +, /, =
        # Mọi ký tự khác (bao gồm cả \xac) sẽ bị xóa sạch tại đây
        clean_content = re.sub(r'[^A-Za-z0-9+/=]', '', content)
        
        # Ghép lại định dạng chuẩn RSA cho Google
        creds_dict["private_key"] = f"{header}\n{clean_content}\n{footer}"
        
        # 3. Nạp quyền
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi nạp bảo mật: {str(e)}")
        return None

# --- TRIỂN KHAI GIAO DIỆN CHUYÊN NGHIỆP ---
st.set_page_config(page_title="4Oranges AI Center", layout="wide")
client = get_gsheet_client()

if client:
    try:
        # Link Sheet của sếp
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet = client.open_by_url(SHEET_URL).sheet1
        
        st.success("✅ AI Command Center: Kết nối bảo mật thành công!")
        
        # Đọc dữ liệu
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Hiển thị Dashboard chuyên nghiệp
        st.title("🛡️ Trung Tâm Điều Hành 4Oranges")
        st.dataframe(df, use_container_width=True)
        
    except Exception as e:
        st.error(f"Lỗi truy cập dữ liệu: {e}")
