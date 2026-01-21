import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd

st.set_page_config(page_title="4Oranges SDM - AI Command Center", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

# --- HÀM KẾT NỐI VÀ LẤY DỮ LIỆU ---
def fetch_data():
    try:
        # 1. Giải mã Key từ Secrets
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        decoded = base64.b64decode(st.secrets[k_name]).decode('utf-8')
        info = json.loads(decoded)
        
        # 2. Thiết lập quyền truy cập
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scope)
        client = gspread.authorize(creds)
        
        # 3. Mở Sheet (Dùng ID file cố định của sếp)
        # ID này nằm giữa /d/ và /edit trong link Google Sheet của sếp
        SHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH"
        
        # Thử mở bằng ID (Cách chắc chắn nhất cho Service Account)
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.get_worksheet(0) # Lấy trang tính đầu tiên
        
        # 4. Đọc dữ liệu
        data = worksheet.get_all_records()
        return pd.DataFrame(data), info.get("client_email"), None
    except Exception as e:
        return None, None, str(e)

# Chạy lệnh lấy dữ liệu
df, email, err = fetch_data()

if df is not None:
    st.success(f"✅ KẾT NỐI THÀNH CÔNG! (Tài khoản: {email})")
    
    # Hiển thị Dashboard chuyên nghiệp
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("MÁY PHA", str(df['MACHINE_ID'].iloc[0]) if 'MACHINE_ID' in df.columns else "N/A")
    with c2: st.metric("TRẠNG THÁI", str(df['STATUS'].iloc[0]) if 'STATUS' in df.columns else "N/A")
    with c3: st.metric("TỔNG BẢN GHI", len(df))
    
    st.divider()
    
    st.subheader("📑 Nhật ký vận hành thiết bị")
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    if st.button("🔄 Cập nhật dữ liệu"):
        st.cache_data.clear()
        st.rerun()
else:
    st.error(f"⚠️ Vẫn còn chút vướng mắc: {err}")
    st.info("Mẹo: Sếp hãy kiểm tra xem ID file trong code đã khớp với ID trên trình duyệt của sếp chưa nhé.")
