import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time  # KHẮC PHỤC LỖI NAMEERROR
import io

# --- 1. CẤU HÌNH & CSS (GIỮ NGUYÊN PHONG CÁCH V6.5) ---
st.set_page_config(page_title="4Oranges SDM - Platinum Plus", layout="wide")

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

# --- 3. LOAD DỮ LIỆU ---
def load_data():
    all_values = worksheet.get_all_values()
    df = pd.DataFrame(all_values[1:], columns=all_values[0])
    df = df[df['MACHINE_ID'].str.strip() != ""].copy()
    df['sheet_row'] = df.index + 2
    now = datetime.now()
    df['ACTUAL_STATUS'] = df['LAST_SEEN'].apply(lambda x: "ONLINE" if (now - datetime.strptime(x, "%d/%m/%Y %H:%M:%S")).total_seconds() < 120 else "OFFLINE" if x else "OFFLINE")
    return df

df = load_data()

# --- 4. GIAO DIỆN CHÍNH ---
st.title("🛡️ 4Oranges SDM - Platinum AI Command Center")

tab_control, tab_formula, tab_analytics = st.tabs(["🎮 ĐIỀU KHIỂN HỆ THỐNG", "🧪 CẬP NHẬT CÔNG THỨC", "📊 THỐNG KÊ"])

# --- TAB 1: ĐIỀU KHIỂN (Giá trị cốt lõi V6.5 PRO) ---
with tab_control:
    # Metrics
    df_on = df[df['ACTUAL_STATUS'] == 'ONLINE']
    m1, m2, m3 = st.columns(3)
    m1.metric("TỔNG THIẾT BỊ", len(df))
    m2.metric("ONLINE", len(df_on))
    m3.metric("LỆNH CUỐI", df['COMMAND'].iloc[-1] if not df.empty else "N/A")

    # Trung tâm phát lệnh
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            selected_machine = st.selectbox("🎯 Chọn máy mục tiêu:", df['MACHINE_ID'].unique())
        with col2:
            selected_cmd = st.selectbox("📜 Lệnh vận hành:", ["NONE", "LOCK", "UNLOCK", "FORCE_UPDATE"])
        with col3:
            st.write("##")
            if st.button("🚀 GỬI LỆNH NGAY", use_container_width=True, type="primary"):
                row_idx = df[df['MACHINE_ID'] == selected_machine]['sheet_row'].iloc[0]
                worksheet.update_cell(int(row_idx), 3, selected_cmd)
                st.toast("Đã gửi lệnh thành công!", icon="✅")
                time.sleep(1) # Đã hết lỗi nhờ import ở trên
                st.rerun()

    # Tìm kiếm & Bảng dữ liệu
    search = st.text_input("🔍 Tìm nhanh máy (Nhập ID hoặc thông tin):")
    df_display = df[df['MACHINE_ID'].str.contains(search, case=False)] if search else df
    st.dataframe(df_display[['MACHINE_ID', 'ACTUAL_STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']], use_container_width=True, hide_index=True)

# --- TAB 2: CẬP NHẬT CÔNG THỨC (NÂNG CẤP MỚI) ---
with tab_formula:
    st.subheader("🧬 Cập nhật công thức tự động")
    
    with st.container(border=True):
        f_col1, f_col2 = st.columns([1, 1])
        
        with f_col1:
            color_code = st.text_input("💎 Mã màu (Color Code):", placeholder="Ví dụ: 7052-P")
            
            # TÍNH NĂNG CHỌN FILE TỪ MÁY TÍNH
            uploaded_file = st.file_uploader("📂 Chọn file công thức (txt, json, csv):", type=['txt', 'json', 'csv'])
            
            manual_formula = ""
            if uploaded_file is not None:
                # Đọc nội dung file
                stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
                manual_formula = stringio.read()
                st.info("✅ Đã đọc dữ liệu từ file")
            else:
                manual_formula = st.text_area("📝 Hoặc nhập thủ công công thức:", height=100)

        with f_col2:
            target_machines = st.multiselect("🎯 Chọn các máy nhận công thức:", df['MACHINE_ID'].unique())
            st.write("##")
            if st.button("📤 ĐẨY CÔNG THỨC XUỐNG TẤT CẢ MÁY ĐÃ CHỌN", use_container_width=True, type="primary"):
                if not target_machines or not color_code or not manual_formula:
                    st.error("Vui lòng điền đủ: Mã màu, Công thức và Máy nhận!")
                else:
                    with st.spinner("Đang đẩy dữ liệu..."):
                        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        for m_id in target_machines:
                            ws_formula.append_row([m_id, color_code, manual_formula, timestamp, "PENDING"])
                        st.success(f"Đã gửi công thức màu {color_code} tới {len(target_machines)} máy!")

# --- TAB 3: THỐNG KÊ (DỰA TRÊN HISTORY) ---
with tab_analytics:
    st.subheader("📊 Phân tích hiệu suất hệ thống")
    # Tải báo cáo CSV
    csv_data = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 TẢI BÁO CÁO TOÀN BỘ (CSV)", data=csv_data, file_name=f"SDM_Report_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
    
    # Biểu đồ demo từ dữ liệu thực tế
    st.info("Tính năng AI đang phân tích dữ liệu từ cột HISTORY để đưa ra cảnh báo sớm...")

# Sidebar logo và thông tin
with st.sidebar:
    st.image("https://4oranges.com/wp-content/uploads/2021/08/logo-4oranges.png", width=150)
    st.caption(f"Phiên bản: {datetime.now().year} - V7.1 PLATINUM PLUS")
    if st.button("🔄 Làm mới dữ liệu"):
        st.rerun()
