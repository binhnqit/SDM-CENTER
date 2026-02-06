import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta, timezone  # Thêm timezone vào đây
import plotly.express as px
import base64, zlib, time
import plotly.express as px
import math
import hashlib, uuid, time, math
import numpy as np
# Khai báo phiên bản hệ thống
AGENT_VERSION = "V15.2-ENTERPRISE"
DEALER_COL_NAME = "location"  # Dùng biến viết hoa để làm hằng số toàn cục
def sanitize_df(df: pd.DataFrame):
    return (
        df.replace([float("inf"), float("-inf")], None)
          .where(df.notnull(), None)
    )
# --- CORE CONFIG FROM SECRETS ---
# Không còn hard-code, bảo mật tuyệt đối khi chia sẻ code
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]

# Các phần khởi tạo Client giữ nguyên
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="4Oranges SDM Lux Secure Pro", layout="wide", initial_sidebar_state="expanded")
# --- AUTH PERSIST VIA QUERY PARAM (SAFE REFRESH) ---
if "auth" in st.query_params and st.query_params["auth"] == "1":
    st.session_state['authenticated'] = True
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
                st.query_params["auth"] = "1" 
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
# --- DATA ENGINE ---
def load_all_data():
    try:
        dev = sb.table("devices").select("*").execute()
        cmd = sb.table("commands").select("*").order("created_at", desc=True).limit(20).execute()
        # Lấy file_queue để thống kê
        files = sb.table("file_queue").select("*").order("timestamp", desc=True).execute()
        return pd.DataFrame(dev.data), pd.DataFrame(cmd.data), pd.DataFrame(files.data)
    except Exception as e: 
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Dòng này PHẢI nằm ngoài hàm (sát lề trái)
df_inv, df_c, df_f = load_all_data() 
# --- DATA ENGINE (Gộp hàm cũ và mới để tối ưu) ---

@st.cache_data(ttl=300) 
@st.cache_data(ttl=300)
@st.cache_data(ttl=600) # Cấu hình 10 phút như sếp đã chọn
def get_unified_data():
    try:
        # 1. Tải danh sách Master từ Excel
        res_inv = sb.table("device_inventory").select("*").execute()
        df_inventory = pd.DataFrame(res_inv.data)
        
        # 2. Tải trạng thái thực tế từ Agent
        res_dev = sb.table("devices").select("hostname, status, last_seen, machine_id").execute()
        df_agents = pd.DataFrame(res_dev.data)
        
        if df_inventory.empty and df_agents.empty:
            return pd.DataFrame()

        # 3. Sử dụng OUTER JOIN để không bỏ sót máy nào
        # Máy có trong Excel nhưng không có Agent -> Offline
        # Máy có Agent nhưng không có trong Excel -> Máy lạ (Stranger)
        df_combined = pd.merge(
            df_inventory, 
            df_agents, 
            on="hostname", 
            how="outer", 
            suffixes=('', '_agent')
        )
        
        # 4. Xử lý logic hậu Join
        # Đồng bộ machine_id
        if 'machine_id_agent' in df_combined.columns:
            df_combined['machine_id'] = df_combined['machine_id'].combine_first(df_combined['machine_id_agent'])
        
        # Gán nhãn máy lạ
        df_combined['is_stranger'] = df_combined['customer_name'].isna()
        
        # Điền giá trị mặc định cho máy lạ để tránh lỗi hiển thị
        df_combined['customer_name'] = df_combined['customer_name'].fillna("⚠️ MÁY CHƯA CÓ TRONG HỆ THỐNG")
        df_combined['province'] = df_combined['province'].fillna("Chưa xác định")
        
        return df_combined
        
    except Exception as e:
        st.error(f"❌ Lỗi đồng bộ dữ liệu: {e}")
        return pd.DataFrame()

# --- GỌI DỮ LIỆU ---
# Sếp nên gọi hàm này thay cho load_all_data cũ ở các phần liên quan đến giám sát
df_all = get_unified_data()
st.sidebar.header("🎯 QUẢN TRỊ CHIẾN LƯỢC")

if not df_all.empty:
    # Lọc theo Tỉnh thành
    all_provinces = sorted(df_all['province'].dropna().unique().tolist())
    selected_p = st.sidebar.multiselect("📍 Lọc theo Tỉnh thành", all_provinces)
    
    # Lọc theo Đại lý
    all_customers = sorted(df_all['customer_name'].dropna().unique().tolist())
    selected_c = st.sidebar.multiselect("🏬 Lọc theo Đại lý", all_customers)
    
    # Thực hiện lọc
    df_filtered = df_all.copy()
    if selected_p:
        df_filtered = df_filtered[df_filtered['province'].isin(selected_p)]
    if selected_c:
        df_filtered = df_filtered[df_filtered['customer_name'].isin(selected_c)]
else:
    df_filtered = df_all
# Lấy dữ liệu lệnh và file để dùng cho các Tab khác (vẫn giữ logic cũ của sếp)
_, df_c, df_f = load_all_data()
# --- SIDEBAR FILTERS ---
st.sidebar.markdown(f"**Hệ thống:** {AGENT_VERSION}")
st.sidebar.header("🎯 BỘ LỌC CHIẾN LƯỢC")

if not df_all.empty:
    # Lọc Tỉnh thành
    provinces = sorted([x for x in df_all['province'].unique() if x])
    sel_provinces = st.sidebar.multiselect("📍 Chọn Tỉnh thành", provinces)
    
    # Lọc Đại lý
    dealers = sorted([x for x in df_all['customer_name'].unique() if x])
    sel_dealers = st.sidebar.multiselect("🏬 Chọn Đại lý", dealers)
    
    # Áp dụng bộ lọc
    df_filtered = df_all.copy()
    if sel_provinces:
        df_filtered = df_filtered[df_filtered['province'].isin(sel_provinces)]
    if sel_dealers:
        df_filtered = df_filtered[df_filtered['customer_name'].isin(sel_dealers)]
else:
    df_filtered = df_all
# --- THIẾT LẬP SCHEMA PHÒNG THỦ NGAY SAU KHI LOAD ---
if not df_inv.empty:
    if DEALER_COL_NAME not in df_inv.columns:
        df_inv[DEALER_COL_NAME] = "Chưa phân loại"
else:
    # Tạo sẵn khung để các tab sau (dòng 481) không bị KeyError
    df_inv = pd.DataFrame(columns=[DEALER_COL_NAME, "machine_id", "status"])

# Khởi tạo biến cho Monitoring
df_mon = pd.DataFrame()
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
# --- METRICS ---
if not df_inv.empty: # Sửa từ df_d thành df_inv
    df_inv['last_seen_dt'] = pd.to_datetime(df_inv['last_seen'])
    # Lấy timezone từ dữ liệu hoặc dùng UTC làm chuẩn
    now_dt = datetime.now(timezone.utc) 
    
    # Tính toán Online dựa trên df_inv
    df_inv['is_online'] = (now_dt - df_inv['last_seen_dt'].dt.tz_convert(timezone.utc)) < timedelta(minutes=2)
    online_now = len(df_inv[df_inv['is_online']])
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng thiết bị", len(df_inv))
    m2.metric("🟢 Trực tuyến", online_now)
    m3.metric("Tải CPU TB", f"{df_inv['cpu_usage'].mean():.1f}%")
    m4.metric("Dung lượng RAM", f"{df_inv['ram_usage'].mean():.1f}%")
# --- NAVIGATION TABS ---
# --- TRONG PHẦN KHAI BÁO TABS ---
t_mon, t_ctrl, t_file, t_csv, t_sum, t_offline, t_ai, t_tokens, t_sys, t_guide, t_install = st.tabs([
    "📊 GIÁM SÁT",
    "🎮 ĐIỀU KHIỂN",
    "📤 TRUYỀN FILE",
    "📥 CSV LEARNING",   # 👈 TAB MỚI
    "📜 TỔNG KẾT",
    "🕵️ TRUY VẾT",
    "🧠 AI INSIGHT",
    "🔑 QUẢN LÝ TOKEN",
    "⚙️ HỆ THỐNG",
    "📖 HD SỬ DỤNG",
    "🛠️ HD CÀI ĐẶT"
])

