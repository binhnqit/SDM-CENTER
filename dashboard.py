import streamlit as st
import json
import base64
import requests

st.set_page_config(page_title="Hệ thống Truy vết 4Oranges", layout="wide")
st.title("🔍 Chẩn đoán Hệ thống Step-by-Step")

def start_diagnostic():
    # --- BƯỚC 1: KIỂM TRA KEY ---
    st.write("### 🟢 Bước 1: Kiểm tra chìa khóa (Secrets)")
    try:
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        if not k_name:
            st.error("Thất bại: Không thấy Key trong Secrets!")
            return
        
        info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
        service_email = info.get("client_email")
        st.success(f"Key OK. Email Service Account: `{service_email}`")
    except Exception as e:
        st.error(f"Lỗi Bước 1: {e}")
        return

    # --- BƯỚC 2: LẤY TOKEN KẾT NỐI ---
    st.write("### 🟢 Bước 2: Thử gọi Google API (Check Permission)")
    # ID file của sếp
    SHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH"
    
    # Chúng ta dùng link metadata để kiểm tra quyền truy cập nhanh
    test_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=properties(title)"
    
    st.info("Đang gửi yêu cầu xác thực đến Google...")
    
    # Ở đây chúng ta tạm dùng link public để check xem link có chết không
    # Nếu link public sếp đã tắt, bước này sẽ báo lỗi 403 - ĐÓ LÀ LÚC TA BIẾT EMAIL CẦN QUYỀN
    try:
        response = requests.get(test_url)
        status = response.status_code
        
        if status == 200:
            st.success("✅ Tuyệt vời: Link vẫn đang mở Public hoặc truy cập được!")
            st.write("Tên file:", response.json().get('properties', {}).get('title'))
        elif status == 403:
            st.error("❌ Lỗi 403 (Forbidden): Google đã chặn.")
            st.warning(f"Lý do: File này đang được BẢO MẬT. Sếp cần đảm bảo email `{service_email}` đã có quyền Editor.")
        elif status == 404:
            st.error("❌ Lỗi 404: Không tìm thấy ID file. Sếp kiểm tra lại ID trong code.")
        else:
            st.write(f"Mã phản hồi khác: {status}")
            
    except Exception as e:
        st.error(f"Lỗi kết nối mạng: {e}")

if st.button("🚀 BẮT ĐẦU TRUY VẾT"):
    start_diagnostic()
