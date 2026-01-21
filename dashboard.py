import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials

# --- PHẦN 1: KẾT NỐI ---
st.title("🧪 Kiểm tra kết nối & Cấu trúc")

try:
    # Lấy đúng chìa khóa từ Secrets (không tự đoán tên biến)
    # Sếp hãy kiểm tra tên biến trong Secrets là gì thì thay vào ['GCP_KEY'] nhé
    k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
    
    if k_name:
        # Giải mã và nạp quyền
        decoded_info = json.loads(base64.b64decode(st.secrets[k_name]).decode())
        creds = Credentials.from_service_account_info(
            decoded_info, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)
        
        # Mở Sheet bằng ID thực tế của sếp
        SPREADSHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH"
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        
        st.success("✅ ĐÃ KẾT NỐI ĐƯỢC VỚI GOOGLE SHEET!")

        # --- PHẦN 2: IN TÊN CỘT ---
        # Chỉ lấy duy nhất hàng 1 (hàng tiêu đề)
        headers = sheet.row_values(1)
        
        if headers:
            st.write("### Danh sách tên cột tìm thấy:")
            st.code(headers) # In ra dưới dạng mảng để sếp nhìn rõ nhất
        else:
            st.warning("Kết nối được nhưng hàng 1 đang trống.")
            
    else:
        st.error("Không tìm thấy Key trong Secrets. Sếp hãy kiểm tra lại bảng điều khiển Streamlit.")

except Exception as e:
    st.error(f"Lỗi: {str(e)}")
