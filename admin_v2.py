import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import base64
import zlib
import json

# --- CONFIG ---
SUPABASE_URL = "https://glzdktdphoydqhofszvh.supabase.co"
SUPABASE_KEY = "sb_publishable_MCfri2GPc3dn-bIcx_XJ_A_RxgsF1YU"
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="4Oranges SDM Pro AI", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #1E88E5; }
    .stButton>button { border-radius: 8px; height: 3em; width: 100%; }
    .status-online { color: #2ecc71; font-weight: bold; }
    .status-offline { color: #e74c3c; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA ENGINE ---
@st.cache_data(ttl=5) # Cache 5 giây để đảm bảo tính real-time
def load_all_data():
    try:
        dev_res = sb.table("devices").select("*").execute()
        cmd_res = sb.table("commands").select("*").order("created_at", desc=True).limit(50).execute()
        df_d = pd.DataFrame(dev_res.data) if dev_res.data else pd.DataFrame()
        df_c = pd.DataFrame(cmd_res.data) if cmd_res.data else pd.DataFrame()
        return df_d, df_c
    except Exception as e:
        st.error(f"Lỗi kết nối Database: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_devices, df_commands = load_all_data()

# --- SIDEBAR QUẢN TRỊ ---
with st.sidebar:
    st.image("https://4oranges.com/wp-content/uploads/2021/08/logo-4oranges.png", width=180)
    st.title("SDM COMMAND CENTER")
    st.write(f"🕒 Cập nhật: {datetime.now().strftime('%H:%M:%S')}")
    
    if st.button("🔄 REFRESH SYSTEM"):
        st.rerun()
    
    st.divider()
    st.markdown("### 🛠️ THIẾT LẬP NHANH")
    auto_refresh = st.toggle("Tự động làm mới (30s)", value=True)
    if auto_refresh:
        time_to_wait = 30
        # Streamlit không có auto-refresh native, ta dùng trick empty
        # st.empty() ... (giản lược để tập trung tính năng)

# --- MAIN DASHBOARD ---
st.title("🛡️ 4Oranges Intelligence System v3.0")

# 1. METRICS TỔNG QUAN
if not df_devices.empty:
    # Tính toán trạng thái thực tế
    df_devices['last_seen_dt'] = pd.to_datetime(df_devices['last_seen'])
    now = datetime.now(df_devices['last_seen_dt'].dt.tz)
    df_devices['is_online'] = (now - df_devices['last_seen_dt']) < timedelta(minutes=2)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng thiết bị", len(df_devices))
    m2.metric("🟢 Đang Online", len(df_devices[df_devices['is_online'] == True]))
    m3.metric("🔴 Mất kết nối", len(df_devices[df_devices['is_online'] == False]))
    m4.metric("🔒 Đang Khóa", len(df_devices[df_devices['status'].str.contains("LOCKED", na=False)]))

st.divider()

# 2. HỆ THỐNG TABS CHỨC NĂNG
t_monitor, t_control, t_file, t_ai = st.tabs([
    "📊 GIÁM SÁT CHI TIẾT", "🎮 ĐIỀU KHIỂN CHIẾN LƯỢC", "📤 TRUYỀN TẢI SDF", "🧠 AI INSIGHT CENTER"
])

# --- TAB: GIÁM SÁT ---
with t_monitor:
    st.subheader("📡 Danh sách máy khách 5.000+")
    search_q = st.text_input("🔍 Tìm máy (ID hoặc Version):", placeholder="Gõ ID máy cần tìm...")
    
    if not df_devices.empty:
        filtered = df_devices[df_devices['machine_id'].str.contains(search_q, case=False)]
        st.dataframe(
            filtered[['machine_id', 'status', 'cpu_usage', 'ram_usage', 'last_seen', 'agent_version']],
            column_config={
                "cpu_usage": st.column_config.ProgressColumn("CPU (%)", format="%f", min_value=0, max_value=100),
                "ram_usage": st.column_config.ProgressColumn("RAM (%)", format="%f", min_value=0, max_value=100),
            },
            use_container_width=True, hide_index=True
        )

# --- TAB: ĐIỀU KHIỂN ---
with t_control:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("🚀 Gửi lệnh tức thì")
        targets = st.multiselect("Chọn danh sách máy mục tiêu:", df_devices['machine_id'].tolist())
        cmd_action = st.radio("Chọn hành động:", ["LOCK", "UNLOCK", "RESTART AGENT"], horizontal=True)
        
        if st.button("🔥 XÁC NHẬN THỰC THI", type="primary"):
            if targets:
                new_cmds = [{"machine_id": t, "command": cmd_action, "is_executed": False} for t in targets]
                sb.table("commands").insert(new_cmds).execute()
                st.success(f"Đã gửi lệnh {cmd_action} tới {len(targets)} thiết bị qua luồng Supabase Real-time!")
            else:
                st.warning("Vui lòng chọn ít nhất một thiết bị.")

    with c2:
        st.subheader("📜 Nhật ký lệnh")
        if not df_commands.empty:
            st.dataframe(df_commands[['machine_id', 'command', 'is_executed']], use_container_width=True)

# --- TAB: TRUYỀN FILE ---
with t_file:
    st.subheader("📦 Đẩy dữ liệu SDF hàng loạt")
    up_file = st.file_uploader("Chọn file .SDF:", type=['sdf'])
    f_targets = st.multiselect("Chọn máy nhận:", df_devices['machine_id'].tolist() if not df_devices.empty else [])
    
    if st.button("📤 BẮT ĐẦU ĐẨY FILE"):
        if up_file and f_targets:
            with st.status("AI đang xử lý file..."):
                # 1. Nén và mã hóa file
                raw_data = up_file.getvalue()
                encoded = base64.b64encode(zlib.compress(raw_data)).decode('utf-8')
                
                # 2. Chia nhỏ (Chunking) để vượt rào cản băng thông
                chunk_size = 30000
                chunks = [encoded[i:i+chunk_size] for i in range(0, len(encoded), chunk_size)]
                ts = datetime.now().strftime("%Y%m%d%H%M%S") # Tạo timestamp định danh duy nhất
                
                payload = []
                for m in f_targets:
                    for i, c in enumerate(chunks):
                        payload.append({
                            "machine_id": m,
                            "file_name": up_file.name,
                            "data_chunk": c,
                            "part_info": f"PART_{i+1}/{len(chunks)}",
                            "timestamp": ts, # Timestamp này giúp Agent nhận biết bộ file
                            "target_path": r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Updates",
                            "status": "PENDING"
                        })
                
                # 3. Đẩy lên Supabase
                sb.table("file_queue").insert(payload).execute()
                st.success(f"🚀 Đã phát lệnh truyền file {up_file.name} tới {len(f_targets)} máy!")
