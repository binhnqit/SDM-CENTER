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
st.set_page_config(page_title="4Oranges SDM - V8.7 Stable", layout="wide")

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

# Định nghĩa cấu trúc chuẩn 7 cột
EXPECTED_HEADERS = ["MACHINE_ID", "FILE_NAME", "DATA_CHUNK", "TARGET_PATH", "TIMESTAMP", "PART_INFO", "STATUS"]

try:
    ws_formula = sh.worksheet("Formulas")
    # Kiểm tra nếu tiêu đề cũ không khớp thì xóa đi tạo lại để tránh lỗi GSpreadException
    current_headers = ws_formula.row_values(1)
    if not current_headers or current_headers[0] != EXPECTED_HEADERS[0]:
        sh.del_worksheet(ws_formula)
        raise Exception("Reset Sheet")
except:
    ws_formula = sh.add_worksheet("Formulas", rows=2000, cols=7)
    ws_formula.append_row(EXPECTED_HEADERS)

# --- 2. HÀM LOAD DỮ LIỆU ---
def load_data():
    data = worksheet.get_all_values()
    if not data or len(data) < 2: return pd.DataFrame()
    df = pd.DataFrame(data[1:], columns=data[0])
    now = datetime.now()
    def parse_time(x):
        try: return datetime.strptime(x, "%d/%m/%Y %H:%M:%S")
        except: return None
        
    df['ACTUAL_STATUS'] = df['LAST_SEEN'].apply(lambda x: "ONLINE" if parse_time(x) and (now - parse_time(x)).total_seconds() < 120 else "OFFLINE")
    return df

df = load_data()

# --- 3. GIAO DIỆN ---
st.title("🛡️ 4Oranges SDM - V8.7 Stable Command")

tab_control, tab_formula = st.tabs(["🎮 ĐIỀU KHIỂN", "🧪 PRISMAPRO UPDATE"])

with tab_control:
    st.dataframe(df[['MACHINE_ID', 'ACTUAL_STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']], use_container_width=True, hide_index=True)

with tab_formula:
    st.subheader("🧬 Truyền tải File .sdf dung lượng lớn")
    PRISMA_PATH = r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Updates"
    
    with st.container(border=True):
        f_col1, f_col2 = st.columns([1, 1])
        with f_col1:
            uploaded_file = st.file_uploader("📂 Chọn file .sdf:", type=['sdf'], key="sdf_v87")
            chunks = []
            if uploaded_file:
                raw_data = uploaded_file.getvalue()
                # Nén dữ liệu
                compressed = base64.b64encode(zlib.compress(raw_data)).decode('utf-8')
                # Chia nhỏ mỗi chunk 30,000 ký tự (mức cực kỳ an toàn cho Google API)
                chunk_size = 30000
                chunks = [compressed[i:i+chunk_size] for i in range(0, len(compressed), chunk_size)]
                st.info(f"📦 File: {uploaded_file.name} | Chia làm: {len(chunks)} phần.")
        
        with f_col2:
            target_machines = st.multiselect("🎯 Chọn máy nhận:", df['MACHINE_ID'].unique() if not df.empty else [])
            if st.button("🚀 ĐẨY FILE", use_container_width=True, type="primary"):
                if uploaded_file and target_machines:
                    ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    total_parts = len(chunks)
                    all_rows = []
                    for m_id in target_machines:
                        for idx, chunk in enumerate(chunks):
                            all_rows.append([m_id, uploaded_file.name, chunk, PRISMA_PATH, ts, f"PART_{idx+1}/{total_parts}", "PENDING"])
                    
                    try:
                        ws_formula.append_rows(all_rows)
                        st.success(f"✅ Đã gửi {len(all_rows)} block dữ liệu thành công!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Lỗi khi lưu vào Sheet: {e}")
                else:
                    st.error("Vui lòng chọn đầy đủ File và Máy!")

    # Cách lấy nhật ký an toàn hơn get_all_records()
    if st.checkbox("Xem nhật ký truyền tải"):
        st.write("### 50 hàng dữ liệu cuối cùng")
        raw_logs = ws_formula.get_all_values()
        if len(raw_logs) > 1:
            log_df = pd.DataFrame(raw_logs[1:], columns=raw_logs[0]).tail(50)
            st.dataframe(log_df, use_container_width=True)
