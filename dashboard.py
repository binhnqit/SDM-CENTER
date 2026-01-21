import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd

st.set_page_config(page_title="4Oranges Secure Center", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center (Secure Mode)")

# --- HÀM KẾT NỐI BẢO MẬT ---
def get_secure_client():
    try:
        # Tìm key trong Secrets (Dùng lại chìa khóa cũ của sếp)
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        if not k_name:
            st.error("Chưa cấu hình Key trong Secrets!")
            return None
        
        # Giải mã và cấp quyền
        decoded = base64.b64decode(st.secrets[k_name]).decode()
        info = json.loads(decoded)
        creds = Credentials.from_service_account_info(
            info, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi chìa khóa bảo mật: {e}")
        return None

client = get_secure_client()

if client:
    try:
        # ID Sheet bảo mật (Lấy từ URL của sếp)
        SHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH"
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.get_worksheet(0)
        
        # Lấy dữ liệu
        raw_data = worksheet.get_all_values()
        
        if len(raw_data) > 0:
            st.success("🔒 KẾT NỐI BẢO MẬT THÀNH CÔNG")
            
            # Chuyển thành bảng để hiển thị chuyên nghiệp
            # Cố định đúng 5 cột sếp đã xác nhận ở bước trước
            headers = raw_data[0]
            df = pd.DataFrame(raw_data[1:], columns=headers)
            
            # Hiển thị Dashboard
            st.subheader("📑 Bảng điều khiển thiết bị")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            if st.button("🔄 Refresh Data"):
                st.rerun()
        else:
            st.warning("Sheet trống dữ liệu.")

    except Exception as e:
        st.error(f"Lỗi truy cập bảo mật: {e}")
        st.info("💡 Hãy đảm bảo sếp đã Share quyền Editor cho email Service Account trong Google Sheet.")
