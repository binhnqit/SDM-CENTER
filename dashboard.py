import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, timedelta
import time

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="4Oranges SDM - AI Command Center", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS để giao diện "chất" hơn như hình sếp gửi
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    div[data-testid="stExpander"] { background-color: white; border-radius: 10px; }
    .status-online { color: #28a745; font-weight: bold; }
    .status-offline { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- KẾT NỐI HỆ THỐNG ---
@st.cache_resource(ttl=300) # Cache 5 phút để tối ưu API
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
def load_data():
    all_values = worksheet.get_all_values()
    if not all_values: return pd.DataFrame()
    df = pd.DataFrame(all_values[1:], columns=all_values[0])
    df = df[df['MACHINE_ID'].str.strip() != ""].copy()
    df['sheet_row'] = df.index + 2
    
    # Tính toán trạng thái thực tế dựa trên LAST_SEEN
    now = datetime.now()
    def check_alive(last_seen_str):
        try:
            ls = datetime.strptime(last_seen_str, "%d/%m/%Y %H:%M:%S")
            return "ONLINE" if (now - ls).total_seconds() < 60 else "OFFLINE"
        except: return "UNKNOWN"
    
    df['ACTUAL_STATUS'] = df['LAST_SEEN'].apply(check_alive)
    return df

df = load_data()

# --- GIAO DIỆN CHÍNH ---
st.title("🛡️ 4Oranges SDM - AI Command Center")

# --- 1. METRICS DASHBOARD ---
total_devices = len(df)
online_count = len(df[df['ACTUAL_STATUS'] == 'ONLINE'])
m1, m2, m3, m4 = st.columns(4)
m1.metric("TỔNG THIẾT BỊ", total_devices)
m2.metric("ĐANG TRỰC TUYẾN", online_count, delta=f"{online_count/max(total_devices,1)*100:.1f}%")
m3.metric("LỆNH CHỜ", len(df[df['COMMAND'] != 'NONE']))
m4.metric("PHIÊN BẢN MỚI NHẤT", "V5.3-FINAL")

st.divider()

# --- 2. TRUNG TÂM PHÁT LỆNH ---
st.subheader("🎮 Trung tâm Phát lệnh Điều khiển")
with st.container(border=True):
    col_target, col_cmd, col_btn = st.columns([2, 2, 1])
    with col_target:
        machine_list = df['MACHINE_ID'].unique().tolist()
        selected_machine = st.selectbox("🎯 Chọn máy mục tiêu:", machine_list)
    with col_cmd:
        cmd_options = ["NONE", "LOCK", "UNLOCK", "FORCE_UPDATE", "COLLECT_LOGS"]
        selected_cmd = st.selectbox("📜 Chọn lệnh vận hành:", cmd_options)
    with col_btn:
        st.write("##")
        if st.button("🚀 GỬI LỆNH NGAY", use_container_width=True, type="primary"):
            row_idx = df[df['MACHINE_ID'] == selected_machine]['sheet_row'].iloc[0]
            worksheet.update_cell(int(row_idx), 3, selected_cmd)
            st.toast(f"Đã gửi {selected_cmd} tới {selected_machine}", icon="✅")
            time.sleep(1)
            st.rerun()

# --- 3. BẢNG GIÁM SÁT CHI TIẾT ---
st.subheader("📑 Danh sách thiết bị & Nhật ký")

# Định dạng bảng màu sắc
def color_status(val):
    if val == 'ONLINE': return 'color: #28a745; font-weight: bold'
    if val == 'OFFLINE': return 'color: #dc3545'
    return ''

st.dataframe(
    df[['MACHINE_ID', 'ACTUAL_STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']]
    .style.applymap(color_status, subset=['ACTUAL_STATUS']),
    use_container_width=True,
    hide_index=True
)

# --- 4. TÍNH NĂNG MỞ RỘNG (DÀNH CHO TƯƠNG LAI) ---
with st.sidebar:
    st.image("https://4oranges.com/wp-content/uploads/2021/08/logo-4oranges.png", width=150)
    st.header("Cài đặt hệ thống")
    st.toggle("Tự động làm mới (30s)", value=True)
    st.divider()
    if st.button("🧹 Xóa Nhật ký cũ"):
        st.warning("Tính năng đang phát triển")
    
    st.info(f"Đang quản lý: {total_devices} máy pha màu trên toàn quốc.")
