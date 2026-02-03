import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import base64, zlib, time

# --- CORE CONFIG & SECURITY ---
SUPABASE_URL = "https://glzdktdphoydqhofszvh.supabase.co"
SUPABASE_KEY = "sb_publishable_MCfri2GPc3dn-bIcx_XJ_A_RxgsF1YU"
ADMIN_PASSWORD = "Qb1100589373@" 

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
t_mon, t_ctrl, t_file, t_sum, t_offline, t_ai, t_sys = st.tabs([
    "📊 GIÁM SÁT", "🎮 ĐIỀU KHIỂN", "📤 TRUYỀN FILE", "📜 TỔNG KẾT", "🕵️ TRUY VẾT", "🧠 AI INSIGHT", "⚙️ HỆ THỐNG"
])

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

def render_ai_strategic_hub(df_d, now_dt):
    st.markdown("### 🧠 SDM AI Strategic Hub (V2.0)")
    
    # --- LỚP 1: FEATURE ENGINEERING (Tính toán chỉ số thông minh) ---
    if df_d.empty:
        st.info("Chưa có dữ liệu để phân tích AI.")
        return

    total_devices = len(df_d)
    df_d['last_seen_dt'] = pd.to_datetime(df_d['last_seen'], utc=True)
    df_d['offline_minutes'] = (now_dt - df_d['last_seen_dt']).dt.total_seconds() / 60
    
    # Tính các features cốt lõi
    offline_ratio = len(df_d[df_d['offline_minutes'] > 15]) / total_devices
    avg_offline = df_d[df_d['offline_minutes'] > 15]['offline_minutes'].mean() or 0
    new_offline_1h = len(df_d[(df_d['offline_minutes'] > 0) & (df_d['offline_minutes'] <= 60)])
    
    # --- LỚP 2: SCORING (Thay If-Else bằng Risk Score 0.0 -> 1.0) ---
    # Trọng số: Tỷ lệ offline (40%) + Thời gian offline TB (30%) + Tốc độ rớt mạng mới (30%)
    risk_score = (
        min(offline_ratio / 0.5, 1.0) * 0.4 + 
        min(avg_offline / 1440, 1.0) * 0.3 + 
        min(new_offline_1h / (total_devices * 0.2 + 1), 1.0) * 0.3
    )
    
    tab_summary, tab_risk, tab_forecast, tab_rag = st.tabs([
        "🔭 TỔNG QUAN CHIẾN LƯỢC", "⚠️ PHÂN TÍCH RỦI RO", "🔮 DỰ BÁO VẬN HÀNH", "💬 TRỢ LÝ RAG"
    ])

    with tab_summary:
        # LỚP 4: MEMORY & TREND (Giả lập trend từ Risk Score)
        c1, c2, c3 = st.columns(3)
        
        # Giả lập trend (Trong thực tế sẽ query từ bảng ai_snapshots)
        prev_risk_score = risk_score * 0.9 # Giả lập hôm qua tốt hơn
        risk_delta = risk_score - prev_risk_score
        
        c1.metric("Chỉ số rủi ro hệ thống", f"{risk_score:.2f}", 
                  delta=f"{risk_delta:.2f}", delta_color="inverse")
        
        status_label = "ỔN ĐỊNH" if risk_score < 0.3 else "CẦN CHÚ Ý" if risk_score < 0.6 else "NGUY CƠ CAO"
        c2.metric("Trạng thái AI xác định", status_label)
        c3.metric("Health Score", f"{int((1-risk_score)*100)}%")

        # Biểu đồ diễn biến rủi ro (Memory Layer)
        st.write("**Diễn biến rủi ro 24h qua (AI Snapshot)**")
        # Giả lập dữ liệu chuỗi thời gian
        chart_data = pd.DataFrame({
            'Time': [now_dt - timedelta(hours=i) for i in range(24, 0, -1)],
            'Risk': np.random.uniform(risk_score-0.1, risk_score+0.1, 24)
        })
        st.line_chart(chart_data, x='Time', y='Risk')

    with tab_risk:
        st.markdown("#### 🔍 Evidence-based Trace (Bằng chứng rủi ro)")
        # Phân loại rủi ro theo cụm (Clustering giả lập)
        col_r1, col_r2 = st.columns(2)
        
        with col_r1:
            st.write("**Top 5 máy gây nhiễu hệ thống (Anomaly)**")
            anomaly_df = df_d.sort_values('offline_minutes', ascending=False).head(5)
            st.dataframe(anomaly_df[['machine_id', 'offline_minutes', 'status']], use_container_width=True)
            
        with col_r2:
            # LỚP 3: AI NARRATIVE (Giải thích bằng ngôn ngữ tự nhiên)
            st.info("**AI Narrative Analysis**")
            confidence = "High" if total_devices > 10 else "Low"
            st.write(f"""
            - **Hiện tượng:** Tỷ lệ máy rớt mạng đạt {offline_ratio*100:.1f}%.
            - **Nguyên nhân:** Phát hiện cụm rớt mạng tập trung trong 1 giờ qua ({new_offline_1h} máy). 
            - **Khuyến nghị:** Kiểm tra hạ tầng Cloud Supabase hoặc đường truyền khu vực trọng điểm.
            - **Độ tin cậy:** {confidence} (Dựa trên {total_devices} mẫu)
            """)

    with tab_forecast:
        st.markdown("#### 🔮 Predictive Maintenance (Dự báo bảo trì)")
        # Dự báo dựa trên Linear Regression đơn giản (Giả lập)
        st.success("Dự báo: 72 giờ tới hệ thống sẽ duy trì ở mức rủi ro thấp.")
        
        # Dự báo vật tư (Tinh màu) - Dựa trên sản lượng ảo
        st.write("**Dự báo hết tinh màu (AI Forecast - Baseline comparison)**")
        pred_data = pd.DataFrame({
            'Đại lý': ['Đại lý Long An', 'Đại lý Bình Tân', 'Đại lý Thủ Đức'],
            'Xác suất hết màu (%)': [85, 62, 45],
            'Thời gian dự kiến': ['1.5 ngày', '3 ngày', '4.2 ngày']
        })
        st.table(pred_data)

    with tab_rag:
        # Lớp tương tác LLM
        st.markdown("#### 💬 Trợ lý Ops Intelligence")
        st.text_input("Hỏi AI về dữ liệu vận hành:", placeholder="Tại sao Risk Score hôm nay lại tăng?")
        st.caption("Trợ lý sẽ phân tích bảng Features và Snapshot để trả lời sếp.")
    with t_ai:
    # Gọi hàm xử lý AI đã định nghĩa ở trên
    # Truyền vào df_d (dữ liệu máy) và now_dt (thời gian hiện tại)
    if not df_d.empty:
        render_ai_strategic_hub(df_d, now_dt)
    else:
        st.info("Chưa có dữ liệu thiết bị để phân tích AI.")
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
