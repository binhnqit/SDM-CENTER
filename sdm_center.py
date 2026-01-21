import streamlit as st
import pandas as pd
from shillelagh.backends.apsw.db import connect # Thư viện kết nối Google Sheet nhanh

st.set_page_config(page_title="SDM-CENTER 3000", layout="wide")

# 1. KẾT NỐI DATABASE (Sếp thay URL bằng link Google Sheet của sếp)
SHEET_URL = "URL_GOOGLE_SHEET_CUA_SEP"

def get_data():
    # Logic đọc dữ liệu từ Google Sheet để hiển thị danh sách máy
    # Giả lập data để sếp thấy giao diện trước
    return pd.DataFrame([
        {"ID": "PC-001", "Trạng thái": "Online", "Lệnh chờ": "None", "Vùng": "Bắc"},
        {"ID": "PC-002", "Trạng thái": "Offline", "Lệnh chờ": "Update_v1", "Vùng": "Trung"}
    ])

st.title("📡 SDM-CENTER: ĐIỀU KHIỂN 3.000 MÁY TRẠM")

# 2. KHU VỰC KPI
df = get_data()
m1, m2, m3 = st.columns(3)
m1.metric("MÁY ONLINE", "2,850/3,000", "95%")
m2.metric("LỆNH ĐANG ĐẨY", "12 máy")
m3.metric("PHIÊN BẢN CŨ", "45 máy", "-5", delta_color="inverse")

# 3. TRẠM PHÁT LỆNH (COMMAND STATION)
with st.expander("🚀 BẢNG ĐIỀU KHIỂN TỪ XA", expanded=True):
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        target = st.multiselect("Chọn máy đích", df['ID'].tolist())
    with col2:
        cmd = st.selectbox("Chọn lệnh", ["Đẩy Update v12", "Logout", "Khóa máy", "Hiện Popup Cảnh báo"])
    with col3:
        if st.button("PHÁT LỆNH", type="primary", use_container_width=True):
            st.success("Đã ghi lệnh vào Database!")

# 4. DANH SÁCH CHI TIẾT
st.subheader("📍 Chi tiết trạng thái máy")
st.dataframe(df, use_container_width=True)
