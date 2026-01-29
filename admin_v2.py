import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import base64, zlib, time

# --- CORE CONFIG & SECURITY ---
SUPABASE_URL = "https://glzdktdphoydqhofszvh.supabase.co"
SUPABASE_KEY = "sb_publishable_MCfri2GPc3dn-bIcx_XJ_A_RxgsF1YU"
ADMIN_PASSWORD = "Qb1100589373@" # Mật khẩu của sếp

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="4Oranges SDM Lux Secure Pro", layout="wide", initial_sidebar_state="collapsed")

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
    .login-box { max-width: 400px; margin: auto; padding: 50px; background: white; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); }
    </style>
""", unsafe_allow_html=True)

# --- LOGIN LOGIC ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.write(""); st.write("") 
        st.markdown("<div style='text-align: center;'><h1 style='color: #1d1d1f;'>🍎 SDM Secure Pro</h1><p style='color: #86868b;'>Vui lòng nhập mật khẩu quản trị</p></div>", unsafe_allow_html=True)
        pwd = st.text_input("", type="password", placeholder="Password", label_visibility="collapsed")
        if st.button("Đăng nhập", use_container_width=True, type="primary"):
            if pwd == ADMIN_PASSWORD:
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("Mật khẩu không chính xác.")
    st.stop()

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
    st.title("🍎 4Oranges Lux Management Pro")
    st.caption(f"Hệ thống vận hành thông minh v4.3 | {datetime.now().strftime('%d/%m/%Y')}")
with c_head2:
    if st.button("Đăng xuất", use_container_width=True):
        st.session_state['authenticated'] = False
        st.rerun()

# --- TOP METRICS & TIMING ---
if not df_d.empty:
    df_d['last_seen_dt'] = pd.to_datetime(df_d['last_seen'])
    # Lấy thời gian hiện tại chuẩn múi giờ của dữ liệu
    now_dt = datetime.now(df_d['last_seen_dt'].dt.tz)
    
    df_d['is_online'] = (now_dt - df_d['last_seen_dt']) < timedelta(minutes=2)
    online_now = len(df_d[df_d['is_online']])
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng thiết bị", len(df_d))
    m2.metric("🟢 Trực tuyến", online_now, delta=f"{online_now/len(df_d)*100:.1f}%")
    m3.metric("Tải CPU TB", f"{df_d['cpu_usage'].mean():.1f}%")
    m4.metric("Dung lượng RAM", f"{df_d['ram_usage'].mean():.1f}%")

# --- NAVIGATION TABS (Đã sửa lỗi khớp biến) ---
t_mon, t_ctrl, t_file, t_sum, t_offline, t_ai = st.tabs([
    "📊 GIÁM SÁT", 
    "🎮 ĐIỀU KHIỂN", 
    "📤 TRUYỀN FILE", 
    "📜 TỔNG KẾT", 
    "🕵️ TRUY VẾT OFFLINE", 
    "🧠 AI INSIGHT"
])

with t_mon:
    st.subheader("Trạng thái thiết bị thời gian thực")
    if not df_d.empty:
        st.dataframe(df_d[['machine_id', 'status', 'cpu_usage', 'ram_usage', 'last_seen', 'agent_version']], 
                     use_container_width=True, hide_index=True)

with t_ctrl:
    st.subheader("Trung tâm lệnh chiến lược")
    selected_machines = st.multiselect("Nhắm mục tiêu:", df_d['machine_id'].tolist() if not df_d.empty else [])
    c_btn1, c_btn2, _ = st.columns([1, 1, 4])
    if c_btn1.button("🔒 KHÓA MÁY", use_container_width=True, type="primary"):
        if selected_machines:
            sb.table("commands").insert([{"machine_id": m, "command": "LOCK"} for m in selected_machines]).execute()
            st.toast("Lệnh LOCK đã được phát tán!", icon="🔒")
    if c_btn2.button("🔓 MỞ MÁY", use_container_width=True):
        if selected_machines:
            sb.table("commands").insert([{"machine_id": m, "command": "UNLOCK"} for m in selected_machines]).execute()
            st.toast("Lệnh UNLOCK đã được phát tán!", icon="🔓")

with t_file:
    st.subheader("Phát hành bộ dữ liệu SDF")
    file_up = st.file_uploader("Kéo thả file .SDF", type=['sdf'])
    f_targets = st.multiselect("Đại lý nhận mục tiêu:", df_d['machine_id'].tolist() if not df_d.empty else [])
    if st.button("🚀 KÍCH HOẠT ĐỒNG BỘ") and file_up and f_targets:
        with st.status("Mã hóa & Truyền tải dữ liệu..."):
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
            st.success("Tác vụ truyền tải đã được kích hoạt.")

with t_sum:
    st.subheader("Nhật ký đồng bộ hóa chi tiết")
    if not df_f.empty:
        df_summary = df_f.groupby(['machine_id', 'file_name', 'status']).size().reset_index(name='mảnh')
        st.table(df_summary)

with t_offline:
    st.subheader("🕵️ Kiểm soát thiết bị vắng mặt dài hạn")
    col_filter1, col_filter2 = st.columns([2, 5])
    with col_filter1:
        threshold = st.selectbox("Ngưỡng vắng mặt:", [15, 30, 60, 90], format_func=lambda x: f"Trên {x} ngày", index=0)
    
    if not df_d.empty:
        df_d['offline_duration'] = now_dt - df_d['last_seen_dt']
        long_offline = df_d[df_d['offline_duration'] > timedelta(days=threshold)].copy()
        
        if not long_offline.empty:
            st.warning(f"Phát hiện {len(long_offline)} máy đã Offline trên {threshold} ngày.")
            long_offline['Thời gian Offline'] = long_offline['offline_duration'].apply(lambda x: f"{x.days} ngày")
            long_offline = long_offline.sort_values(by='offline_duration', ascending=False)
            
            st.dataframe(long_offline[['machine_id', 'last_seen', 'Thời gian Offline', 'status', 'agent_version']], 
                         use_container_width=True, hide_index=True)
            
            csv = long_offline.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Xuất danh sách xử lý (.csv)", data=csv, file_name=f'offline_{threshold}_days.csv', mime='text/csv')
        else:
            st.success(f"Không có máy nào vắng mặt trên {threshold} ngày.")

with t_ai:
    st.subheader("Trí tuệ nhân tạo SDM AI Analyst")
    c_ai1, c_ai2 = st.columns(2)
    with c_ai1:
        if not df_d.empty:
            fig = px.pie(df_d, names='status', title="Tỷ lệ Trạng thái Thiết bị", hole=0.4, 
                         color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig, use_container_width=True)
    with c_ai2:
        st.markdown("### 💡 AI Insights & Security Report")
        st.info("Trạng thái bảo mật: **LEVEL 1 (Tối đa)**")
        st.markdown(f"""
        - **Cập nhật:** Có {len(df_f[df_f['status']=='DONE'])} mảnh dữ liệu đã được nạp thành công.
        - **Cảnh báo:** {len(df_d[df_d['is_online']==False])} máy hiện đang Offline.
        - **Khuyến nghị:** Kiểm tra các máy vắng mặt trên 30 ngày để tối ưu băng thông.
        """)