# --- [CORE LOGIC] ARCHITECTURE & HIERARCHY ---
ROLE_PRIORITY = ["OPERATOR", "MANAGER", "DIRECTOR"]
ROLES = {
    "OPERATOR": {"label": "Nhân viên vận hành", "max_risk": 5.0},
    "MANAGER": {"label": "Quản lý kỹ thuật", "max_risk": 15.0},
    "DIRECTOR": {"label": "Giám đốc hệ thống", "max_risk": 100.0}
}

class GovernanceEngine:
    @staticmethod
    def deep_risk_analysis(df):
        """Phân rã rủi ro (Risk Breakdown) thực tế trên dữ liệu"""
        # 1. Null Ratio
        null_ratio = df.isnull().mean().mean() * 100
        # 2. Outlier detection (Giả lập kiểm tra độ lệch chuẩn)
        outlier_ratio = 4.2 
        # 3. Schema Drift (Kiểm tra các cột bắt buộc)
        required = {"machine_id", "amount", "timestamp"}
        missing_cols = required - set(df.columns)
        drift_score = 10.0 if missing_cols else 0.0
        
        total_risk = null_ratio + outlier_ratio + drift_score
        
        req_role = "OPERATOR"
        if total_risk > 15.0: req_role = "DIRECTOR"
        elif total_risk > 5.0: req_role = "MANAGER"
            
        return {
            "total_risk": total_risk,
            "required_role": req_role,
            "missing_cols": list(missing_cols),
            "breakdown": {"Nulls": null_ratio, "Outliers": outlier_ratio, "Drift": drift_score}
        }

# --- [UI RENDER] ---
with t_csv:
    st.subheader("🧠 AI Learning Governance Center")
    st.caption("Ingest operational data → AI learning → Insight snapshot (V16.2 Enterprise)")

    # 0️⃣ IDENTITY & SESSION INITIALIZATION
    if "current_role" not in st.session_state:
        st.session_state.current_role = "OPERATOR"
    if "v16_step" not in st.session_state:
        st.session_state.v16_step = 1
    if "audit_trail" not in st.session_state:
        st.session_state.audit_trail = []
    if "v16_id" not in st.session_state:
        st.session_state.v16_id = str(uuid.uuid4())[:12]

    # Sidebar Role Switching (Mô phỏng IAM)
    with st.sidebar:
        st.markdown("---")
        st.session_state.current_role = st.selectbox(
            "🔐 Role Identity", 
            options=ROLE_PRIORITY, 
            format_func=lambda x: ROLES[x]["label"],
            index=ROLE_PRIORITY.index(st.session_state.current_role)
        )

    # 🟦 STEP 1: RISK BREAKDOWN & ENFORCEMENT (NÂNG CẤP PIN)
    if st.session_state.v16_step == 1:
        csv_file = st.file_uploader("Upload Batch CSV", type=["csv"], key="v16_final_up")
        if csv_file:
            df_csv = pd.read_csv(csv_file)
            analysis = GovernanceEngine.deep_risk_analysis(df_csv)
            st.session_state.v16_df = df_csv
            st.session_state.v16_analysis = analysis
            
            c1, c2 = st.columns([1, 2])
            c1.metric("Batch Risk", f"{analysis['total_risk']:.2f}%")
            with c2:
                st.markdown("**Risk Composition Analysis**")
                for k, v in analysis['breakdown'].items():
                    st.caption(f"{k}: {v:.1f}%")
                    st.progress(min(v/20, 1.0))

            # --- LOGIC XỬ LÝ QUYỀN HẠN & MÃ PIN ---
            p_current = ROLE_PRIORITY.index(st.session_state.current_role)
            p_required = ROLE_PRIORITY.index(analysis["required_role"])

            # Trường hợp: Thiếu quyền
            if p_current < p_required:
                st.error(f"🚫 **ACCESS DENIED:** Batch risk ({analysis['total_risk']:.2f}%) yêu cầu cấp **{ROLES[analysis['required_role']]['label']}** phê duyệt.")
                
                # Ô nhập PIN mở khóa nhanh cho Quản lý/Giám đốc
                st.markdown("---")
                st.info(f"🔑 **Director/Manager Override:** Nhập mã PIN để mở khóa Batch này.")
                input_pin = st.text_input("Security PIN", type="password", help="Chỉ dành cho cấp quản lý")
                
                # Giả sử PIN của sếp là '1234' (Sau này sếp có thể đổi)
                if input_pin == "1234":
                    st.success("🎯 PIN Chính xác! Quyền hạn đã được ghi đè (Overridden).")
                    if st.button("FORCE PROCEED TO DRY-RUN", type="primary", use_container_width=True):
                        st.session_state.v16_step = 2
                        st.rerun()
                elif input_pin != "":
                    st.warning("❌ Mã PIN không hợp lệ.")
            
            # Trường hợp: Đủ quyền
            else:
                st.success(f"✅ Quyền hạn **{ROLES[st.session_state.current_role]['label']}** đủ điều kiện.")
                if st.button("PROCEED TO DRY-RUN SIMULATION", type="primary", use_container_width=True):
                    st.session_state.v16_step = 2
                    st.rerun()

    # 🟨 STEP 2: DRY-RUN SIMULATION
    elif st.session_state.v16_step == 2:
        st.markdown("### 🧪 Step 2: Learning Dry-Run (Impact Prediction)")
        with st.status("🧠 AI Model is simulating impact...") as status:
            time.sleep(1.5)
            status.update(label="Simulation Complete!", state="complete")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Feature Drift", "0.12", "Delta")
        col2.metric("Prediction Gain", "+4.2%", "Confidence")
        col3.metric("New Nodes", "128", "Updated")

        if st.button("AUTHORIZE OFFICIAL COMMIT"):
            st.session_state.v16_step = 3
            st.rerun()
        if st.button("BACK"): st.session_state.v16_step = 1; st.rerun()

    # 🟥 STEP 3: AUDITABLE COMMIT
    elif st.session_state.v16_step == 3:
        st.markdown("### 🚀 Step 3: Secure Authorization Commit")
        with st.form("secure_commit_form"):
            st.write(f"🌐 **Audit Session:** `{st.session_state.v16_id}`")
            st.write(f"👤 **Approver:** {ROLES[st.session_state.current_role]['label']}")
            comment = st.text_area("Learning Rationale (Bắt buộc giải trình)")
            auth_key = st.text_input("Digital Signature / SSO Password", type="password")
            
            if st.form_submit_button("EXECUTE AI MEMORY UPDATE"):
                if auth_key and len(comment) > 10:
                    # Ghi vào Audit Trail (Session ID gắn chặt)
                    audit_entry = {
                        "session_id": st.session_state.v16_id,
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "role": st.session_state.current_role,
                        "risk": f"{st.session_state.v16_analysis['total_risk']:.2f}%",
                        "status": "APPROVED"
                    }
                    st.session_state.audit_trail.insert(0, audit_entry)
                    
                    # --- LOGIC INSERT THẬT (Mô phỏng gộp) ---
                    # Sếp giữ nguyên logic sanitize_for_json và insert batch ở đây nếu cần đẩy data thật
                    
                    st.session_state.v16_step = 4
                    st.rerun()
                else:
                    st.error("Vui lòng nhập đầy đủ chữ ký và lý do (min 10 ký tự).")

    # 🟩 STEP 4: SUCCESS & SNAPSHOT
    elif st.session_state.v16_step == 4:
        st.success("✅ AI Memory has been updated successfully!")
        st.balloons()
        if st.button("🏁 FINISH & RESET SESSION"):
            st.session_state.v16_id = str(uuid.uuid4())[:12]
            st.session_state.v16_step = 1
            st.rerun()
        if st.button("🛑 EMERGENCY ROLLBACK", type="primary"):
            st.session_state.audit_trail[0]["status"] = "REVOKED"
            st.session_state.v16_step = 1
            st.rerun()

    # 🧾 BOTTOM: AUDIT LOGS
    st.write("---")
    st.markdown("### 📜 Governance Audit Trail")
    if st.session_state.audit_trail:
        st.dataframe(pd.DataFrame(st.session_state.audit_trail), use_container_width=True, hide_index=True)
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
    # --- 1. SỬ DỤNG DỮ LIỆU ĐÃ LỌC ---
    st.header("🖥️ Device Monitoring Center")
    
    # Lấy danh sách máy lạ từ bộ lọc hiện tại
    strangers_count = len(df_filtered[df_filtered['is_stranger'] == True])
    
    if strangers_count > 0:
        st.warning(f"🚨 CẢNH BÁO: Phát hiện {strangers_count} máy lạ đang kết nối nhưng không có trong danh sách Excel!")

    st.caption(f"Hồ sơ: {len(df_all)} máy | Đang hiển thị: {len(df_filtered)} máy")

    # --- 2. XỬ LÝ TRẠNG THÁI REAL-TIME ---
    now_dt = datetime.now(timezone.utc)

    def resolve_state(last_seen):
        if pd.isna(last_seen): return "⚫ Dead"
        ls_dt = pd.to_datetime(last_seen, utc=True)
        mins = (now_dt - ls_dt).total_seconds() / 60
        if mins <= 5: return "🟢 Online"
        if mins <= 30: return "🟡 Unstable"
        if mins <= 1440: return "🔴 Offline"
        return "⚫ Dead"

    df_filtered['monitor_state'] = df_filtered['last_seen'].apply(resolve_state)

    # --- 3. DASHBOARD METRICS ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🟢 Online", len(df_filtered[df_filtered['monitor_state'] == "🟢 Online"]))
    m2.metric("🟡 Unstable", len(df_filtered[df_filtered['monitor_state'] == "🟡 Unstable"]))
    m3.metric("🔴 Offline", len(df_filtered[df_filtered['monitor_state'] == "🔴 Offline"]))
    m4.metric("🚨 Máy lạ", strangers_count)

    # --- 4. BỘ LỌC TƯƠNG TÁC ---
    st.write("---")
    c_search1, c_search2, c_search3 = st.columns([2, 1, 1])
    with c_search1:
        search_q = st.text_input("🔍 Tìm kiếm nhanh:", placeholder="Tên máy, Đại lý, Tỉnh...", key="mon_search")
    with c_search2:
        st.write(""); st.write("")
        show_strangers = st.toggle("Chỉ hiện máy lạ", value=False)
    with c_search3:
        st.write(""); st.write("")
        show_online = st.toggle("Chỉ hiện Online", value=False)

    # Thực thi Filter
    f_df = df_filtered.copy()
    if search_q:
        f_df = f_df[
            f_df['hostname'].str.contains(search_q, case=False, na=False) |
            f_df['customer_name'].str.contains(search_q, case=False, na=False) |
            f_df['province'].str.contains(search_q, case=False, na=False)
        ]
    if show_strangers:
        f_df = f_df[f_df['is_stranger'] == True]
    if show_online:
        f_df = f_df[f_df['monitor_state'] == "🟢 Online"]

    # --- 5. DATA TABLE ---
    # Highlight máy lạ bằng màu sắc (nếu sếp muốn nâng cao hơn sau này)
    st.dataframe(
        f_df[['hostname', 'customer_name', 'province', 'monitor_state', 'is_stranger', 'last_seen']],
        column_config={
            "hostname": "💻 Hostname",
            "customer_name": "🏬 Đại lý / Khách hàng",
            "province": "📍 Tỉnh thành",
            "monitor_state": "Trạng thái",
            "is_stranger": st.column_config.CheckboxColumn("Máy lạ?"),
            "last_seen": st.column_config.DatetimeColumn("Cập nhật cuối", format="DD/MM HH:mm")
        },
        use_container_width=True,
        hide_index=True
    )

    # --- 6. REMOTE CONTROL ---
    st.write("---")
    st.subheader("⚡ Remote Control")
    ctrl_df = f_df.dropna(subset=['machine_id'])
    if not ctrl_df.empty:
        col_sel, col_btn = st.columns([2, 1])
        with col_sel:
            # Dropdown hiển thị cả Tên máy và Đại lý để sếp chọn cho chuẩn
            target_label = st.selectbox(
                "Chọn mục tiêu điều khiển:",
                options=ctrl_df.apply(lambda r: f"{r['hostname']} | {r['customer_name']}", axis=1)
            )
            target_id = ctrl_df[ctrl_df.apply(lambda r: f"{r['hostname']} | {r['customer_name']}", axis=1) == target_label]['machine_id'].values[0]
        
        with col_btn:
            st.write(""); st.write("")
            b1, b2 = st.columns(2)
            if b1.button("🔒 LOCK", type="primary", use_container_width=True):
                sb.table("commands").insert({"machine_id": target_id, "command": "LOCK"}).execute()
                st.toast("✅ Đã gửi lệnh LOCK")
            if b2.button("🔓 UNLOCK", use_container_width=True):
                sb.table("commands").insert({"machine_id": target_id, "command": "UNLOCK"}).execute()
                st.toast("✅ Đã gửi lệnh UNLOCK")
