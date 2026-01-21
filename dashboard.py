import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd

# Cấu hình giao diện
st.set_page_config(page_title="4Oranges Secure Center", layout="wide", page_icon="🛡️")

# --- HÀM KẾT NỐI BẢO MẬT (Dùng Service Account) ---
def get_gspread_client():
    try:
        # Tự động tìm Key trong Secrets của sếp
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        if not k_name:
            return None
        
        # Giải mã Key JSON
        decoded_key = base64.b64decode(st.secrets[k_name]).decode('utf-8')
        info = json.loads(decoded_key)
        
        # Thiết lập quyền truy cập
        creds = Credentials.from_service_account_info(
            info, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi xác thực: {e}")
        return None

# Giao diện chính
st.title("🛡️ 4Oranges SDM - AI Command Center")
st.info(f"Đang kết nối qua tài khoản bảo mật: sdm-manage@phonic-impact-480807-d2...")

client = get_gspread_client()

if client:
    try:
        # Mở Sheet bằng ID (ID này là duy nhất và cố định)
        SPREADSHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH"
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        
        # Lấy dữ liệu
        data = sheet.get_all_values()
        
        if len(data) > 0:
            st.success("✅ KẾT NỐI BẢO MẬT THÔNG SUỐT!")
            
            # Xử lý dữ liệu sang bảng đẹp
            headers = data[0]
            df = pd.DataFrame(data[1:], columns=headers)
            
            # --- PHẦN 1: TỔNG QUAN (Metric) ---
            if not df.empty:
                m1, m2, m3 = st.columns(3)
                m1.metric("Thiết bị", df['MACHINE_ID'].iloc[0] if 'MACHINE_ID' in df else "N/A")
                m2.metric("Trạng thái", df['STATUS'].iloc[0] if 'STATUS' in df else "N/A")
                m3.metric("Số bản ghi", len(df))
            
            st.divider()
            
            # --- PHẦN 2: BẢNG CHI TIẾT ---
            st.subheader("📑 Nhật ký vận hành thiết bị")
            st.dataframe(
                df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "STATUS": st.column_config.TextColumn("Trạng thái"),
                    "LAST_SEEN": st.column_config.TextColumn("Thời gian cập nhật")
                }
            )
            
            # Nút cập nhật thủ công
            if st.button("🔄 Cập nhật dữ liệu tức thì"):
                st.rerun()
                
        else:
            st.warning("⚠️ Kết nối thành công nhưng Sheet chưa có dữ liệu.")
            
    except Exception as e:
        st.error(f"Lỗi truy cập dữ liệu: {str(e)}")
        st.info("Mẹo: Đảm bảo sếp đã tắt chế độ 'Publish to Web' để đảm bảo tính riêng tư tuyệt đối.")
else:
    st.error("❌ Không thể khởi tạo kết nối. Sếp kiểm tra lại chuỗi Base64 trong Secrets nhé.")
