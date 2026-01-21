import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials

# 1. Kết nối trực tiếp (Quét sạch các lỗi bảo mật/đường truyền)
def get_client():
    try:
        # Tìm Key trong Secrets của sếp (Tự động nhận diện mọi tên biến)
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        decoded = base64.b64decode(st.secrets[k_name]).decode()
        info = json.loads(decoded)
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except: return None

st.set_page_config(page_title="4Oranges SDM Center", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

client = get_client()

if client:
    try:
        # Mở Sheet bằng URL thực tế của sếp
        url = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sh = client.open_by_url(url).sheet1
        
        # LẤY DỮ LIỆU THÔ (Dạng mảng 2 chiều cơ bản nhất)
        all_data = sh.get_all_values()
        
        if all_data:
            st.success("✅ HỆ THỐNG ĐÃ THÔNG SUỐT!")
            
            # --- HIỂN THỊ CÁC Ô CHỈ SỐ NHANH ---
            if len(all_data) > 1:
                # Lấy dòng đầu tiên có dữ liệu (Dòng 2 trên Sheet)
                row2 = all_data[1]
                c1, c2, c3 = st.columns(3)
                c1.metric("THIẾT BỊ", row2[0] if row2[0] else "---")
                c2.metric("TRẠNG THÁI", row2[1] if row2[1] else "---")
                c3.metric("CẬP NHẬT", row2[3] if row2[3] else "---")
            
            st.divider()
            
            # --- HIỂN THỊ BẢNG DỮ LIỆU (Bản sao 1:1 từ Sheet) ---
            st.write("### 📑 Chi tiết dữ liệu vận hành")
            # Dùng st.table để đảm bảo mọi ô (kể cả ô trống) đều hiện lên rõ ràng
            st.table(all_data)
            
            if st.button("🔄 Làm mới dữ liệu"):
                st.rerun()
        else:
            st.warning("⚠️ Chưa có dữ liệu trong Sheet.")
    except Exception as e:
        st.error(f"⚠️ Lỗi đọc dữ liệu: {e}")
else:
    st.error("❌ Không tìm thấy Key trong Secrets. Sếp hãy kiểm tra lại nhé.")
