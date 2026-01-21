import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd

st.title("🛡️ 4Oranges SDM - Kết nối Thành công")

try:
    # 1. Kết nối
    k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
    info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
    creds = Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    
    # 2. Mở Sheet
    SHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH"
    sh = client.open_by_key(SHEET_ID)
    worksheet = sh.get_worksheet(0)
    
    # 3. Lấy dữ liệu
    data = worksheet.get_all_values()
    
    if data:
        st.success("✅ ĐÃ THÔNG SUỐT DỮ LIỆU!")
        
        # In tên cột (Bước 2 sếp giao)
        headers = data[0]
        st.write("### 📋 Danh sách các cột:")
        cols = st.columns(len(headers))
        for i, h in enumerate(headers):
            cols[i].info(f"**{h}**")
            
        # In bảng dữ liệu
        st.write("### 📑 Dữ liệu hiện tại:")
        df = pd.DataFrame(data[1:], columns=headers)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    if st.button("🔄 Làm mới dữ liệu"):
        st.rerun()

except Exception as e:
    st.error(f"Vẫn chưa truy cập được. Lý do: {e}")
    st.info("Sếp hãy kiểm tra lại nút Share trên Google Sheet cho email sdm-manage@...")
