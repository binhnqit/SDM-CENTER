import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Kiểm tra xem tiêu đề [gcp_service_account] có tồn tại không
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Lỗi: Không tìm thấy mục [gcp_service_account] trong Secrets!")
        st.info("Sếp hãy kiểm tra lại xem đã có dòng [gcp_service_account] ở đầu phần Secrets chưa.")
        return None
        
    try:
        # Nạp dữ liệu từ Secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # Làm sạch khóa (xử lý các ký tự xuống dòng dư thừa)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].strip()
            
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi nạp bảo mật chi tiết: {str(e)}")
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
