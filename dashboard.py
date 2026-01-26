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
st.set_page_config(page_title="4Oranges SDM - Multi-Block System", layout="wide")

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

try:
    ws_formula = sh.worksheet("Formulas")
except:
    ws_formula = sh.add_worksheet("Formulas", rows=2000, cols=7)
    # Thêm cột PART_INFO để Agent biết thứ tự ghép file
    ws_formula.append_row(["MACHINE_ID", "FILE_NAME", "DATA_CHUNK", "TARGET_PATH", "TIMESTAMP", "PART_INFO", "STATUS"])

# --- 2. LOAD DỮ LIỆU MÁY ---
def load_data():
    data = worksheet.get_all_values()
    if not data or len(data) < 2: return pd.DataFrame()
    df = pd.DataFrame(data[1:], columns=data[0])
    now = datetime.now()
    df['ACTUAL_STATUS'] = df['LAST_SEEN'].apply(lambda x: "ONLINE" if x and (now - datetime.strptime(x, "%d/%m/%Y %H:%M:%S")).total_seconds() < 120 else "OFFLINE")
    return df

df = load_data()

# --- 3. GIAO DIỆN ---
st.title("🛡️ 4Oranges SDM - V8.6 Multi-Block Update")

tab_control, tab_formula = st.tabs(["🎮 ĐIỀU KHIỂN", "🧪 PRISMAPRO UPDATE (FILE LỚN)"])

with tab_control:
    st.dataframe(df[['MACHINE_ID', 'ACTUAL_STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']], use_container_width=True)

with tab_formula:
    st.subheader("🧬 Truyền tải File .sdf dung lượng lớn")
    PRISMA_PATH = r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Updates"
    
    with st.container(border=True):
        f_col1, f_col2 = st.columns([1, 1])
        with f_col1:
            uploaded_file = st.file_uploader("📂 Chọn file .sdf (Hỗ trợ file nặng):", type=['sdf'])
            if uploaded_file:
                # Nén và chuyển sang Base64
                raw_data = uploaded_file.getvalue()
                compressed = base64.b64encode(zlib.compress(raw_data)).decode('utf-8')
                
                # Chia nhỏ chunk (Mỗi chunk 40,000 ký tự cho an toàn tuyệt đối)
                chunk_size = 40000
                chunks = [compressed[i:i+chunk_size] for i in range(0, len(compressed), chunk_size)]
                st.info(f"📦 File gốc: {len(raw_data)/1024:.1f} KB. Sau khi nén: {len(chunks)} phần.")
        
        with f_col2:
            target_machines = st.multiselect("🎯 Chọn máy nhận:", df['MACHINE_ID'].unique() if not df.empty else [])
            if st.button("🚀 ĐẨY FILE NGAY", use_container_width=True, type="primary"):
                if uploaded_file and target_machines:
                    ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    total_parts = len(chunks)
                    
                    with st.spinner(f"Đang truyền {total_parts} phần dữ liệu..."):
                        all_rows = []
                        for m_id in target_machines:
                            for idx, chunk in enumerate(chunks):
                                # Cấu trúc: [ID, Tên file, Dữ liệu nhỏ, Đường dẫn, Giờ, Phần x/y, Trạng thái]
                                part_info = f"PART_{idx+1}_OF_{total_parts}"
                                all_rows.append([m_id, uploaded_file.name, chunk, PRISMA_PATH, ts, part_info, "PENDING"])
                        
                        # Gửi hàng loạt để tăng tốc
                        ws_formula.append_rows(all_rows)
                    
                    st.success(f"✅ Đã đẩy thành công file {uploaded_file.name}!")
                    st.balloons()
                else:
                    st.error("Vui lòng chọn file và máy!")

# Hiển thị trạng thái các phần đang chờ
if st.checkbox("Xem tiến độ truyền tải"):
    st.write("### Trạng thái các Block dữ liệu trên Cloud")
    formula_data = ws_formula.get_all_records()
    if formula_data:
        st.dataframe(pd.DataFrame(formula_data).tail(10), use_container_width=True)
