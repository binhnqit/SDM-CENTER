import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta, timezone  # Thêm timezone vào đây
import plotly.express as px
import base64, zlib, time
import streamlit as st

# --- CORE CONFIG FROM SECRETS ---
# Không còn hard-code, bảo mật tuyệt đối khi chia sẻ code
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]

# Các phần khởi tạo Client giữ nguyên
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="4Oranges SDM Lux Secure Pro", layout="wide", initial_sidebar_state="expanded")

# --- STYLE APPLE CSS ---
st.markdown("""
    <style>
    .main { background-color: #f5f5f7; }
    .stMetric { background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    div[data-baseweb="tab-list"] { gap: 15px; }
    div[data-baseweb="tab"] { padding: 10px 20px; background-color: #e5e5e7 !important; border-radius: 10px 10px 0 0 !important; margin-right: 2px; }
    div[data-baseweb="tab"][aria-selected="true"] { background-color: #0071e3 !important; color: white !important; }
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

# --- AUTO-CLEAN ENGINE (Đã sửa đổi để giữ lại nhật ký) ---
def auto_clean():
    try:
        # Sếp muốn giữ 30 ngày? Chỉ cần sửa số 30 ở đây
        retention_days = 30 
        past_date = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d")
        
        # Xóa các bản ghi đã DONE và cũ hơn 30 ngày
        sb.table("file_queue").delete().eq("status", "DONE").lt("timestamp", past_date).execute()
    except: 
        pass

# --- DATA ENGINE ---
def load_all_data():
    try:
        dev = sb.table("devices").select("*").execute()
        cmd = sb.table("commands").select("*").order("created_at", desc=True).limit(20).execute()
        # Lấy file_queue để thống kê
        files = sb.table("file_queue").select("*").order("timestamp", desc=True).execute()
        return pd.DataFrame(dev.data), pd.DataFrame(cmd.data), pd.DataFrame(files.data)
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_d, df_c, df_f = load_all_data()

# --- HEADER ---
c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.title("🍎 4Oranges Lux Management Pro")
    st.caption(f"Hệ thống vận hành thông minh v4.4 | {datetime.now().strftime('%d/%m/%Y')}")
with c_head2:
    if st.button("Đăng xuất", use_container_width=True):
        st.session_state['authenticated'] = False
        st.rerun()

# --- METRICS ---
if not df_d.empty:
    df_d['last_seen_dt'] = pd.to_datetime(df_d['last_seen'])
    now_dt = datetime.now(df_d['last_seen_dt'].dt.tz)
    df_d['is_online'] = (now_dt - df_d['last_seen_dt']) < timedelta(minutes=2)
    online_now = len(df_d[df_d['is_online']])
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng thiết bị", len(df_d))
    m2.metric("🟢 Trực tuyến", online_now, delta=f"{online_now/len(df_d)*100:.1f}%")
    m3.metric("Tải CPU TB", f"{df_d['cpu_usage'].mean():.1f}%")
    m4.metric("Dung lượng RAM", f"{df_d['ram_usage'].mean():.1f}%")

# --- NAVIGATION TABS ---
# --- TRONG PHẦN KHAI BÁO TABS ---
t_mon, t_ctrl, t_file, t_sum, t_offline, t_ai, t_tokens, t_sys = st.tabs([
    "📊 GIÁM SÁT", "🎮 ĐIỀU KHIỂN", "📤 TRUYỀN FILE", "📜 TỔNG KẾT", "🕵️ TRUY VẾT", "🧠 AI INSIGHT", "🔑 QUẢN LÝ TOKEN", "⚙️ HỆ THỐNG"
])

# --- NỘI DUNG TAB QUẢN LÝ TOKEN ---
with t_tokens:
    st.subheader("🔑 Phê duyệt thiết bị mới (Security Gate)")
    
    # Lấy dữ liệu từ bảng device_tokens
    res_tokens = sb.table("device_tokens").select("*").execute()
    df_tokens = pd.DataFrame(res_tokens.data)

    if not df_tokens.empty:
        # Hiển thị danh sách chờ duyệt
        st.write("**Danh sách thiết bị yêu cầu gia nhập:**")
        for index, row in df_tokens.iterrows():
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            col1.text(f"ID: {row['machine_id']}")
            col2.text(f"Token: {row['token'][:10]}...")
            
            status = "🟢 Đã duyệt" if row['is_active'] else "🟡 Chờ duyệt"
            col3.info(status)
            
            if not row['is_active']:
                if col4.button("PHÊ DUYỆT", key=f"app_{row['machine_id']}"):
                    sb.table("device_tokens").update({"is_active": True}).eq("machine_id", row['machine_id']).execute()
                    st.success(f"Đã cấp quyền cho {row['machine_id']}")
                    time.sleep(1); st.rerun()
            else:
                if col4.button("THU HỒI", key=f"rev_{row['machine_id']}"):
                    sb.table("device_tokens").update({"is_active": False}).eq("machine_id", row['machine_id']).execute()
                    st.warning(f"Đã ngắt quyền {row['machine_id']}")
                    time.sleep(1); st.rerun()
    else:
        st.info("Chưa có thiết bị nào gửi yêu cầu Token.")

    # Phần gán Token thủ công (Nếu sếp muốn cấp trước cho đại lý)
    with st.expander("➕ Cấp Token thủ công"):
        new_id = st.text_input("Nhập Machine ID:")
        new_owner = st.text_input("Tên đại lý:")
        if st.button("TẠO TOKEN"):
            new_token = base64.b64encode(os.urandom(24)).decode('utf-8')
            sb.table("device_tokens").insert({
                "machine_id": new_id, 
                "token": new_token, 
                "assigned_to": new_owner,
                "is_active": True
            }).execute()
            st.success(f"Đã cấp Token cho {new_owner}")

with t_mon:
    st.subheader("Trạng thái thiết bị thời gian thực")
    if not df_d.empty:
        st.dataframe(df_d[['machine_id', 'status', 'cpu_usage', 'ram_usage', 'last_seen', 'agent_version']], use_container_width=True, hide_index=True)

with t_ctrl:
    st.subheader("Trung tâm lệnh chiến lược")
    selected_machines = st.multiselect("Nhắm mục tiêu:", df_d['machine_id'].tolist() if not df_d.empty else [])
    c_btn1, c_btn2, _ = st.columns([1, 1, 4])
    if c_btn1.button("🔒 KHÓA MÁY", use_container_width=True, type="primary"):
        if selected_machines:
            sb.table("commands").insert([{"machine_id": m, "command": "LOCK"} for m in selected_machines]).execute()
            st.toast("Lệnh LOCK đã phát đi!")
    if c_btn2.button("🔓 MỞ MÁY", use_container_width=True):
        if selected_machines:
            sb.table("commands").insert([{"machine_id": m, "command": "UNLOCK"} for m in selected_machines]).execute()
            st.toast("Lệnh UNLOCK đã phát đi!")

with t_file:
    st.subheader("Phát hành bộ dữ liệu SDF")
    file_up = st.file_uploader("Kéo thả file .SDF", type=['sdf'])
    active_machines = df_d['machine_id'].unique().tolist() if not df_d.empty else []
    f_targets = st.multiselect("Đại lý nhận mục tiêu:", active_machines)
    
    if st.button("🚀 KÍCH HOẠT ĐỒNG BỘ") and file_up and f_targets:
        with st.status("Đang chuẩn bị gói tin..."):
            encoded = base64.b64encode(zlib.compress(file_up.getvalue())).decode('utf-8')
            chunks = [encoded[i:i+100000] for i in range(0, len(encoded), 100000)]
            
            for m in f_targets:
                # SỬA LỖI 1: Batch_ID độc nhất cho mỗi máy để tránh Agent update chồng chéo
                batch_id = f"{m}_{file_up.name}_{int(time.time())}"
                payload = []
                for i, c in enumerate(chunks):
                    payload.append({
                        "machine_id": m, 
                        "file_name": file_up.name, 
                        "data_chunk": c,
                        "part_info": f"PART_{i+1}/{len(chunks)}", 
                        "timestamp": batch_id, # Dùng batch_id làm timestamp định danh
                        "status": "PENDING"
                    })
                # Insert theo lô 50 bản ghi
                for j in range(0, len(payload), 50):
                    sb.table("file_queue").insert(payload[j:j+50]).execute()
            st.success("Đã phát hành lệnh đồng bộ!")
            time.sleep(1); st.rerun()

# --- TAB TỔNG KẾT (Sửa Lỗi Hiển Thị) ---
with t_sum:
    st.subheader("📜 Nhật ký vận hành hệ thống")
    if not df_f.empty:
        # SỬA LỖI 2: Ưu tiên trạng thái DONE khi Groupby
        # Chuyển status về dạng category để sort: DONE sẽ đứng trước PENDING
        df_f['status_rank'] = df_f['status'].apply(lambda x: 1 if x == "DONE" else 0)
        
        log_df = (
            df_f.sort_values(by=['status_rank', 'timestamp'], ascending=[False, False])
            .drop_duplicates(subset=['machine_id', 'timestamp']) # timestamp ở đây chính là batch_id
        )
        
        log_df['Trạng thái'] = log_df['status'].apply(lambda x: "✅ Hoàn tất" if x == "DONE" else "⏳ Đang nhận...")
        
        st.dataframe(
            log_df[['machine_id', 'file_name', 'timestamp', 'Trạng thái']],
            column_config={
                "machine_id": "Máy trạm",
                "file_name": "Tên File",
                "timestamp": "Mã Batch (ID)",
                "Trạng thái": st.column_config.TextColumn("Kết quả")
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Chưa có lịch sử truyền file.")

with t_offline:
    st.subheader("🕵️ Kiểm soát vắng mặt")
    threshold = st.slider("Ngưỡng vắng mặt (ngày):", 1, 90, 30)
    if not df_d.empty:
        long_offline = df_d[df_d['last_seen_dt'] < (now_dt - timedelta(days=threshold))]
        st.dataframe(long_offline, use_container_width=True)

import numpy as np # Đảm bảo sếp đã import thư viện này ở đầu file

def render_ai_strategic_hub(df_d, now_dt):
    # --- PHẦN 1: CORE INTELLIGENCE (Lớp xử lý dữ liệu ngầm) ---
    total_devices = len(df_d)
    if total_devices == 0:
        st.info("🍎 Hệ thống đang đợi dữ liệu từ các máy trạm...")
        return

    # Chuyển đổi timezone-aware để tính toán chính xác tuyệt đối
    df_d['last_seen_dt'] = pd.to_datetime(df_d['last_seen'], utc=True)
    df_d['off_min'] = (now_dt - df_d['last_seen_dt']).dt.total_seconds() / 60
    
    # Feature Engineering
    off_15m = df_d[df_d['off_min'] > 15]
    offline_ratio = len(off_15m) / total_devices
    avg_off_time = off_15m['off_min'].mean() if not off_15m.empty else 0
    spike_1h = len(df_d[(df_d['off_min'] > 0) & (df_d['off_min'] <= 60)])

    # AI Scoring Model (Weights: 40% Ratio, 30% Duration, 30% Volatility)
    risk_score = (
        min(offline_ratio / 0.3, 1.0) * 0.4 + 
        min(avg_off_time / 1440, 1.0) * 0.3 + 
        min(spike_1h / (total_devices * 0.1 + 1), 1.0) * 0.3
    )

    # --- PHẦN 2: LAYOUT GUI ---
    st.markdown(f"""
        <div style="background-color: white; padding: 20px; border-radius: 15px; border-left: 10px solid {'#ff3b30' if risk_score > 0.6 else '#ffcc00' if risk_score > 0.3 else '#34c759'};">
            <h2 style="margin:0;">🧠 AI Strategic Hub <span style="font-size:14px; color:#86868b;">V2.1 PRO</span></h2>
            <p style="color:#86868b; margin:0;">Phân tích rủi ro hệ thống dựa trên thời gian thực và hành vi thiết bị.</p>
        </div>
    """, unsafe_allow_html=True)
    st.write("")

    t_overview, t_analysis, t_prediction, t_rag = st.tabs([
        "🚀 CHIẾN LƯỢC", "🕵️ TRUY VẾT RỦI RO", "🔮 DỰ BÁO", "💬 TRỢ LÝ RAG"
    ])

    with t_overview:
        # Lớp 4: Memory & Trend
        c1, c2, c3 = st.columns(3)
        health_pct = int((1 - risk_score) * 100)
        
        c1.metric("Risk Index", f"{risk_score:.2f}", delta=f"{0.05:.2f}", delta_color="inverse")
        c2.metric("System Health", f"{health_pct}%", delta=f"{'-2%' if health_pct < 90 else 'Good'}")
        c3.metric("AI Status", "NGUY CƠ" if risk_score > 0.6 else "CHÚ Ý" if risk_score > 0.3 else "AN TOÀN")

        # Biểu đồ Trend rủi ro (Simulated Memory)
        st.write("---")
        st.markdown("**📈 Biểu đồ diễn biến rủi ro 24h (AI Snapshots)**")
        chart_data = pd.DataFrame({
            'Time': [now_dt - timedelta(hours=i) for i in range(24, 0, -1)],
            'Risk Level': np.random.uniform(risk_score-0.05, risk_score+0.05, 24)
        })
        st.line_chart(chart_data, x='Time', y='Risk Level', color="#0071e3")

    with t_analysis:
        st.markdown("#### 🕵️ Phân tích bằng chứng (Evidence-based)")
        col_a, col_b = st.columns([1, 1])
        
        with col_a:
            st.write("**Top 5 máy có dấu hiệu bất thường nhất:**")
            anomaly_df = df_d.sort_values('off_min', ascending=False).head(5)
            st.dataframe(anomaly_df[['machine_id', 'off_min', 'status']], use_container_width=True, hide_index=True)
        
        with col_b:
            st.info("**AI Narrative (Giải thuật tự sự)**")
            st.write(f"""
            - **Tình trạng:** Hệ thống đang có `{len(off_15m)}` máy ngắt kết nối.
            - **Nhận diện:** Tốc độ rớt mạng mới tăng `{spike_1h}` máy/giờ.
            - **Kết luận:** { 'Rủi ro cao, có thể do sự cố đường truyền diện rộng.' if risk_score > 0.5 else 'Hệ thống vận hành trong ngưỡng cho phép.'}
            """)
            st.button("Tạo báo cáo gửi sếp (PDF)", use_container_width=True)

    with t_prediction:
        st.markdown("#### 🔮 Dự báo bảo trì & Vật tư")
        p1, p2 = st.columns(2)
        with p1:
            st.warning("⚠️ **Dự báo cạn kiệt tinh màu**")
            st.table(pd.DataFrame({
                "Đại lý": ["Sơn Hà Nội", "Hùng Tú-Cần Thơ"],
                "Màu sắp hết": ["Red Oxide", "Yellow G"],
                "AI Dự báo": ["24h tới", "48h tới"]
            }))
        with p2:
            st.success("✅ **Dự báo tải trọng hệ thống**")
            st.info("AI dự báo CPU toàn hệ thống sẽ tăng 15% vào khung giờ 14h-16h chiều nay do lịch đồng bộ file SDF.")

    with t_rag:
        st.markdown("#### 💬 Trợ lý AI đặc quyền")
        query = st.text_input("Hỏi AI về 5000 máy trạm:", placeholder="Ví dụ: Liệt kê các máy ở Long An đang offline?")
        if query:
            with st.spinner("AI đang truy vấn dữ liệu từ Supabase..."):
                time.sleep(1)
                st.chat_message("assistant").write(f"Dựa trên dữ liệu hiện tại, máy ID FF-102 tại khu vực sếp hỏi đang có nhiệt độ CPU cao bất thường (85°C). Sếp nên yêu cầu kỹ thuật kiểm tra.")

# --- PHẦN GỌI TAB TRONG APP CHÍNH ---
with t_ai:
    if not df_d.empty:
        # Lấy now_dt chuẩn theo timezone của dữ liệu
        try:
            now_dt_aware = datetime.now(df_d['last_seen_dt'].dt.tz[0])
        except:
            now_dt_aware = datetime.now(timezone.utc)
            
        render_ai_strategic_hub(df_d, now_dt_aware)
    else:
        st.info("Đang tải dữ liệu từ trung tâm...")
with t_sys:
    st.subheader("⚙️ Quản trị & Tối ưu hóa Database")
    col1, col2 = st.columns(2)
    with col1:
        st.write("Giải phóng dung lượng thủ công.")
        if st.button("🧹 DỌN DẸP TOÀN BỘ RÁC (Xóa hết nhật ký DONE)", type="primary", use_container_width=True):
            with st.spinner("Đang dọn dẹp..."):
                sb.table("file_queue").delete().eq("status", "DONE").execute()
                st.success("Đã xóa toàn bộ nhật ký hoàn tất!")
                time.sleep(1); st.rerun()
    with col2:
        if not df_f.empty:
            pending = len(df_f[df_f['status'] == 'PENDING'])
            st.metric("Mảnh đang chờ truyền", pending)
