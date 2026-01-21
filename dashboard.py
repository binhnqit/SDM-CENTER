import streamlit as st
import pandas as pd
from datetime import datetime

# Cấu hình trang
st.set_page_config(page_title="4Oranges SDM Center", layout="wide")

st.title("🎨 4Oranges SDM - Hệ Thống Quản Lý Máy Pha Trung Tâm")

# Giả lập đọc dữ liệu từ Google Sheet (Sếp sẽ thay bằng gspread)
# Ở bước này, tôi hướng dẫn sếp dùng Pandas để hiển thị dữ liệu từ link CSV của Sheet
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/pub?gid=0&single=true&output=csv" 

def load_data():
    df = pd.read_csv(SHEET_CSV_URL)
    return df

try:
    data = load_data()
    
    # --- THỐNG KÊ NHANH ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng số máy", len(data))
    col2.metric("Đang hoạt động", len(data[data['STATUS'] == 'Online']))
    col3.metric("Cần chú ý", len(data[data['HISTORY'] == 'Read Error']))

    # --- BẢNG ĐIỀU KHIỂN ---
    st.subheader("Trạng thái chi tiết các đại lý")
    st.dataframe(data, use_container_width=True)

    # --- KHU VỰC ĐIỀU KHIỂN ---
    st.sidebar.header("🕹️ Lệnh điều khiển")
    target_id = st.sidebar.selectbox("Chọn máy mục tiêu", data['MACHINE_ID'])
    action = st.sidebar.radio("Hành động", ["UNLOCK", "LOCK"])
    
    if st.sidebar.button("Gửi lệnh"):
        st.sidebar.success(f"Đã gửi lệnh {action} tới máy {target_id}")
        # Logic này sẽ ghi ngược lại vào cột COMMAND trên Google Sheet

except:
    st.error("Đang chờ kết nối dữ liệu từ Google Sheet...")
