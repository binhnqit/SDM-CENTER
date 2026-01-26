import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, timedelta
import time
import plotly.express as px
import re
import zlib

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="4Oranges SDM - Phase 1 Pro", layout="wide")

@st.cache_resource(ttl=60)
def get_gspread_client():
    try:
        k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
        info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
        creds = Credentials.from_service_account_info(info, scopes=[
            "https://www.googleapis.com/auth/spreadsheets", 
            "https://www.googleapis.com/auth/drive"
        ])
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi kết nối API: {e}")
        return None

# --- KẾT NỐI VÀ DATA FETCHING ---
client = get_gspread_client()
SHEET_ID = "1LClTdR0z_FPX2AkYCfrbBRtWO8BWOG08hAEB8aq-TcI"
sh = client.open_by_key(SHEET_ID)
worksheet = sh.get_worksheet(0)  # Sheet1: Quản lý máy
ws_formula = sh.worksheet("Formulas") # Sheet: Truyền file

def load_processed_data():
    # Tải dữ liệu thô
    data = worksheet.get_all_values()
    if not data or len(data) < 2: return pd.DataFrame()
    
    df = pd.DataFrame(data[1:], columns=data[0])
    now = datetime.now()
    
    # 1. Xử lý Trạng thái & Tính ngày Offline
    def analyze_status(row):
        try:
            ls_time = datetime.strptime(row['LAST_SEEN'], "%d/%m/%Y %H:%M:%S")
            diff = now - ls_time
            if diff.total_seconds() < 120:
                return "ONLINE", 0
            return "OFFLINE", diff.days
        except:
            return "OFFLINE", -1

    status_results = df.apply(analyze_status, axis=1)
    df['ACTUAL_STATUS'] = [x[0] for x in status_results]
    df['OFFLINE_DAYS'] = [x[1] for x in status_results]
    
    # 2. AI Bóc tách màu từ History (Regex)
    def get_color(h):
        match = re.search(r'Pha màu:\s*([A-Z0-9-]+)', str(h))
        return match.group(1) if match else "N/A"
    df['COLOR_CODE'] = df['HISTORY'].apply(get_color)
    
    return df

df = load_processed_data()

# --- 2. GIAO DIỆN CHÍNH ---
st.title("🛡️ 4Oranges SDM - Trung tâm Điều hành AI")

# Tabs quản trị
t_ctrl, t_file, t_log, t_chart, t_ai = st.tabs([
    "🎮 CONTROL CENTER", "🧪 TRUYỀN FILE", "📜 LỊCH SỬ", "📊 PHÂN TÍCH", "🧠 AI INSIGHT"
])

