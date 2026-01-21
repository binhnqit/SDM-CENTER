import streamlit as st
import json
import gspread
import base64
import pandas as pd
from google.oauth2.service_account import Credentials

# 1. Khởi tạo kết nối
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        if "GCP_KEY_V3" not in st.secrets:
            st.error("❌ Thiếu biến 'GCP_KEY_V3' trong Secrets!")
            return None
        decoded_data = base64.b64decode(st.secrets["GCP_KEY_V3"]).decode('utf-8')
        info = json.loads(decoded_data)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi xác thực: {str(e)}")
        return None

st.title("🛡️ 4Oranges SDM - AI Command Center")

client = get_gsheet_client()

if client:
    try:
        # URL Sheet từ ảnh của sếp
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet = client.open_by_url(SHEET_URL).sheet1
        
        # LẤY DỮ LIỆU VÀ XỬ LÝ LỖI CỘT
        raw_data = sheet.get_all_values() # Lấy toàn bộ mảng thô
        
        if len(raw_data) > 1:
            # Lấy dòng đầu tiên làm tiêu đề, các dòng sau là dữ liệu
            df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
            
            # Xử lý làm sạch: Bỏ các dòng trắng hoàn toàn
            df = df.replace('', pd.NA).dropna(how='all')
            
            st.success(f"✅ Đã kết nối thành công! Tìm thấy {len(df)} dòng dữ liệu.")
            
            # Hiển thị bảng dữ liệu sạch
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Thêm bộ lọc nhanh nếu sếp muốn
            if st.button("🔄 Làm mới dữ liệu"):
                st.rerun()
        else:
            st.warning("⚠️ Sheet đang chỉ có tiêu đề, chưa có dữ liệu máy pha.")
            
    except Exception as e:
        st.error(f"⚠️ Lỗi xử lý bảng tính: {str(e)}")
        st.info("Mẹo: Hãy kiểm tra xem dòng đầu tiên trong Google Sheet của sếp có bị trống ô nào không.")
