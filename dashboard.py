import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd

st.title("🛡️ 4Oranges SDM - AI Command Center")

# Xóa cache để tránh lỗi 403 cũ
st.cache_data.clear()

def get_data():
    try:
        # 1. Giải mã Key
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
        
        # 2. Kết nối
        creds = Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(creds)
        
        # 3. Mở file (Dùng ID chính xác của sếp)
        sh = client.open_by_key("1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH")
        
        # Lấy dữ liệu từ Sheet đầu tiên
        worksheet = sh.get_worksheet(0)
        data = worksheet.get_all_values()
        return data, None
    except Exception as e:
        return None, str(e)

# Thực thi lấy dữ liệu
data, error = get_data()

if data:
    st.success("🎉 CHÚC MỪNG SẾP! KẾT NỐI ĐÃ THÔNG SUỐT.")
    
    # Hiển thị bảng
    headers = data[0]
    df = pd.DataFrame(data[1:], columns=headers)
    
    st.write("### 📋 Danh sách thiết bị vận hành")
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # In tên các cột để xác nhận (Bước 2 sếp giao)
    st.info(f"Các cột tìm thấy: {', '.join(headers)}")
    
else:
    st.error(f"Lỗi: {error}")
    st.warning("Sếp hãy Reboot App trong mục 'Manage app' để xóa bộ nhớ đệm quyền truy cập nhé.")
