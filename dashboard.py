import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time
import io

# --- 1. CẤU HÌNH TRANG & GIAO DIỆN ---
st.set_page_config(page_title="4Oranges SDM - AI Command Center", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .status-online { color: #28a745; font-weight: bold; font-size: 0.9em; }
    .status-offline { color: #dc3545; font-weight: bold; font-size: 0.9em; }
    div[data-testid="stExpander"] { background-color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KẾT NỐI HỆ THỐNG ---
@st.cache_resource(ttl=60) # Tần suất cập nhật nhanh hơn cho real-time
def get_gspread_client():
    try:
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi kết nối Google: {e}")
        return None

client = get_gspread_client()
SHEET_ID = "1LClTdR0z_FPX2AkYCfrbBRtWO8BWOG08hAEB8aq-TcI" 
sh = client.open_by_key(SHEET_ID)
worksheet = sh.get_worksheet(0)

# --- 3. XỬ LÝ DỮ LIỆU ---
def load_and_process():
    all_values = worksheet.get_all_values()
    if not all_values: return pd.DataFrame()
    
    df = pd.DataFrame(all_values[1:], columns=all_values[0])
    df = df[df['MACHINE_ID'].str.strip() != ""].copy()
    df['sheet_row'] = df.index + 2
    
    # Logic kiểm tra trạng thái Online thực tế (trễ < 2 phút)
    now = datetime.now()
    def check_alive(last_seen_str):
        try:
            ls = datetime.strptime(last_seen_str, "%d/%m/%Y %H:%M:%S")
            diff = (now - ls).total_seconds()
            return "ONLINE" if diff < 120 else "OFFLINE"
        except: return "OFFLINE"
    
    df['ACTUAL_STATUS'] = df['LAST_SEEN'].apply(check_alive)
    return df

df_full = load_and_process()

# --- 4. GIAO DIỆN COMMAND CENTER ---
st.title("🛡️ 4Oranges SDM - AI Command Center")

# Metrics Tổng quát
df_on = df_full[df_full['ACTUAL_STATUS'] == 'ONLINE']
df_off = df_full[df_full['ACTUAL_STATUS'] == 'OFFLINE']

m1, m2, m3, m4 = st.columns(4)
m1.metric("TỔNG MÁY", len(df_full))
m2.metric("ĐANG TRỰC TUYẾN", len(df_on), delta=f"{len(df_on)} Active")
m3.metric("MẤT KẾT NỐI", len(df_off), delta=f"-{len(df_off)}", delta_color="inverse")
m4.metric("LỆNH CHỜ", len(df_full[df_full['COMMAND'] != 'NONE']))

st.divider()

# --- 5. TRUNG TÂM PHÁT LỆNH ---
st.subheader("🎮 Điều khiển thiết bị")
with st.container(border=True):
    c_target, c_cmd, c_btn = st.columns([2, 2, 1])
    with c_target:
        # Chỉ cho phép chọn máy đang ONLINE để đảm bảo lệnh thực thi ngay
        target_list = df_on['MACHINE_ID'].unique().tolist()
        selected_machine = st.selectbox("🎯 Chọn máy (Chỉ hiện máy Online):", 
                                        target_list if target_list else ["Không có máy online"])
    with c_cmd:
        selected_cmd = st.selectbox("📜 Lệnh vận hành:", ["NONE", "LOCK", "UNLOCK", "FORCE_UPDATE", "COLLECT_LOGS"])
    with c_btn:
        st.write("##")
        if st.button("🚀 GỬI LỆNH NGAY", use_container_width=True, type="primary") and target_list:
            row_idx = df_full[df_full['MACHINE_ID'] == selected_machine]['sheet_row'].iloc[0]
            worksheet.update_cell(int(row_idx), 3, selected_cmd)
            st.toast(f"Đã gửi {selected_cmd} tới {selected_machine}", icon="✅")
            time.sleep(1)
            st.rerun()

# --- 6. TÌM KIẾM & QUẢN LÝ DANH SÁCH ---
st.subheader("📑 Danh sách Chi tiết & Báo cáo")

# Thanh công cụ: Tìm kiếm và Tải báo cáo
tool_1, tool_2 = st.columns([3, 1])
with tool_1:
    search_query = st.text_input("🔍 Tìm kiếm tên máy hoặc IP...", placeholder="Nhập MACHINE_ID để lọc...")
with tool_2:
    st.write("##")
    # Xuất báo cáo CSV
    buffer = io.BytesIO()
    df_full.to_csv(buffer, index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 TẢI BÁO CÁO TOÀN BỘ",
        data=buffer.getvalue(),
        file_name=f"SDM_Report_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# Tách Tab Online/Offline
tab_on, tab_off = st.tabs([f"🟢 ONLINE ({len(df_on)})", f"🔴 OFFLINE ({len(df_off)})"])

def display_styled_df(target_df):
    if search_query:
        target_df = target_df[target_df['MACHINE_ID'].str.contains(search_query, case=False)]
    
    st.dataframe(
        target_df[['MACHINE_ID', 'ACTUAL_STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']],
        use_container_width=True, hide_index=True
    )

with tab_on:
    display_styled_df(df_on)

with tab_off:
    st.info("Những máy này đã lâu không gửi tín hiệu (Heartbeat) về Cloud.")
    display_styled_df(df_off)

# Side bar
with st.sidebar:
    st.image("https://4oranges.com/wp-content/uploads/2021/08/logo-4oranges.png", width=150)
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
