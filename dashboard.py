import streamlit as st
import json
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="4Oranges AI Command Center", layout="wide", page_icon="🎨")

def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    try:
        # Kiểm tra biến đầu vào
        if "gcp_json_raw" not in st.secrets:
            st.error("❌ Secrets thiếu biến 'gcp_json_raw'")
            return None
            
        # 1. Chuyển chuỗi JSON thô thành Dictionary
        info = json.loads(st.secrets["gcp_json_raw"])
        
        # 2. LÀM SẠCH PRIVATE KEY (Xử lý lỗi Incorrect Padding & JWT Signature)
        key = info.get("private_key", "")
        if key:
            # Loại bỏ Header/Footer để xử lý phần ruột
            header = "-----BEGIN PRIVATE KEY-----"
            footer = "-----END PRIVATE KEY-----"
            
            # Trích xuất và dọn dẹp tuyệt đối khoảng trắng/xuống dòng
            core = key.replace(header, "").replace(footer, "").strip()
            clean_core = "".join(core.split()) # Xóa mọi ký tự trống mà không cần 're'
            
            # Tự động bù Padding '=' nếu độ dài không chia hết cho 4
            missing_padding = len(clean_core) % 4
            if missing_padding:
                clean_core += "=" * (4 - missing_padding)
            
            # Tái cấu trúc lại khóa chuẩn
            info["private_key"] = f"{header}\n{clean_content if 'clean_content' in locals() else clean_core}\n{footer}"

        # 3. Nạp từ bộ nhớ - Miễn nhiễm lỗi Bit Stream
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
        
    except Exception as e:
        st.error(f"❌ Lỗi bảo mật hệ thống: {str(e)}")
        return None

# --- 2. LUỒNG XỬ LÝ CHÍNH ---
client = get_gsheet_client()

if client:
    try:
        # Kết nối Sheet (ID sếp đã cung cấp)
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet_obj = client.open_by_url(SHEET_URL).sheet1
        
        # Load dữ liệu vào DataFrame
        data = sheet_obj.get_all_records()
        df = pd.DataFrame(data)

        if not df.empty:
            st.title("🛡️ 4Oranges SDM - Hệ Thống Điều Hành AI")
            
            # Tracking Online/Offline (10 phút)
            if 'LAST_SEEN' in df.columns:
                df['LAST_SEEN'] = pd.to_datetime(df['LAST_SEEN'], errors='coerce')
                now = datetime.now()
                df['STATUS'] = df['LAST_SEEN'].apply(
                    lambda x: '🟢 Online' if (not pd.isna(x) and (now - x).total_seconds() < 600) else '🔴 Offline'
                )

            # --- GIAO DIỆN QUẢN TRỊ ---
            col1, col2, col3 = st.columns(3)
            col1.metric("Tổng máy đại lý", len(df))
            if 'STATUS' in df.columns:
                col2.metric("Máy Online", len(df[df['STATUS'] == '🟢 Online']))
            if 'COMMAND' in df.columns:
                col3.metric("Lệnh Khóa", len(df[df['COMMAND'] == 'LOCK']))

            st.divider()
            
            # Bảng dữ liệu chính
            st.subheader("📑 Danh sách chi tiết thiết bị")
            st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"⚠️ Lỗi truy cập dữ liệu Sheet: {e}")
