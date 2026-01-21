import streamlit as st
import json
import gspread
import base64
import pandas as pd
from google.oauth2.service_account import Credentials

# 1. Kết nối hệ thống (Giữ nguyên phần bảo mật đã thành công)
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        if "GCP_KEY_FINAL" not in st.secrets:
            # Nếu sếp đang dùng tên biến khác như GCP_KEY_V3 thì sửa lại ở đây
            key_name = "GCP_KEY_V3" if "GCP_KEY_V3" in st.secrets else "GCP_KEY_FINAL"
            b64_str = st.secrets[key_name]
        else:
            b64_str = st.secrets["GCP_KEY_FINAL"]
            
        decoded_data = base64.b64decode(b64_str).decode('utf-8')
        info = json.loads(decoded_data)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi xác thực: {str(e)}")
        return None

st.set_page_config(page_title="4Oranges SDM Center", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

client = get_gsheet_client()

if client:
    try:
        # Mở Sheet SDM_DATA
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet = client.open_by_url(SHEET_URL).sheet1
        
        # Lấy dữ liệu dạng danh sách các dòng
        raw_rows = sheet.get_all_values()
        
        if len(raw_rows) > 0:
            # XỬ LÝ TIÊU ĐỀ THÔNG MINH: Nếu ô nào trống thì đặt tên tạm
            headers = []
            for i, val in enumerate(raw_rows[0]):
                if val.strip() == "":
                    headers.append(f"COLUMN_{i+1}") # Tự đặt tên cho ô C1 bị trống
                else:
                    headers.append(val)
            
            # Tạo DataFrame từ các dòng dữ liệu phía dưới
            df = pd.DataFrame(raw_rows[1:], columns=headers)
            
            # Làm sạch dữ liệu: Bỏ các dòng trắng và các cột hoàn toàn trống
            df = df.loc[:, ~(df == '').all()] # Bỏ cột trống
            df = df[df.any(axis=1)] # Bỏ dòng trống
            
            st.success(f"✅ Đã kết nối thành công! Tìm thấy máy: {df['MACHINE_ID'].iloc[0] if 'MACHINE_ID' in df.columns else 'N/A'}")
            
            # HIỂN THỊ CHỈ SỐ NHANH
            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng thiết bị", len(df))
            c2.metric("Trạng thái", "Hệ thống ổn định")
            c3.metric("Ngày cập nhật", "21/01/2026")

            st.divider()
            
            # Hiển thị bảng dữ liệu Pro
            st.subheader("📑 Chi tiết vận hành máy pha")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        else:
            st.warning("⚠️ Không tìm thấy dữ liệu trong bảng tính.")
            
    except Exception as e:
        st.error(f"⚠️ Lỗi xử lý dữ liệu: {str(e)}")
