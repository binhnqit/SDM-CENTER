import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time
import io
import re

# --- 1. CẤU HÌNH & KẾT NỐI (GIỮ NGUYÊN LÕI V8.1) ---
st.set_page_config(page_title="4Oranges SDM - PrismaPro Update", layout="wide")

@st.cache_resource(ttl=60)
def get_gspread_client():
    k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
    info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
    creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

client = get_gspread_client()
SHEET_ID = "1LClTdR0z_FPX2AkYCfrbBRtWO8BWOG08hAEB8aq-TcI"
sh = client.open_by_key(SHEET_ID)
worksheet = sh.get_worksheet(0)

# Đảm bảo Sheet Formulas có cấu trúc chuẩn để Agent đọc đường dẫn
try:
    ws_formula = sh.worksheet("Formulas")
except:
    ws_formula = sh.add_worksheet("Formulas", rows=1000, cols=10)
    ws_formula.append_row(["MACHINE_ID", "FILE_NAME", "CONTENT", "TARGET_PATH", "TIMESTAMP", "STATUS"])

# --- 2. LOAD DỮ LIỆU ---
def load_data():
    data = worksheet.get_all_values()
    if not data or len(data) < 2: return pd.DataFrame()
    df = pd.DataFrame(data[1:], columns=data[0])
    df = df[df['MACHINE_ID'].str.strip() != ""].copy()
    df['sheet_row'] = df.index + 2
    now = datetime.now()
    df['ACTUAL_STATUS'] = df['LAST_SEEN'].apply(lambda x: "ONLINE" if x and (now - datetime.strptime(x, "%d/%m/%Y %H:%M:%S")).total_seconds() < 120 else "OFFLINE")
    return df

df = load_data()

# --- 3. GIAO DIỆN CHÍNH ---
st.title("🛡️ 4Oranges SDM - PrismaPro Update Center")

tab_control, tab_formula = st.tabs(["🎮 ĐIỀU KHIỂN", "🧪 CẬP NHẬT CÔNG THỨC (.SDF)"])

# --- TAB 1: CONTROL CENTER (GIỮ NGUYÊN) ---
with tab_control:
    st.info("Sử dụng để khóa/mở hoặc kiểm tra trạng thái máy pha màu.")
    # (Phần này giữ nguyên code hiển thị bảng và phát lệnh của sếp)
    st.dataframe(df[['MACHINE_ID', 'ACTUAL_STATUS', 'COMMAND', 'LAST_SEEN']], use_container_width=True)

# --- TAB 2: FORMULA SYNC (SỬA ĐỔI THEO YÊU CẦU) ---
with tab_formula:
    st.subheader("🧬 Đẩy file công thức hệ thống (.sdf)")
    
    # Đường dẫn cố định theo yêu cầu của sếp
    PRISMA_PATH = r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Updates"
    
    st.warning(f"📍 Đường dẫn đích trên máy khách: `{PRISMA_PATH}`")
    
    with st.container(border=True):
        f_col1, f_col2 = st.columns([1, 1])
        
        with f_col1:
            # Sửa đổi 1: Chỉ chấp nhận file .sdf
            uploaded_file = st.file_uploader("📂 Chọn file công thức (.sdf):", type=['sdf'], key="sdf_uploader")
            
            file_content = ""
            file_name = ""
            if uploaded_file:
                file_name = uploaded_file.name
                # Đọc dữ liệu file (SDF thường là text hoặc binary tùy phiên bản, ở đây đọc dạng string base64 để an toàn)
                file_content = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
                st.success(f"✅ Đã sẵn sàng file: {file_name}")
            
            manual_name = st.text_input("Hoặc nhập tên file thủ công (nếu không upload):", placeholder="ColorData.sdf")

        with f_col2:
            target_machines = st.multiselect("🎯 Chọn máy đại lý cần cập nhật:", df['MACHINE_ID'].unique(), key="target_sync")
            st.write("##")
            
            if st.button("🚀 GỬI CẬP NHẬT XUỐNG MÁY CHỌN", use_container_width=True, type="primary"):
                final_name = file_name if file_name else manual_name
                
                if not target_machines or not final_name or not file_content:
                    st.error("Vui lòng chọn File .sdf và ít nhất 1 Máy mục tiêu!")
                else:
                    with st.spinner("Đang truyền dữ liệu qua Cloud..."):
                        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        for m_id in target_machines:
                            # Gửi dữ liệu kèm theo đường dẫn đích (TARGET_PATH)
                            ws_formula.append_row([
                                m_id, 
                                final_name, 
                                file_content, 
                                PRISMA_PATH, 
                                ts, 
                                "PENDING"
                            ])
                        st.balloons()
                        st.success(f"Đã gửi lệnh cập nhật file {final_name} tới {len(target_machines)} máy thành công!")

    # Hiển thị lịch sử đẩy file
    st.write("### 🕒 Nhật ký đẩy file gần đây")
    try:
        log_data = ws_formula.get_all_records()
        if log_data:
            st.table(pd.DataFrame(log_data).tail(5))
    except:
        st.info("Chưa có nhật ký cập nhật.")
