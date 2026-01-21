import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="4Oranges SDM - AI Command Center", layout="wide", page_icon="🎨")

# --- 2. KẾT NỐI DỮ LIỆU (GOOGLE SHEETS API) ---
# Sếp cần file credentials.json để dùng tính năng GHI (Lock/Unlock)
@st.cache_resource
def get_sheet_connection():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Lưu ý: Thay 'credentials.json' bằng file của sếp hoặc dùng Streamlit Secrets
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        # Thay link sheet của sếp vào đây
        sheet_url = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        return client.open_by_url(sheet_url).sheet1
    except Exception as e:
        st.error(f"Lỗi kết nối API: {e}")
        return None

sheet = get_sheet_connection()

# --- 3. HÀM ĐỌC DỮ LIỆU ---
def load_data():
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        # Chuyển đổi cột thời gian
        df['LAST_SEEN'] = pd.to_datetime(df['LAST_SEEN'], errors='coerce')
        return df
    return pd.DataFrame()

# --- 4. GIAO DIỆN CHÍNH ---
st.title("🎨 4Oranges SDM - Trung Tâm Điều Hành AI")
st.markdown("---")

df = load_data()

if not df.empty:
    # --- PHẦN AI: PHÂN TÍCH VÀ CẢNH BÁO ---
    now = datetime.now()
    df['Status_AI'] = df['LAST_SEEN'].apply(lambda x: 'Online' if (now - x).total_seconds() < 300 else 'Offline')
    
    # --- HÀNG CHỈ SỐ (METRICS) ---
    m1, m2, m3, m4 = st.columns(4)
    total_machines = len(df)
    online_now = len(df[df['Status_AI'] == 'Online'])
    locked_machines = len(df[df['COMMAND'] == 'LOCK'])
    
    m1.metric("Tổng Máy Pha", total_machines)
    m2.metric("Đang Hoạt Động", online_now, f"{online_now/total_machines*100:.1f}%")
    m3.metric("Máy Đang Khóa", locked_machines, delta_color="inverse")
    m4.metric("Cảnh Báo AI", len(df[df['HISTORY'].str.contains("Error", na=False)]), delta_color="off")

    # --- TAB CHỨC NĂNG ---
    tab1, tab2, tab3 = st.tabs(["📊 Giám Sát Real-time", "🤖 Phân Tích AI", "🕹️ Điều Khiển"])

    with tab1:
        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.subheader("Xu Hướng Pha Màu Hệ Thống")
            color_df = df['HISTORY'].value_counts().reset_index()
            color_df.columns = ['Màu', 'Số lần']
            fig = px.bar(color_df.head(15), x='Màu', y='Số lần', color='Số lần', color_continuous_scale='Reds')
            st.plotly_chart(fig, use_container_width=True)
        
        with col_b:
            st.subheader("Tỷ Lệ Kết Nối")
            pie_fig = px.pie(df, names='Status_AI', hole=0.5, color_discrete_sequence=['#2ecc71', '#e74c3c'])
            st.plotly_chart(pie_fig, use_container_width=True)

    with tab2:
        st.subheader("🤖 AI Insights: Phát Hiện Bất Thường")
        # Logic AI đơn giản: Cảnh báo nếu máy Offline quá 24h hoặc pha màu lạ
        dead_machines = df[df['Status_AI'] == 'Offline']
        if not dead_machines.empty:
            st.warning(f"Phát hiện {len(dead_machines)} máy mất tín hiệu trên 5 phút. Cần kiểm tra kết nối mạng tại đại lý.")
            st.dataframe(dead_machines[['MACHINE_ID', 'LAST_SEEN', 'HISTORY']], use_container_width=True)
        else:
            st.success("Tất cả hệ thống đang vận hành tối ưu.")

    with tab3:
        st.subheader("🕹️ Điều Khiển Từ Xa")
        st.info("Chọn máy để thực hiện lệnh LOCK (Khóa màn hình) hoặc UNLOCK.")
        
        with st.form("control_form"):
            selected_id = st.selectbox("Chọn ID Máy Đại Lý", df['MACHINE_ID'].tolist())
            action = st.radio("Hành động", ["UNLOCK (NONE)", "LOCK (Khóa máy)"], horizontal=True)
            submit = st.form_submit_button("XÁC NHẬN GỬI LỆNH")
            
            if submit:
                try:
                    # Tìm dòng của máy đó trên Sheet
                    cell = sheet.find(str(selected_id))
                    cmd_value = "LOCK" if "LOCK" in action else "NONE"
                    sheet.update_cell(cell.row, 3, cmd_value) # Cột 3 là COMMAND
                    st.success(f"✅ Đã gửi lệnh {cmd_value} tới máy {selected_id}")
                    st.cache_data.clear() # Xóa cache để cập nhật lại dữ liệu
                except Exception as e:
                    st.error(f"Không tìm thấy ID máy trên Sheet: {e}")

    # --- BẢNG DỮ LIỆU CHI TIẾT ---
    st.markdown("### 📑 Danh sách chi tiết toàn hệ thống")
    st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.warning("⚠️ Đang chờ dữ liệu từ hệ thống 4Oranges...")
