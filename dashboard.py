import streamlit as st
import pandas as pd
import json
import base64
from google.oauth2.service_account import Credentials
import gspread

st.set_page_config(page_title="4Oranges Secure Dashboard", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

# --- HÀM LẤY DỮ LIỆU KHÔNG QUA TRUNG GIAN LỖI ---
def load_data_securely():
    try:
        # 1. Giải mã chìa khóa từ Secrets
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        decoded = base64.b64decode(st.secrets[k_name]).decode('utf-8')
        info = json.loads(decoded)
        
        # 2. Thiết lập quyền
        creds = Credentials.from_service_account_info(
            info, 
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(creds)
        
        # 3. Mở Sheet bằng ID
        SHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH"
        sh = client.open_by_key(SHEET_ID)
        df = pd.DataFrame(sh.sheet1.get_all_records())
        
        return df, info.get("client_email")

    except Exception as e:
        st.error(f"❌ LỖI HỆ THỐNG: {str(e)}")
        return None, None

# Thực thi
df, email = load_data_securely()

if df is not None:
    st.success(f"✅ KẾT NỐI THÀNH CÔNG (Tài khoản: {email})")
    
    # Hiển thị Dashboard
    c1, c2 = st.columns([1, 4])
    with c1:
        st.metric("MÁY PHA", str(df.iloc[0, 0]) if not df.empty else "N/A")
        st.metric("TRẠNG THÁI", str(df.iloc[0, 1]) if not df.empty else "N/A")
    with c2:
        st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.warning("🔄 Đang đợi sếp xử lý quyền truy cập trên Google Sheet...")
    st.info(f"📧 Sếp hãy đảm bảo email này đã là 'Editor': \n\n `{email if email else 'Đang tải...'}`")
