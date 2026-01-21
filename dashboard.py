import streamlit as st
import json
import gspread
import base64
import pandas as pd
from google.oauth2.service_account import Credentials

# 1. Kết nối (Giữ nguyên phần đã thông suốt)
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # Tự động quét biến Key trong Secrets
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        if not k_name: return None
        decoded_data = base64.b64decode(st.secrets[k_name]).decode('utf-8')
        info = json.loads(decoded_data)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
    except: return None

st.set_page_config(page_title="4Oranges AI Center", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

client = get_gsheet_client()

if client:
    try:
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet = client.open_by_url(SHEET_URL).sheet1
        
        # Lấy dữ liệu thô hoàn toàn
        raw_rows = sheet.get_all_values()
        
        if raw_rows:
            # Thuật toán gán cột linh hoạt:
            # Chúng ta ưu tiên 5 cột chính theo ảnh sếp gửi
            std_cols = ["MACHINE_ID", "STATUS", "COMMAND", "LAST_SEEN", "HISTORY"]
            
            # Tạo bảng từ dữ liệu dòng 2 trở đi
            df = pd.DataFrame(raw_rows[1:])
            
            # Cắt hoặc bù thêm cột cho khớp với dữ liệu thực tế trong Sheet
            actual_col_count = df.shape[1]
            display_cols = std_cols[:actual_col_count]
            
            # Nếu Sheet nhiều cột hơn chuẩn, đặt tên tự động cho cột dư
            if actual_col_count > len(std_cols):
                for i in range(len(std_cols), actual_col_count):
                    display_cols.append(f"EXTRA_{i+1}")
            
            df.columns = display_cols

            # Làm sạch: Loại bỏ dòng trắng hoàn toàn
            df = df.replace('', pd.NA).dropna(how='all')

            # --- GIAO DIỆN CHUYÊN NGHIỆP ---
            st.success("✅ HỆ THỐNG ĐÃ SẴN SÀNG VẬN HÀNH!")
            
            # Hiển thị thông tin máy pha chính (Dòng 2 trong Sheet)
            if not df.empty:
                m_id = df['MACHINE_ID'].iloc[0] if pd.notna(df['MACHINE_ID'].iloc[0]) else "N/A"
                status = df['STATUS'].iloc[0] if pd.notna(df['STATUS'].iloc[0]) else "N/A"
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Thiết bị", m_id)
                c2.metric("Trạng thái", status)
                c3.metric("Kết nối", "Ổn định" if "Online" in status else "Kiểm tra lại")

            st.divider()
            st.subheader("📑 Nhật ký dữ liệu máy pha")
            
            # Hiển thị bảng dữ liệu sạch đẹp
            st.dataframe(df.fillna(""), use_container_width=True, hide_index=True)
            
            if st.button("🔄 Cập nhật dữ liệu mới"):
                st.rerun()
        else:
            st.warning("⚠️ Không tìm thấy dữ liệu trong Sheet.")
            
    except Exception as e:
        st.error(f"⚠️ Lỗi xử lý: {str(e)}")
else:
    st.error("❌ Không thể kết nối Google Cloud. Vui lòng kiểm tra lại Secrets.")
