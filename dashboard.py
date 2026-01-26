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
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi cấu hình Secrets: {e}")
        return None

client = get_gspread_client()
SHEET_ID = "1LClTdR0z_FPX2AkYCfrbBRtWO8BWOG08hAEB8aq-TcI"
sh = client.open_by_key(SHEET_ID)
worksheet = sh.get_worksheet(0)

# Cấu hình chuẩn 7 cột cho Formulas (Multi-Block)
EXPECTED_HEADERS = ["MACHINE_ID", "FILE_NAME", "DATA_CHUNK", "TARGET_PATH", "TIMESTAMP", "PART_INFO", "STATUS"]

try:
    ws_formula = sh.worksheet("Formulas")
    header_row = ws_formula.row_values(1)
    if not header_row or header_row != EXPECTED_HEADERS:
        ws_formula.update('A1:G1', [EXPECTED_HEADERS])
except:
    ws_formula = sh.add_worksheet("Formulas", rows=2000, cols=7)
    ws_formula.append_row(EXPECTED_HEADERS)

# --- 3. HÀM XỬ LÝ DỮ LIỆU AI ---
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
    def check_status(last_seen_str):
        try:
            ls = datetime.strptime(last_seen_str, "%d/%m/%Y %H:%M:%S")
            return "ONLINE" if (now - ls).total_seconds() < 120 else "OFFLINE"
        except: return "OFFLINE"
        
    df['ACTUAL_STATUS'] = df['LAST_SEEN'].apply(check_status)
    return df

df = load_and_analyze()

# --- 4. GIAO DIỆN CHÍNH ---
st.title("🛡️ 4Oranges SDM - AI Intelligence Center")

tab_control, tab_formula, tab_history, tab_color_stats, tab_ai_insight = st.tabs([
    "🎮 CONTROL CENTER", "🧪 PRISMAPRO UPDATE", "📜 LỊCH SỬ TRUYỀN TẢI", "🎨 COLOR ANALYTICS", "🧠 AI STRATEGY"
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
                    st.success(f"Đã gửi lệnh {selected_cmd} thành công!")
                    time.sleep(1)
                    st.rerun()

        search = st.text_input("🔍 Tìm nhanh máy hoặc Nhật ký:", key="search_box")
        df_disp = df[df.apply(lambda row: search.lower() in row.astype(str).str.lower().values, axis=1)] if search else df
        st.dataframe(df_disp[['MACHINE_ID', 'ACTUAL_STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']], use_container_width=True, hide_index=True)
    else:
        st.warning("Chưa có dữ liệu từ hệ thống.")

# --- TAB 2: PRISMAPRO UPDATE (MULTI-BLOCK) ---
with tab_formula:
    st.subheader("🧬 Cập nhật công thức & Truyền file dung lượng lớn")
    PRISMA_PATH = r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Updates"
    
    with st.container(border=True):
        f_col1, f_col2 = st.columns([1, 1])
        with f_col1:
            uploaded_file = st.file_uploader("📂 Chọn file .sdf:", type=['sdf'], key="f_file")
            chunks = []
            if uploaded_file:
                raw_data = uploaded_file.getvalue()
                # Nén và chia nhỏ chunk
                compressed = base64.b64encode(zlib.compress(raw_data)).decode('utf-8')
                chunk_size = 30000 
                chunks = [compressed[i:i+chunk_size] for i in range(0, len(compressed), chunk_size)]
                st.info(f"📦 File: {uploaded_file.name} | Dung lượng nén: {len(chunks)} phần.")
        
        with f_col2:
            target_machines = st.multiselect("🎯 Máy nhận:", df['MACHINE_ID'].unique() if not df.empty else [], key="f_targets")
            st.write("##")
            if st.button("📤 ĐẨY FILE NGAY", use_container_width=True, type="primary"):
                if uploaded_file and target_machines:
                    ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    all_rows = []
                    for m_id in target_machines:
                        for idx, chunk in enumerate(chunks):
                            all_rows.append([m_id, uploaded_file.name, chunk, PRISMA_PATH, ts, f"PART_{idx+1}/{len(chunks)}", "PENDING"])
                    
                    with st.spinner("Đang truyền dữ liệu lên Cloud..."):
                        ws_formula.append_rows(all_rows)
                    st.success(f"✅ Đã đẩy thành công {len(chunks)} phần của file {uploaded_file.name}!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Vui lòng chọn đủ File và Máy nhận!")

# --- TAB 3: LỊCH SỬ TRUYỀN TẢI ---
with tab_history:
    st.subheader("📜 Nhật ký truyền tải dữ liệu")
    raw_logs = ws_formula.get_all_values()
    if len(raw_logs) > 1:
        header = raw_logs[0]
        # Khử trùng tên cột cho DataFrame
        clean_cols = [f"{c}_{i}" if header.count(c) > 1 else c for i, c in enumerate(header)]
        log_df = pd.DataFrame(raw_logs[1:], columns=clean_cols)
        
        # Chỉ hiển thị các cột quan trọng
        display_cols = [c for c in log_df.columns if any(x in c for x in ["MACHINE_ID", "FILE_NAME", "TIMESTAMP", "PART_INFO", "STATUS"])]
        
        # Thống kê nhanh
        st.write(f"Tổng số bản ghi: **{len(log_df)}**")
        st.dataframe(log_df[display_cols].tail(50), use_container_width=True)
    else:
        st.info("Chưa có lịch sử truyền tải nào.")

# --- TAB 4: COLOR ANALYTICS ---
with tab_color_stats:
    st.subheader("📊 Phân tích Sản lượng Màu pha")
    color_df = df[df['EXTRACTED_COLOR'] != "N/A"] if not df.empty else pd.DataFrame()
    if not color_df.empty:
        c1, c2 = st.columns(2)
        with c1:
            top_c = color_df['EXTRACTED_COLOR'].value_counts().head(10).reset_index()
            top_c.columns = ['Mã Màu', 'Số Lần']
            st.plotly_chart(px.bar(top_c, x='Mã Màu', y='Số Lần', title="🔥 TOP 10 MÀU PHA", color='Số Lần'), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(df, names='ACTUAL_STATUS', title="📈 TRẠNG THÁI HỆ THỐNG"), use_container_width=True)
    else:
        st.info("Chưa có dữ liệu pha màu để phân tích.")

# --- TAB 5: AI STRATEGY ---
with tab_ai_insight:
    st.subheader("🧠 Trợ lý AI & Báo cáo Quản trị")
    if not df.empty:
        off_count = len(df[df['ACTUAL_STATUS'] == 'OFFLINE'])
        st.info(f"**AI Insight:** Hiện tại có {off_count} máy mất kết nối. Đề xuất kiểm tra đường truyền tại các đại lý này.")
        
        csv_final = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 TẢI BÁO CÁO TỔNG HỢP (CSV)", data=csv_final, file_name=f"SDM_Report_{datetime.now().strftime('%d%m%Y')}.csv", mime="text/csv")

# Sidebar
with st.sidebar:
    st.image("https://4oranges.com/wp-content/uploads/2021/08/logo-4oranges.png", width=150)
    st.markdown("---")
    st.write(f"🕒 Update: {datetime.now().strftime('%H:%M:%S')}")
    st.write(f"🤖 Ver: {AGENT_VERSION if 'AGENT_VERSION' in locals() else 'V8.8 AI'}")
    if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.rerun()
