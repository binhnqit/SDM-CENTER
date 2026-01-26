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

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="4Oranges SDM - AI Intelligence", layout="wide")

# Custom CSS cho giao diện chuyên nghiệp
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #e1e4e8; border-radius: 5px 5px 0 0; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #ff4b4b !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KẾT NỐI HỆ THỐNG ---
@st.cache_resource(ttl=60)
def get_gspread_client():
    k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
    info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
    creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

client = get_gspread_client()
SHEET_ID = "1LClTdR0z_FPX2AkYCfrbBRtWO8BWOG08hAEB8aq-TcI"
sh = client.open_by_key(SHEET_ID)
worksheet = sh.get_worksheet(0)

# Tự động tạo Sheet Formulas nếu chưa có
try:
    ws_formula = sh.worksheet("Formulas")
except:
    ws_formula = sh.add_worksheet("Formulas", rows=1000, cols=10)
    ws_formula.append_row(["MACHINE_ID", "COLOR_CODE", "FORMULA_DATA", "TIMESTAMP", "STATUS"])

# --- 3. HÀM XỬ LÝ DỮ LIỆU AI ---
def load_and_analyze():
    data = worksheet.get_all_values()
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data[1:], columns=data[0])
    df = df[df['MACHINE_ID'].str.strip() != ""].copy()
    df['sheet_row'] = df.index + 2
    
    # AI Parsing: Trích xuất mã màu từ HISTORY
    def extract_color(history):
        match = re.search(r'Pha màu:\s*([A-Z0-9-]+)', str(history))
        return match.group(1) if match else "N/A"
    
    df['EXTRACTED_COLOR'] = df['HISTORY'].apply(extract_color)
    
    # Tính toán trạng thái thực tế
    now = datetime.now()
    def check_status(last_seen_str):
        try:
            ls = datetime.strptime(last_seen_str, "%d/%m/%Y %H:%M:%S")
            return "ONLINE" if (now - ls).total_seconds() < 120 else "OFFLINE"
        except: return "OFFLINE"
        
    df['ACTUAL_STATUS'] = df['LAST_SEEN'].apply(check_status)
    return df

df = load_and_analyze()

# --- 4. GIAO DIỆN CHÍNH ---
st.title("🛡️ 4Oranges SDM - AI Intelligence Dashboard")

tab_control, tab_formula, tab_color_stats, tab_ai_insight = st.tabs([
    "🎮 CONTROL CENTER", "🧪 FORMULA SYNC", "🎨 COLOR ANALYTICS", "🧠 AI STRATEGY"
])

# --- TAB 1: CONTROL CENTER (CORE V6.5) ---
with tab_control:
    df_on = df[df['ACTUAL_STATUS'] == 'ONLINE']
    m1, m2, m3 = st.columns(3)
    m1.metric("TỔNG THIẾT BỊ", len(df))
    m2.metric("ONLINE", len(df_on))
    m3.metric("LỆNH CUỐI", df['COMMAND'].iloc[-1] if not df.empty else "N/A")

    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            selected_machine = st.selectbox("🎯 Chọn máy mục tiêu:", df['MACHINE_ID'].unique(), key="ctrl_machine")
        with col2:
            selected_cmd = st.selectbox("📜 Lệnh vận hành:", ["NONE", "LOCK", "UNLOCK", "FORCE_UPDATE"], key="ctrl_cmd")
        with col3:
            st.write("##")
            if st.button("🚀 GỬI LỆNH NGAY", use_container_width=True, type="primary"):
                row_idx = df[df['MACHINE_ID'] == selected_machine]['sheet_row'].iloc[0]
                worksheet.update_cell(int(row_idx), 3, selected_cmd)
                st.toast(f"Đã gửi {selected_cmd} tới {selected_machine}", icon="✅")
                time.sleep(1)
                st.rerun()

    search = st.text_input("🔍 Tìm nhanh máy hoặc Nhật ký:", placeholder="Nhập MACHINE_ID hoặc nội dung HISTORY...")
    df_disp = df[df.apply(lambda row: search.lower() in row.astype(str).str.lower().values, axis=1)] if search else df
    st.dataframe(df_disp[['MACHINE_ID', 'ACTUAL_STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']], use_container_width=True, hide_index=True)

# --- TAB 2: FORMULA SYNC (CORE V7.1) ---
with tab_formula:
    st.subheader("🧬 Cập nhật công thức & Đẩy File")
    with st.container(border=True):
        f_col1, f_col2 = st.columns([1, 1])
        with f_col1:
            color_code = st.text_input("💎 Mã màu (Color Code):", placeholder="Ví dụ: 7052-P")
            uploaded_file = st.file_uploader("📂 Chọn file công thức (txt, json, csv):", type=['txt', 'json', 'csv'])
            if uploaded_file:
                manual_formula = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
                st.info("✅ Đã lấy dữ liệu từ file")
            else:
                manual_formula = st.text_area("📝 Hoặc nhập nội dung công thức:", height=100)
        with f_col2:
            target_machines = st.multiselect("🎯 Máy nhận công thức:", df['MACHINE_ID'].unique())
            st.write("##")
            if st.button("📤 ĐẨY CÔNG THỨC", use_container_width=True, type="primary"):
                if target_machines and color_code and manual_formula:
                    ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    for m_id in target_machines:
                        ws_formula.append_row([m_id, color_code, manual_formula, ts, "PENDING"])
                    st.success("Đã đẩy công thức thành công!")
                else:
                    st.error("Thiếu thông tin cập nhật!")

# --- TAB 3: COLOR ANALYTICS (MỚI) ---
with tab_color_stats:
    st.
