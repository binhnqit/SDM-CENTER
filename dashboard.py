import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials

# 1. Kết nối thẳng vào Google Sheet
def get_client():
    try:
        # Tự động quét tìm Key trong Secrets của sếp
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
        # Mở Sheet bằng URL
        url = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sh = client.open_by_url(url).sheet1
        
        # Lấy toàn bộ dữ liệu thô (Mảng 2 chiều)
        raw_data = sh.get_all_values()
        
        if raw_data:
            st.success("✅ ĐÃ KẾT NỐI - DỮ LIỆU THỰC TẾ TRÊN SHEET:")
            
            # 2. Hiển thị Dashboard đơn giản
            # Lấy dòng 2 (Dòng dữ liệu đầu tiên) để hiện thông số nhanh
            if len(raw_data) > 1:
                top = raw_data[1]
                c1, c2 = st.columns(2)
                c1.metric("MÁY PHA", top[0] if top[0] else "---")
                c2.metric("TRẠNG THÁI", top[1] if top[1] else "---")
            
            st.divider()
            
            # 3. HIỂN THỊ BẢNG DỮ LIỆU (Dùng hàm cơ bản nhất của Streamlit)
            # Hàm này sẽ hiện đúng những gì sếp thấy trên Google Sheet
            st.write("### 📑 Chi tiết bảng dữ liệu (5x5)")
            st.table(raw_data) 
            
            if st.button("🔄 Bấm để làm mới dữ liệu"):
                st.rerun()
        else:
            st.warning("Sheet không có dữ liệu.")
    except Exception as e:
        st.error(f"Lỗi đọc Sheet: {str(e)}")
else:
    st.error("❌ Lỗi kết nối Google Cloud. Sếp kiểm tra lại Secrets nhé.")
