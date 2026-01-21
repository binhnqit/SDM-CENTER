import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="4Oranges SDM - AI Command Center", layout="wide")

# --- KẾT NỐI HỆ THỐNG ---
@st.cache_resource
def get_gspread_client():
    k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
    info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(creds)

client = get_gspread_client()
SHEET_ID = "1LClTdR0z_FPX2AkYCfrbBRtWO8BWOG08hAEB8aq-TcI" # ID chuẩn sếp vừa fix
sh = client.open_by_key(SHEET_ID)
worksheet = sh.get_worksheet(0)

# --- GIAO DIỆN CHÍNH ---
st.title("🛡️ 4Oranges SDM - AI Command Center")

# Load dữ liệu
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# Khu vực hiển thị Metrics
c1, c2, c3 = st.columns(3)
with c1: st.metric("MÁY PHA", df['MACHINE_ID'].iloc[0])
with c2: st.metric("TRẠNG THÁI", df['STATUS'].iloc[0])
with c3: st.metric("LẦN CUỐI THẤY", df['LAST_SEEN'].iloc[0])

st.divider()

# --- KHU VỰC ĐIỀU KHIỂN (COMMAND) ---
st.subheader("🎮 Bảng điều khiển lệnh")
with st.container(border=True):
    col_input, col_btn = st.columns([3, 1])
    
    with col_input:
        # Danh sách lệnh mẫu hoặc sếp tự nhập
        cmd_input = st.selectbox("Chọn lệnh vận hành:", 
                                ["NONE", "START_DISPENSING", "STOP_EMERGENCY", "CLEAN_SYSTEM", "UPDATE_FIRMWARE"])
    
    with col_btn:
        st.write("##") # Căn lề nút
        if st.button("🚀 GỬI LỆNH", use_container_width=True):
            # Ghi lệnh vào dòng 2, cột 3 (Cột COMMAND)
            worksheet.update_cell(2, 3, cmd_input)
            # Cập nhật thời gian gửi lệnh vào cột 4
            now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            worksheet.update_cell(2, 4, now)
            
            st.toast(f"Đã gửi lệnh: {cmd_input}", icon="✅")
            st.rerun()

# --- BẢNG DỮ LIỆU ---
st.subheader("📑 Dữ liệu chi tiết từ hệ thống")
st.dataframe(df, use_container_width=True, hide_index=True)

if st.button("🔄 Làm mới dữ liệu"):
    st.cache_data.clear()
    st.rerun()
