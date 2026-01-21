import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd

st.title("🛡️ 4Oranges SDM - AI Command Center")

# --- HÀM KẾT NỐI TỐI GIẢN ---
def connect():
    try:
        # Lấy Key từ Secrets
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
        
        # Thiết lập quyền
        creds = Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi Key: {e}")
        return None

client = connect()

if client:
    try:
        # Mở Sheet bằng ID
        sh = client.open_by_key("1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH")
        df = pd.DataFrame(sh.sheet1.get_all_records())
        
        st.success("✅ ĐÃ THÔNG SUỐT DỮ LIỆU!")
        
        # In tên cột và Bảng
        st.write("### 📋 Các cột hiện có:", ", ".join(df.columns))
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    except Exception as e:
        st.error("❌ VẪN BỊ CHẶN QUYỀN TRUY CẬP (Lỗi 403)")
        st.info("Sếp hãy kiểm tra lại Bước 1 (Share Editor) và Bước 2 (Enable API) ở trên nhé.")
