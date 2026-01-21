import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials

# 1. Kết nối trực tiếp (Quét sạch mọi loại Key trong Secrets)
def get_client():
    try:
        # Tự động tìm key bất kể sếp đặt tên biến là gì
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        if not k_name:
            st.error("❌ Không tìm thấy biến Key trong Secrets!")
            return None
        
        info = json.loads(base64.b64decode(st.secrets[k_name]).decode())
        creds = Credentials.from_service_account_info(
            info, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi xác thực Key: {str(e)}")
        return None

st.set_page_config(page_title="4Oranges SDM", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

client = get_client()

if client:
    try:
        # ID Sheet lấy trực tiếp từ URL sếp gửi
        SPREADSHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH"
        
        # Mở bằng ID để tránh lỗi định dạng URL
        sh = client.open_by_key(SPREADSHEET_ID)
        worksheet = sh.get_worksheet(0) # Mở tab đầu tiên
        
        # LẤY DỮ LIỆU
        all_values = worksheet.get_all_values()
        
        if all_values:
            st.success("✅ HỆ THỐNG ĐÃ THÔNG SUỐT!")
            
            # Dashboard Widget
            if len(all_values) > 1:
                row2 = all_values[1]
                c1, c2, c3 = st.columns(3)
                c1.metric("THIẾT BỊ", row2[0] if len(row2) > 0 else "---")
                c2.metric("TRẠNG THÁI", row2[1] if len(row2) > 1 else "---")
                c3.metric("LỆNH", row2[2] if len(row2) > 2 else "---")
            
            st.divider()
            
            # Hiển thị bảng 1:1 như Google Sheet
            st.write("### 📑 Bảng dữ liệu thực tế")
            st.table(all_values)
            
        else:
            st.warning("⚠️ Sheet này hiện đang trống.")
            
    except gspread.exceptions.APIError as e:
        st.error(f"❌ Lỗi API Google: Có thể sếp chưa bật 'Google Sheets API' trong Google Cloud Console.")
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("❌ Không tìm thấy file Sheet. Kiểm tra lại ID hoặc quyền chia sẻ.")
    except Exception as e:
        st.error(f"❌ Lỗi không xác định: {str(e)}")
else:
    st.info("💡 Mẹo: Hãy đảm bảo sếp đã dán đúng chuỗi Base64 vào Secrets.")
