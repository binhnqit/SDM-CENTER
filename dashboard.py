import streamlit as st
import json
import gspread
import base64
import pandas as pd
from google.oauth2.service_account import Credentials

# 1. Kết nối an toàn (Tự động nhận diện mọi loại Key sếp đã đặt)
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # Tìm bất kỳ biến nào có chứa thông tin Key trong Secrets
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        if not k_name: return None
        decoded_data = base64.b64decode(st.secrets[k_name]).decode('utf-8')
        info = json.loads(decoded_data)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
    except: return None

# Giao diện DashBoard
st.set_page_config(page_title="4Oranges AI Center", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

client = get_gsheet_client()

if client:
    try:
        # ID Sheet từ URL của sếp
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet = client.open_by_url(SHEET_URL).sheet1
        
        # LẤY DỮ LIỆU THÔ (Chống mọi lỗi cấu trúc)
        raw_rows = sheet.get_all_values()
        
        if len(raw_rows) > 0:
            # Ép tên cột theo đúng thực tế sếp thấy trên màn hình
            headers = ["MACHINE_ID", "STATUS", "COMMAND", "LAST_SEEN", "HISTORY"]
            
            # Tạo DataFrame từ dòng 2 trở đi
            # Chúng ta lấy đủ 5 cột đầu tiên, bỏ qua các cột thừa (F, G...) nếu có
            data = [row[:5] for row in raw_rows[1:]]
            df = pd.DataFrame(data, columns=headers)
            
            # Làm sạch: Loại bỏ những dòng trắng hoàn toàn
            df = df.replace('', pd.NA).dropna(how='all')

            # --- HIỂN THỊ CHỈ SỐ ---
            st.success("✅ HỆ THỐNG ĐÃ THÔNG SUỐT!")
            
            m1, m2, m3 = st.columns(3)
            # Lấy thông tin từ dòng đầu tiên có ID máy
            main_machine = df[df['MACHINE_ID'].notna()].iloc[0] if not df[df['MACHINE_ID'].notna()].empty else None
            
            if main_machine is not None:
                m1.metric("Thiết bị", main_machine['MACHINE_ID'])
                m2.metric("Trạng thái", main_machine['STATUS'])
                m3.metric("Lệnh cuối", main_machine['HISTORY'][:15] + "..." if len(main_machine['HISTORY']) > 15 else main_machine['HISTORY'])

            st.divider()
            
            # Hiển thị bảng nhật ký (bao gồm cả các dòng NONE)
            st.subheader("📑 Nhật ký vận hành (History Log)")
            st.dataframe(df.fillna(""), use_container_width=True, hide_index=True)
            
            if st.button("🔄 Làm mới dữ liệu"):
                st.rerun()
        else:
            st.warning("⚠️ Sheet đang trống dữ liệu.")
            
    except Exception as e:
        st.error(f"⚠️ Lỗi xử lý: {str(e)}")
        st.info("Mẹo: Đảm bảo sếp không xóa các tiêu đề ở dòng 1 của Google Sheet.")
else:
    st.error("❌ Không thể kết nối. Kiểm tra lại Key trong Secrets.")
