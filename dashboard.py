import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re  # Đã thêm để sửa lỗi 'name re is not defined'
import json

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="4Oranges AI Command Center", layout="wide", page_icon="🎨")

def get_gsheet_client():
    # Khai báo các thư viện cần thiết ngay trong hàm để đảm bảo an toàn
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Thiếu cấu hình [gcp_service_account] trong Secrets!")
        return None
        
    try:
        # Lấy dữ liệu từ Secrets
        s = st.secrets["gcp_service_account"]
        
        # --- BỘ LỌC NANO: XỬ LÝ LỖI SHORT SUBSTRATE & UNUSED BYTES ---
        raw_key = s["private_key"]
        header = "-----BEGIN PRIVATE KEY-----"
        footer = "-----END PRIVATE KEY-----"
        
        # Lấy phần ruột và dùng Regex (re) lọc sạch mọi ký tự lạ không phải Base64
        content = raw_key.replace(header, "").replace(footer, "")
        clean_content = re.sub(r'[^A-Za-z0-9+/=]', '', content)
        
        # Xây dựng lại Key chuẩn 100%
        fixed_key = f"{header}\n{clean_content}\n{footer}"
        
        # Tạo Dictionary để nạp vào Google API
        creds_dict = {
            "type": s["type"],
            "project_id": s["project_id"],
            "private_key_id": s["private_key_id"],
            "private_key": fixed_key,
            "client_email": s["client_email"],
            "client_id": s["client_id"],
            "auth_uri": s.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": s.get("token_uri", "https://oauth2.googleapis.com/token"),
            "auth_provider_x509_cert_url": s.get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
            "client_x509_cert_url": s["client_x509_cert_url"]
        }
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi nạp bảo mật chi tiết: {str(e)}")
        return None

# --- 2. GIAO DIỆN ĐIỀU HÀNH ---
client = get_gsheet_client()

if client:
    try:
        # ID Sheet dữ liệu 4Oranges của sếp
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet_obj = client.open_by_url(SHEET_URL).sheet1
        
        # Đọc và xử lý dữ liệu AI
        data = sheet_obj.get_all_records()
        df = pd.DataFrame(data)

        if not df.empty:
            # AI Tracking: Online/Offline
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
                if st.button("🔒 KHÓA MÁY", use_container_width=True, type="primary"):
                    cell = sheet_obj.find(str(target))
                    sheet_obj.update_cell(cell.row, 3, "LOCK")
                    st.toast(f"Đã gửi lệnh KHÓA tới {target}")
                    st.rerun()
                if st.button("🔓 MỞ KHÓA", use_container_width=True):
                    cell = sheet_obj.find(str(target))
                    sheet_obj.update_cell(cell.row, 3, "NONE")
                    st.toast(f"Đã mở khóa máy {target}")
                    st.rerun()

            with right:
                st.subheader("📊 Phân tích màu sắc")
                fig = px.bar(df['HISTORY'].value_counts().head(5), orientation='h')
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("📑 Danh sách chi tiết")
            st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ Lỗi truy cập Sheet: {e}")