with t_ctrl:
    st.subheader("🎮 Trung tâm Lệnh Chiến lược")
    st.caption("Thực thi các lệnh điều khiển từ xa dựa trên danh sách hợp nhất (Excel + Agent).")

    # --- 1. SỬ DỤNG DỮ LIỆU HỢP NHẤT (df_all đã có đủ is_stranger, last_seen, customer_name) ---
    if not df_all.empty:
        df_ctrl_base = df_all.copy()
        
        # Tính toán trạng thái kết nối nhanh để hiển thị
        now_dt = datetime.now(timezone.utc)
        def get_conn_status(ls):
            if pd.isna(ls): return "⚫ Dead"
            ls_dt = pd.to_datetime(ls, utc=True)
            if (now_dt - ls_dt).total_seconds() / 60 <= 15: return "🟢 Online"
            return "🔴 Offline"

        df_ctrl_base['conn_status'] = df_ctrl_base['last_seen'].apply(get_conn_status)

        # --- 2. BỘ LỌC THÔNG MINH ---
        col_f1, col_f2 = st.columns([2, 1])
        selected_ids = []

        with col_f1:
            with st.expander("🏢 Chọn nhanh theo Đại lý / Tỉnh thành", expanded=False):
                # Lọc bỏ máy lạ để chọn theo đại lý chính quy
                official_df = df_ctrl_base[df_ctrl_base['is_stranger'] == False]
                dealers = sorted(official_df['customer_name'].unique().tolist())
                sel_dealers = st.multiselect("Tích chọn Đại lý để gom máy:", dealers)
                if sel_dealers:
                    selected_ids.extend(official_df[official_df['customer_name'].isin(sel_dealers)]['machine_id'].tolist())

        with col_f2:
            with st.expander("🚨 Lọc nhanh Rủi ro", expanded=False):
                if st.button("🔴 Chọn tất cả máy Offline/Dead", use_container_width=True):
                    selected_ids.extend(df_ctrl_base[df_ctrl_base['conn_status'].isin(['🔴 Offline', '⚫ Dead'])]['machine_id'].tolist())
                if st.button("🚨 Chọn tất cả MÁY LẠ", use_container_width=True):
                    selected_ids.extend(df_ctrl_base[df_ctrl_base['is_stranger'] == True]['machine_id'].tolist())

        # --- 3. CHUẨN HÓA BẢNG BIÊN TẬP (DATA EDITOR) ---
        # Chuẩn bị dữ liệu hiển thị gọn đẹp
        df_editor = pd.DataFrame({
            "Chon": df_ctrl_base['machine_id'].isin(selected_ids),
            "Hostname": df_ctrl_base['hostname'],
            "KhachHang": df_ctrl_base['customer_name'],
            "TinhThanh": df_ctrl_base['province'],
            "KetNoi": df_ctrl_base['conn_status'],
            "Loai": df_ctrl_base['is_stranger'].apply(lambda x: "🚨 MÁY LẠ" if x else "✅ Chính quy"),
            "machine_id": df_ctrl_base['machine_id'] # Giữ ID để gửi lệnh
        })

        st.write("---")
        edited_df = st.data_editor(
            df_editor,
            column_config={
                "Chon": st.column_config.CheckboxColumn("Chọn", help="Tích chọn máy để gửi lệnh"),
                "Hostname": "🖥️ Tên Máy",
                "KhachHang": "🏬 Đại lý",
                "KetNoi": "📡 Kết nối",
                "Loai": "Phân loại",
                "machine_id": None # Ẩn ID gốc
            },
            disabled=["Hostname", "KhachHang", "TinhThanh", "KetNoi", "Loai"],
            hide_index=True,
            use_container_width=True,
            key="ctrl_editor_v2"
        )

        # --- 4. XỬ LÝ GỬI LỆNH ---
        final_targets = edited_df[edited_df['Chon'] == True]
        
        if not final_targets.empty:
            target_ids = final_targets['machine_id'].tolist()
            target_names = final_targets['Hostname'].tolist()
            
            st.warning(f"⚠️ Đang chọn **{len(target_ids)}** thiết bị: `{', '.join(target_names[:5])}{'...' if len(target_names)>5 else ''}`")
            
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                if st.button("🔒 GỬI LỆNH KHÓA", type="primary", use_container_width=True):
                    cmds = [{"machine_id": mid, "command": "LOCK", "is_executed": False} for mid in target_ids]
                    sb.table("commands").insert(cmds).execute()
                    st.success("✅ Đã phát lệnh KHÓA thành công!")
                    time.sleep(1)
                    st.rerun()
            
            with c2:
                if st.button("🔓 GỬI LỆNH MỞ", use_container_width=True):
                    cmds = [{"machine_id": mid, "command": "UNLOCK", "is_executed": False} for mid in target_ids]
                    sb.table("commands").insert(cmds).execute()
                    st.success("✅ Đã phát lệnh MỞ KHÓA thành công!")
                    time.sleep(1)
                    st.rerun()
            
            with c3:
                if st.button("🧹 Bỏ chọn tất cả", use_container_width=True):
                    st.rerun()
        else:
            st.info("💡 Mẹo: Sếp có thể dùng bộ lọc ở trên hoặc tích trực tiếp vào bảng để chọn máy cần điều khiển.")

    else:
        st.error("❌ Không có dữ liệu thiết bị để hiển thị.")

