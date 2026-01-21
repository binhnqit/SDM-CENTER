import streamlit as st
import json
import gspread
import base64
import pandas as pd
from google.oauth2.service_account import Credentials

# 1. Kết nối bảo mật (Tự động quét mọi loại Key sếp đã đặt)
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # Tự động tìm key trong Secrets của sếp
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        if not k_name: return None
        decoded_data = base64.b64decode(st.secrets[k_name]).decode('utf-8')
        info = json.loads(decoded_data)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
    except: return None

st.set_page_config(page_title="4Oranges SDM Center", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

client = get_gsheet_client()

if client:
    try:
        # ID Sheet từ ảnh của sếp
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet = client.open_by_url(SHEET_URL).sheet1
        
        # LẤY DỮ LIỆU THÔ HOÀN TOÀN (Lấy mảng 2 chiều để tránh lỗi cấu trúc)
        values = sheet.get_all_values()
        
        if values:
            # Tự định nghĩa lại tiêu đề để đảm bảo khớp 100% với ảnh sếp gửi
            headers = ["MACHINE_ID", "STATUS", "COMMAND", "LAST_SEEN", "HISTORY"]
            
            # Xử lý từng dòng dữ liệu: Chỉ lấy đúng 5 cột đầu tiên
            data_rows = []
            for row in values[1:]:
                # Nếu dòng ngắn hơn 5 cột, bù thêm ô trống để không bị lỗi
                clean_row = (row + [""] * 5)[:5]
                data_rows.append(clean_row)
            
            df = pd.DataFrame(data_rows, columns=headers)
            
            # Hiển thị Dashboard
            st.success("✅ ĐÃ THÔNG SUỐT HỆ THỐNG!")
            
            # Hiển thị thông số máy pha chính (Dòng đầu tiên có ID)
            main_row = df[df['MACHINE_ID'] != ""].iloc[0] if not df[df['MACHINE_ID'] != ""].empty else None
            if main_row is not None:
                c1, c2, c3 = st.columns(3)
                c1.metric("Thiết bị", main_row['MACHINE_ID'])
                c2.metric("Trạng thái", main_row['STATUS'])
                c3.metric("Lệnh mới nhất", main_row['COMMAND'] or "NONE")

            st.divider()
            st.subheader("📑 Nhật ký vận hành & Lịch sử lệnh")
            
            # Hiển thị bảng dữ liệu (Dùng fillna để bảng sạch đẹp)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            if st.button("🔄 Cập nhật dữ liệu ngay"):
                st.rerun()
        else:
            st.warning("⚠️ Bảng tính hiện đang trống.")
            
    except Exception as e:
        st.error(f"⚠️ Lỗi hệ thống: {str(e)}")
else:
    st.error("❌ Không thể kết nối. Sếp hãy kiểm tra lại Key trong Secrets.")
