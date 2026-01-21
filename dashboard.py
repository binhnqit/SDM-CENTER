import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re

# --- 1. CẤU HÌNH GIAO DIỆN CHUẨN ENTERPRISE ---
st.set_page_config(page_title="4Oranges AI Dashboard", layout="wide", page_icon="🎨")

def get_gsheet_client():
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Không tìm thấy cấu hình 'gcp_service_account' trong Secrets!")
        return None
    try:
        # Lấy dữ liệu thô từ Secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # --- CƠ CHẾ CHUYÊN GIA: LỌC SẠCH KHÓA BẢO MẬT (FIX LỖI \xac) ---
        raw_key = creds_dict["private_key"]
        
        # Tách header/footer để xử lý phần lõi
        header = "-----BEGIN PRIVATE KEY-----"
        footer = "-----END PRIVATE KEY-----"
        
        # Chỉ giữ lại phần mã hóa Base64 và loại bỏ MỌI ký tự lạ không phải Base64 chuẩn
        # Điều này sẽ quét sạch các byte dư thừa như \xac
        content = raw_key.replace(header, "").replace(footer, "")
        clean_content = re.sub(r'[^A-Za-z0-9+/=]', '', content)
        
        # Ghép lại định dạng RSA hoàn hảo cho Google API
        creds_dict["private_key"] = f"{header}\n{clean_content}\n{footer}"
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi nạp bảo mật: {str(e)}")
        return None

# --- 2. TRUNG TÂM ĐIỀU HÀNH AI ---
client = get_gsheet_client()

if client:
    try:
        # Link Sheet dữ liệu 4Oranges của sếp
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet = client.open_by_url(SHEET_URL).sheet1
        
        # Đọc và chuẩn hóa dữ liệu
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            df['LAST_SEEN'] = pd.to_datetime(df['LAST_SEEN'], errors='coerce')
            now = datetime.now()
            # AI Phân loại trạng thái Online/Offline
            df['STATUS'] = df['LAST_SEEN'].apply(
                lambda x: '🟢 ONLINE' if (not pd.isna(x) and (now - x).total_seconds() < 600) else '🔴 OFFLINE'
            )

            st.title("🛡️ 4Oranges SDM - AI Command Center")
            st.markdown(f"**Trạng thái hệ thống:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

            # --- HÀNG CHỈ SỐ (METRICS) ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Tổng máy pha", len(df))
            m2.metric("Đang kết nối", len(df[df['STATUS'] == '🟢 ONLINE']))
            m3.metric("Lệnh Khóa", len(df[df['COMMAND'] == 'LOCK']))
            m4.metric("Cảnh báo lỗi", len(df[df['HISTORY'].str.contains("Error", na=False)]))

            st.divider()

            # --- KHU VỰC ĐIỀU KHIỂN & PHÂN TÍCH ---
            col_ctrl, col_chart = st.columns([1, 2])

            with col_ctrl:
                st.subheader("🕹️ Điều khiển Remote")
                with st.container(border=True):
                    selected_id = st.selectbox("Chọn ID Máy đại lý", df['MACHINE_ID'].unique())
                    c1, c2 = st.columns(2)
                    
                    if c1.button("🔒 KHÓA MÁY", use_container_width=True, type="primary"):
                        cell = sheet.find(str(selected_id))
                        sheet.update_cell(cell.row, 3, "LOCK")
                        st.toast(f"Đã gửi lệnh KHÓA tới {selected_id}", icon="🔒")
                        st.rerun()

                    if c2.button("🔓 MỞ KHÓA", use_container_width=True):
                        cell = sheet.find(str(selected_id))
                        sheet.update_cell(cell.row, 3, "NONE")
                        st.toast(f"Đã mở khóa máy {selected_id}", icon="🔓")
                        st.rerun()

            with col_chart:
                st.subheader("📊 AI Analytics - Xu hướng màu sắc")
                if 'HISTORY' in df.columns:
                    trend = df['HISTORY'].value_counts().head(10)
                    fig = px.pie(values=trend.values, names=trend.index, hole=0.4, 
                                 color_discrete_sequence=px.colors.sequential.Reds_r)
                    st.plotly_chart(fig, use_container_width=True)

            # --- BẢNG DỮ LIỆU CHI TIẾT ---
            st.subheader("📑 Danh sách chi tiết")
            st.dataframe(df[['MACHINE_ID', 'STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']], 
                         use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"⚠️ Lỗi truy cập dữ liệu Sheet: {e}")
