import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os  # Đã thêm để sửa lỗi NameError: name 'os' is not defined

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="4Oranges AI Command Center", layout="wide", page_icon="🎨")

def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    key_file_path = "key.json"
    
    if not os.path.exists(key_file_path):
        st.error("❌ Không tìm thấy file key.json trên GitHub!")
        return None
        
    try:
        # Sử dụng cache để không nạp lại file nhiều lần gây chậm
        creds = ServiceAccountCredentials.from_json_keyfile_name(key_file_path, scope)
        return gspread.authorize(creds)
    except Exception as e:
        # Nếu lỗi JWT, khả năng cao là do file Key bị hỏng hoặc hết hạn
        st.error(f"❌ Lỗi xác thực Google (JWT): Chìa khóa không khớp. Sếp hãy tạo lại Key mới!")
        st.info("Chi tiết: " + str(e))
        return None
# --- 2. GIAO DIỆN ĐIỀU HÀNH ---
client = get_gsheet_client()

if client:
    try:
        # ID Sheet dữ liệu 4Oranges của sếp
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet_obj = client.open_by_url(SHEET_URL).sheet1
        
        # Đọc dữ liệu
        data = sheet_obj.get_all_records()
        df = pd.DataFrame(data)

        if not df.empty:
            # AI Tracking Online/Offline
            df['LAST_SEEN'] = pd.to_datetime(df['LAST_SEEN'], errors='coerce')
            now = datetime.now()
            df['STATUS'] = df['LAST_SEEN'].apply(
                lambda x: '🟢 Online' if (not pd.isna(x) and (now - x).total_seconds() < 600) else '🔴 Offline'
            )

            st.title("🛡️ 4Oranges SDM - Hệ Thống Điều Hành AI")
            
            # --- TỔNG QUAN ---
            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng máy đại lý", len(df))
            c2.metric("Máy đang chạy", len(df[df['STATUS'] == '🟢 Online']))
            c3.metric("Lệnh Khóa", len(df[df['COMMAND'] == 'LOCK']))

            st.divider()

            # --- ĐIỀU KHIỂN & BIỂU ĐỒ ---
            left, right = st.columns([1, 2])
            with left:
                st.subheader("🕹️ Điều khiển Remote")
                target = st.selectbox("Chọn ID Máy", df['MACHINE_ID'].unique())
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("🔒 KHÓA MÁY", use_container_width=True, type="primary"):
                    cell = sheet_obj.find(str(target))
                    sheet_obj.update_cell(cell.row, 3, "LOCK")
                    st.toast(f"Đã gửi lệnh KHÓA tới {target}")
                    st.rerun()
                if col_btn2.button("🔓 MỞ KHÓA", use_container_width=True):
                    cell = sheet_obj.find(str(target))
                    sheet_obj.update_cell(cell.row, 3, "NONE")
                    st.toast(f"Đã mở khóa máy {target}")
                    st.rerun()

            with right:
                st.subheader("📊 Phân tích màu sắc")
                if 'HISTORY' in df.columns:
                    fig = px.bar(df['HISTORY'].value_counts().head(5), orientation='h', color_discrete_sequence=['#FF4B4B'])
                    st.plotly_chart(fig, use_container_width=True)

            st.subheader("📑 Danh sách chi tiết")
            st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"⚠️ Lỗi truy cập dữ liệu: {e}")