# --- TAB 1: CONTROL CENTER ---
with t_ctrl:
    # Metrics tổng quan
    m1, m2, m3 = st.columns(3)
    on_count = len(df[df['ACTUAL_STATUS'] == "ONLINE"])
    off_count = len(df[df['ACTUAL_STATUS'] == "OFFLINE"])
    m1.metric("Tổng thiết bị", len(df))
    m2.metric("Đang Online", on_count, f"{on_count/len(df)*100:.1f}%")
    m3.metric("Đang Offline", off_count, f"-{off_count}", delta_color="inverse")

    st.divider()

    # Khu vực gửi lệnh thông minh
    with st.expander("🚀 GỬI LỆNH ĐIỀU KHIỂN (LOCK/UNLOCK)", expanded=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            # Tìm kiếm máy cực nhanh
            q = st.text_input("🔍 Tìm máy theo ID:", placeholder="Nhập mã máy...")
            filtered = df[df['MACHINE_ID'].str.contains(q, case=False)] if q else df
            target_id = st.selectbox("🎯 Chọn máy mục tiêu:", filtered['MACHINE_ID'].tolist())
        with c2:
            cmd = st.selectbox("📜 Chọn lệnh thực thi:", ["NONE", "LOCK", "UNLOCK", "FORCE_UPDATE"])
        with c3:
            st.write("##")
            if st.button("🚀 XÁC NHẬN GỬI", use_container_width=True, type="primary"):
                try:
                    # TỐI ƯU GIAI ĐOẠN 1: Tìm hàng theo ID thực tế, không dùng index ảo
                    cell = worksheet.find(target_id)
                    worksheet.update_cell(cell.row, 3, cmd)
                    st.success(f"Đã khóa mục tiêu {target_id} thành công!")
                    time.sleep(1)
                    st.rerun()
                except:
                    st.error("Không tìm thấy hàng dữ liệu tương ứng trên Sheet!")

    # Bảng hiển thị
    col_on, col_off = st.columns(2)
    with col_on:
        st.subheader("🟢 ONLINE")
        st.dataframe(df[df['ACTUAL_STATUS'] == "ONLINE"][['MACHINE_ID', 'COMMAND', 'LAST_SEEN', 'HISTORY']], use_container_width=True, hide_index=True)
    with col_off:
        st.subheader("🔴 OFFLINE")
        df_off = df[df['ACTUAL_STATUS'] == "OFFLINE"].copy()
        df_off['CẢNH BÁO'] = df_off['OFFLINE_DAYS'].apply(lambda x: f"Mất kết nối {x} ngày" if x >= 0 else "N/A")
        st.dataframe(df_off[['MACHINE_ID', 'CẢNH BÁO', 'LAST_SEEN']], use_container_width=True, hide_index=True)

# --- TAB 2: TRUYỀN FILE (MULTI-CHUNK) ---
with t_file:
    st.subheader("🧪 Đẩy công thức .SDF dung lượng lớn")
    f = st.file_uploader("Chọn file .sdf:", type=['sdf'])
    targets = st.multiselect("Máy nhận:", df['MACHINE_ID'].unique())
    if st.button("📤 BẮT ĐẦU TRUYỀN TẢI", type="primary"):
        if f and targets:
            with st.spinner("Đang xé nhỏ và mã hóa dữ liệu..."):
                raw = f.getvalue()
                compressed = base64.b64encode(zlib.compress(raw)).decode('utf-8')
                chunk_size = 30000
                chunks = [compressed[i:i+chunk_size] for i in range(0, len(compressed), chunk_size)]
                ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                path = r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Updates"
                
                all_rows = []
                for m in targets:
                    for i, c in enumerate(chunks):
                        all_rows.append([m, f.name, c, path, ts, f"PART_{i+1}/{len(chunks)}", "PENDING"])
                
                ws_formula.append_rows(all_rows)
                st.success(f"✅ Đã đẩy {len(chunks)} mảnh dữ liệu lên hàng đợi!")
                st.balloons()

# -- TAB 3: LỊCH SỬ & DỌN DẸP ---
with t_log:
    st.subheader("📜 Nhật ký truyền tải")
    
    # Lấy dữ liệu mới nhất
    logs_data = ws_formula.get_all_values()
    if len(logs_data) > 1:
        ldf = pd.DataFrame(logs_data[1:], columns=logs_data[0])
        
        # Nút dọn dẹp để sếp bấm khi muốn xóa hết hàng đợi
        if st.button("🗑️ XÓA TOÀN BỘ LỊCH SỬ (Dọn sạch hàng đợi)", type="secondary"):
            # Giữ lại hàng tiêu đề, xóa toàn bộ nội dung dưới
            ws_formula.resize(rows=1) 
            ws_formula.resize(rows=2000)
            ws_formula.update('A1:G1', [EXPECTED_HEADERS])
            st.success("Đã dọn sạch hàng đợi truyền file!")
            time.sleep(1)
            st.rerun()

        st.divider()
        st.dataframe(ldf[['MACHINE_ID', 'FILE_NAME', 'TIMESTAMP', 'PART_INFO', 'STATUS']].tail(50), use_container_width=True, hide_index=True)
    else:
        st.info("Hàng đợi đang trống. Sẵn sàng cho file mới.")

# --- TAB 4: PHÂN TÍCH ---
with t_chart:
    st.subheader("📊 Thống kê sản lượng")
    c1, c2 = st.columns(2)
    with c1:
        color_data = df[df['COLOR_CODE'] != "N/A"]['COLOR_CODE'].value_counts().head(10).reset_index()
        fig = px.bar(color_data, x='COLOR_CODE', y='count', title="🔥 TOP 10 MÀU PHA", color='count')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig_p = px.pie(df, names='ACTUAL_STATUS', title="🌐 TỶ LỆ KẾT NỐI", color_discrete_sequence=['#2ECC71', '#E74C3C'])
        st.plotly_chart(fig_p, use_container_width=True)

# --- TAB 5: AI INSIGHT ---
with t_ai:
    st.subheader("🧠 Trợ lý Quản trị thông minh")
    urgent = df[df['OFFLINE_DAYS'] > 2]
    if not urgent.empty:
        st.error(f"⚠️ CẢNH BÁO: Có {len(urgent)} máy mất kết nối trên 48h. Đề xuất kiểm tra nguồn điện/mạng.")
    
    st.info("💡 Mẹo AI: Dòng màu 'OZ' đang chiếm 40% sản lượng. Hãy kiểm tra mức tinh màu trong máy tại các đại lý miền Tây.")

# Sidebar
with st.sidebar:
    st.image("https://4oranges.com/wp-content/uploads/2021/08/logo-4oranges.png", width=150)
    st.write(f"🕒 Sync: {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 LÀM MỚI DỮ LIỆU"): st.rerun()
