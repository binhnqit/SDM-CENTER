import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import re

def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Không tìm thấy Secrets!")
        return None
        
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        raw_key = creds_dict["private_key"]

        # --- THUẬT TOÁN DỌN RÁC BASE64 CHUYÊN GIA ---
        # 1. Tách phần đầu và cuối của khóa RSA
        header = "-----BEGIN PRIVATE KEY-----"
        footer = "-----END PRIVATE KEY-----"
        
        # Lấy phần nội dung nằm giữa
        content = raw_key.replace(header, "").replace(footer, "")
        
        # 2. Loại bỏ TOÀN BỘ ký tự xuống dòng, khoảng trắng, tab... 
        # Chỉ giữ lại các ký tự Base64 hợp lệ (A-Z, a-z, 0-9, +, /, =)
        clean_content = re.sub(r'[^A-Za-z0-9+/=]', '', content)
        
        # 3. Ghép lại định dạng chuẩn: Header + Content (đã sạch) + Footer
        # Google yêu cầu phần nội dung phải sạch sẽ hoàn toàn
        fixed_key = f"{header}\n{clean_content}\n{footer}"
        
        creds_dict["private_key"] = fixed_key
        
        # 4. Nạp vào thư viện
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
        
    except Exception as e:
        st.error(f"❌ Lỗi nạp bảo mật: {str(e)}")
        return None

# --- TRIỂN KHAI TIẾP THEO ---
client = get_gsheet_client()
if client:
    st.success("✅ Dashboard 4Oranges: Kết nối bảo mật thành công!")
    # Tiếp tục code đọc sheet của sếp...


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
