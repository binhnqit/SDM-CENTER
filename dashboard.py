import streamlit as st
import json
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="4Oranges AI Command Center", layout="wide", page_icon="🎨")

def get_gsheet_client():
    # Định nghĩa quyền truy cập
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # Lấy JSON thô từ Secrets
        if "gcp_json_raw" not in st.secrets:
            st.error("❌ Thiếu 'gcp_json_raw' trong Secrets!")
            return None
            
        # Chuyển chuỗi thành Dictionary
        info = json.loads(st.secrets["gcp_json_raw"])
        
        # Nạp trực tiếp từ bộ nhớ (Sửa lỗi Bit Stream & JWT Signature)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi mổ xẻ hệ thống: {str(e)}")
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
            st.title("🛡️ 4Oranges SDM - Hệ Thống Điều Hành AI")
            
            # Xử lý trạng thái Online/Offline
            if 'LAST_SEEN' in df.columns:
                df['LAST_SEEN'] = pd.to_datetime(df['LAST_SEEN'], errors='coerce')
                now = datetime.now()
                df['STATUS'] = df['LAST_SEEN'].apply(
                    lambda x: '🟢 Online' if (not pd.isna(x) and (now - x).total_seconds() < 600) else '🔴 Offline'
                )

            # --- HIỂN THỊ CHỈ SỐ ---
            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng máy đại lý", len(df))
            if 'STATUS' in df.columns:
                c2.metric("Máy đang chạy", len(df[df['STATUS'] == '🟢 Online']))
            if 'COMMAND' in df.columns:
                c3.metric("Lệnh Khóa", len(df[df['COMMAND'] == 'LOCK']))

            st.divider()

            # --- DANH SÁCH CHI TIẾT ---
            st.subheader("📑 Danh sách chi tiết hệ thống máy pha")
            st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"⚠️ Lỗi truy cập dữ liệu: {e}")
