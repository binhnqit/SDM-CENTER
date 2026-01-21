import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Cấu hình giao diện
st.set_page_config(page_title="4Oranges Command Center", layout="wide", page_icon="🎨")

# 2. Đọc dữ liệu từ Link CSV của sếp
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/pub?gid=0&single=true&output=csv"

def load_data():
    df = pd.read_csv(CSV_URL)
    # Đảm bảo các cột đúng định dạng
    df.columns = ['MACHINE_ID', 'STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']
    return df

# 3. Giao diện chính
st.title("🚀 4Oranges SDM - Hệ Thống Giám Sát 3.000 Máy Pha")

try:
    df = load_data()

    # --- HÀNG THỐNG KÊ TỔNG QUAN ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tổng số máy", len(df))
    with col2:
        online_count = len(df[df['STATUS'] == 'Online'])
        st.metric("Máy đang Online", online_count, delta=f"{online_count/len(df)*100:.1f}%")
    with col3:
        # Giả sử "Cảnh báo" là những máy có Read Error hoặc không thấy dữ liệu
        warning_count = len(df[df['HISTORY'].str.contains('Error', na=False)])
        st.metric("Cảnh báo lỗi", warning_count, delta_color="inverse")
    with col4:
        st.write("**Thời gian hệ thống:**")
        st.write(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    st.divider()

    # --- PHÂN TÍCH DỮ LIỆU PHA MÀU ---
    st.subheader("📊 Phân tích hoạt động pha màu")
    c1, c2 = st.columns([2, 1])
    
    with c1:
        # Biểu đồ Top màu được pha nhiều nhất
        if 'HISTORY' in df.columns:
            color_counts = df['HISTORY'].value_counts().reset_index()
            color_counts.columns = ['Màu sắc', 'Số lần pha']
            fig = px.bar(color_counts.head(10), x='Màu sắc', y='Số lần pha', 
                         title="Top 10 màu pha nhiều nhất toàn hệ thống",
                         color='Số lần pha', color_continuous_scale='Viridis')
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Biểu đồ tròn trạng thái
        status_fig = px.pie(df, names='STATUS', title="Tỷ lệ kết nối", hole=0.4)
        st.plotly_chart(status_fig, use_container_width=True)

    # --- BẢNG CHI TIẾT & TÌM KIẾM ---
    st.subheader("📑 Danh sách chi tiết đại lý")
    search = st.text_input("🔍 Tìm nhanh mã máy hoặc tên màu...", "")
    
    if search:
        df_display = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
    else:
        df_display = df

    st.dataframe(df_display, use_container_width=True, hide_index=True)

except Exception as e:
    st.warning("Đang kết nối tới máy chủ dữ liệu Google...")
    st.info("Lưu ý: Sếp cần đảm bảo Sheet đã được 'Xuất bản lên web' ở định dạng CSV.")
