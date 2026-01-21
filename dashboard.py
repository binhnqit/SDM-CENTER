import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="4Oranges SDM - AI Command Center", layout="wide")

# --- KẾT NỐI HỆ THỐNG (Giữ nguyên từ VerBase) ---
@st.cache_resource
def get_gspread_client():
    k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
    info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(creds)

client = get_gspread_client()
SHEET_ID = "1LClTdR0z_FPX2AkYCfrbBRtWO8BWOG08hAEB8aq-TcI" 
sh = client.open_by_key(SHEET_ID)
worksheet = sh.get_worksheet(0)

# --- GIAO DIỆN CHÍNH ---
st.title("🛡️ 4Oranges SDM - AI Command Center")

# Load dữ liệu và làm sạch
data = worksheet.get_all_records()
df = pd.DataFrame(data)
# Loại bỏ các dòng trống nếu có để tránh lỗi index
df = df[df['MACHINE_ID'] != ""].reset_index(drop=True)

# --- 1. THEO DÕI TỔNG QUAN (Metrics) ---
total_devices = len(df)
online_devices = len(df[df['STATUS'] == 'Online'])

m1, m2, m3 = st.columns(3)
m1.metric("TỔNG THIẾT BỊ", total_devices)
m2.metric("ĐANG TRỰC TUYẾN", online_devices, delta=f"{online_devices/total_devices:.0%}")
m3.metric("LỆNH CUỐI", df['COMMAND'].iloc[0] if not df.empty else "N/A")

st.divider()

# --- 2. KHU VỰC ĐIỀU KHIỂN CHI TIẾT (Nâng cấp từ VerBase) ---
st.subheader("🎮 Trung tâm Phát lệnh Điều khiển")

with st.container(border=True):
    col_target, col_cmd, col_btn = st.columns([2, 2, 1])
    
    with col_target:
        # Cho phép sếp chọn máy muốn gửi lệnh
        target_machine = st.selectbox("🎯 Chọn máy mục tiêu:", df['MACHINE_ID'].tolist())
    
    with col_cmd:
        # Danh sách lệnh mở rộng
        cmd_options = ["NONE", "LOCK", "UNLOCK", "START_DISPENSING", "STOP_EMERGENCY", "CLEAN_SYSTEM"]
        cmd_input = st.selectbox("📜 Chọn lệnh vận hành:", cmd_options)
        
    with col_btn:
        st.write("##")
        if st.button("🚀 GỬI LỆNH NGAY", use_container_width=True, type="primary"):
            # Tìm vị trí dòng của máy được chọn (Sheets bắt đầu từ 1, +1 cho Header, +index)
            target_idx = df[df['MACHINE_ID'] == target_machine].index[0]
            row_to_update = int(target_idx) + 2 # Header là 1, data bắt đầu từ 2
            
            # Ghi lệnh (Cột 3) và Thời gian (Cột 4)
            now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            worksheet.update_cell(row_to_update, 3, cmd_input)
            worksheet.update_cell(row_to_update, 4, now)
            
            st.toast(f"Đã gửi lệnh {cmd_input} tới {target_machine}", icon="🚀")
            st.rerun()

# --- 3. QUẢN LÝ TRẠNG THÁI (Dữ liệu chi tiết) ---
st.subheader("📑 Danh sách thiết bị & Nhật ký")

# Highlight máy đang Online/Offline
def highlight_status(val):
    color = '#d4edda' if val == 'Online' else '#f8d7da'
    return f'background-color: {color}'

if not df.empty:
    st.dataframe(
        df.style.applymap(highlight_status, subset=['STATUS']),
        use_container_width=True,
        hide_index=True
    )

if st.button("🔄 Làm mới toàn bộ"):
    st.cache_data.clear()
    st.rerun()
