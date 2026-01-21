import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="4Oranges AI Command Center", layout="wide", page_icon="🎨")

def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Thiếu cấu hình Secrets: gcp_service_account")
        return None
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # --- THUẬT TOÁN LỌC KÝ TỰ LẠ (\xac, Tiếng Việt, Khoảng trắng) ---
        raw_key = creds_dict["private_key"]
        header = "-----BEGIN PRIVATE KEY-----"
        footer = "-----END PRIVATE KEY-----"
        
        # Lấy phần lõi và lọc bỏ mọi ký tự không phải Base64 chuẩn
        content = raw_key.replace(header, "").replace(footer, "")
        clean_content = re.sub(r'[^A-Za-z0-9+/=]', '', content)
        
        # Ghép lại định dạng chuẩn RSA
        creds_dict["private_key"] = f"{header}\n{clean_content}\n{footer}"
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi nạp bảo mật: {str(e)}")
        return None

# --- 2. XỬ LÝ DỮ LIỆU ---
def load_data(sheet):
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        # Chuẩn hóa thời gian
        df['LAST_SEEN'] = pd.to_datetime(df['LAST_SEEN'], errors='coerce')
        # AI Phân loại trạng thái
        now = datetime.now()
        df['AI_STATUS'] = df['LAST_SEEN'].apply(
            lambda x: '🟢 Online' if (not pd.isna(x) and (now - x).total_seconds() < 600) else '🔴 Offline'
        )
    return df

# --- 3. GIAO DIỆN ĐIỀU HÀNH ---
client = get_gsheet_client()

if client:
    try:
        # Kết nối tới Sheet (Sếp thay ID sheet của sếp vào đây)
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet_obj = client.open_by_url(SHEET_URL).sheet1
        df = load_data(sheet_obj)

        st.title("🚀 4Oranges SDM - Hệ Thống Quản Trị Trung Tâm")
        st.markdown(f"**Cập nhật cuối:** {datetime.now().strftime('%H:%M:%S')}")

        # --- HÀNG CHỈ SỐ TỔNG QUAN ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tổng Máy Đại Lý", len(df))
        m2.metric("Máy Đang Chạy", len(df[df['AI_STATUS'] == '🟢 Online']))
        m3.metric("Máy Đã Khóa", len(df[df['COMMAND'] == 'LOCK']))
        m4.metric("Lỗi Dữ Liệu", len(df[df['HISTORY'].str.contains("Error", na=False)]))

        st.divider()

        # --- PHẦN ĐIỀU KHIỂN & BIỂU ĐỒ ---
        col_left, col_right = st.columns([1, 2])

        with col_left:
            st.subheader("🕹️ Điều Khiển Từ Xa")
            with st.container(border=True):
                target_id = st.selectbox("Chọn máy mục tiêu", df['MACHINE_ID'].unique())
                c_lock, c_unlock = st.columns(2)
                
                if c_lock.button("🔒 KHÓA MÁY", use_container_width=True, type="primary"):
                    cell = sheet_obj.find(str(target_id))
                    sheet_obj.update_cell(cell.row, 3, "LOCK")
                    st.toast(f"Đã gửi lệnh KHÓA tới {target_id}")
                    st.rerun()
                
                if c_unlock.button("🔓 MỞ KHÓA", use_container_width=True):
                    cell = sheet_obj.find(str(target_id))
                    sheet_obj.update_cell(cell.row, 3, "NONE")
                    st.toast(f"Đã mở khóa máy {target_id}")
                    st.rerun()

        with col_right:
            st.subheader("📊 Thống Kê Màu Sắc")
            if not df['HISTORY'].empty:
                color_fig = px.bar(df['HISTORY'].value_counts().head(10), 
                                   labels={'index': 'Màu', 'value': 'Số lần pha'},
                                   color_discrete_sequence=['#FF4B4B'])
                st.plotly_chart(color_fig, use_container_width=True)

        # --- BẢNG CHI TIẾT ---
        st.subheader("📑 Danh Sách Chi Tiết Toàn Hệ Thống")
        st.dataframe(df[['MACHINE_ID', 'AI_STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']], 
                     use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"⚠️ Lỗi truy cập dữ liệu: {e}")
