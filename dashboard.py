import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time
import io
import plotly.express as px
import re
from googleapiclient.discovery import build # Thêm thư viện Drive API
from googleapiclient.http import MediaIoBaseUpload

# --- 1. CẤU HÌNH & KẾT NỐI ---
st.set_page_config(page_title="4Oranges SDM - AI Cloud Sync", layout="wide")

@st.cache_resource(ttl=60)
def get_all_creds():
    k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
    info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
    scopes = ["https://www.googleapis.com/auth/spreadsheets", 
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return creds

creds = get_all_creds()
client = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds) # Khởi tạo Drive Service

SHEET_ID = "1LClTdR0z_FPX2AkYCfrbBRtWO8BWOG08hAEB8aq-TcI"
sh = client.open_by_key(SHEET_ID)
worksheet = sh.get_worksheet(0)

try:
    ws_formula = sh.worksheet("Formulas")
except:
    ws_formula = sh.add_worksheet("Formulas", rows=1000, cols=6)
    ws_formula.append_row(["MACHINE_ID", "FILE_NAME", "DRIVE_LINK", "TARGET_PATH", "TIMESTAMP", "STATUS"])

# --- 2. HÀM UPLOAD FILE LÊN DRIVE ---
def upload_to_drive(file_obj, filename):
    file_metadata = {'name': filename}
    media = MediaIoBaseUpload(file_obj, mimetype='application/octet-stream', resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    # Cấp quyền xem cho bất kỳ ai có link (để Agent tải được)
    drive_service.permissions().create(fileId=file.get('id'), body={'type': 'anyone', 'role': 'viewer'}).execute()
    return f"https://drive.google.com/uc?id={file.get('id')}"

# --- 3. XỬ LÝ DỮ LIỆU ---
def load_and_analyze():
    data = worksheet.get_all_values()
    if not data or len(data) < 2: return pd.DataFrame()
    df = pd.DataFrame(data[1:], columns=data[0])
    df = df[df['MACHINE_ID'].str.strip() != ""].copy()
    df['sheet_row'] = df.index + 2
    
    def check_status(ls_str):
        try:
            ls = datetime.strptime(ls_str, "%d/%m/%Y %H:%M:%S")
            return "ONLINE" if (datetime.now() - ls).total_seconds() < 120 else "OFFLINE"
        except: return "OFFLINE"
    
    df['ACTUAL_STATUS'] = df['LAST_SEEN'].apply(check_status)
    return df

df = load_and_analyze()

# --- 4. GIAO DIỆN TABS ---
st.title("🛡️ 4Oranges SDM - Cloud Sync Elite")

tab_control, tab_formula, tab_color_stats, tab_ai_insight = st.tabs([
    "🎮 CONTROL CENTER", "🧪 PRISMAPRO CLOUD UPDATE", "🎨 COLOR ANALYTICS", "🧠 AI STRATEGY"
])

# --- TAB 1: CONTROL CENTER (GIỮ NGUYÊN) ---
with tab_control:
    if not df.empty:
        # Code hiển thị metrics và phát lệnh giống V8.3
        st.dataframe(df[['MACHINE_ID', 'ACTUAL_STATUS', 'COMMAND', 'LAST_SEEN', 'HISTORY']], use_container_width=True, hide_index=True)

# --- TAB 2: PRISMAPRO UPDATE (XỬ LÝ LỖI QUA DRIVE) ---
with tab_formula:
    st.subheader("🧬 Đẩy File .sdf qua Cloud Drive")
    PRISMA_PATH = r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Updates"
    
    with st.container(border=True):
        f_col1, f_col2 = st.columns([1, 1])
        with f_col1:
            uploaded_file = st.file_uploader("📂 Chọn file công thức (.sdf):", type=['sdf'], key="f_sdf_v84")
        
        with f_col2:
            target_machines = st.multiselect("🎯 Máy nhận file:", df['MACHINE_ID'].unique() if not df.empty else [])
            if st.button("📤 TẢI LÊN & ĐẨY LỆNH", use_container_width=True, type="primary"):
                if uploaded_file and target_machines:
                    with st.spinner("Đang tải file lên Cloud Drive..."):
                        try:
                            # 1. Upload lên Drive lấy link
                            drive_link = upload_to_drive(io.BytesIO(uploaded_file.getvalue()), uploaded_file.name)
                            
                            # 2. Đẩy Link vào Sheet Formulas
                            ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                            for m_id in target_machines:
                                ws_formula.append_row([m_id, uploaded_file.name, drive_link, PRISMA_PATH, ts, "PENDING"])
                            
                            st.success(f"✅ Đã tải lên Drive và lập lịch cho {len(target_machines)} máy!")
                        except Exception as e:
                            st.error(f"Lỗi hệ thống Cloud: {e}")
                else:
                    st.error("Vui lòng chọn File và Máy mục tiêu!")

# (Tab 3 & 4 giữ nguyên logic thống kê của sếp)
