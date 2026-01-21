import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json  # Đã thêm để sửa lỗi 'name json is not defined'

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="4Oranges AI Command Center", layout="wide", page_icon="🎨")

def get_gsheet_client():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Thiếu cấu hình Secrets!")
        return None
    try:
        # Lấy dict từ secrets
        s = st.secrets["gcp_service_account"]
        
        # LỌC SẠCH KHÓA: Loại bỏ mọi ký tự không phải Base64/RSA chuẩn
        # Đây là bước xử lý lỗi 'Short substrate' triệt để nhất
        key = s["private_key"]
        header = "-----BEGIN PRIVATE KEY-----"
        footer = "-----END PRIVATE KEY-----"
        
        # Chỉ lấy phần ruột và xóa sạch ký tự lạ
        inner_key = key.replace(header, "").replace(footer, "")
        clean_inner = re.sub(r'[^A-Za-z0-9+/=]', '', inner_key)
        
        # Xây dựng lại dictionary sạch 100%
        creds_dict = {
            "type": s["type"],
            "project_id": s["project_id"],
            "private_key_id": s["private_key_id"],
            "private_key": f"{header}\n{clean_content}\n{footer}",
            "client_email": s["client_email"],
            "client_id": s["client_id"],
            "auth_uri": s["auth_uri"],
            "token_uri": s["token_uri"],
            "auth_provider_x509_cert_url": s["auth_provider_x509_cert_url"],
            "client_x509_cert_url": s["client_x509_cert_url"]
        }
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi nạp bảo mật: {str(e)}")
        return None
# --- 2. GIAO DIỆN ĐIỀU HÀNH ---
client = get_gsheet_client()

if client:
    try:
        # Link Sheet dữ liệu của sếp
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet_obj = client.open_by_url(SHEET_URL).sheet1
        
        # Đọc dữ liệu
        data = sheet_obj.get_all_records()
        df = pd.DataFrame(data)

        if not df.empty:
            # AI Phân loại trạng thái Online/Offline
            df['LAST_SEEN'] = pd.to_datetime(df['LAST_SEEN'], errors='coerce')
            now = datetime.now()
            df['STATUS'] = df['LAST_SEEN'].apply(
                lambda x: '🟢 Online' if (not pd.isna(x) and (now - x).total_seconds() < 600) else '🔴 Offline'
            )

            st.title("🚀 4Oranges SDM - AI Management")
            st.divider()

            # --- HÀNG CHỈ SỐ (METRICS) ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Tổng máy pha", len(df))
            m2.metric("Máy đang chạy", len(df[df['STATUS'] == '🟢 Online']))
            m3.metric("Lệnh Khóa", len(df[df['COMMAND'] == 'LOCK']))
            m4.metric("Cảnh báo AI", len(df[df['HISTORY'].str.contains("Error", na=False)]))

            # --- KHU VỰC ĐIỀU KHIỂN & PHÂN TÍCH ---
            col_ctrl, col_chart = st.columns([1, 2])

            with col_ctrl:
                st.subheader("🕹️ Điều khiển Remote")
                with st.container(border=True):
                    target_id = st.selectbox("Chọn ID Máy", df['MACHINE_ID'].unique())
                    c1, c2 = st.columns(2)
                    
                    if c1.button("🔒 KHÓA MÁY", use_container_width=True, type="primary"):
                        cell = sheet_obj.find(str(target_id))
                        sheet_obj.update_cell(cell.row, 3, "LOCK")
                        st.toast(f"Đã gửi lệnh KHÓA tới {target_id}")
                        st.rerun()

                    if c2.button("🔓 MỞ KHÓA", use_container_width=True):
                        cell = sheet_obj.find(str(target_id))
                        sheet_obj.update_cell(cell.row, 3, "NONE")
                        st.toast(f"Đã mở khóa máy {target_id}")
                        st.rerun()

            with col_chart:
                st.subheader("📊 AI Analytics")
                trend = df['HISTORY'].value_counts().head(10)
                fig = px.pie(values=trend.values, names=trend.index, hole=0.4, title="Xu hướng màu sắc")
                st.plotly_chart(fig, use_container_width=True)

            # --- BẢNG CHI TIẾT ---
            st.subheader("📑 Danh sách chi tiết")
            st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"⚠️ Lỗi truy cập dữ liệu Sheet: {e}")
