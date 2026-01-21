import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd

st.set_page_config(page_title="4Oranges Secure Center", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

# --- HÀM KIỂM TRA LỖI CHI TIẾT ---
def get_verified_client():
    try:
        # 1. Tìm Key
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        if not k_name:
            st.error("❌ Lỗi: Không tìm thấy Key trong Secrets.")
            return None
        
        # 2. Giải mã JSON
        try:
            decoded = base64.b64decode(st.secrets[k_name]).decode('utf-8')
            info = json.loads(decoded)
        except:
            st.error("❌ Lỗi: Chuỗi Base64 trong Secrets bị hỏng hoặc sai định dạng JSON.")
            return None
            
        # 3. Kết nối Google
        creds = Credentials.from_service_account_info(
            info, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Lỗi xác thực hệ thống: {str(e)}")
        return None

client = get_verified_client()

if client:
    try:
        # ID Sheet cố định của sếp
        SHEET_ID = "1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH"
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.get_worksheet(0)
        
        # Lấy dữ liệu thô
        raw_values = worksheet.get_all_values()
        
        if raw_values:
            st.success("🔒 TRẠNG THÁI: KẾT NỐI BẢO MẬT ĐÃ THÔNG SUỐT")
            
            # Hiển thị bảng dữ liệu (Ép đúng 5 cột như sếp đã xác nhận)
            headers = ["MACHINE_ID", "STATUS", "COMMAND", "LAST_SEEN", "HISTORY"]
            # Chỉ lấy dữ liệu từ hàng 2, bù ô trống nếu thiếu
            data_rows = [(row + [""] * 5)[:5] for row in raw_values[1:]]
            
            df = pd.DataFrame(data_rows, columns=headers)
            
            # Hiển thị Dashboard chuyên nghiệp
            c1, c2 = st.columns([1, 3])
            with c1:
                st.metric("Thiết bị", df['MACHINE_ID'].iloc[0] if not df.empty else "N/A")
                st.metric("Trạng thái", df['STATUS'].iloc[0] if not df.empty else "N/A")
            
            with c2:
                st.subheader("📑 Nhật ký vận hành thực tế")
                st.dataframe(df, use_container_width=True, hide_index=True)
            
            if st.button("🔄 Refresh Data"):
                st.rerun()
        else:
            st.warning("⚠️ Kết nối OK nhưng Sheet không có dữ liệu.")

    except gspread.exceptions.APIError:
        st.error("❌ Lỗi: Google Sheets API chưa được bật trong Google Cloud Console.")
        st.info("Sếp hãy vào link này nhấn ENABLE: https://console.cloud.google.com/apis/library/sheets.googleapis.com")
    except Exception as e:
        st.error(f"❌ Lỗi truy cập dữ liệu: {str(e)}")
        st.info("💡 Mẹo: Sếp hãy thử vào 'Manage app' -> 'Reboot App' để làm mới quyền truy cập.")
