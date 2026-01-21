import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd

# 1. Cấu hình trang
st.set_page_config(page_title="4Oranges Secure Dashboard", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

# 2. Kết nối bảo mật
def get_gspread_client():
    try:
        # Lấy Key từ Secrets
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        decoded_key = base64.b64decode(st.secrets[k_name]).decode('utf-8')
        info = json.loads(decoded_key)
        
        # Cấp quyền
        creds = Credentials.from_service_account_info(
            info, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi cấu hình Key: {e}")
        return None

client = get_gspread_client()

if client:
    try:
        # Mở Sheet bằng ID cố định
        SHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH"
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.get_worksheet(0)
        
        # Đọc dữ liệu
        all_data = worksheet.get_all_values()
        
        if all_data:
            st.success("✅ HỆ THỐNG ĐÃ THÔNG SUỐT & BẢO MẬT")
            
            # Chuyển dữ liệu sang DataFrame (Bỏ qua dòng tiêu đề để lấy nội dung)
            df = pd.DataFrame(all_data[1:], columns=all_data[0])
            
            # Hiển thị Chỉ số nhanh
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("MÁY PHA", df.iloc[0, 0] if not df.empty else "N/A")
            with c2: st.metric("TRẠNG THÁI", df.iloc[0, 1] if not df.empty else "N/A")
            with c3: st.metric("DÒNG DỮ LIỆU", len(df))
            
            st.divider()
            
            # Bảng dữ liệu chính
            st.subheader("📑 Dữ liệu vận hành chi tiết")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            if st.button("🔄 Cập nhật"):
                st.rerun()
        else:
            st.warning("Sheet đang trống.")

    except Exception as e:
        st.error("❌ CHƯA CÓ QUYỀN TRUY CẬP")
        st.write(f"Chi tiết kỹ thuật: {e}")
        st.info(f"👉 Sếp hãy kiểm tra lại: Email `sdm-manage@phonic-impact-480807-d2.iam.gserviceaccount.com` đã được nhấn nút 'Share' và chọn quyền 'Editor' trên file Google Sheet chưa?")
else:
    st.error("Không tìm thấy Key JSON.")
