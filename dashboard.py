import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials

# 1. Kết nối (Quét sạch Secrets)
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
        # ID Sheet lấy từ link sếp gửi
        SPREADSHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH"
        sh = client.open_by_key(SPREADSHEET_ID)
        worksheet = sh.get_worksheet(0)
        
        # LẤY DỮ LIỆU DẠNG MẢNG ĐƠN GIẢN NHẤT
        data = worksheet.get_all_values()
        
        if data:
            st.success("✅ KẾT NỐI THÀNH CÔNG")
            
            # CHỈ HIỂN THỊ DỮ LIỆU THÔ - KHÔNG XỬ LÝ
            # Sếp sẽ thấy y hệt như trên Google Sheet
            for row in data:
                # Tạo các cột nhỏ để hiển thị dữ liệu từng dòng
                cols = st.columns(len(row))
                for i, cell_value in enumerate(row):
                    cols[i].write(f"**{cell_value}**" if data.index(row) == 0 else cell_value)
            
            if st.button("🔄 Cập nhật"):
                st.rerun()
        else:
            st.warning("Sheet trống.")
            
    except Exception as e:
        st.error(f"❌ Lỗi: {str(e)}")
        st.info("Hãy chắc chắn sếp đã Share quyền Editor cho email Service Account.")
else:
    st.error("❌ Kiểm tra lại Secrets (Base64).")
