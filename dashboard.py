import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd

st.set_page_config(page_title="4Oranges SDM - Final Fix", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

# --- HÀM KẾT NỐI CHUẨN ---
def start_connection():
    try:
        # 1. Giải mã Key
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
        
        # 2. Cấp quyền
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scope)
        client = gspread.authorize(creds)
        
        # 3. ID FILE GỐC (Trích xuất từ link sếp gửi)
        # Link: docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJw/edit
        # ID CHUẨN LÀ CỤM DƯỚI ĐÂY:
        SHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJw"
        
        # Mở bằng ID - Đây là cách an toàn nhất tránh lỗi 404
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.get_worksheet(0)
        
        # Đọc dữ liệu
        data = worksheet.get_all_values()
        return data, None
    except Exception as e:
        return None, str(e)

# Chạy lệnh
data, err = start_connection()

if data:
    st.success("✅ KẾT NỐI THÀNH CÔNG - ĐÃ ĐỌC ĐƯỢC DỮ LIỆU!")
    
    # Bước 2 sếp giao: In tên cột
    headers = data[0]
    st.write("### 📋 Các cột trong hệ thống:")
    cols = st.columns(len(headers))
    for i, h in enumerate(headers):
        cols[i].info(f"**{h}**")
    
    # In bảng dữ liệu
    st.write("### 📑 Bảng dữ liệu thực tế:")
    df = pd.DataFrame(data[1:], columns=headers)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    if st.button("🔄 Làm mới"):
        st.rerun()
else:
    st.error(f"❌ Vẫn vướng tại: {err}")
    st.info("💡 Sếp lưu ý: ID file là chuỗi ký tự nằm giữa /d/ và /edit trong link trình duyệt của sếp.")
