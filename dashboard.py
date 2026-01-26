import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="4Oranges SDM - Control Center", layout="wide")

# --- KẾT NỐI HỆ THỐNG ---
@st.cache_resource
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
all_values = worksheet.get_all_values()
headers = all_values[0]
data_rows = all_values[1:]

df = pd.DataFrame(data_rows, columns=headers)
df = df[df['MACHINE_ID'].str.strip() != ""].copy()
df['index_original'] = df.index
df['sheet_row'] = df['index_original'] + 2

# Phân loại trạng thái (Dựa trên cột STATUS gửi từ Agent)
df['IS_ONLINE'] = df['STATUS'].str.upper().str.contains('ONLINE')

# --- GIAO DIỆN CHÍNH ---
st.title("🛡️ 4Oranges SDM - AI Command Center")

# --- KHU VỰC THỐNG KÊ NHANH ---
c1, c2, c3, c4 = st.columns(4)
df_online = df[df['IS_ONLINE']]
df_offline = df[~df['IS_ONLINE']]

c1.metric("TỔNG MÁY", len(df))
c2.metric("ĐANG ONLINE", len(df_online))
c3.metric("MẤT KẾT NỐI", len(df_offline))

# Tính năng Tải báo cáo toàn bộ
with c4:
    st.write("##")
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 TẢI BÁO CÁO (CSV)",
        data=csv,
        file_name=f'SDM_Report_{datetime.now().strftime("%d%m_%H%M")}.csv',
        mime='text/csv',
        use_container_width=True
    )

st.divider()

# --- TRUNG TÂM PHÁT LỆNH ---
with st.expander("🎮 TRUNG TÂM ĐIỀU KHIỂN (Chọn máy để gửi lệnh)", expanded=True):
    col_target, col_cmd, col_btn = st.columns([2, 2, 1])
    with col_target:
        # Chỉ hiển thị máy Online để phát lệnh cho hiệu quả
        online_list = df_online['MACHINE_ID'].tolist()
        selected_machine = st.selectbox("🎯 Chọn máy mục tiêu (Chỉ hiện máy Online):", online_list if online_list else ["Không có máy online"])
    with col_cmd:
        cmd_options = ["NONE", "LOCK", "UNLOCK", "START_DISPENSING", "STOP_EMERGENCY"]
        selected_cmd = st.selectbox("📜 Lệnh vận hành:", cmd_options)
    with col_btn:
        st.write("##")
        if st.button("🚀 GỬI LỆNH", use_container_width=True, type="primary") and online_list:
            row_in_sheet = df[df['MACHINE_ID'] == selected_machine]['sheet_row'].iloc[0]
            now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            worksheet.update_cell(int(row_in_sheet), 3, selected_cmd)
            worksheet.update_cell(int(row_in_sheet), 4, now)
            st.success(f"Đã gửi {selected_cmd}!")
            st.rerun()

# --- PHÂN TÁCH DANH SÁCH (TÌM KIẾM & LỌC) ---
st.subheader("📑 Quản lý Chi tiết")

tab1, tab2 = st.tabs(["🟢 MÁY ĐANG HOẠT ĐỘNG", "🔴 MÁY MẤT KẾT NỐI (CẦN KIỂM TRA)"])

with tab1:
    search_online = st.text_input("🔍 Tìm nhanh máy Online (Nhập tên máy...):", key="search_on")
    if search_online:
        df_on_display = df_online[df_online['MACHINE_ID'].str.contains(search_online, case=False)]
    else:
        df_on_display = df_online
    
    st.dataframe(df_on_display[['MACHINE_ID', 'STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']], use_container_width=True, hide_index=True)

with tab2:
    st.warning("Danh sách các máy đã lâu không có tín hiệu phản hồi về hệ thống.")
    search_offline = st.text_input("🔍 Tìm nhanh máy Offline:", key="search_off")
    if search_offline:
        df_off_display = df_offline[df_offline['MACHINE_ID'].str.contains(search_offline, case=False)]
    else:
        df_off_display = df_offline
        
    st.dataframe(df_off_display[['MACHINE_ID', 'STATUS', 'LAST_SEEN', 'HISTORY']], use_container_width=True, hide_index=True)

if st.button("🔄 Refresh Data"):
    st.rerun()
