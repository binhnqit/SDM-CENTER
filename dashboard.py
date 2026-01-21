import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials

# 1. Kết nối (Dùng lại đúng cái chìa khóa sếp đã mở được lúc nãy)
def get_client():
    try:
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        info = json.loads(base64.b64decode(st.secrets[k_name]).decode())
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except: return None

st.set_page_config(page_title="4Oranges SDM", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

client = get_client()

if client:
    try:
        # ID Sheet lấy từ link của sếp
        SPREADSHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH"
        sh = client.open_by_key(SPREADSHEET_ID)
        worksheet = sh.get_worksheet(0)
        
        # LẤY DỮ LIỆU DẠNG DANH SÁCH (Mảng thô)
        data = worksheet.get_all_values()
        
        if data:
            st.success("✅ KẾT NỐI LẠI THÀNH CÔNG!")
            
            # CHỈ DÙNG 1 HÀM DUY NHẤT ĐỂ HIỂN THỊ - KHÔNG CHIA CỘT PHỨC TẠP
            # Để tránh lỗi Streamlit không dựng được giao diện
            st.write("### Dữ liệu máy pha thực tế:")
            st.dataframe(data) # Dùng dataframe cơ bản nhất, nó rất bền
            
            if st.button("🔄 Bấm để ép tải lại dữ liệu"):
                st.rerun()
        else:
            st.warning("⚠️ Sheet trống.")
            
    except Exception as e:
        st.error(f"❌ Lỗi phát sinh: {str(e)}")
        st.info("Mẹo: Nếu lỗi, sếp hãy vào 'Manage app' -> chọn 'Reboot App' để xóa bộ nhớ đệm.")
else:
    st.error("❌ Không tìm thấy Key trong Secrets. Sếp kiểm tra lại nhé.")
