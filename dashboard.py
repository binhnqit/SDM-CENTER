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
import zlib # Thư viện nén để xử lý dứt điểm lỗi dung lượng ô

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="4Oranges SDM - AI Intelligence", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #e1e4e8 !important; border-radius: 5px 5px 0 0; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #ff4b4b !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KẾT NỐI HỆ THỐNG ---
@st.cache_resource(ttl=60)
def get_gspread_client():
    try:
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
        # Chỉ cần dùng scope Spreadsheet để tránh lỗi Drive 403
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi cấu hình Secrets: {e}")
        return None

client = get_gspread_client()
SHEET_ID = "1LClTdR0z_FPX2AkYCfrbBRtWO8BWOG08hAEB8aq-TcI"
sh = client.open_by_key(SHEET_ID)
worksheet = sh.get_worksheet(0)

# Khởi tạo Sheet Formulas chuẩn (6 cột)
try:
    ws_formula = sh.worksheet("Formulas")
except:
    ws_formula = sh.add_worksheet("Formulas", rows=1000, cols=6)
    ws_formula.append_row(["MACHINE_ID", "FILE_NAME", "COMPRESSED_DATA", "TARGET_PATH", "TIMESTAMP", "STATUS"])

# --- 3. HÀM XỬ LÝ DỮ LIỆU ---
def load_and_analyze():
    data = worksheet.get_all_values()
    if not data or len(data) < 2: return pd.DataFrame()
    df = pd.DataFrame(data[1:], columns=data[0])
    df = df[df['MACHINE_ID'].str.strip() != ""].copy()
    df['sheet_row'] = df.index + 2
    
    def extract_color(history):
        match = re.search(r'Pha màu:\s*([A-Z0-9-]+)', str(history))
        return match.group(1) if match else "N/A"
    
    df['EXTRACTED_COLOR'] = df['HISTORY'].apply(extract_color)
    
    now = datetime.now()
    def check_status(ls_str):
        try:
            ls = datetime.strptime(ls_str, "%d/%m/%Y %H:%M:%S")
            return "ONLINE" if (now - ls).total_seconds() < 120 else "OFFLINE"
        except: return "OFFLINE"
        
    df['ACTUAL_STATUS'] = df['LAST_SEEN'].apply(check_status)
    return df

df = load_and_analyze()

# --- 4. GIAO DIỆN TABS ---
st.title("🛡️ 4Oranges SDM - Platinum AI Command Center")

tab_control, tab_formula, tab_color_stats, tab_ai_insight = st.tabs([
    "🎮 CONTROL CENTER", "🧪 PRISMAPRO UPDATE", "🎨 COLOR ANALYTICS", "🧠 AI STRATEGY"
])

# --- TAB 1: CONTROL CENTER ---
with tab_control:
    if not df.empty:
        df_on = df[df['ACTUAL_STATUS'] == 'ONLINE']
        m1, m2, m3 = st.columns(3)
        m1.metric("TỔNG THIẾT BỊ", len(df))
        m2.metric("ONLINE", len(df_on))
        m3.metric("LỆNH CUỐI", df['COMMAND'].iloc[-1] if not df.empty else "N/A")

        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                selected_machine = st.selectbox("🎯 Chọn máy mục tiêu:", df['MACHINE_ID'].unique(), key="ctrl_m")
            with col2:
                selected_cmd = st.selectbox("📜 Lệnh vận hành:", ["NONE", "LOCK", "UNLOCK", "FORCE_UPDATE"], key="ctrl_c")
            with col3:
                st.write("##")
                if st.button("🚀 GỬI LỆNH", use_container_width=True, type="primary"):
                    row_idx = df[df['MACHINE_ID'] == selected_machine]['sheet_row'].iloc[0]
                    worksheet.update_cell(int(row_idx), 3, selected_cmd)
                    st.toast(f"Đã gửi {selected_cmd}!", icon="✅")
                    time.sleep(0.5)
                    st.rerun()

        search = st.text_input("🔍 Tìm nhanh máy hoặc Nhật ký:", key="search_box")
        df_disp = df[df.apply(lambda row: search.lower() in row.astype(str).str.lower().values, axis=1)] if search else df
        st.dataframe(df_disp[['MACHINE_ID', 'ACTUAL_STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']], use_container_width=True, hide_index=True)

# --- TAB 2: PRISMAPRO UPDATE (.SDF) ---
with tab_formula:
    st.subheader("🧬 Cập nhật File hệ thống PrismaPro")
    PRISMA_PATH = r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Updates"
    st.warning(f"📍 Thư mục đích trên máy khách: `{PRISMA_PATH}`")
    
    with st.container(border=True):
        f_col1, f_col2 = st.columns([1, 1])
        with f_col1:
            uploaded_file = st.file_uploader("📂 Chọn file công thức (.sdf):", type=['sdf'], key="f_sdf_final")
            file_name = ""
            compressed_str = ""
            if uploaded_file:
                file_name = uploaded_file.name
                # Thuật toán: Nén dữ liệu để vượt giới hạn 50k ký tự của Google Sheets
                raw_bytes = uploaded_file.getvalue()
                compressed_bytes = zlib.compress(raw_bytes)
                compressed_str = base64.b64encode(compressed_bytes).decode('utf-8')
                st.success(f"✅ Đã xử lý file: {file_name} (Dung lượng nén: {len(compressed_str)} ký tự)")
        
        with f_col2:
            target_machines = st.multiselect("🎯 Chọn máy nhận file:", df['MACHINE_ID'].unique() if not df.empty else [], key="f_targets")
            st.write("##")
            if st.button("📤 ĐẨY FILE XUỐNG MÁY", use_container_width=True, type="primary"):
                if target_machines and compressed_str:
                    if len(compressed_str) > 48000:
                        st.error("❌ File quá lớn (kể cả sau khi nén). Vui lòng chia nhỏ file .sdf!")
                    else:
                        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        with st.spinner("Đang truyền dữ liệu..."):
                            for m_id in target_machines:
                                # Gửi chính xác 6 cột dữ liệu
                                ws_formula.append_row([m_id, file_name, compressed_str, PRISMA_PATH, ts, "PENDING"])
                        st.success("Đã đẩy dữ liệu thành công!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("Thiếu File .sdf hoặc chưa chọn Máy!")

# --- TAB 3 & 4 (GIỮ NGUYÊN) ---
with tab_color_stats:
    st.subheader("📊 Thống kê màu pha")
    color_df = df[df['EXTRACTED_COLOR'] != "N/A"] if not df.empty else pd.DataFrame()
    if not color_df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(color_df['EXTRACTED_COLOR'].value_counts().head(10).reset_index(), x='EXTRACTED_COLOR', y='count', title="🔥 TOP 10 MÀU PHA", color='count'), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(df, names='ACTUAL_STATUS', title="📈 TRẠNG THÁI ONLINE"), use_container_width=True)

with tab_ai_insight:
    st.subheader("🧠 Trợ lý AI")
    if not df.empty:
        st.info(f"Phát hiện {len(df[df['ACTUAL_STATUS'] == 'OFFLINE'])} máy ngoại tuyến.")
        st.download_button("📥 TẢI BÁO CÁO", data=df.to_csv(index=False).encode('utf-8-sig'), file_name="4O_Report.csv")

with st.sidebar:
    st.image("https://4oranges.com/wp-content/uploads/2021/08/logo-4oranges.png", width=150)
    st.button("🔄 Refresh Data", on_click=st.rerun)
