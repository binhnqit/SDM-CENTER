import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. KẾT NỐI AN TOÀN (VỚI CƠ CHẾ AUTO-FIX PADDING) ---
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Thiếu cấu hình Secrets: gcp_service_account")
        return None
        
    try:
        # Lấy dữ liệu từ Secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # AUTO-FIX: Xử lý lỗi Incorrect Padding và ký tự xuống dòng
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi nạp bảo mật: {str(e)}")
        return None

# --- 2. KHỞI CHẠY GIAO DIỆN ---
st.set_page_config(page_title="4Oranges AI Command Center", layout="wide")
st.title("🤖 4Oranges SDM - Hệ Thống Quản Trị AI")

client = get_gsheet_client()

if client:
    try:
        # Sếp dán link Sheet của sếp vào đây
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet = client.open_by_url(SHEET_URL).sheet1
        
        # Đọc dữ liệu
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        if not df.empty:
            # THỐNG KÊ TỔNG QUAN
            st.success("✅ Kết nối bảo mật thành công!")
            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng máy pha", len(df))
            c2.metric("Trạng thái", "Hệ thống ổn định")
            
            # MODULE ĐIỀU KHIỂN SIDEBAR
            st.sidebar.header("🕹️ Trung tâm Điều khiển")
            target = st.sidebar.selectbox("Chọn ID máy", df['MACHINE_ID'].tolist())
            
            if st.sidebar.button("🔒 GỬI LỆNH KHÓA"):
                cell = sheet.find(str(target))
                sheet.update_cell(cell.row, 3, "LOCK")
                st.sidebar.warning(f"Đã gửi lệnh KHÓA tới {target}")
                st.rerun()

            if st.sidebar.button("🔓 GỬI LỆNH MỞ"):
                cell = sheet.find(str(target))
                sheet.update_cell(cell.row, 3, "NONE")
                st.sidebar.info(f"Đã gửi lệnh MỞ tới {target}")
                st.rerun()

            # BẢNG DỮ LIỆU VÀ BIỂU ĐỒ
            st.dataframe(df, use_container_width=True)
            fig = px.pie(df, names='HISTORY', title="Phân tích màu sắc tiêu thụ")
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ Lỗi truy cập dữ liệu Sheet: {e}")
