import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import base64, zlib, time

# --- CORE CONFIG ---
SUPABASE_URL = "https://glzdktdphoydqhofszvh.supabase.co"
SUPABASE_KEY = "sb_publishable_MCfri2GPc3dn-bIcx_XJ_A_RxgsF1YU"
ADMIN_PASSWORD = "Qb1100589373@" 
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="4Oranges SDM Lux Secure Pro", layout="wide")

# --- LOGIN LOGIC (Khôi phục nguyên bản) ---
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if not st.session_state['authenticated']:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>🍎 SDM Secure Pro</h1>", unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password")
        if st.button("Đăng nhập", use_container_width=True):
            if pwd == ADMIN_PASSWORD: st.session_state['authenticated'] = True; st.rerun()
            else: st.error("Sai mật khẩu")
    st.stop()

# --- DATA LOADING ---
def load_all_data():
    try:
        dev = sb.table("devices").select("*").execute()
        cmd = sb.table("commands").select("*").order("created_at", desc=True).limit(20).execute()
        files = sb.table("file_queue").select("*").order("timestamp", desc=True).execute()
        return pd.DataFrame(dev.data), pd.DataFrame(cmd.data), pd.DataFrame(files.data)
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_d, df_c, df_f = load_all_data()

# --- HEADER (Khôi phục nguyên bản) ---
st.title("🍎 4Oranges Lux Management Pro")

# --- 7 TABS CHIẾN LƯỢC (Khôi phục đầy đủ) ---
t_mon, t_ctrl, t_file, t_sum, t_trace, t_ai, t_sys = st.tabs([
    "📊 GIÁM SÁT", "🎮 ĐIỀU KHIỂN", "📤 TRUYỀN FILE", "📜 TỔNG KẾT", "🕵️ TRUY VẾT", "🧠 AI INSIGHT", "⚙️ HỆ THỐNG"
])

with t_mon:
    st.subheader("Trạng thái thiết bị thời gian thực")
    st.dataframe(df_d, use_container_width=True, hide_index=True)

with t_ctrl:
    st.subheader("Trung tâm lệnh chiến lược")
    selected = st.multiselect("Nhắm mục tiêu:", df_d['machine_id'].tolist() if not df_d.empty else [])
    c1, c2 = st.columns(2)
    if c1.button("🔒 KHÓA MÁY", type="primary"):
        for m in selected: sb.table("commands").insert({"machine_id": m, "command": "LOCK"}).execute()
        st.toast("Lệnh LOCK phát đi!")
    if c2.button("🔓 MỞ MÁY"):
        for m in selected: sb.table("commands").insert({"machine_id": m, "command": "UNLOCK"}).execute()
        st.toast("Lệnh UNLOCK phát đi!")

with t_file:
    st.subheader("Phát hành bộ dữ liệu SDF")
    file_up = st.file_uploader("Kéo thả file .SDF", type=['sdf'])
    f_targets = st.multiselect("Đại lý nhận mục tiêu:", df_d['machine_id'].unique().tolist() if not df_d.empty else [])
    if st.button("🚀 KÍCH HOẠT ĐỒNG BỘ") and file_up and f_targets:
        encoded = base64.b64encode(zlib.compress(file_up.getvalue())).decode('utf-8')
        chunks = [encoded[i:i+100000] for i in range(0, len(encoded), 100000)]
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        for m in f_targets:
            payload = [{"machine_id": m, "file_name": file_up.name, "data_chunk": c, "part_info": f"PART_{i+1}/{len(chunks)}", "timestamp": ts, "status": "PENDING"} for i, c in enumerate(chunks)]
            sb.table("file_queue").insert(payload).execute()
        st.success("Đã phát lệnh đồng bộ!")

with t_sum:
    st.subheader("📜 Nhật ký vận hành")
    if not df_f.empty:
        log_df = df_f.drop_duplicates(subset=['machine_id', 'timestamp'])
        log_df['Kết quả'] = log_df['status'].apply(lambda x: "✅ Hoàn tất" if x == "DONE" else "⏳ Đang nhận...")
        st.dataframe(log_df[['machine_id', 'file_name', 'timestamp', 'Kết quả']], use_container_width=True)

with t_trace:
    st.subheader("🕵️ Kiểm soát vắng mặt")
    # Khôi phục logic slider của sếp
    threshold = st.slider("Ngưỡng vắng mặt (ngày):", 1, 90, 30)
    if not df_d.empty:
        df_d['last_seen_dt'] = pd.to_datetime(df_d['last_seen'])
        long_offline = df_d[df_d['last_seen_dt'] < (datetime.now(df_d['last_seen_dt'].dt.tz) - timedelta(days=threshold))]
        st.dataframe(long_offline, use_container_width=True)

with t_ai:
    st.subheader("🧠 SDM AI Strategic Hub")
    # Khôi phục biểu đồ và dự báo của sếp
    c_st1, c_st2 = st.columns(2)
    with c_st1:
        if not df_d.empty:
            st.plotly_chart(px.pie(df_d, names='status', title="Tình trạng hệ thống", hole=0.4))
    with c_st2:
        st.info("💡 **AI Dự báo:** Màu Xanh Ocean đang tăng trưởng mạnh.")

with t_sys:
    st.subheader("⚙️ Quản trị Database")
    if st.button("🧹 DỌN DẸP TOÀN BỘ RÁC", type="primary"):
        sb.table("file_queue").delete().eq("status", "DONE").execute()
        st.success("Đã dọn dẹp!")
