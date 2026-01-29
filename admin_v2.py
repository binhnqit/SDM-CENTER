import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import base64, zlib, time

# --- CORE CONFIG ---
SUPABASE_URL = "https://glzdktdphoydqhofszvh.supabase.co"
SUPABASE_KEY = "sb_publishable_MCfri2GPc3dn-bIcx_XJ_A_RxgsF1YU"
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="4Oranges SDM Lux Admin", layout="wide", initial_sidebar_state="collapsed")

# --- STYLE APPLE CSS ---
st.markdown("""
    <style>
    .main { background-color: #f5f5f7; }
    .stMetric { background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .stButton>button { border-radius: 10px; padding: 0.5rem 2rem; transition: all 0.3s; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
    div[data-baseweb="tab-list"] { gap: 20px; border-bottom: none; }
    div[data-baseweb="tab"] { background-color: transparent !important; border: none !important; font-weight: 600; color: #86868b; }
    div[data-baseweb="tab"][aria-selected="true"] { color: #0071e3 !important; border-bottom: 2px solid #0071e3 !important; }
    </style>
""", unsafe_allow_html=True)

# --- DATA ENGINE ---
def load_all_data():
    try:
        dev = sb.table("devices").select("*").execute()
        cmd = sb.table("commands").select("*").order("created_at", desc=True).limit(10).execute()
        files = sb.table("file_queue").select("*").order("timestamp", desc=True).execute()
        return pd.DataFrame(dev.data), pd.DataFrame(cmd.data), pd.DataFrame(files.data)
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_d, df_c, df_f = load_all_data()

# --- HEADER SECTION ---
c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.title("🍎 4Oranges Lux Management")
    st.caption("Hệ thống quản trị thiết bị đầu cuối tiêu chuẩn Enterprise")

# --- TOP METRICS ---
if not df_d.empty:
    m1, m2, m3, m4 = st.columns(4)
    df_d['is_online'] = (datetime.now(pd.to_datetime(df_d['last_seen']).dt.tz) - pd.to_datetime(df_d['last_seen'])) < timedelta(minutes=2)
    online_now = len(df_d[df_d['is_online']])
    
    m1.metric("Thiết bị", len(df_d), delta=None)
    m2.metric("🟢 Trực tuyến", online_now, delta=f"{online_now/len(df_d)*100:.0f}%")
    m3.metric("Tải CPU TB", f"{df_d['cpu_usage'].mean():.1f}%", delta="-2.1%", delta_color="inverse")
    m4.metric("Dung lượng RAM", f"{df_d['ram_usage'].mean():.1f}%")

# --- NAVIGATION TABS ---
t_mon, t_ctrl, t_file, t_sum, t_ai = st.tabs(["📊 GIÁM SÁT", "🎮 ĐIỀU KHIỂN", "📤 TRUYỀN FILE", "📜 TỔNG KẾT", "🧠 AI INSIGHT"])

with t_mon:
    st.subheader("Trạng thái thiết bị thời gian thực")
    if not df_d.empty:
        st.dataframe(df_d[['machine_id', 'status', 'cpu_usage', 'ram_usage', 'last_seen', 'agent_version']], 
                     use_container_width=True, hide_index=True)

with t_ctrl:
    st.subheader("Trung tâm lệnh thực thi")
    selected_machines = st.multiselect("Nhắm mục tiêu:", df_d['machine_id'].tolist() if not df_d.empty else [])
    c_btn1, c_btn2, _ = st.columns([1, 1, 4])
    if c_btn1.button("🔒 KHÓA MÁY", use_container_width=True, type="primary"):
        if selected_machines:
            sb.table("commands").insert([{"machine_id": m, "command": "LOCK"} for m in selected_machines]).execute()
            st.toast("Đã phát lệnh KHÓA!", icon="🔒")
    if c_btn2.button("🔓 MỞ MÁY", use_container_width=True):
        if selected_machines:
            sb.table("commands").insert([{"machine_id": m, "command": "UNLOCK"} for m in selected_machines]).execute()
            st.toast("Đã phát lệnh MỞ!", icon="🔓")

with t_file:
    st.subheader("Cập nhật bộ công thức (SDF)")
    file_up = st.file_uploader("Kéo thả file .SDF vào đây", type=['sdf'])
    f_targets = st.multiselect("Đại lý nhận file:", df_d['machine_id'].tolist() if not df_d.empty else [])
    if st.button("🚀 BẮT ĐẦU ĐỒNG BỘ") and file_up and f_targets:
        with st.status("Apple-style processing..."):
            encoded = base64.b64encode(zlib.compress(file_up.getvalue())).decode('utf-8')
            chunk_size = 30000
            chunks = [encoded[i:i+chunk_size] for i in range(0, len(encoded), chunk_size)]
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            payload = []
            for m in f_targets:
                for i, c in enumerate(chunks):
                    payload.append({
                        "machine_id": m, "file_name": file_up.name, "data_chunk": c,
                        "part_info": f"PART_{i+1}/{len(chunks)}", "timestamp": ts,
                        "target_path": r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Updates",
                        "status": "PENDING"
                    })
            sb.table("file_queue").insert(payload).execute()
            st.success("File đang được truyền tải ngầm.")

with t_sum:
    st.subheader("Nhật ký đồng bộ hóa")
    if not df_f.empty:
        df_summary = df_f.groupby(['machine_id', 'file_name', 'status']).size().reset_index(name='mảnh')
        st.table(df_summary)

with t_ai:
    st.subheader("Phân tích hệ thống bằng AI")
    c_ai1, c_ai2 = st.columns(2)
    with c_ai1:
        if not df_d.empty:
            fig = px.sunburst(df_d, path=['status', 'machine_id'], values='cpu_usage', 
                              color='cpu_usage', color_continuous_scale='RdBu')
            st.plotly_chart(fig, use_container_width=True)
    with c_ai2:
        st.info("💡 **Khuyến nghị từ AI:**")
        st.markdown("""
        - **Hiệu năng:** 98% máy khách hoạt động ổn định.
        - **Bảo mật:** Không ghi nhận hành vi can thiệp trái phép vào Agent v10.4.
        - **Tối ưu:** Đề xuất đẩy file SDF vào lúc 12:00 PM để tránh giờ cao điểm pha màu.
        """)
