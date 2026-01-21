import streamlit as st
import json
import base64
from googleapiclient.discovery import build
from google.oauth2 import service_account

st.title("🔍 Chẩn đoán Hệ thống 4Oranges (Step-by-Step)")

def start_diagnostic():
    # --- STEP 1: KIỂM TRA CHÌA KHÓA SECRETS ---
    st.write("### 🟢 Bước 1: Kiểm tra cấu trúc Key")
    try:
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        decoded_key = base64.b64decode(st.secrets[k_name]).decode('utf-8')
        info = json.loads(decoded_key)
        service_email = info.get("client_email")
        st.success(f"Key hợp lệ. Email Service Account: `{service_email}`")
    except Exception as e:
        st.error(f"Thất bại tại Bước 1: {e}")
        return

    # --- STEP 2: KHỞI TẠO KẾT NỐI (AUTHORIZATION) ---
    st.write("### 🟢 Bước 2: Thiết lập kết nối Google API")
    try:
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        service = build('sheets', 'v4', credentials=creds)
        st.success("Kết nối API thành công.")
    except Exception as e:
        st.error(f"Thất bại tại Bước 2: {e}")
        return

    # --- STEP 3: KIỂM TRA QUYỀN TRUY CẬP FILE (THE CRITICAL STEP) ---
    st.write("### 🟢 Bước 3: Thử mở File & Kiểm tra quyền")
    # ID file lấy từ URL sếp cung cấp
    SPREADSHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH"
    
    try:
        # Thử lấy thông tin cơ bản của file (Metadata)
        sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        title = sheet_metadata.get('properties', {}).get('title')
        st.success(f"Mở file thành công! Tên Sheet: **{title}**")
    except Exception as e:
        error_json = json.loads(e.content.decode('utf-8')) if hasattr(e, 'content') else {}
        error_detail = error_json.get('error', {}).get('message', str(e))
        status_code = error_json.get('error', {}).get('code', 'N/A')
        
        st.error(f"Thất bại tại Bước 3 (Mã lỗi {status_code})")
        st.warning(f"Lý do từ Google: **{error_detail}**")
        
        if status_code == 403:
            st.info("💡 Đây là lỗi Quyền: Sếp hãy đảm bảo email ở Bước 1 đã có quyền 'Viewer' hoặc 'Editor' trên file.")
        elif status_code == 404:
            st.info("💡 Đây là lỗi ID: Google không tìm thấy file này. Sếp kiểm tra lại ID trong code.")
        return

    # --- STEP 4: ĐỌC DỮ LIỆU THỰC TẾ ---
    st.write("### 🟢 Bước 4: Đọc dữ liệu dòng đầu tiên")
    try:
        range_name = 'Sheet1!A1:E1' # Thử đọc hàng tiêu đề
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
        values = result.get('values', [])
        
        if values:
            st.success("Đã đọc được dữ liệu!")
            st.code(values[0])
            st.balloons()
        else:
            st.warning("File mở được nhưng không có dữ liệu tại vùng 'Sheet1!A1:E1'.")
    except Exception as e:
        st.error(f"Thất bại tại Bước 4: {e}")

if st.button("🚀 BẮT ĐẦU CHẨN ĐOÁN"):
    start_diagnostic()
