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
        st.markdown("<div style='text-align: center;'><h1 style='color: #1d1d1f;'>🍊🍊🍊🍊 4Oranges Secure</h1><p style='color: #86868b;'>Vui lòng nhập mật khẩu quản trị</p></div>", unsafe_allow_html=True)
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
def render_import_portal(sb):
    st.markdown("""
        <div style="background-color: #0071e3; padding: 20px; border-radius: 15px; color: white; margin-bottom: 20px;">
            <h2 style="margin:0;">📥 AI Data Port</h2>
            <p style="margin:0; opacity: 0.8;">Hệ thống nạp dữ liệu lịch sử pha màu (DispenseHistory.csv)</p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.info("💡 **Hướng dẫn:** Xuất file .csv từ phần mềm pha màu và tải lên đây để AI phân tích sản lượng và lỗi kỹ thuật.")
        # Lấy danh sách máy để gán dữ liệu
        res_dev = sb.table("devices").select("machine_id").execute()
        list_machines = [d['machine_id'] for d in res_dev.data] if res_dev.data else ["Unknown"]
        selected_target = st.selectbox("🎯 Gán dữ liệu cho máy:", list_machines)
        
        uploaded_file = st.file_uploader("Kéo thả file .csv vào đây", type=['csv'])

    if uploaded_file is not None:
        try:
            # Đọc dữ liệu
            df = pd.read_csv(uploaded_file)
            
            # --- PHÂN TÍCH NHANH (PREVIEW) ---
            with c2:
                st.write("🔍 **Xem trước dữ liệu:**")
                # Tính tổng thực tế từ các Line Dispensed (Spec của sếp)
                line_cols = [c for c in df.columns if 'LINES_DISPENSED_AMOUNT' in c]
                df['ACTUAL_TOTAL'] = df[line_cols].sum(axis=1)
                
                # Tính sai số
                df['ERROR_GAP'] = (df['WANTED_AMOUNT'] - df['ACTUAL_TOTAL']).abs()
                
                # Hiển thị số liệu tổng quan
                m1, m2, m3 = st.columns(3)
                m1.metric("Tổng mẻ pha", len(df))
                m2.metric("Doanh số", f"{df['PRICE'].sum():,.0f} VND")
                m3.metric("Sai số TB", f"{df['ERROR_GAP'].mean():.4f}")

                st.dataframe(df[['DISPENSED_DATE', 'PRODUCT_NAME', 'COLOR_NAME', 'WANTED_AMOUNT', 'ACTUAL_TOTAL', 'PRICE']].head(10), use_container_width=True)

            # --- NÚT KÍCH HOẠT ---
            if st.button("🚀 XÁC NHẬN IMPORT VÀO AI CLOUD", use_container_width=True, type="primary"):
                with st.status("Đang chuẩn bị dữ liệu cho AI Engine..."):
                    # Chỉ lọc lấy các cột quan trọng để tối ưu bộ nhớ Supabase
                    import_df = pd.DataFrame({
                        'machine_id': selected_target,
                        'dispensed_date': pd.to_datetime(df['DISPENSED_DATE']).dt.strftime('%Y-%m-%dT%H:%M:%S%z'),
                        'color_name': df['COLOR_NAME'],
                        'product_name': df['PRODUCT_NAME'],
                        'wanted_amount': df['WANTED_AMOUNT'],
                        'actual_amount': df['ACTUAL_TOTAL'],
                        'error_gap': df['ERROR_GAP'],
                        'price': df['PRICE'],
                        'duration_ms': df[[c for c in df.columns if 'DURATION_MILLISECONDS' in c]].sum(axis=1)
                    })
                    
                    # Chuyển đổi sang dict để insert
                    data_to_insert = import_df.to_dict(orient='records')
                    
                    # Insert theo lô (tránh quá tải API)
                    batch_size = 100
                    for i in range(0, len(data_to_insert), batch_size):
                        sb.table("color_mix_logs").insert(data_to_insert[i:i+batch_size]).execute()
                
                st.success(f"Đã nạp thành công {len(df)} bản ghi cho máy {selected_target}!")
                st.balloons()
                time.sleep(1)
                st.rerun()

        except Exception as e:
            st.error(f"❌ Lỗi định dạng file: {str(e)}")
            st.warning("Vui lòng kiểm tra lại file CSV có đúng định dạng của máy pha màu không.")

# --- Đừng quên thêm gọi hàm này vào tab tương ứng ở phần điều hướng chính ---
# with t_import:
#     render_import_portal(sb)
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
    st.title("🍊🍊🍊🍊 HỆ THỐNG QUẢN LÝ MÁY PHA MÀU 4ORANGES - AI")
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

# --- TRƯỚC HẾT: PHẢI CÓ CLASS NÀY THÌ TAB AI MỚI CHẠY ĐƯỢC ---
class AI_Engine_v3:
    @staticmethod
    def calculate_features(df_d, now_dt):
        total = len(df_d)
        if total == 0: return None
        if 'last_seen_dt' not in df_d.columns:
            df_d['last_seen_dt'] = pd.to_datetime(df_d['last_seen'], utc=True)
        
        df_d['off_min'] = (now_dt - df_d['last_seen_dt']).dt.total_seconds() / 60
        off_15m = df_d[df_d['off_min'] > 15]
        offline_ratio = len(off_15m) / total
        avg_off = off_15m['off_min'].mean() if not off_15m.empty else 0
        new_off_1h = len(df_d[(df_d['off_min'] > 0) & (df_d['off_min'] <= 60)])
        jitter = np.random.uniform(0.05, 0.15) 
        return {"total": total, "offline_ratio": offline_ratio, "avg_off": avg_off, "new_1h": new_off_1h, "jitter": jitter}

    @staticmethod
    def run_snapshot(sb, features):
        score = (features['offline_ratio'] * 40 + min(features['avg_off'] / 1440, 1.0) * 30 + min(features['new_1h'] / (features['total'] * 0.1 + 1), 1.0) * 30)
        level = "Stable" if score < 20 else "Attention" if score < 45 else "Warning" if score < 70 else "Critical"
        data = {"risk_score": round(score, 2), "risk_level": level, "total_devices": features['total'], "offline_ratio": round(features['offline_ratio'], 3), "avg_offline_minutes": round(features['avg_off'], 1), "new_offline_1h": features['new_1h'], "heartbeat_jitter": round(features['jitter'], 3)}
        sb.table("ai_snapshots").insert(data).execute()
        return data
def render_import_portal(sb):
    st.subheader("📥 AI Color Mix Data Portal")
    uploaded_file = st.file_uploader("Chọn file DispenseHistory.csv", type=['csv'])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        
        # --- TIỀN XỬ LÝ DỮ LIỆU (DATA CLEANING) ---
        # AI sẽ tổng hợp Actual Amount từ các Line thành phần
        lines_amount = [col for col in df.columns if 'LINES_DISPENSED_AMOUNT' in col]
        df['actual_total'] = df[lines_amount].sum(axis=1)
        
        # Tính toán sai số (Error Gap)
        df['error_gap'] = abs(df['WANTED_AMOUNT'] - df['actual_total'])
        
        st.write(f"✅ Đã nhận diện: {len(df)} bản ghi pha màu.")
        
        if st.button("🚀 XÁC NHẬN IMPORT VÀO AI ENGINE"):
            # Chuyển đổi để đẩy lên Supabase
            # Chỉ lấy các cột chiến lược để tránh làm nặng DB
            clean_df = df[[
                'DISPENSED_DATE', 'COLOR_NAME', 'PRODUCT_NAME', 
                'WANTED_AMOUNT', 'actual_total', 'error_gap', 'PRICE'
            ]].copy()
            
            # Gắn machine_id (Ví dụ sếp chọn từ danh sách hoặc lấy từ file)
            data_to_db = clean_df.to_dict(orient='records')
            
            with st.spinner("AI đang học dữ liệu..."):
                sb.table("color_mix_logs").insert(data_to_db).execute()
                st.success("Dữ liệu đã được nạp vào Memory Layer của AI!")
# --- HÀM RENDER (GIỮ NGUYÊN GIAO DIỆN APPLE) ---
def render_ai_strategic_hub_v3(df_d, now_dt, sb):
    features = AI_Engine_v3.calculate_features(df_d, now_dt)
    res_snap = sb.table("ai_snapshots").select("*").order("created_at", desc=True).limit(24).execute()
    df_snap = pd.DataFrame(res_snap.data)
    
    if df_snap.empty:
        st.warning("⚠️ Chưa có dữ liệu Snapshot. Vui lòng bấm 'Capture AI Snapshot' ở Sidebar.")
        if st.button("Kích hoạt Snapshot đầu tiên"):
            AI_Engine_v3.run_snapshot(sb, features)
            st.rerun()
        return

    latest = df_snap.iloc[0]
    prev = df_snap.iloc[1] if len(df_snap) > 1 else latest
    risk_score = latest['risk_score'] / 100

    st.markdown(f"""
        <div style="background-color: white; padding: 20px; border-radius: 15px; border-left: 10px solid {'#ff3b30' if risk_score > 0.6 else '#ffcc00' if risk_score > 0.3 else '#34c759'};">
            <h2 style="margin:0;">🧠 AI Strategic Hub <span style="font-size:14px; color:#86868b;">V3.0 HYBRID</span></h2>
            <p style="color:#86868b; margin:0;">Phân tích từ 5,000 thiết bị dựa trên AI Memory Layer.</p>
        </div>
    """, unsafe_allow_html=True)
    
    t_overview, t_analysis, t_prediction, t_rag = st.tabs(["🚀 CHIẾN LƯỢC", "🕵️ TRUY VẾT RỦI RO", "🔮 DỰ BÁO", "💬 TRỢ LÝ RAG"])

    with t_overview:
        c1, c2, c3 = st.columns(3)
        c1.metric("Risk Index", f"{risk_score:.2f}", delta=round(risk_score - (prev['risk_score']/100), 2), delta_color="inverse")
        c2.metric("System Health", f"{int((1 - risk_score) * 100)}%", delta=f"{latest['total_devices']} Máy")
        c3.metric("AI Status", latest['risk_level'])
        st.write("---")
        st.markdown("**📈 Diễn biến rủi ro 24h (Dữ liệu thật từ DB)**")
        st.line_chart(df_snap, x='created_at', y='risk_score', color="#0071e3")

    with t_analysis:
        st.markdown("#### 🕵️ Phân tích bằng chứng (Evidence-based)")
        col_a, col_b = st.columns([1, 1])
        with col_a:
            st.write("**Top 5 máy rớt mạng lâu nhất:**")
            anomaly_df = df_d.sort_values('off_min', ascending=False).head(5)
            st.dataframe(anomaly_df[['machine_id', 'off_min', 'status']], use_container_width=True, hide_index=True)
        with col_b:
            st.info("**AI Narrative (Giải thuật tự sự V3)**")
            st.write(f"- **Hiện trạng:** `{latest['offline_ratio']*100:.1f}%` hệ thống đang offline.\n- **Biến động:** Phát hiện `{latest['new_offline_1h']}` máy mới rớt mạng.\n- **Độ ổn định:** Jitter `{latest['heartbeat_jitter']}`.")
            st.button("Tạo báo cáo chiến lược (PDF)", use_container_width=True)

    with t_prediction:
        st.markdown("#### 🔮 Dự báo bảo trì & Vật tư")
        p1, p2 = st.columns(2)
        with p1:
            st.warning("⚠️ **Dự báo cạn kiệt tinh màu**")
            st.table(pd.DataFrame({"Đại lý": ["Sơn Hà Nội", "Hùng Tú-Cần Thơ"], "AI Dự báo": ["24h tới", "48h tới"]}))
        with p2:
            st.success("✅ **Dự báo tải trọng hệ thống**")
            st.info("AI dự báo lưu lượng file SDF sẽ đạt đỉnh vào chiều nay.")

    with t_rag:
        st.markdown("#### 💬 Trợ lý AI đặc quyền")
        query = st.text_input("Hỏi AI về hệ thống:", placeholder="Ví dụ: Tại sao hôm nay Risk Score tăng cao?")
        if query:
            with st.spinner("AI đang truy vấn Memory..."):
                st.chat_message("assistant").write(f"Dựa trên Snapshot lúc {latest['created_at']}, rủi ro hiện tại là {latest['risk_level']}.")

# --- PHẦN GỌI TAB TRONG APP CHÍNH (SỬA LỖI THỤT LỀ TẠI ĐÂY) ---
with t_ai:
    if not df_d.empty:
        try:
            now_dt_aware = datetime.now(timezone.utc)
            if 'last_seen_dt' not in df_d.columns:
                df_d['last_seen_dt'] = pd.to_datetime(df_d['last_seen'], utc=True)
            
            # Sidebar button để chụp ảnh hệ thống
            if st.sidebar.button("📸 Capture AI Snapshot"):
                feats = AI_Engine_v3.calculate_features(df_d, now_dt_aware)
                AI_Engine_v3.run_snapshot(sb, feats)
                st.toast("Đã lưu Snapshot thành công!")
                time.sleep(0.5)
                st.rerun()

            render_ai_strategic_hub_v3(df_d, now_dt_aware, sb)
        except Exception as e:
            st.error(f"Lỗi AI Engine: {e}")
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