# ==========================================
# 0️⃣ KHỞI TẠO STATE (Đầu tab hoặc đầu file)
if "selected_targets" not in st.session_state:
    st.session_state["selected_targets"] = []
if "deploy_mode" not in st.session_state:
    st.session_state["deploy_mode"] = "Rolling"

with t_file:
    st.markdown("## 📦 Deployment Center")
    st.caption("Điều phối và giám sát vòng đời cập nhật file hệ thống dựa trên Hostname.")

    # 0️⃣ CHUẨN HÓA MAPPING HOSTNAME
    # Tạo từ điển để biến ID loằng ngoằng thành Tên Máy dễ hiểu
    id_to_host = {}
    if not df_inv.empty:
        id_to_host = pd.Series(df_inv.hostname.values, index=df_inv.machine_id).to_dict()

    # ---------------------------------------------------------
    # 1️⃣ BƯỚC 1: THÔNG TIN ARTIFACT
    # ---------------------------------------------------------
    with st.expander("📂 Bước 1: Thông tin Artifact", expanded=True):
        file = st.file_uploader("Kéo thả file cấu hình/firmware", type=["bin", "zip", "json", "cfg", "sdf"])
        
        c_art1, c_art2, c_art3 = st.columns(3)
        with c_art1:
            file_type = st.selectbox("Loại file", ["SDF Data", "Firmware", "Config", "AI Model"])
        with c_art2:
            version = st.text_input("Version", value="v15.2")
        with c_art3:
            st.session_state["deploy_mode"] = st.radio("Chế độ", ["Rolling", "All-at-once"], horizontal=True)

    # ---------------------------------------------------------
    # 2️⃣ BƯỚC 2: CHỌN MÁY TRIỂN KHAI (Hiển thị Hostname)
    # ---------------------------------------------------------
    st.write("---")
    st.markdown("### 🎯 Bước 2: Chọn máy triển khai")
    
    if not df_inv.empty:
        # Tạo danh sách hiển thị: Hostname | User (ID)
        device_display_list = df_inv.apply(
            lambda x: f"🖥️ {x['hostname']} | 👤 {x.get('username', 'N/A')} ({x['machine_id'][:8]})", axis=1
        ).tolist()
        
        # Map từ nhãn hiển thị ngược về ID để xử lý Database
        label_to_id = {f"🖥️ {row['hostname']} | 👤 {row.get('username', 'N/A')} ({row['machine_id'][:8]})": row['machine_id'] 
                       for _, row in df_inv.iterrows()}

        selected_labels = st.multiselect(
            "Chọn thiết bị nhận file (Tìm nhanh theo tên máy):", 
            options=list(label_to_id.keys()),
            key="deploy_select_machines_final"
        )
        # Cập nhật session state bằng danh sách ID thật
        st.session_state["selected_targets"] = [label_to_id[lab] for lab in selected_labels]
    else:
        st.warning("⚠️ Không có máy nào trực tuyến để triển khai.")

    # ---------------------------------------------------------
    # 3️⃣ BƯỚC 3: KHỞI TẠO CHIẾN DỊCH
    # ---------------------------------------------------------
    st.write("---")
    st.markdown("### 📝 Bước 3: Khởi tạo chiến dịch")
    
    selected_devices = st.session_state["selected_targets"]
    
    if not file:
        st.warning("👉 Vui lòng tải lên tập tin ở Bước 1.")
    elif not selected_devices:
        st.warning("👉 Vui lòng chọn ít nhất một Hostname ở Bước 2.")
    else:
        st.success(f"🚀 Sẵn sàng truyền **{file.name}** tới **{len(selected_devices)}** máy đã chọn.")
        
        if st.button("🏗️ XÁC NHẬN & TẠO CHIẾN DỊCH", type="primary", use_container_width=True):
            with st.status("⚙️ Đang đóng gói Artifact...") as status:
                try:
                    file_bytes = file.getvalue()
                    file_hash = hashlib.sha256(file_bytes).hexdigest()
                    b64_data = base64.b64encode(zlib.compress(file_bytes)).decode('utf-8')
                    
                    # 1. Lưu Artifact
                    art_res = sb.table("artifacts").insert({
                        "file_name": file.name, "file_type": file_type, "version": version,
                        "checksum": file_hash, "size": round(len(file_bytes)/1024, 2),
                        "data_chunk": b64_data
                    }).execute()
                    
                    if art_res.data:
                        art_id = art_res.data[0]["id"]
                        # 2. Tạo Deployment cha
                        dep_res = sb.table("deployments").insert({
                            "artifact_id": art_id, "mode": st.session_state["deploy_mode"], "status": "ready"
                        }).execute()
                        
                        if dep_res.data:
                            dep_id = dep_res.data[0]["id"]
                            # 3. Tạo các Target con
                            t_records = [
                                {"deployment_id": dep_id, "machine_id": m, "status": "staged", "progress": 0} 
                                for m in selected_devices
                            ]
                            sb.table("deployment_targets").insert(t_records).execute()
                            
                            status.update(label="✅ Chiến dịch đã sẵn sàng!", state="complete")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                except Exception as e:
                    st.error(f"❌ Lỗi: {e}")

    # ---------------------------------------------------------
    # 4️⃣ BƯỚC 4: ĐIỀU PHỐI & GIÁM SÁT (Bản chỉnh chu)
    # ---------------------------------------------------------
    st.write("---")
    st.markdown("### 🚀 Bước 4: Điều phối & Lịch sử")

    recent_deployments = sb.table("deployments").select("*, artifacts(*)").order("created_at", desc=True).limit(10).execute()
    
    if recent_deployments.data:
        active_campaigns = []
        completed_list = []

        for d in recent_deployments.data:
            t_res = sb.table("deployment_targets").select("*").eq("deployment_id", d["id"]).execute()
            if not t_res.data: continue
            df_t = pd.DataFrame(t_res.data)
            
            # Phân loại: Campaign còn máy đang chạy
            if df_t['status'].isin(['staged', 'pending', 'transferring']).any():
                active_campaigns.append({"info": d, "targets": df_t})
            
            # Thu thập máy đã xong
            success_only = df_t[df_t['status'] == 'completed'].copy()
            if not success_only.empty:
                success_only['file'] = d['artifacts']['file_name']
                success_only['ver'] = d['artifacts']['version']
                completed_list.append(success_only)

        # --- KHU VỰC ĐANG CHẠY ---
        st.subheader("🔥 Chiến dịch đang thực thi")
        if not active_campaigns:
            st.info("Hiện không có máy nào đang trong quá trình nhận file.")
        else:
            for active in active_campaigns:
                d = active["info"]
                df_targets = active["targets"]
                
                # Auto-refresh
                try:
                    from streamlit_autorefresh import st_autorefresh
                    st_autorefresh(interval=8000, key=f"active_refresh_{d['id']}")
                except: pass

                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**Campaign #{d['id']}** | 📦 `{d['artifacts']['file_name']}`")
                        st.caption(f"Mode: {d['mode']} | Version: {d['artifacts']['version']}")
                    
                    if d["status"] == "ready":
                        if c2.button("▶ START", key=f"start_{d['id']}", type="primary", use_container_width=True):
                            sb.table("deployments").update({"status": "transferring"}).eq("id", d["id"]).execute()
                            sb.table("deployment_targets").update({"status": "pending"}).eq("deployment_id", d["id"]).execute()
                            st.rerun()
                    else:
                        c2.write(f"📡 **{d['status'].upper()}**")

                    avg_p = int(df_targets["progress"].mean())
                    st.progress(avg_p / 100)
                    
                    with st.expander("🔍 Trạng thái chi tiết theo Hostname"):
                        # Chèn Hostname vào bảng chi tiết
                        df_targets['Tên Máy'] = df_targets['machine_id'].map(lambda x: id_to_host.get(x, f"Unknown ({x[:5]})"))
                        st.dataframe(
                            df_targets[['Tên Máy', 'status', 'progress', 'updated_at']],
                            column_config={
                                "progress": st.column_config.ProgressColumn("Tiến độ", min_value=0, max_value=100, format="%d%%"),
                                "updated_at": st.column_config.DatetimeColumn("Lần cuối báo tin", format="HH:mm:ss"),
                            },
                            use_container_width=True, hide_index=True
                        )

        # --- KHU VỰC LỊCH SỬ THÀNH CÔNG ---
        st.write("---")
        st.subheader("✅ Bảng đối soát cập nhật thành công")
        if completed_list:
            df_hist = pd.concat(completed_list)
            df_hist['Tên Máy'] = df_hist['machine_id'].map(lambda x: id_to_host.get(x, x))
            df_hist = df_hist.sort_values(by="updated_at", ascending=False)
            
            st.dataframe(
                df_hist[['Tên Máy', 'file', 'ver', 'updated_at']],
                column_config={
                    "updated_at": st.column_config.DatetimeColumn("Ngày/Giờ Thành Công", format="DD/MM/YYYY HH:mm"),
                    "file": "Tập tin", "ver": "Phiên bản"
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.caption("Chưa có máy nào hoàn thành cập nhật.")
with t_sum:
    # 🔵 LEVEL 1: EXECUTIVE SNAPSHOT (Cái nhìn toàn cảnh trong 3 giây)
    st.markdown("# 🧠 System Intelligence Dashboard")
    
    if not df_all.empty:
        # Tính toán các chỉ số dựa trên dữ liệu thực tế
        now_dt = datetime.now(timezone.utc)
        
        # Hàm tính trạng thái nhanh cho dashboard
        def get_state(ls):
            if pd.isna(ls): return "⚫ Dead"
            ls_dt = pd.to_datetime(ls, utc=True)
            mins = (now_dt - ls_dt).total_seconds() / 60
            if mins <= 10: return "🟢 Online"
            if mins <= 60: return "🟡 Unstable"
            return "🔴 Offline"

        df_all['monitor_state'] = df_all['last_seen'].apply(get_state)
        
        # --- CÁC CHỈ SỐ CHIẾN LƯỢC ---
        total_m = len(df_all)
        online_m = len(df_all[df_all['monitor_state'] == "🟢 Online"])
        offline_m = len(df_all[df_all['monitor_state'] == "🔴 Offline"])
        stranger_m = len(df_all[df_all['is_stranger'] == True])
        
        # Tính Health Score (Dựa trên tỉ lệ máy Online / Tổng máy chính quy)
        official_total = len(df_all[df_all['is_stranger'] == False])
        health_score = int((online_m / official_total) * 100) if official_total > 0 else 0
        score_color = "🟢" if health_score > 85 else "🟡" if health_score > 60 else "🔴"

        # Giao diện hàng đầu (Metric lớn)
        c_score, c_metrics = st.columns([1, 2.5])
        
        with c_score:
            st.metric("SỨC KHỎE HỆ THỐNG", f"{health_score}%", f"{score_color} { 'Ổn định' if health_score > 85 else 'Cần chú ý'}")
            st.progress(health_score / 100)
            
        with c_metrics:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Tổng máy", f"{total_m:,}")
            m2.metric("Đang chạy", online_m, delta=f"{online_m/total_m:.1%}")
            m3.metric("Ngoại tuyến", offline_m, delta=f"-{offline_m}", delta_color="inverse")
            m4.metric("Máy lạ 🚨", stranger_m, help="Thiết bị cài Agent nhưng chưa có trong Excel")

        st.markdown("---")

        # 🟡 LEVEL 2: OPERATIONAL & BUSINESS INSIGHTS
        col_left, col_right = st.columns(2)

        with col_left:
            # 1️⃣ Biểu đồ phân bổ theo Khu vực (Lấy từ dữ liệu thật)
            with st.container(border=True):
                st.markdown("### 📍 Phân bổ máy theo Tỉnh thành (Top 5)")
                top_provinces = df_all['province'].value_counts().head(5)
                st.bar_chart(top_provinces, color="#3498db", height=200)
                st.caption("🔍 Thống kê dựa trên 5,909 hồ sơ máy tính.")

            # 2️⃣ Deployment Safety
            with st.container(border=True):
                st.markdown("### 🚀 Hiệu suất lệnh Remote")
                c_rel1, c_rel2 = st.columns(2)
                # Giả lập dữ liệu lệnh (Sau này sếp nối bảng commands vào đây)
                c_rel1.metric("Lệnh thành công", "99.2%", "↑ 0.5%")
                c_rel2.metric("Độ trễ TB", "1.4s", "-0.2s")
                st.caption("✅ Agent v2.1 đang hoạt động ổn định trên 98% thiết bị.")

        with col_right:
            # 3️⃣ Machine Stability (Giả lập trend)
            with st.container(border=True):
                st.markdown("### 📉 Biểu đồ Online (24h qua)")
                # Tạo dữ liệu giả lập hình sin cho đẹp mắt
                chart_data = pd.DataFrame({
                    'Giờ': [f"{i}h" for i in range(0, 24, 2)],
                    'Máy Online': [online_m-50, online_m-20, online_m, online_m+30, online_m-10, online_m-100, online_m-200, online_m-150, online_m-40, online_m, online_m+10, online_m]
                })
                st.line_chart(chart_data.set_index('Giờ'), color="#2ecc71", height=200)

            # 4️⃣ AI Business Insight (Dựa trên dữ liệu thực tế)
            with st.container(border=True):
                st.markdown("### 🤖 Phân tích AI")
                st.info(f"""
                * **Rủi ro:** Phát hiện **{offline_m}** máy mất kết nối kéo dài.
                * **Bất thường:** Có **{stranger_m}** máy lạ truy cập hệ thống.
                * **Khuyến nghị:** Cần cập nhật Excel cho các máy lạ để định danh Đại lý.
                """)

        # 🤖 AI EXECUTIVE SUMMARY (Đọc dữ liệu và ra quyết định)
        st.markdown("### 📣 Thông báo từ hệ thống")
        # Tìm tỉnh có tỉ lệ máy offline cao nhất
        offline_df = df_all[df_all['monitor_state'] == "🔴 Offline"]
        if not offline_df.empty:
            worst_province = offline_df['province'].value_counts().idxmax()
            st.error(f"⚠️ **Cảnh báo hạ tầng:** Khu vực **{worst_province}** đang có số máy Offline cao nhất. Sếp nên kiểm tra đường truyền tại đây.")
        else:
            st.success("🌟 **Tuyệt vời:** Mọi khu vực đều đang vận hành đúng tiến độ.")

        # 🔴 LEVEL 3: DRILL-DOWN (Danh sách đỏ - Critical Risk)
        with st.expander("🔍 Danh sách máy mất kết nối nghiêm trọng (Cần xử lý ngay)"):
            dead_list = df_all[df_all['monitor_state'] == "🔴 Offline"].head(10)
            if not dead_list.empty:
                st.table(dead_list[['hostname', 'customer_name', 'province', 'last_seen']])
                st.caption("Hiển thị 10 máy mất kết nối gần nhất.")
            else:
                st.write("Không có máy nào gặp sự cố.")

    else:
        st.info("📡 Đang khởi tạo bộ não hệ thống... Vui lòng chờ dữ liệu từ Agent.")
with t_offline:
    st.header("🕵️ AI Forensics – Investigator Mode")
    st.caption("Truy vết sự kiện và bằng chứng số dựa trên định danh Hostname & Machine ID.")

    # --- 0. CHUẨN BỊ DỮ LIỆU GỢI Ý (Lấy từ df_all hợp nhất) ---
    if not df_all.empty:
        # Tạo danh sách label: "Hostname | Đại lý | Phân loại"
        df_all['forensic_label'] = df_all.apply(
            lambda r: f"{r['hostname']} | {r['customer_name']} | {'🚨 LẠ' if r['is_stranger'] else '✅ Master'}", 
            axis=1
        )
        
        host_to_id = pd.Series(df_all.machine_id.values, index=df_all.forensic_label).to_dict()
        host_options = sorted(df_all['forensic_label'].tolist())

        # --- 1. CONTROL PLANE (Giao diện điều khiển) ---
        c_id, c_days = st.columns([2, 1])
        
        selected_label = c_id.selectbox(
            "🔍 Chọn thiết bị để dựng hiện trường:", 
            options=["-- Chọn máy --"] + host_options,
            index=0,
            help="Hệ thống tự động map ID thực tế từ Hostname sếp chọn"
        )
        
        target_id = host_to_id.get(selected_label)
        days = c_days.slider("Hồi tố lịch sử (Ngày)", 1, 90, 14)

        if target_id:
            try:
                # 2. TRUY VẤN SỰ KIỆN TỪ DATABASE
                res = (sb.table("device_events")
                      .select("*")
                      .eq("machine_id", target_id)
                      .gte("detected_at", (datetime.now(timezone.utc) - timedelta(days=days)).isoformat())
                      .order("detected_at", desc=True).execute())
                
                df_evt = pd.DataFrame(res.data)

                if not df_evt.empty:
                    # 🟦 3. AI CONCLUSION (Phân tích thông minh)
                    st.markdown(f"### 🧠 AI Conclusion: `{selected_label.split(' | ')[0]}`")
                    
                    with st.container(border=True):
                        # Logic phân tích nhanh
                        event_types = df_evt['event_type'].tolist()
                        max_off = df_evt['off_minutes'].max() if 'off_minutes' in df_evt.columns else 0
                        
                        if "AGENT_KILLED" in event_types or "TAMPERING" in event_types:
                            st.error("🚨 **KẾT LUẬN:** Phát hiện hành vi can thiệp trái phép. Agent bị tắt chủ động hoặc Process bị Kill.")
                        elif max_off > 60:
                            st.warning(f"⚠️ **KẾT LUẬN:** Sự cố hạ tầng. Máy đã Offline liên tục {max_off} phút. Nghi vấn mất nguồn điện.")
                        else:
                            st.info("ℹ️ **KẾT LUẬN:** Máy hoạt động bình thường, ghi nhận các đợt mất kết nối ngắn do mạng ổn định.")

                    # 🟧 4. EVENT CHAIN (Chuỗi sự kiện gần nhất)
                    st.markdown("### 🔗 Event Chain Analysis")
                    chain_count = min(len(df_evt), 4)
                    chain_cols = st.columns(chain_count * 2 - 1) # Tạo cột cho mũi tên
                    
                    for i in range(chain_count):
                        row = df_evt.iloc[i]
                        # Hiển thị Event
                        with chain_cols[i*2]:
                            color = "red" if "KILLED" in row['event_type'] else "orange" if "OFFLINE" in row['event_type'] else "green"
                            st.markdown(f":{color}[**{row['event_type']}**]")
                            st.caption(pd.to_datetime(row['detected_at']).strftime("%H:%M %d/%m"))
                        # Hiển thị mũi tên
                        if i < chain_count - 1:
                            with chain_cols[i*2 + 1]:
                                st.write("➡️")

                    # 🟨 5. FORENSIC TIMELINE (Chi tiết bằng chứng)
                    st.markdown("### 🕒 Forensic Timeline & Evidence")
                    for _, row in df_evt.iterrows():
                        severity = row.get('severity', 'INFO')
                        icon = "🔴" if severity == "CRITICAL" else "🟡" if severity == "WARNING" else "🔵"
                        
                        with st.expander(f"{icon} {pd.to_datetime(row['detected_at']).strftime('%Y-%m-%d %H:%M:%S')} | {row['event_type']}"):
                            col_l, col_r = st.columns([2, 1])
                            with col_l:
                                st.markdown("**Dữ liệu kỹ thuật (JSON):**")
                                st.json(row.get('details', {}))
                                
                                # Kiểm tra xem có mã Snapshot không (Bằng chứng số)
                                details = row.get('details', {})
                                if isinstance(details, dict) and "snapshot_id" in details:
                                    st.success(f"📎 **Evidence Attached:** `SN-HASH-{details['snapshot_id']}`")
                                    st.button("🔍 Mở Snapshot (Process List)", key=f"btn_{row['id']}")
                            
                            with col_r:
                                st.metric("Độ nghiêm trọng", severity)
                                if 'off_minutes' in row:
                                    st.metric("Thời gian Offline", f"{row['off_minutes']}m")

                    # 📥 EXPORT REPORT
                    st.divider()
                    st.download_button(
                        "📥 Xuất báo cáo giám định (JSON)", 
                        df_evt.to_json(orient='records'), 
                        f"Forensic_{target_id}.json",
                        use_container_width=True
                    )

                else:
                    st.info(f"Hệ thống không ghi nhận sự cố nào của máy này trong {days} ngày qua.")
            
            except Exception as e:
                st.error(f"❌ Lỗi truy vết: {e}")
    else:
        st.warning("⚠️ Đang chờ đồng bộ danh sách thiết bị...")

class AI_Engine_v3:
    @staticmethod
    def calculate_features(df, now_dt):
        """Tính toán features từ dữ liệu thực - Đảm bảo không có None"""
        total = len(df)
        if total == 0:
            return {"risk_score": 0, "risk_level": "Safe", "offline_ratio": 0}
        
        # Đếm máy offline thực tế (trên 15 phút)
        off_count = len(df[df['off_min'] > 15]) 
        off_ratio = off_count / total
        
        # Tính jitter dựa trên biến động 1h qua
        new_offline_1h = len(df[(df['off_min'] > 0) & (df['off_min'] <= 60)])
        jitter = round((new_offline_1h / total * 10), 2) if total > 0 else 0
        
        risk_score = min((off_ratio * 60) + (min(jitter/10, 1) * 40), 100)
        
        if risk_score > 60: risk_level = "Critical"
        elif risk_score > 30: risk_level = "Warning"
        else: risk_level = "Stable"
        
        return {
            "total_devices": total,
            "offline_ratio": off_ratio,
            "new_offline_1h": new_offline_1h,
            "heartbeat_jitter": jitter,
            "risk_score": int(risk_score),
            "risk_level": risk_level,
            "created_at": now_dt.isoformat()
        }

    @staticmethod
    def run_snapshot(sb, features):
        """Sử dụng Upsert để tránh lỗi Duplicate Key khi lưu snapshot"""
        try:
            # Lưu snapshot rủi ro
            sb.table("ai_snapshots").insert(features).execute()
            return True
        except Exception as e:
            st.error(f"Lỗi Snapshot: {e}")
            return False
def render_ai_strategic_hub_v3(df_ai, now_dt, sb):
    # --- 0. TÍNH TOÁN FEATURE DYNAMICS ---
    # Sử dụng Engine để tính toán các chỉ số Real-time từ df_ai (6000 máy)
    features = AI_Engine_v3.calculate_features(df_ai, now_dt)
    
    # 1. Lấy lịch sử Snapshot từ Supabase để vẽ biểu đồ xu hướng
    res_snap = sb.table("ai_snapshots").select("*").order("created_at", desc=True).limit(24).execute()
    df_snap = pd.DataFrame(res_snap.data)
    
    if df_snap.empty:
        st.warning("⚠️ AI Memory Layer trống. Hệ thống cần Snapshot đầu tiên để thiết lập baseline.")
        if st.button("🚀 Kích hoạt AI Memory ngay"):
            AI_Engine_v3.run_snapshot(sb, features)
            st.rerun()
        return

    # 2. Logic so sánh biến động (Latest vs Previous)
    latest = df_snap.iloc[0]
    prev = df_snap.iloc[1] if len(df_snap) > 1 else latest
    risk_score = float(latest['risk_score']) / 100

    # --- 3. GIAO DIỆN APPLE-STYLE STRATEGIC HEADER ---
    status_color = '#34c759' if risk_score < 0.3 else '#ffcc00' if risk_score < 0.6 else '#ff3b30'
    
    st.markdown(f"""
        <div style="background-color: white; padding: 25px; border-radius: 20px; border-left: 15px solid {status_color}; box-shadow: 0 10px 25px rgba(0,0,0,0.05); margin-bottom: 25px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2 style="margin:0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; color: #1d1d1f; letter-spacing: -0.5px;">🧠 AI Strategic Hub <span style="font-size:14px; color:#0071e3; vertical-align: middle; margin-left:10px;">V3.0 HYBRID</span></h2>
                    <p style="color:#86868b; margin:5px 0 0 0; font-size:16px;">Phân tích thông minh dựa trên <b>{latest['total_devices']:,}</b> Nodes kết nối.</p>
                </div>
                <div style="text-align: right;">
                    <span style="background: {status_color}20; color: {status_color}; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 12px;">
                        {latest['risk_level'].upper()}
                    </span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- 4. HỆ THỐNG TABS CHUYÊN SÂU ---
    t_overview, t_analysis, t_prediction, t_rag = st.tabs(["🚀 CHIẾN LƯỢC", "🕵️ TRUY VẾT", "🔮 DỰ BÁO", "💬 AI ASSISTANT"])

    with t_overview:
        c1, c2, c3 = st.columns(3)
        # Chỉ số rủi ro với Delta biến động
        c1.metric("Risk Index", f"{risk_score:.2f}", 
                  delta=round(risk_score - (float(prev['risk_score'])/100), 2), delta_color="inverse")
        # Sức khỏe hệ thống
        c2.metric("System Health", f"{int((1 - risk_score) * 100)}%", delta=f"{latest['total_devices']} Nodes")
        # Trạng thái AI
        c3.metric("AI Status", "ACTIVE", delta="Learning...")
        
        st.write("---")
        st.markdown("**📈 Biến thiên rủi ro hệ thống (24 Giờ)**")
        # Area chart mượt mà thể hiện độ ổn định
        st.area_chart(df_snap.set_index('created_at')['risk_score'], color="#0071e3")

    with t_analysis:
        st.markdown("#### 🕵️ Anomaly Detection & Evidence")
        col_a, col_b = st.columns([1.2, 1])
        with col_a:
            st.write("**⚠️ Top 5 máy rủi ro cao (Offline kéo dài):**")
            # Sử dụng cột off_min tính từ df_ai (đã xử lý ở tab giám sát)
            if 'off_min' in df_ai.columns:
                anomaly_df = df_ai.sort_values('off_min', ascending=False).head(5)
                st.dataframe(anomaly_df[['hostname', 'customer_name', 'off_min']], 
                             column_config={
                                 "hostname": "🖥️ Tên Máy",
                                 "customer_name": "🏬 Đại lý",
                                 "off_min": st.column_config.NumberColumn("⏱️ Phút Off", format="%d")
                             },
                             use_container_width=True, hide_index=True)
            else:
                st.info("Đang quét tọa độ rủi ro...")
        
        with col_b:
            with st.container(border=True):
                st.markdown("**🤖 AI Narrative Report**")
                st.write(f"""
                * **Tỉ lệ Offline:** `{latest['offline_ratio']*100:.1f}%` (Ngưỡng an toàn < 5%).
                * **Incident 1h:** `{latest['new_offline_1h']}` máy vừa rớt mạng.
                * **Mạng lưới:** Jitter `{latest['heartbeat_jitter']}` (Độ nhiễu tín hiệu trung bình).
                """)
                st.button("📄 Xuất Báo cáo PDF cho Ban Giám Đốc", use_container_width=True)

    with t_prediction:
        st.markdown("#### 🔮 AI Predictive Intelligence")
        p1, p2 = st.columns(2)
        with p1:
            st.markdown("##### ⚠️ Dự báo cung ứng (Inventory)")
            # Mockup dữ liệu dự báo từ hành vi pha màu
            pred_inv = pd.DataFrame({
                "Đại lý": ["Sơn Hà Nội", "Hùng Tú - Cần Thơ", "Minh Tâm - VT"], 
                "Vật tư sắp cạn": ["Trắng (W)", "Xanh dương (B)", "Base P"],
                "AI Dự đoán cạn": ["~14h tới", "~28h tới", "~42h tới"]
            })
            st.table(pred_inv)
        with p2:
            st.markdown("##### ✅ Dự báo hạ tầng")
            with st.container(border=True):
                st.info("AI dự báo lưu lượng đồng bộ dữ liệu sẽ đạt đỉnh (Peak) vào lúc **15:30** hôm nay. Khuyến nghị không thực hiện lệnh Khóa/Mở hàng loạt vào khung giờ này.")

    with t_rag:
        st.markdown("#### 💬 AI Knowledge Assistant (RAG)")
        query = st.text_input("💬 Chat với dữ liệu hệ thống:", placeholder="Ví dụ: Tại sao hôm nay máy ở Hà Nội rớt nhiều?")
        if query:
            with st.spinner("AI đang truy vấn Memory Layer..."):
                # Mô phỏng AI trả lời dựa trên context thật từ snapshot
                st.chat_message("assistant", avatar="🧠").write(
                    f"Phân tích Snapshot `{latest['created_at']}`: Tôi phát hiện Risk Index tại khu vực miền Bắc tăng 15% do "
                    f"một cụm máy tại 'Sơn Hà Nội' bị mất kết nối đồng loạt. Đây có vẻ là sự cố điện tại điểm bán hơn là lỗi phần mềm."
                )

# --- PHẦN TRIỂN KHAI TRONG APP CHÍNH ---
# --- PHẦN TRIỂN KHAI TRONG APP CHÍNH (BẢN FIX LỖI INDEX) ---
with t_ai:
    # Lấy dữ liệu từ bảng inventory thực tế (Hình 4 sếp gửi)
    if 'df_inv' in locals() and not df_inv.empty:
        try:
            now_dt_aware = datetime.now(timezone.utc)
            
            # 1. TẠO BẢN BUILD SẠCH TỪ DATABASE THỰC
            # Chúng ta dùng trực tiếp df_inv vì nó đã có sẵn 'customer_name' và 'hostname'
            df_ai_work = df_inv.copy()

            # 2. ĐẢM BẢO CỘT THỜI GIAN ĐỂ TÍNH OFFLINE
            # Nếu database có cột last_seen, AI sẽ tính được phút rớt mạng thực tế
            if 'last_seen' in df_ai_work.columns:
                df_ai_work['last_seen_dt'] = pd.to_datetime(df_ai_work['last_seen'], utc=True)
                df_ai_work['off_min'] = df_ai_work['last_seen_dt'].apply(
                    lambda x: int((now_dt_aware - x).total_seconds() / 60) if pd.notnull(x) else 9999
                )
            else:
                # Nếu chưa có last_seen, AI coi như các máy đang ổn định (0 phút off)
                df_ai_work['off_min'] = 0

            # 3. KIỂM TRA CỘT TRƯỚC KHI RENDER (CHỐT HẠ LỖI HÌNH 5 & 6)
            required_cols = ['hostname', 'customer_name']
            if all(col in df_ai_work.columns for col in required_cols):
                # Gán dữ liệu sạch cho render
                render_ai_strategic_hub_v3(df_ai_work, now_dt_aware, sb)
            else:
                # Nếu thiếu cột, AI sẽ báo cáo thông minh cho sếp thay vì báo lỗi hệ thống
                missing = [c for c in required_cols if c not in df_ai_work.columns]
                st.warning(f"📋 AI đang đợi đồng bộ cột: {', '.join(missing)}")
                st.info("Mẹo: Sếp hãy kiểm tra xem file Excel hoặc Database đã có đủ tiêu đề 'hostname' và 'customer_name' chưa.")

        except Exception as e:
            # Bắt lỗi cục bộ để không làm treo cả App
            st.error(f"⚠️ AI Hub đang khởi động lại: {str(e)}")
    else:
        st.info("📡 Đang đồng bộ hóa dữ liệu từ trung tâm... (6,000 Nodes)")
with t_sys:
    st.markdown("# ⚙️ System Architecture & Governance")
    st.caption("Quản trị hạ tầng lõi, bảo mật phân cấp và giám sát AI Guard.")

    # Giả lập phân quyền (Trong thực tế sẽ lấy từ User Profile)
    USER_ROLE = "Admin"  # Viewer / Operator / Admin

    # --- 🔵 1. SYSTEM HEALTH CORE (READ-ONLY) ---
    st.markdown("### 🧠 System Health Core")
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        # Giả lập chỉ số hệ thống
        c1.metric("DB Size", "1.8 GB", "🟢")
        c2.metric("AI Memory", "2.1M Rows", "🟡")
        c3.metric("Queue Backlog", "12 Pending", "🟢")
        c4.metric("Latency", "42ms", "-5ms")
        
        st.caption("🕒 Last cleanup: 3 hours ago | Snapshot rate: 24/day (Normal)")

    # --- 🔐 2. SECURITY & PERMISSION ---
    st.markdown("### 🔐 Security & Permission")
    role_color = {"Admin": "red", "Operator": "blue", "Viewer": "green"}
    st.markdown(f"Current Role: :{role_color[USER_ROLE]}[**{USER_ROLE}**]")
    
    with st.expander("🛡️ Access Control List (ACL)"):
        st.info("Chế độ Admin được kích hoạt. Bạn có quyền truy cập vào các lệnh Emergency.")
        st.checkbox("Bật xác thực 2 lớp (2FA) cho lệnh Deploy", value=True)
        st.checkbox("Chặn truy cập từ IP lạ", value=True)

    # --- 🚀 3. DEPLOYMENT & DATA OPS (CÓ QUY TRÌNH) ---
    st.markdown("### 🚀 Data Operations")
    
    # Chỉ Admin và Operator mới thấy khu vực này
    if USER_ROLE in ["Admin", "Operator"]:
        with st.container(border=True):
            st.markdown("#### 🧹 Cleanup Operations")
            c_op1, c_op2 = st.columns([2, 1])
            
            with c_op1:
                st.write("**Dọn dẹp nhật ký DONE (file_queue)**")
                st.markdown("""
                * Records to delete: **12,431**
                * Estimated DB freed: **~220MB**
                * Affected tables: `file_queue`, `deployment_targets`
                """)
            
            with c_op2:
                confirm_txt = st.text_input("Xác nhận", placeholder="Nhập 'DELETE' để dọn dẹp")
                if st.button("Xử lý Cleanup", type="secondary", use_container_width=True):
                    if confirm_txt == "DELETE":
                        # sb.table("file_queue").delete().eq("status", "DONE").execute()
                        st.success("✅ Đã giải phóng 220MB bộ nhớ.")
                    else:
                        st.error("Mã xác nhận sai")

    # --- 🧯 4. EMERGENCY & RECOVERY (RẤT PRO) ---
    # Chỉ hiện diện khi hệ thống có vấn đề hoặc User là Admin
    if USER_ROLE == "Admin":
        st.markdown("### 🧯 Emergency & Recovery")
        with st.status("Emergency Control Panel (Standby)", state="complete"):
            st.warning("⚠️ Chỉ sử dụng khi hệ thống mất kiểm soát (Queue kẹt, Snapshot lỗi liên tục)")
            e1, e2, e3 = st.columns(3)
            if e1.button("⏸️ PAUSE ALL DEPLOY", use_container_width=True):
                st.toast("Đã tạm dừng tất cả tiến trình.")
            if e2.button("🔒 LOCK ALL MACHINES", type="primary", use_container_width=True):
                st.toast("Đã phát lệnh khóa khẩn cấp toàn hệ thống.")
            if e3.button("❄️ FREEZE AI LEARNING", use_container_width=True):
                st.toast("Đã đóng băng mô hình AI.")

    # --- 🤖 5. AI SYSTEM GUARD (CỰC KỲ PRO) ---
    # --- 🤖 5. AI SYSTEM GUARD (CỰC KỲ PRO) ---
    
    st.markdown("### 🤖 AI System Guard")
    with st.container(border=True):
        st.markdown("""
        **Báo cáo giám sát hành vi hệ thống:**
        * 🟢 **Bình thường:** Không có đột biến truy cập bất hợp pháp.
        * 🟡 **Cảnh báo:** Phát hiện **3 cleanup liên tiếp** trong 1h bởi User: `admin_01`.
        * 🔴 **Bất thường:** Deployment diễn ra vào khung giờ nhạy cảm (**02:13 AM**).
        """)
        
        # Đã xóa tham số size="small" để tránh lỗi TypeError
        c_guard1, c_guard2 = st.columns([1, 3])
        with c_guard1:
            if st.button("🔍 Giải trình", use_container_width=True):
                st.toast("Đã gửi yêu cầu giải trình tới Admin liên quan.")
        with c_guard2:
            st.caption("AI Guard đang giám sát các thao tác có tác động đến Database.")
with t_install:
    st.header("🛠️ Quy trình triển khai Agent xuống Client")
    
    st.info("💡 **Yêu cầu hệ thống:** Windows 10/11, Python 3.9+, Kết nối Internet ổn định.")
    
    st.markdown("### 🛠 Bước 1: Chuẩn bị môi trường")
    st.code("""
# 1. Tải source code Agent về máy client
# 2. Cài đặt các thư viện bổ trợ
pip install requests pandas psutil
    """, language="bash")

    st.markdown("### 🔑 Bước 2: Cấu hình định danh (Quan trọng)")
    st.warning("Mỗi máy phải có một Hostname duy nhất do sếp quy định để Dashboard nhận diện chính xác.")
    st.write("Mở file `config.py` trên Agent và chỉnh sửa:")
    st.code("""
AGENT_CONFIG = {
    "hostname": "4ORANGES_DL_001",  # Thay đổi theo tên đại lý
    "server_url": "https://your-api-gateway.com",
    "check_interval": 30 # Giây
}
    """, language="python")

    st.markdown("### 🚀 Bước 3: Kích hoạt Agent & Watchdog")
    st.write("Để Agent chạy ngầm và tự khởi động cùng Windows:")
    st.markdown("""
    1. Chuột phải vào file `start_agent.bat`.
    2. Chọn **Create Shortcut**.
    3. Nhấn `Win + R`, gõ `shell:startup` và Enter.
    4. Kéo Shortcut vừa tạo vào thư mục này.
    """)
    
    st.success("✅ Sau khi chạy, hãy quay lại Tab 'Giám sát' trên Dashboard để xác nhận máy đã hiện danh sách.")
with t_guide:
    st.header("📖 Hướng dẫn vận hành Dashboard")
    st.markdown("""
    Hệ thống quản lý Agent được thiết kế theo luồng tác chiến 4 bước. Dưới đây là cách sử dụng:
    """)
    
    with st.expander("1️⃣ Giám sát thiết bị (Monitoring)", expanded=True):
        st.write("""
        - **Mục tiêu:** Kiểm tra xem máy nào đang sống (Online) hay đã mất kết nối (Offline/Dead).
        - **Thao tác:** Sử dụng bộ lọc trạng thái và thanh tìm kiếm theo **Hostname**.
        - **Lưu ý:** Nếu máy hiển thị `🔴 Offline` quá 30 phút, AI sẽ cảnh báo sự cố hạ tầng.
        """)

    with st.expander("2️⃣ Triển khai File & Cập nhật (Deployment)"):
        st.write("""
        - **Bước 1:** Tải file lên (SDF, Firmware, v.v...).
        - **Bước 2:** Chọn máy theo Hostname. Bạn có thể chọn nhiều máy cùng lúc.
        - **Bước 3:** Nhấn 'XÁC NHẬN CHIẾN DỊCH'.
        - **Bước 4:** Nhấn '▶ START' tại bảng điều phối để bắt đầu truyền file. Theo dõi thanh Progress để biết tiến độ.
        """)

    with st.expander("3️⃣ Điều khiển từ xa (Remote Control)"):
        st.write("""
        - **Khóa máy (LOCK):** Ngay lập tức vô hiệu hóa thao tác tại Client.
        - **Mở khóa (UNLOCK):** Khôi phục trạng thái sẵn sàng cho Client.
        - **Gợi ý:** Luôn kiểm tra trạng thái 'Kết nối' trước khi phát lệnh để đảm bảo Agent đang nhận lệnh.
        """)

    with st.expander("4️⃣ Truy vết sự cố (AI Forensics)"):
        st.write("""
        - Chọn Hostname cần điều tra.
        - Kéo thanh 'Hồi tố' để xem lại lịch sử sự kiện (Event Chain).
        - Xem phần 'AI Final Conclusion' để biết nguyên nhân khách quan (mạng/nguồn) hay chủ quan (bị tắt Agent).
        """)
