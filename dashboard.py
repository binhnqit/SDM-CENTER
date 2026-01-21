import streamlit as st
import json
import gspread
import base64
import pandas as pd
from google.oauth2.service_account import Credentials

# 1. Kết nối (Tự tìm Key trong Secrets)
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        if not k_name: return None
        decoded_data = base64.b64decode(st.secrets[k_name]).decode('utf-8')
        info = json.loads(decoded_data)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
    except: return None

st.set_page_config(page_title="4Oranges AI Center", layout="wide")
st.title("🛡️ 4Oranges SDM - AI Command Center")

client = get_gsheet_client()

if client:
    try:
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/edit"
        sheet = client.open_by_url(SHEET_URL).sheet1
        
        # Lấy mảng dữ liệu thô
        raw_rows = sheet.get_all_values()
        
        if len(raw_rows) > 1:
            # Ép cấu trúc 5 cột chuẩn
            headers = ["MACHINE_ID", "STATUS", "COMMAND", "LAST_SEEN", "HISTORY"]
            
            # Xử lý dữ liệu thông minh: Nếu dòng dưới thiếu ID, lấy ID dòng trên điền vào
            clean_data = []
            last_id = ""
            last_status = ""
            
            for row in raw_rows[1:]:
                # Bù ô trống nếu dòng ngắn hơn 5 cột
                r = (row + [""] * 5)[:5]
                
                # Logic điền khuyết (Fill-forward)
                current_id = r[0].strip()
                current_status = r[1].strip()
                
                if not current_id: r[0] = last_id
                else: last_id = current_id
                
                if not current_status: r[1] = last_status
                else: last_status = current_status
                
                clean_data.append(r)
            
            df = pd.DataFrame(clean_data, columns=headers)
            
            # HIỂN THỊ THÀNH QUẢ
            st.success("✅ ĐÃ ĐỒNG BỘ DỮ LIỆU THÀNH CÔNG!")
            
            # Widget chỉ số
            c1, c2, c3 = st.columns(3)
            c1.metric("Thiết bị", df['MACHINE_ID'].iloc[0])
            c2.metric("Trạng thái", df['STATUS'].iloc[0])
            c3.metric("Lệnh mới nhất", df[df['COMMAND'] != ""]['COMMAND'].iloc[-1] if not df[df['COMMAND'] != ""].empty else "NONE")

            st.divider()
            st.subheader("📑 Nhật ký vận hành thiết bị")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            if st.button("🔄 Cập nhật dữ liệu"):
                st.rerun()
        else:
            st.warning("⚠️ Sheet đang chỉ có tiêu đề.")
    except Exception as e:
        st.error(f"⚠️ Lỗi cấu trúc Sheet: {str(e)}")
else:
    st.error("❌ Không tìm thấy Key trong Secrets.")
