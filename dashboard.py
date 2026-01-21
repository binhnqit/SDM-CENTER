import streamlit as st
import json
import gspread
import base64
import pandas as pd
from google.oauth2.service_account import Credentials

def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # Tự động tìm biến key trong Secrets
        k = next(v for k, v in st.secrets.items() if "GCP_KEY" in k or "gcp_base64" in k)
        decoded_data = base64.b64decode(k).decode('utf-8')
        info = json.loads(decoded_data)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
    except: return None

st.set_page_config(page_title="4Oranges AI Center", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

client = get_gsheet_client()

if client:
    try:
        # Mở Sheet bằng URL chuẩn
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet = client.open_by_url(SHEET_URL).sheet1
        
        # 1. Lấy dữ liệu dạng mảng thô (Chống lỗi tiêu đề trống)
        raw_rows = sheet.get_all_values()
        
        if len(raw_rows) > 0:
            # 2. Ép tên cột theo đúng thứ tự sếp muốn (A, B, C, D, E)
            standard_headers = ["MACHINE_ID", "STATUS", "COMMAND", "LAST_SEEN", "HISTORY"]
            
            # Nếu Sheet có ít hơn hoặc nhiều hơn 5 cột, chúng ta vẫn xử lý được
            data_rows = raw_rows[1:] # Lấy từ dòng 2 trở đi
            df = pd.DataFrame(data_rows)
            
            # Gán lại tên cột cho chuẩn
            df.columns = standard_headers[:len(df.columns)]
            
            # 3. Làm sạch dữ liệu (Xóa dòng hoàn toàn trống)
            df = df.replace('', pd.NA).dropna(how='all')

            # --- HIỂN THỊ ---
            st.success("✅ ĐÃ KẾT NỐI VÀ ĐỒNG BỘ CỘT THÀNH CÔNG!")
            
            # Dashboard mini
            col1, col2 = st.columns(2)
            col1.metric("Máy đang quản lý", df['MACHINE_ID'].iloc[0] if not df.empty else "N/A")
            col2.metric("Trạng thái hiện tại", df['STATUS'].iloc[0] if not df.empty else "N/A")

            st.divider()
            st.subheader("📑 Nhật ký vận hành hệ thống")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        else:
            st.warning("⚠️ Sheet đang trống.")
    except Exception as e:
        st.error(f"⚠️ Lỗi cấu trúc: {str(e)}")
