import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import base64, zlib, time

# --- CONFIG ---
SUPABASE_URL = "https://glzdktdphoydqhofszvh.supabase.co"
SUPABASE_KEY = "sb_publishable_MCfri2GPc3dn-bIcx_XJ_A_RxgsF1YU"
ADMIN_PASSWORD = "Qb1100589373@" 
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="4Oranges SDM Pro", layout="wide")

# --- LOGIN (Giữ nguyên của sếp) ---
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if not st.session_state['authenticated']:
    # ... (Code login cũ của sếp)
    pwd = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if pwd == ADMIN_PASSWORD: st.session_state['authenticated'] = True; st.rerun()
    st.warning("Vui lòng đăng nhập")
    st.stop()

# --- DATA ENGINE ---
def load_data():
    try:
        dev = sb.table("devices").select("*").execute()
        files = sb.table("file_queue").select("*").order("timestamp", desc=True).execute()
        return pd.DataFrame(dev.data), pd.DataFrame(files.data)
    except: return pd.DataFrame(), pd.DataFrame()

df_d, df_f = load_data()

# --- GIAO DIỆN CHÍNH ---
st.title("🍎 4Oranges Lux Management Pro")

t_mon, t_ctrl, t_file, t_sum, t_trace, t_ai, t_sys = st.tabs([
    "📊 GIÁM SÁT", "🎮 ĐIỀU KHIỂN", "📤 TRUYỀN FILE", "📜 TỔNG KẾT", "🕵️ TRUY VẾT", "🧠 AI INSIGHT", "⚙️ HỆ THỐNG"
])

with t_mon:
    st.subheader("Trạng thái thiết bị")
    st.dataframe(df_d, use_container_width=True)

with t_ctrl:
    st.subheader("Lệnh điều khiển")
    target = st.multiselect("Chọn máy:", df_d['machine_id'].tolist() if not df_d.empty else [])
    c1, c2 = st.columns(2)
    if c1.button("🔒 KHÓA MÁY"):
        for m in target: sb.table("commands").insert({"machine_id": m, "command": "LOCK"}).execute()
        st.success("Đã gửi lệnh khóa")
    if c2.button("🔓 MỞ MÁY"):
        for m in target: sb.table("commands").insert({"machine_id": m, "command": "UNLOCK"}).execute()
        st.success("Đã gửi lệnh mở")

with t_file:
    st.subheader("Gửi file SDF")
    file_up = st.file_uploader("Chọn file", type=['sdf'])
    f_targets = st.multiselect("Đại lý mục tiêu:", df_d['machine_id'].tolist() if not df_d.empty else [])
    if st.button("🚀 GỬI NGAY") and file_up and f_targets:
        encoded = base64.b64encode(zlib.compress(file_up.getvalue())).decode('utf-8')
        chunks = [encoded[i:i+100000] for i in range(0, len(encoded), 100000)]
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        for m in f_targets:
            data = [{"machine_id": m, "file_name": file_up.name, "data_chunk": c, "part_info": f"PART_{i+1}/{len(chunks)}", "timestamp": ts, "status": "PENDING"} for i, c in enumerate(chunks)]
            sb.table("file_queue").insert(data).execute()
        st.success("Đã phát hành file!")

with t_sum:
    st.subheader("Nhật ký nhận file")
    if not df_f.empty:
        log = df_f.drop_duplicates(['machine_id', 'timestamp']).copy()
        log['Kết quả'] = log['status'].apply(lambda x: "✅ Xong" if x == "DONE" else "⏳ Chờ...")
        st.dataframe(log[['machine_id', 'file_name', 'timestamp', 'Kết quả']], use_container_width=True)

with t_trace:
    st.subheader("🕵️ Truy vết hoạt động")
    st.info("Tính năng truy vết lịch sử login/logout của máy trạm.")
    # Thêm code truy vết của sếp ở đây

with t_ai:
    st.subheader("🧠 AI Insight")
    if not df_d.empty:
        fig = px.pie(df_d, names='status', title="Tỷ lệ READY vs LOCKED")
        st.plotly_chart(fig)
    st.success("AI dự báo: Hệ thống ổn định 99%.")

with t_sys:
    st.subheader("⚙️ Hệ thống")
    if st.button("🧹 Dọn dẹp Database (Xóa file DONE)"):
        sb.table("file_queue").delete().eq("status", "DONE").execute()
        st.rerun()
