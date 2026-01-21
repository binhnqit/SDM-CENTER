import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Không tìm thấy Secrets!")
        return None
        
    try:
        # 1. Lấy dữ liệu từ Secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # 2. XỬ LÝ CHUỖI PRIVATE_KEY (Cực kỳ quan trọng)
        raw_key = creds_dict["private_key"]
        
        # Loại bỏ các ký tự xuống dòng bị lặp lại hoặc khoảng trắng lạ
        # Bước này giải quyết lỗi "Invalid base64-encoded string"
        lines = raw_key.split('\n')
        clean_lines = []
        for line in lines:
            line = line.strip()
            if line:
                clean_lines.append(line)
        
        # Ghép lại với ký tự xuống dòng chuẩn \n
        fixed_key = "\n".join(clean_lines)
        
        # Đảm bảo có đúng cấu trúc đầu cuối
        if "-----BEGIN PRIVATE KEY-----" not in fixed_key:
            fixed_key = "-----BEGIN PRIVATE KEY-----\n" + fixed_key
        if "-----END PRIVATE KEY-----" not in fixed_key:
            fixed_key = fixed_key + "\n-----END PRIVATE KEY-----"
            
        creds_dict["private_key"] = fixed_key
        
        # 3. Nạp vào thư viện Google
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
        
    except Exception as e:
        st.error(f"❌ Lỗi nạp bảo mật: {str(e)}")
        return None

# --- TRIỂN KHAI TIẾP THEO ---
client = get_gsheet_client()
if client:
    st.success("✅ Tuyệt vời sếp ơi! Hệ thống đã thông qua lớp bảo mật.")
    # Tiếp tục logic đọc Sheet ở đây...

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
