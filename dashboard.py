import streamlit as st
import json
import gspread
import base64
import pandas as pd
from google.oauth2.service_account import Credentials

# 1. Kết nối bảo mật (Đã thông suốt)
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # Tự động lấy biến Key mới nhất từ Secrets
        key_name = "GCP_KEY_V3" if "GCP_KEY_V3" in st.secrets else "GCP_KEY_FINAL"
        if key_name not in st.secrets:
            st.error(f"❌ Thiếu biến {key_name} trong Secrets!")
            return None
            
        decoded_data = base64.b64decode(st.secrets[key_name]).decode('utf-8')
        info = json.loads(decoded_data)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi xác thực: {str(e)}")
        return None

st.set_page_config(page_title="4Oranges AI Center", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

client = get_gsheet_client()

if client:
    try:
        # ID Sheet từ ảnh sếp gửi
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet = client.open_by_url(SHEET_URL).sheet1
        
        # Lấy dữ liệu dạng mảng thô để xử lý lỗi tiêu đề trống
        raw_rows = sheet.get_all_values()
        
        if len(raw_rows) > 0:
            # Thuật toán tự sửa tiêu đề: Nếu ô trống thì đặt tên là 'COMMAND' (theo ảnh sếp gửi)
            headers = []
            for i, val in enumerate(raw_rows[0]):
                name = val.strip()
                if not name:
                    # Nếu là cột C (index 2) bị trống, đặt là COMMAND
                    headers.append("COMMAND" if i == 2 else f"COL_{i+1}")
                else:
                    headers.append(name)
            
            # Tạo bảng dữ liệu
            df = pd.DataFrame(raw_rows[1:], columns=headers)
            
            # Làm sạch: Loại bỏ các dòng hoàn toàn trống
            df = df.replace('', pd.NA).dropna(how='all')
            
            # --- HIỂN THỊ DASHBOARD ---
            st.success("✅ ĐÃ KẾT NỐI DỮ LIỆU THÀNH CÔNG!")
            
            # Chỉ số tóm tắt
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Tổng thiết bị", len(df))
            with c2:
                online_count = len(df[df['STATUS'].str.contains('Online', na=False)])
                st.metric("Máy đang chạy", online_count)
            with c3:
                st.metric("Trạng thái lệnh", "Đang sẵn sàng")

            st.divider()
            st.subheader("📑 Chi tiết vận hành thiết bị")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        else:
            st.warning("⚠️ Bảng tính đang trống dữ liệu.")
            
    except Exception as e:
        st.error(f"⚠️ Lỗi xử lý bảng tính: {str(e)}")
