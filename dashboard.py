import streamlit as st
import json
import gspread
import base64
import pandas as pd
from google.oauth2.service_account import Credentials

# 1. Kết nối bảo mật (Tự động quét Key)
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # Tìm bất kỳ biến nào chứa mã Key trong Secrets
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
        # URL Sheet từ file của sếp
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet = client.open_by_url(SHEET_URL).sheet1
        
        # Lấy dữ liệu thô (để chống lỗi cấu trúc dòng trống)
        raw_rows = sheet.get_all_values()
        
        if len(raw_rows) > 0:
            # Ép tên cột theo đúng thực tế sếp đang có trên màn hình
            headers = ["MACHINE_ID", "STATUS", "COMMAND", "LAST_SEEN", "HISTORY"]
            
            # Chỉ lấy tối đa 5 cột đầu tiên để tránh lỗi nếu sếp gõ thừa vào cột F, G
            data_clean = [row[:5] for row in raw_rows[1:]]
            
            # Tạo bảng dữ liệu
            df = pd.DataFrame(data_clean, columns=headers)
            
            # Loại bỏ các dòng hoàn toàn không có chữ nào (dòng trắng)
            df = df.replace('', pd.NA).dropna(how='all')

            # --- HIỂN THỊ KẾT QUẢ ---
            st.success("✅ ĐÃ KẾT NỐI VÀ ĐỒNG BỘ DỮ LIỆU THÀNH CÔNG!")
            
            # Lấy thông tin máy đầu tiên để hiện Metric cho oai
            if not df.empty:
                m1, m2 = st.columns(2)
                m1.metric("Thiết bị chính", df['MACHINE_ID'].iloc[0])
                m2.metric("Trạng thái", df['STATUS'].iloc[0] or "N/A")

            st.divider()
            st.subheader("📑 Danh sách chi tiết & Nhật ký lệnh")
            
            # Hiển thị bảng đẹp, thay thế giá trị rỗng bằng dấu gạch ngang
            st.dataframe(df.fillna("-"), use_container_width=True, hide_index=True)
            
            if st.button("🔄 Làm mới dữ liệu từ Google Sheet"):
                st.rerun()
        else:
            st.warning("⚠️ Google Sheet đang trống, sếp hãy nhập dữ liệu vào.")
            
    except Exception as e:
        st.error(f"⚠️ Lỗi xử lý: {str(e)}")
else:
    st.error("❌ Không thể kết nối. Sếp hãy kiểm tra lại mục Secrets trên Streamlit.")
