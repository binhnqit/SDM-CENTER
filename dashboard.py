import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Hệ thống Truy vết Lỗi", layout="wide")
st.title("🛡️ 4Oranges SDM - Hệ thống Truy vết Lỗi")

def trace_error():
    # --- BƯỚC 1: KIỂM TRA SECRETS ---
    st.write("### 🔍 Bước 1: Kiểm tra chìa khóa (Secrets)")
    k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
    
    if not k_name:
        st.error("❌ KHÔNG TÌM THẤY KEY: Sếp chưa dán mã JSON vào mục Secrets.")
        return
    st.success(f"✅ Tìm thấy biến lưu trữ: `{k_name}`")

    # --- BƯỚC 2: GIẢI MÃ JSON ---
    st.write("### 🔍 Bước 2: Giải mã & Kiểm tra định dạng JSON")
    try:
        raw_key = st.secrets[k_name]
        decoded = base64.b64decode(raw_key).decode('utf-8')
        info = json.loads(decoded)
        service_email = info.get("client_email")
        st.success(f"✅ Giải mã thành công JSON.")
        st.info(f"📧 Email Service Account của sếp là: `{service_email}`")
        st.warning("👉 Sếp hãy copy email trên và kiểm tra xem đã Share quyền 'Editor' trong Google Sheet chưa.")
    except Exception as e:
        st.error(f"❌ LỖI ĐỊNH DẠNG: Chìa khóa bị hỏng hoặc dán thiếu. Chi tiết: {e}")
        return

    # --- BƯỚC 3: KẾT NỐI API ---
    st.write("### 🔍 Bước 3: Kết nối đến máy chủ Google API")
    try:
        creds = Credentials.from_service_account_info(
            info, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)
        st.success("✅ Kết nối API thành công.")
    except Exception as e:
        st.error(f"❌ LỖI KẾT NỐI API: Có thể do mạng hoặc Google Cloud chặn. Chi tiết: {e}")
        return

    # --- BƯỚC 4: TRUY CẬP FILE SHEET ---
    st.write("### 🔍 Bước 4: Mở File Sheet & Đọc dữ liệu")
    SHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH"
    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.get_worksheet(0)
        data = worksheet.row_values(1)
        st.success("✅ ĐÃ MỞ ĐƯỢC SHEET VÀ ĐỌC ĐƯỢC DÒNG TIÊU ĐỀ!")
        st.code(data)
    except gspread.exceptions.PermissionError:
        st.error("❌ LỖI QUYỀN TRUY CẬP: Email trên chưa được Share quyền vào Sheet này.")
    except gspread.exceptions.APIError as e:
        if "API has not been used" in str(e):
            st.error("❌ LỖI API: Sếp chưa nhấn 'ENABLE' Google Sheets API trong Google Cloud Console.")
        else:
            st.error(f"❌ Lỗi API khác: {e}")
    except Exception as e:
        st.error(f"❌ Lỗi không xác định khi mở Sheet: {type(e).__name__} - {e}")

# Chạy truy vết
if st.button("🚀 BẮT ĐẦU TRUY VẾT"):
    trace_error()
else:
    st.info("Nhấn nút trên để hệ thống bắt đầu kiểm tra từng bước.")
