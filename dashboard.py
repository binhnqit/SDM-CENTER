import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time
import io
import plotly.express as px
import re
import zlib

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="4Oranges SDM - AI Intelligence", layout="wide")

# --- 2. KẾT NỐI HỆ THỐNG ---
@st.cache_resource(ttl=60)
def get_gspread_client():
    try:
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi cấu hình Secrets: {e}")
        return None

client = get_gspread_client()
SHEET_ID = "1LClTdR0z_FPX2AkYCfrbBRtWO8BWOG08hAEB8aq-TcI"
sh = client.open_by_key(SHEET_ID)

# Sheet1: Quản lý máy (Giữ nguyên cấu trúc của sếp)
worksheet = sh.get_worksheet(0) 

# Sheet Formulas: Truyền file (Tách biệt để an toàn)
EXPECTED_HEADERS = ["MACHINE_ID", "FILE_NAME", "DATA_CHUNK", "TARGET_PATH", "TIMESTAMP", "PART_INFO", "STATUS"]
try:
    ws_formula = sh.worksheet("Formulas")
except:
    ws_formula = sh.add_worksheet("Formulas", rows=2000, cols=7)
    ws_formula.append_row(EXPECTED_HEADERS)

# --- 3. LOAD DỮ LIỆU ---
def load_data():
    data = worksheet.get_all_values()
    if not data or len(data) < 2: return pd.DataFrame()
    df = pd.DataFrame(data[1:], columns=data[0])
    df['sheet_row'] = df.index + 2
    now = datetime.now()
    def check_status(ls_str):
        try:
            ls = datetime.strptime(ls_str, "%d/%m/%Y %H:%M:%S")
            return "ONLINE" if (now - ls).total_seconds() < 120 else "OFFLINE"
        except: return "OFFLINE"
    df['ACTUAL_STATUS'] = df['LAST_SEEN'].apply(check_status)
    return df

df = load_data()

# --- 4. GIAO DIỆN (Đã sửa lỗi NameError) ---
st.title("🛡️ 4Oranges SDM - AI Intelligence Center")

# Khai báo các tab - QUAN TRỌNG: Phải đủ 5 tab ở đây
tab_control, tab_formula, tab_history, tab_color_stats, tab_ai_insight = st.tabs([
    "🎮 CONTROL CENTER", "🧪 TRUYỀN CÔNG THỨC", "📜 LỊCH SỬ TRUYỀN TẢI", "📊 PHÂN TÍCH", "🧠 AI INSIGHT"
])

with tab_control:
    if not df.empty:
        col1, col2, col3 = st.columns([2,2,1])
        with col1:
            sel_m = st.selectbox("🎯 Chọn máy:", df['MACHINE_ID'].unique())
        with col2:
            sel_c = st.selectbox("📜 Lệnh:", ["NONE", "LOCK", "UNLOCK", "FORCE_UPDATE"])
        with col3:
            st.write("##")
            if st.button("🚀 GỬI", use_container_width=True):
                row = df[df['MACHINE_ID'] == sel_m]['sheet_row'].iloc[0]
                worksheet.update_cell(int(row), 3, sel_c) # Cập nhật cột COMMAND
                st.success("Đã gửi!")
                time.sleep(1)
                st.rerun()
        st.dataframe(df[['MACHINE_ID', 'ACTUAL_STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']], use_container_width=True)

with tab_formula:
    st.subheader("🧬 Đẩy File .SDF (Tự động xé nhỏ)")
    f_file = st.file_uploader("📂 Chọn file .sdf:", type=['sdf'])
    targets = st.multiselect("🎯 Máy nhận:", df['MACHINE_ID'].unique() if not df.empty else [])
    if st.button("📤 BẮT ĐẦU ĐẨY FILE"):
        if f_file and targets:
            raw = f_file.getvalue()
            compressed = base64.b64encode(zlib.compress(raw)).decode('utf-8')
            chunk_size = 30000
            chunks = [compressed[i:i+chunk_size] for i in range(0, len(compressed), chunk_size)]
            ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            all_rows = [[m, f_file.name, c, "C:\\ProgramData\\Fast and Fluid Management\\PrismaPro\\Updates", ts, f"PART_{i+1}/{len(chunks)}", "PENDING"] for m in targets for i, c in enumerate(chunks)]
            ws_formula.append_rows(all_rows)
            st.success("✅ Đã đẩy thành công!")
            st.rerun()

with tab_history:
    st.subheader("📜 Nhật ký truyền tải")
    logs = ws_formula.get_all_values()
    if len(logs) > 1:
        log_df = pd.DataFrame(logs[1:], columns=logs[0])
        # Chỉ lấy thông tin sếp cần
        hist_df = log_df[['MACHINE_ID', 'FILE_NAME', 'TIMESTAMP', 'STATUS']].copy()
        hist_df.columns = ['🖥️ Tên Máy', '🧪 Công Thức', '📅 Ngày Tải', '🔔 Trạng Thái']
        st.dataframe(hist_df.tail(50), use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có lịch sử.")

with tab_color_stats:
    st.info("Biểu đồ sản lượng màu đang được cập nhật từ HISTORY...")

with tab_ai_insight:
    st.write("🤖 Hệ thống AI đang phân tích dữ liệu thiết bị...")

with st.sidebar:
    st.image("https://4oranges.com/wp-content/uploads/2021/08/logo-4oranges.png", width=150)
    if st.button("🔄 Refresh"): st.rerun()
