import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. KẾT NỐI AN TOÀN ---
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Đọc thông tin bảo mật từ Streamlit Secrets thay vì file json
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

# --- 2. GIAO DIỆN DASHBOARD ---
st.set_page_config(page_title="4Oranges AI Command Center", layout="wide")
st.title("🤖 4Oranges SDM - Hệ Thống Quản Trị AI")

try:
    client = get_gsheet_client()
    sheet = client.open_by_url("LINK_SHEET_CUA_SEP").sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    # --- HÀNG CHỈ SỐ AI ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng Máy", len(df))
    online_count = len(df[df['STATUS'] == 'Online'])
    c2.metric("Trạng Thái Online", f"{online_count}/{len(df)}")
    
    # --- MODULE AI: PHÁT HIỆN BẤT THƯỜNG ---
    st.subheader("🕵️ AI Insights: Phân tích vận hành")
    df['LAST_SEEN'] = pd.to_datetime(df['LAST_SEEN'], errors='coerce')
    offline_threshold = datetime.now() - pd.Timedelta(minutes=10)
    
    anomalies = df[df['LAST_SEEN'] < offline_threshold]
    if not anomalies.empty:
        st.error(f"Phát hiện {len(anomalies)} máy có dấu hiệu mất kết nối bất thường!")
        st.dataframe(anomalies)

    # --- MODULE ĐIỀU KHIỂN (LOCK/UNLOCK) ---
    st.sidebar.header("🕹️ Trung tâm Điều khiển")
    selected_machine = st.sidebar.selectbox("Chọn máy mục tiêu", df['MACHINE_ID'])
    
    if st.sidebar.button("🔒 GỬI LỆNH KHÓA"):
        cell = sheet.find(selected_machine)
        sheet.update_cell(cell.row, 3, "LOCK")
        st.sidebar.warning(f"Đã khóa máy {selected_machine}")
        st.rerun()

    if st.sidebar.button("🔓 GỬI LỆNH MỞ"):
        cell = sheet.find(selected_machine)
        sheet.update_cell(cell.row, 3, "NONE")
        st.sidebar.success(f"Đã mở khóa máy {selected_machine}")
        st.rerun()

    # --- BIỂU ĐỒ XU HƯỚNG ---
    st.subheader("📊 Xu hướng pha màu (AI Forecast)")
    fig = px.bar(df['HISTORY'].value_counts().reset_index(), x='index', y='HISTORY', color='HISTORY')
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Hệ thống đang khởi tạo bảo mật: {e}")
