import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="4Oranges SDM - AI Command Center", layout="wide")

# --- KẾT NỐI HỆ THỐNG (Giữ nguyên VerBase) ---
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

# --- XỬ LÝ DỮ LIỆU ---
# Lấy toàn bộ dữ liệu (không cache để đảm bảo máy mới hiện ra ngay)
all_values = worksheet.get_all_values()
headers = all_values[0]
data_rows = all_values[1:]

# Tạo DataFrame và lọc bỏ dòng trống
df = pd.DataFrame(data_rows, columns=headers)
df = df[df['MACHINE_ID'].str.strip() != ""].reset_index() 
# Lưu index gốc của Google Sheet (index + 2 vì Sheets bắt đầu từ 1 và có Header)
df['sheet_row'] = df['index'] + 2

# --- GIAO DIỆN CHÍNH ---
st.title("🛡️ 4Oranges SDM - AI Command Center")

# Khu vực hiển thị Metrics tổng quát
total_devices = len(df)
online_count = len(df[df['STATUS'].str.upper() == 'ONLINE'])

m1, m2, m3 = st.columns(3)
m1.metric("TỔNG THIẾT BỊ", total_devices)
m2.metric("ĐANG TRỰC TUYẾN", online_count)
m3.metric("LỆNH CUỐI", df['COMMAND'].iloc[-1] if not df.empty else "N/A")

st.divider()

# --- TRUNG TÂM PHÁT LỆNH (Sửa lỗi không chọn được máy thứ 2) ---
st.subheader("🎮 Trung tâm Phát lệnh Điều khiển")

with st.container(border=True):
    col_target, col_cmd, col_btn = st.columns([2, 2, 1])
    
    with col_target:
        # Lấy danh sách ID máy duy nhất và sạch sẽ
        machine_list = df['MACHINE_ID'].unique().tolist()
        selected_machine = st.selectbox("🎯 Chọn máy mục tiêu:", machine_list, key="target_select")
    
    with col_cmd:
        cmd_options = ["NONE", "LOCK", "UNLOCK", "START_DISPENSING", "STOP_EMERGENCY"]
        selected_cmd = st.selectbox("📜 Chọn lệnh vận hành:", cmd_options)
        
    with col_btn:
        st.write("##")
        if st.button("🚀 GỬI LỆNH NGAY", use_container_width=True, type="primary"):
            # Lấy đúng dòng trên Google Sheet của máy được chọn
            row_in_sheet = df[df['MACHINE_ID'] == selected_machine]['sheet_row'].iloc[0]
            
            # Thực hiện cập nhật
            now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            # Cột 3 là COMMAND, Cột 4 là LAST_SEEN
            worksheet.update_cell(int(row_in_sheet), 3, selected_cmd)
            worksheet.update_cell(int(row_in_sheet), 4, now)
            
            st.toast(f"Đã gửi lệnh {selected_cmd} tới {selected_machine}", icon="🚀")
            st.rerun()

# --- DANH SÁCH CHI TIẾT ---
st.subheader("📑 Danh sách thiết bị & Nhật ký")

# Hàm định dạng màu sắc cho bảng
def style_status(row):
    color = 'background-color: #d4edda' if row.STATUS.upper() == 'ONLINE' else 'background-color: #f8d7da'
    return [color] * len(row)

if not df.empty:
    # Hiển thị bảng dữ liệu với màu sắc trực quan
    st.dataframe(
        df[['MACHINE_ID', 'STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']].style.apply(style_status, axis=1),
        use_container_width=True,
        hide_index=True
    )

if st.button("🔄 Làm mới hệ thống"):
    st.rerun()
