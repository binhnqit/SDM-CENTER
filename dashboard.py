import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="4Oranges AI Dashboard", layout="wide", page_icon="🎨")

def get_gsheet_client():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Chưa tìm thấy cấu hình Secrets!")
        return None
    try:
        # Lấy dữ liệu từ Secrets
        info = dict(st.secrets["gcp_service_account"])
        
        # --- CHUYÊN GIA: XỬ LÝ TRIỆT ĐỂ LỖI 'Unused bytes' ---
        raw_key = info["private_key"]
        
        # Bước 1: Loại bỏ header/footer để lọc phần nội dung
        header = "-----BEGIN PRIVATE KEY-----"
        footer = "-----END PRIVATE KEY-----"
        content = raw_key.replace(header, "").replace(footer, "")
        
        # Bước 2: Chỉ giữ lại các ký tự Base64 hợp lệ (A-Z, a-z, 0-9, +, /, =)
        # Mọi ký tự lạ như \xac sẽ bị quét sạch tại đây
        clean_content = re.sub(r'[^A-Za-z0-9+/=]', '', content)
        
        # Bước 3: Ghép lại đúng định dạng RSA chuẩn
        info["private_key"] = f"{header}\n{clean_content}\n{footer}"
        
        # Nạp quyền bằng thư viện Google
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi nạp bảo mật: {str(e)}")
        return None

# --- 2. GIAO DIỆN CHÍNH ---
client = get_gsheet_client()

if client:
    try:
        # ID Sheet sếp đã cung cấp
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet = client.open_by_url(SHEET_URL).sheet1
        
        # Đọc dữ liệu
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            # Xử lý AI: Phân tích trạng thái Online/Offline (Thời gian thực)
            df['LAST_SEEN'] = pd.to_datetime(df['LAST_SEEN'], errors='coerce')
            now = datetime.now()
            df['STATUS'] = df['LAST_SEEN'].apply(
                lambda x: '🟢 ONLINE' if (now - x).total_seconds() < 600 else '🔴 OFFLINE'
            )

            # --- GIAO DIỆN DASHBOARD CHUYÊN NGHIỆP ---
            st.title("🛡️ 4Oranges SDM - AI Command Center")
            st.info(f"Hệ thống đang quản lý {len(df)} máy đại lý trên toàn quốc.")
            
            # Hàng chỉ số (Metric)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Tổng số máy", len(df))
            col2.metric("Đang hoạt động", len(df[df['STATUS'] == '🟢 ONLINE']))
            col3.metric("Lệnh KHÓA đang thực thi", len(df[df['COMMAND'] == 'LOCK']))
            col4.metric("Dữ liệu lỗi (AI Warning)", len(df[df['HISTORY'].str.contains("Error", na=False)]))

            st.divider()

            # --- TRUNG TÂM ĐIỀU KHIỂN & PHÂN TÍCH ---
            left, right = st.columns([1, 2])
            
            with left:
                st.subheader("🕹️ Điều khiển Remote")
                with st.container(border=True):
                    target_id = st.selectbox("Chọn ID Máy", df['MACHINE_ID'].unique())
                    btn_lock, btn_unlock = st.columns(2)
                    
                    if btn_lock.button("🔒 KHÓA MÁY", use_container_width=True, type="primary"):
                        cell = sheet.find(str(target_id))
                        sheet.update_cell(cell.row, 3, "LOCK")
                        st.success(f"Đã gửi lệnh KHÓA tới {target_id}")
                        st.rerun()
                        
                    if btn_unlock.button("🔓 MỞ KHÓA", use_container_width=True):
                        cell = sheet.find(str(target_id))
                        sheet.update_cell(cell.row, 3, "NONE")
                        st.success(f"Đã mở khóa máy {target_id}")
                        st.rerun()

            with right:
                st.subheader("📊 AI Analytics - Xu hướng pha màu")
                color_trend = df['HISTORY'].value_counts().head(10)
                fig = px.pie(values=color_trend.values, names=color_trend.index, hole=0.4)
                st.plotly_chart(fig, use_container_width=True)

            # Bảng danh sách chi tiết
            st.subheader("📋 Danh sách đại lý chi tiết")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
    except Exception as e:
        st.error(f"⚠️ Lỗi truy cập dữ liệu: {e}")
