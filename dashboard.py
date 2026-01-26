import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time
import io
import re
import zlib

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="4Oranges SDM - Prestige Final", layout="wide")

@st.cache_resource(ttl=60)
def get_gspread_client():
    try:
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi kết nối: {e}")
        return None

client = get_gspread_client()
SHEET_ID = "1LClTdR0z_FPX2AkYCfrbBRtWO8BWOG08hAEB8aq-TcI"
sh = client.open_by_key(SHEET_ID)
worksheet = sh.get_worksheet(0)

# Cấu hình chuẩn 7 cột
EXPECTED_HEADERS = ["MACHINE_ID", "FILE_NAME", "DATA_CHUNK", "TARGET_PATH", "TIMESTAMP", "PART_INFO", "STATUS"]

try:
    ws_formula = sh.worksheet("Formulas")
    header_row = ws_formula.row_values(1)
    if not header_row or header_row != EXPECTED_HEADERS:
        # Nếu tiêu đề sai hoặc thiếu, không xóa cả sheet mà chỉ ghi đè lại hàng 1 để an toàn
        ws_formula.update('A1:G1', [EXPECTED_HEADERS])
except:
    ws_formula = sh.add_worksheet("Formulas", rows=2000, cols=7)
    ws_formula.append_row(EXPECTED_HEADERS)

# --- 2. LOAD DỮ LIỆU ---
def load_data():
    try:
        data = worksheet.get_all_values()
        if not data or len(data) < 2: return pd.DataFrame()
        df = pd.DataFrame(data[1:], columns=data[0])
        now = datetime.now()
        def parse_time(x):
            try: return datetime.strptime(x, "%d/%m/%Y %H:%M:%S")
            except: return None
        df['ACTUAL_STATUS'] = df['LAST_SEEN'].apply(lambda x: "ONLINE" if parse_time(x) and (now - parse_time(x)).total_seconds() < 120 else "OFFLINE")
        return df
    except: return pd.DataFrame()

df = load_data()

# --- 3. GIAO DIỆN ---
st.title("🛡️ 4Oranges SDM - V8.8 Prestige Center")

tab_control, tab_formula = st.tabs(["🎮 CONTROL CENTER", "🧪 PRISMAPRO UPDATE"])

with tab_control:
    if not df.empty:
        st.dataframe(df[['MACHINE_ID', 'ACTUAL_STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']], use_container_width=True, hide_index=True)
    else:
        st.warning("Đang tải dữ liệu hoặc Sheet trống...")

with tab_formula:
    st.subheader("🧬 Truyền tải File .sdf dung lượng lớn")
    PRISMA_PATH = r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Updates"
    
    with st.container(border=True):
        f_col1, f_col2 = st.columns([1, 1])
        with f_col1:
            uploaded_file = st.file_uploader("📂 Chọn file .sdf:", type=['sdf'], key="sdf_final_v8")
            chunks = []
            if uploaded_file:
                raw_data = uploaded_file.getvalue()
                compressed = base64.b64encode(zlib.compress(raw_data)).decode('utf-8')
                chunk_size = 30000 
                chunks = [compressed[i:i+chunk_size] for i in range(0, len(compressed), chunk_size)]
                st.success(f"📦 File: {uploaded_file.name} | Sẵn sàng: {len(chunks)} phần.")
        
        with f_col2:
            target_machines = st.multiselect("🎯 Chọn máy nhận:", df['MACHINE_ID'].unique() if not df.empty else [])
            if st.button("🚀 GỬI CẬP NHẬT", use_container_width=True, type="primary"):
                if uploaded_file and target_machines:
                    ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    all_rows = []
                    for m_id in target_machines:
                        for idx, chunk in enumerate(chunks):
                            all_rows.append([m_id, uploaded_file.name, chunk, PRISMA_PATH, ts, f"PART_{idx+1}/{len(chunks)}", "PENDING"])
                    ws_formula.append_rows(all_rows)
                    st.success("✅ Đã đẩy thành công!")
                    time.sleep(1)
                    st.rerun()

    # XỬ LÝ LỖI DUPLICATE COLUMN TẠI ĐÂY
    if st.checkbox("🔍 Xem nhật ký truyền tải (Admin Only)"):
        raw_logs = ws_formula.get_all_values()
        if len(raw_logs) > 1:
            # Lấy tiêu đề và dữ liệu
            header = raw_logs[0]
            data = raw_logs[1:]
            
            # Tạo DataFrame
            log_df = pd.DataFrame(data)
            
            # Sửa lỗi trùng tên cột: Nếu cột trùng, Pandas tự thêm .1, .2
            log_df.columns = [f"{c}_{i}" if header.count(c) > 1 else c for i, c in enumerate(header)]
            
            # Chỉ lấy các cột cần thiết để hiển thị cho gọn
            cols_to_show = [c for c in log_df.columns if any(x in c for x in ["MACHINE_ID", "FILE_NAME", "TIMESTAMP", "PART_INFO", "STATUS"])]
            st.dataframe(log_df[cols_to_show].tail(30), use_container_width=True)

with st.sidebar:
    st.image("https://4oranges.com/wp-content/uploads/2021/08/logo-4oranges.png", width=150)
    st.button("🔄 Làm mới dữ liệu", on_click=st.rerun)
