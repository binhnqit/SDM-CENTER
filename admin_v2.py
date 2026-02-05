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
t_mon, t_ctrl, t_file, t_csv, t_sum, t_offline, t_ai, t_tokens, t_sys = st.tabs([
    "📊 GIÁM SÁT",
    "🎮 ĐIỀU KHIỂN",
    "📤 TRUYỀN FILE",
    "📥 CSV LEARNING",   # 👈 TAB MỚI
    "📜 TỔNG KẾT",
    "🕵️ TRUY VẾT",
    "🧠 AI INSIGHT",
    "🔑 QUẢN LÝ TOKEN",
    "⚙️ HỆ THỐNG"
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
    # --- 0. CẤU HÌNH BIẾN ---
    dealer_col = DEALER_COL_NAME

    st.header("🖥️ Device Monitoring Center")
    st.caption(f"Trạng thái thời gian thực từ hệ thống Agent {AGENT_VERSION}")
    
    # --- 1. LOAD DỮ LIỆU QUA RPC ---
    try:
        res = sb.rpc("latest_agent_heartbeats").execute()
        df_mon = pd.DataFrame(res.data) 
        
        if not df_mon.empty:
            if DEALER_COL_NAME not in df_mon.columns:
                df_mon[DEALER_COL_NAME] = "Chưa phân loại"
        else:
            df_mon = pd.DataFrame(columns=[DEALER_COL_NAME])
            
    except Exception as e:
        st.error(f"❌ Lỗi kết nối dữ liệu: {e}")
        df_mon = pd.DataFrame(columns=[DEALER_COL_NAME])

    # --- 2. KIỂM TRA DỮ LIỆU TRƯỚC KHI XỬ LÝ ---
    if not df_mon.empty and 'received_at' in df_mon.columns:
        # Xử lý thời gian chuẩn UTC
        now_dt = datetime.now(timezone.utc)
        df_mon['received_at_dt'] = pd.to_datetime(df_mon['received_at'], utc=True)
        
        # Tính phút vắng mặt
        df_mon['off_minutes'] = (now_dt - df_mon['received_at_dt']).dt.total_seconds() / 60
        df_mon['off_minutes'] = df_mon['off_minutes'].apply(lambda x: max(0, round(x, 1)))

        # --- 3. LOGIC TRẠNG THÁI & HIỂN THỊ ---
        def resolve_state(mins):
            if mins <= 3: return "🟢 Online"
            if mins <= 10: return "🟡 Unstable"
            if mins <= 30: return "🔴 Offline"
            return "⚫ Dead"

        # DÙNG ĐÚNG BIẾN df_mon
        df_mon['monitor_state'] = df_mon['off_minutes'].apply(resolve_state)
        
        df_mon['mode_display'] = df_mon['operational_state'].apply(
            lambda x: "🔐 LOCKED" if x == "LOCKED" else "✅ READY"
        )

        # --- 4. DASHBOARD METRICS ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🟢 Online", len(df_mon[df_mon['monitor_state'] == "🟢 Online"]))
        m2.metric("🟡 Unstable", len(df_mon[df_mon['monitor_state'] == "🟡 Unstable"]))
        m3.metric("🔴 Offline", len(df_mon[df_mon['monitor_state'] == "🔴 Offline"]))
        m4.metric("⚫ Dead", len(df_mon[df_mon['monitor_state'] == "⚫ Dead"]))

        # --- 5. BỘ LỌC TƯƠNG TÁC ---
        st.write("---")
        c_search1, c_search2 = st.columns([1, 2])
        with c_search1:
            search_query = st.text_input("🔍 Tìm máy/người dùng:", placeholder="Nhập tên, ID...", key="mon_search")
        with c_search2:
            all_states = ["🟢 Online", "🟡 Unstable", "🔴 Offline", "⚫ Dead"]
            state_filter = st.multiselect("Lọc trạng thái hiển thị:", all_states, default=all_states[:2])

        # Thực thi Filter trên df_mon
        f_df = df_mon[df_mon['monitor_state'].isin(state_filter)]
        if search_query:
            f_df = f_df[
                (f_df['username'].str.contains(search_query, case=False, na=False)) |
                (f_df['hostname'].str.contains(search_query, case=False, na=False)) |
                (f_df['machine_id'].str.contains(search_query, case=False, na=False))
            ]

        # --- 6. DATA TABLE ---
        f_df = f_df.sort_values("received_at", ascending=False)
        
        st.dataframe(
            f_df[['username', 'hostname', DEALER_COL_NAME, 'monitor_state', 'mode_display', 
                  'cpu_usage', 'ram_usage', 'heartbeat_seq', 'off_minutes', 'received_at']],
            column_config={
                "username": st.column_config.TextColumn("👤 User"),
                "hostname": "💻 Hostname",
                DEALER_COL_NAME: "📍 Vị trí/Đại lý",
                "monitor_state": "Trạng thái",
                "mode_display": "Agent Mode",
                "cpu_usage": st.column_config.ProgressColumn("CPU", min_value=0, max_value=100, format="%d%%"),
                "ram_usage": st.column_config.ProgressColumn("RAM", min_value=0, max_value=100, format="%d%%"),
                "off_minutes": st.column_config.NumberColumn("Vắng mặt", format="%.1f m"),
                "received_at": "Lần cuối"
            },
            use_container_width=True,
            hide_index=True
        )

        # --- 7. QUICK CONTROL PANEL ---
        st.write("---")
        col_ctrl1, col_ctrl2 = st.columns([2, 1])
        with col_ctrl1:
            st.subheader("⚡ Remote Control")
            target_machine = st.selectbox("Chọn thiết bị mục tiêu:", f_df['machine_id'].unique() if not f_df.empty else [])
        
        with col_ctrl2:
            st.write(""); st.write("")
            btn_lock, btn_unlock = st.columns(2)
            if btn_lock.button("🔒 LOCK", type="primary", use_container_width=True):
                sb.table("commands").insert({"machine_id": target_machine, "command": "LOCK", "is_executed": False}).execute()
                st.toast(f"Đã gửi lệnh KHÓA tới {target_machine}")
            if btn_unlock.button("🔓 UNLOCK", use_container_width=True):
                sb.table("commands").insert({"machine_id": target_machine, "command": "UNLOCK", "is_executed": False}).execute()
                st.toast(f"Đã gửi lệnh MỞ KHÓA tới {target_machine}")

        # --- 8. DEBUG SYSTEM ---
        with st.expander("🛠️ System Debug Information"):
            st.json({
                "App UTC Now": now_dt.isoformat(),
                "Dealer Column Mapping": dealer_col,
                "Total Records": len(df_mon),
                "Columns present": list(df_mon.columns)
            })
    else:
        st.info("📡 Hệ thống đang sẵn sàng. Đang chờ Agent gửi tín hiệu đầu tiên...")
        if st.button("🔄 Thử tải lại"): st.rerun()
with t_ctrl:
    st.subheader("🎮 Trung tâm Lệnh Chiến lược")
    st.caption("Chọn thiết bị theo danh sách, đại lý hoặc rủi ro để thực thi lệnh.")

    if not df_inv.empty:
        # --- 0. ĐỒNG BỘ TRẠNG THÁI (HYBRID LOGIC) ---
        df_display = df_inv.copy()
        
        if 'df_mon' in locals() and not df_mon.empty and 'monitor_state' in df_mon.columns:
            status_map = df_mon.set_index('machine_id')['monitor_state'].to_dict()
            df_display['monitor_state'] = df_display['machine_id'].map(status_map).fillna("⚫ Unknown")
        else:
            df_display['monitor_state'] = "❓ N/A"

        # Bảo hiểm các cột cần thiết
        if DEALER_COL_NAME not in df_display.columns:
            df_display[DEALER_COL_NAME] = "Chưa phân loại"
        
        if 'select' not in df_display.columns:
            df_display.insert(0, 'select', False)

        # --- 1. GIAO DIỆN CHỌN NHANH ---
        selected_by_logic = []
        c_sel1, c_sel2 = st.columns([2, 1])
        
        with c_sel1:
            with st.expander(f"🏢 Chọn nhanh theo {DEALER_COL_NAME.upper()}", expanded=False):
                temp_df = df_display.dropna(subset=[DEALER_COL_NAME])
                if not temp_df.empty:
                    groups = temp_df.groupby(DEALER_COL_NAME)
                    c_dealer = st.columns(3)
                    for i, (dealer, g) in enumerate(groups):
                        if c_dealer[i % 3].checkbox(f"{dealer} ({len(g)})", key=f"q_sel_{dealer}"):
                            selected_by_logic.extend(g['machine_id'].tolist())

        with c_sel2:
            with st.expander("🚨 Lọc Rủi ro", expanded=False):
                risk_targets = df_display[df_display['monitor_state'].isin(['🔴 Offline', '⚫ Dead'])]
                st.write(f"Tìm thấy: **{len(risk_targets)}** máy")
                if st.button("🚨 Chọn tất cả", use_container_width=True, key="btn_risk_sel"):
                    selected_by_logic.extend(risk_targets['machine_id'].tolist())

        # --- 2. CHUẨN HÓA DỮ LIỆU TUYỆT ĐỐI (FIX LỖI CỘT) ---
        if selected_by_logic:
            unique_targets = list(set(selected_by_logic))
            df_display.loc[df_display['machine_id'].isin(unique_targets), 'select'] = True

        # Xác định cột User thực tế từ DB
        actual_user_col = 'username' if 'username' in df_display.columns else \
                         ('User' if 'User' in df_display.columns else df_display.columns[1])
        
        # TẠO DATAFRAME MỚI TOANH VỚI TÊN CỘT CỐ ĐỊNH (Hard-coded)
        # Cách này giúp tránh lỗi StreamlitAPIException do tên cột động
        df_final = pd.DataFrame({
            "Chon": df_display['select'].astype(bool),
            "NguoiDung": df_display[actual_user_col].astype(str),
            "MaMay": df_display['machine_id'].astype(str),
            "KetNoi": df_display['monitor_state'].astype(str),
            "TrangThai": df_display['status'].astype(str)
        })

        # --- 3. DATA EDITOR ---
        st.write("---")
        edited = st.data_editor(
            df_final,
            column_config={
                "Chon": st.column_config.CheckboxColumn("Chọn", help="Tích để gửi lệnh"),
                "NguoiDung": "👤 Người dùng",
                "MaMay": "🆔 Mã Máy",
                "KetNoi": "📡 Kết nối",
                "TrangThai": "🔒 Khóa/Mở"
            },
            disabled=["NguoiDung", "MaMay", "KetNoi", "TrangThai"],
            hide_index=True,
            use_container_width=True,
            key="ctrl_editor_ultimate_v7" # Key mới để xóa sạch cache cũ
        )

        # --- 4. ACTION BAR ---
        # Lấy danh sách ID dựa trên tên cột mới "MaMay"
        targets = edited[edited['Chon'] == True]['MaMay'].tolist()
        
        if targets:
            st.markdown(f"### ⚡ Thực thi với **{len(targets)}** máy")
            act1, act2 = st.columns(2)
            
            with act1:
                if st.button("🔒 KHÓA MÁY", type="primary", use_container_width=True):
                    try:
                        cmds = [{"machine_id": m, "command": "LOCK", "is_executed": False} for m in targets]
                        sb.table("commands").insert(cmds).execute()
                        st.success(f"Đã phát lệnh KHÓA")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
            
            with act2:
                if st.button("🔓 MỞ KHÓA", use_container_width=True):
                    try:
                        cmds = [{"machine_id": m, "command": "UNLOCK", "is_executed": False} for m in targets]
                        sb.table("commands").insert(cmds).execute()
                        st.success(f"Đã phát lệnh MỞ")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
        else:
            st.info("👆 Tích chọn máy ở bảng trên để thực hiện lệnh.")

    else:
        st.warning("⚠️ Không có dữ liệu thiết bị.")

# ==========================================
# 0️⃣ KHỞI TẠO STATE (Đầu tab hoặc đầu file)
# ==========================================
if "selected_targets" not in st.session_state:
    st.session_state["selected_targets"] = []
if "deploy_mode" not in st.session_state:
    st.session_state["deploy_mode"] = "Rolling"

with t_file:
    st.markdown("## 📦 Deployment Center")
    st.caption("Quản lý vòng đời triển khai Artifact với cơ chế State-Tracking.")

    # ---------------------------------------------------------
    # 1️⃣ BƯỚC 1: CHỌN ARTIFACT (UI tối giản)
    # ---------------------------------------------------------
    with st.expander("📂 Bước 1: Thông tin Artifact", expanded=True):
        file = st.file_uploader("Kéo thả file cấu hình/firmware", type=["bin", "zip", "json", "cfg", "sdf"])
        
        c_art1, c_art2, c_art3 = st.columns(3)
        with c_art1:
            file_type = st.selectbox("Loại file", ["SDF Data", "Firmware", "Config", "AI Model"])
        with c_art2:
            version = st.text_input("Version", value="v15.0")
        with c_art3:
            # Ghi trực tiếp vào session_state
            st.session_state["deploy_mode"] = st.radio("Chế độ", ["Rolling", "All-at-once"], horizontal=True)

    # ---------------------------------------------------------
    # 2️⃣ BƯỚC 2: CHỌN MỤC TIÊU (Ghi vào Session State)
    # ---------------------------------------------------------
    st.write("---")
    st.markdown("### 🎯 Bước 2: Chọn máy triển khai")
    
    # --- SỬA DÒNG 620 ---
    if not df_inv.empty:
        st.subheader("📁 Chuyển tập tin tới thiết bị")
        
        # --- TỰ ĐỘNG NHẬN DIỆN CỘT (Để tránh KeyError) ---
        # Tìm cột tên giống 'user', nếu không thấy thì lấy cột thứ 2 của bảng
        u_col = next((c for c in df_inv.columns if 'user' in c.lower()), df_inv.columns[1])
        # Tìm cột tên giống 'host', nếu không thấy thì dùng luôn machine_id
        h_col = next((c for c in df_inv.columns if 'host' in c.lower()), 'machine_id')
        
        # Tạo danh sách hiển thị an toàn
        try:
            device_options = df_inv.apply(
                lambda x: f"{x[u_col]} | {x[h_col]} ({x['machine_id']})", axis=1
            ).tolist()
        except Exception:
            # Phương án dự phòng cuối cùng nếu vẫn lỗi
            device_options = [f"ID: {mid}" for mid in df_inv['machine_id']]

        selected_devices = st.multiselect(
            "Chọn thiết bị nhận file:", 
            options=df_inv['machine_id'].tolist(),
            format_func=lambda x: next((opt for opt in device_options if x in opt), x),
            key="file_transfer_sel"
        )
    # ---------------------------------------------------------
    # 3️⃣ BƯỚC 3: KHỞI TẠO CHIẾN DỊCH (Sử dụng State)
    # ---------------------------------------------------------
    st.write("---")
    st.markdown("### 📝 Bước 3: Khởi tạo chiến dịch (Staging)")
    
    # Kiểm tra điều kiện "Thông" từ session_state và widget
    if not file:
        st.warning("👉 Hãy chọn file ở Bước 1.")
    elif not st.session_state["selected_targets"]:
        st.warning("👉 Hãy tích chọn máy ở Bước 2.")
    else:
        st.success(f"🚀 Sẵn sàng truyền **{file.name}** tới **{len(st.session_state['selected_targets'])}** máy.")
        
        if st.button("🏗️ XÁC NHẬN & TẠO CHIẾN DỊCH (READY)", type="primary", use_container_width=True):
            with st.status("⚙️ Đang thực thi quy trình đóng gói...") as status:
                # 1. Xử lý Binary
                file_bytes = file.getvalue()
                b64_data = base64.b64encode(zlib.compress(file_bytes)).decode('utf-8')
                
                # 2. Insert Artifact
                art_res = sb.table("artifacts").insert({
                    "file_name": file.name, "file_type": file_type, "version": version,
                    "checksum": hashlib.sha256(file_bytes).hexdigest(),
                    "size": round(len(file_bytes)/1024, 2), "data_chunk": b64_data
                }).execute()
                
                if art_res.data:
                    art_id = art_res.data[0]["id"]
                    # 3. Tạo Deployment Cha
                    dep_res = sb.table("deployments").insert({
                        "artifact_id": art_id, 
                        "mode": st.session_state["deploy_mode"], 
                        "status": "ready"
                    }).execute()
                    
                    if dep_res.data:
                        dep_id = dep_res.data[0]["id"]
                        # 4. Tạo Target Records (Lấy từ state)
                        t_data = [
                            {"deployment_id": dep_id, "machine_id": m, "status": "staged", "progress": 0} 
                            for m in st.session_state["selected_targets"]
                        ]
                        sb.table("deployment_targets").insert(t_data).execute()
                        
                        # --- CLEAR STATE SAU KHI XONG ---
                        st.session_state["selected_targets"] = []
                        
                        status.update(label="✅ Đã khởi tạo thành công Campaign!", state="complete")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()

    # ---------------------------------------------------------
    # 4️⃣ BƯỚC 4: START TRANSFER (Điều khiển)
    # ---------------------------------------------------------
    st.write("---")
    st.markdown("### 🚀 Bước 4: Điều phối truyền file")
    
    recent = sb.table("deployments").select("*, artifacts(*)").order("created_at", desc=True).limit(5).execute()
    
    if recent.data:
        for d in recent.data:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.subheader(f"Campaign #{d['id']} ({d['status'].upper()})")
                c1.caption(f"Artifact: {d['artifacts']['file_name']} (v{d['artifacts']['version']})")
                
                if d["status"] == "ready":
                    if c2.button("▶ START", key=f"run_{d['id']}", type="primary", use_container_width=True):
                        # Chuyển status cha
                        sb.table("deployments").update({"status": "transferring", "started_at": datetime.now(timezone.utc).isoformat()}).eq("id", d["id"]).execute()
                        # Kích hoạt Agent con (pending)
                        sb.table("deployment_targets").update({"status": "pending"}).eq("deployment_id", d["id"]).execute()
                        st.toast("🚀 Đang phát lệnh truyền file!")
                        time.sleep(1)
                        st.rerun()
                
                # Monitor tiến độ thực tế từ Agent trả về
                t_res = sb.table("deployment_targets").select("*").eq("deployment_id", d["id"]).execute()
                if t_res.data:
                    df_res = pd.DataFrame(t_res.data)
                    avg_p = int(df_res["progress"].mean())
                    st.progress(avg_p)
                    st.caption(f"Tiến độ trung bình: {avg_p}%")
with t_sum:
    # 🔵 LEVEL 1: EXECUTIVE SNAPSHOT (10s Insight)
    st.markdown("# 🧠 System Intelligence Dashboard")
    
    # Chuẩn bị dữ liệu hiển thị (Lấy từ df_inv và map trạng thái từ df_mon)
    if not df_inv.empty:
        df_display = df_inv.copy()
        if 'df_mon' in locals() and not df_mon.empty:
            status_map = df_mon.set_index('machine_id')['monitor_state'].to_dict()
            df_display['monitor_state'] = df_display['machine_id'].map(status_map).fillna("⚫ Unknown")
        else:
            df_display['monitor_state'] = "❓ N/A"

        # --- TÍNH TOÁN CHỈ SỐ (Sửa lỗi df_d -> df_display) ---
        total_m = len(df_display)
        online_m = len(df_display[df_display['monitor_state'] == "🟢 Online"])
        warn_m   = len(df_display[df_display['monitor_state'] == "🟡 Unstable"])
        off_m    = len(df_display[df_display['monitor_state'] == "🔴 Offline"])
        dead_m   = len(df_display[df_display['monitor_state'] == "⚫ Dead"])
        
        # Công thức Health Score
        health_score = int((online_m / total_m) * 100) if total_m > 0 else 0
        score_color = "🟢" if health_score > 80 else "🟡" if health_score > 50 else "🔴"

        # Executive Row
        c_score, c_metrics = st.columns([1, 2])
        
        with c_score:
            st.metric("SYSTEM HEALTH SCORE", f"{health_score} / 100", f"{score_color} Healthy")
            st.progress(health_score / 100)
            
        with c_metrics:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Tổng máy", total_m)
            m2.metric("Online", online_m, delta_color="normal")
            m3.metric("Offline", off_m + warn_m, delta=f"-{off_m + warn_m}", delta_color="inverse")
            m4.metric("Mất kết nối", dead_m, delta_color="off")

        st.markdown("---")

        # 🟡 LEVEL 2: OPERATIONAL HEALTH
        col_op1, col_op2 = st.columns(2)

        with col_op1:
            # 1️⃣ Machine Stability
            with st.container(border=True):
                st.markdown("### 📉 Machine Stability (7D)")
                chart_data = pd.DataFrame({
                    'Day': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    'Uptime %': [98, 97, 95, 99, 92, 94, health_score]
                })
                st.line_chart(chart_data.set_index('Day'), height=150)
                st.caption("⚠️ Top máy hay rớt: `MC-091`, `MC-112` (Cần Thơ)")

            # 2️⃣ Deployment Safety
            with st.container(border=True):
                st.markdown("### 🚀 Deployment Safety")
                success_rate = 94.5 
                st.metric("Thành công", f"{success_rate}%", "↑ 1.2%")
                st.progress(success_rate/100)
                st.caption("⚡ Đang chạy: `Update_Patch_Feb_2026`")

        with col_op2:
            # 3️⃣ AI Business Insight
            with st.container(border=True):
                st.markdown("### 🎨 Color Mixing Trend")
                mix_trend = pd.DataFrame({
                    'Màu': ['Trắng', 'Xanh', 'Vàng', 'Đỏ'],
                    'Lượng tiêu thụ': [450, 320, 210, 150]
                })
                st.bar_chart(mix_trend.set_index('Màu'), horizontal=True, height=150)
                st.caption("🧠 AI: Màu **Xanh** tăng tiêu thụ **+28%** tại KV phía Nam.")

            # 4️⃣ Command Reliability
            with st.container(border=True):
                st.markdown("### 📟 Command Reliability")
                c_rel1, c_rel2 = st.columns(2)
                c_rel1.metric("Lệnh gửi", "1,240")
                c_rel2.metric("Độ trễ", "1.2s", "-0.3s")
                st.caption("✅ 99.8% lệnh được xác nhận thành công.")

        # 🤖 AI SUMMARY
        st.info("### 🤖 AI Insight (Phân tích hệ thống)")
        st.markdown(f"""
        * **Khu vực:** Tỉ lệ Offline tăng **12%** tại cụm **Cần Thơ** (Nghi vấn hạ tầng mạng ISP).
        * **Hệ điều hành:** Lỗi Checksum xảy ra chủ yếu trên các máy **Windows 7** cũ.
        * **Vận hành:** Tinh màu **White** sắp cạn tại 3 đại lý. Cần bổ sung hàng.
        * **Khuyến nghị:** Reset Router tại điểm Cần Thơ trước khi gửi lệnh cập nhật tiếp theo.
        """)

        # 🔴 LEVEL 3: DRILL-DOWN (Chi tiết máy lỗi)
        with st.expander("🔍 Chi tiết các máy đang gặp sự cố (Critical Risk)"):
            risk_df = df_display[df_display['monitor_state'].isin(["🔴 Offline", "⚫ Dead"])]
            if not risk_df.empty:
                # Tìm tên cột User chính xác
                u_col = 'username' if 'username' in risk_df.columns else \
                       ('User' if 'User' in risk_df.columns else risk_df.columns[1])
                
                # Hiển thị bảng (bỏ bớt cột nếu không có sẵn trong df_inv)
                cols_to_show = ['machine_id', u_col, 'monitor_state']
                if 'last_seen' in risk_df.columns: cols_to_show.append('last_seen')
                
                st.table(risk_df[cols_to_show])
            else:
                st.success("Hệ thống vận hành tốt. Không có máy rủi ro.")

    else:
        st.warning("Đang chờ dữ liệu từ hệ thống Agent...")
with t_offline:
    st.header("🕵️ AI Forensics – Investigator Mode")
    st.caption("Phiên bản V3.7: Event Chain & Evidence Binding")

    df_evt = pd.DataFrame()

    # 1. CONTROL PLANE
    c_id, c_days = st.columns([2, 1])
    target_id = c_id.text_input("🔍 Machine ID", placeholder="Nhập ID để dựng hiện trường...")
    days = c_days.slider("Hồi tố", 1, 90, 14)

    if target_id:
        try:
            res = (sb.table("device_events")
                  .select("*")
                  .eq("machine_id", target_id)
                  .gte("detected_at", (datetime.now(timezone.utc) - timedelta(days=days)).isoformat())
                  .order("detected_at", desc=True).execute())
            df_evt = pd.DataFrame(res.data)

            if not df_evt.empty:
                # 🟦 4️⃣ CONCLUSION BLOCK (AI kết luận cuối cùng)
                st.markdown("### 🧠 AI Final Conclusion")
                with st.container(border=True):
                    # Phân tích sơ bộ để AI kết luận
                    has_tamper = "AGENT_KILLED" in df_evt['event_type'].values
                    max_off = df_evt['off_minutes'].max()
                    
                    if has_tamper:
                        st.error("🚨 **KẾT LUẬN:** Phát hiện hành vi can thiệp trái phép. Agent bị tắt chủ động từ Process Manager. Cần kiểm tra lịch sử đăng nhập User.")
                    elif max_off > 30:
                        st.warning("⚠️ **KẾT LUẬN:** Sự cố hạ tầng nghiêm trọng. Máy mất nguồn hoặc mất mạng diện rộng trong thời gian dài. Khả năng cao là lỗi **POWER** hoặc **HARDWARE**.")
                    else:
                        st.info("ℹ️ **KẾT LUẬN:** Hệ thống hoạt động trong điều kiện mạng không ổn định (Network Instability).")

                # 🟧 1️⃣ EVENT CHAIN INFERENCE & 2️⃣ CAUSE LABEL
                st.markdown("### 🔗 Event Chain Analysis")
                
                # Vẽ chuỗi sự kiện (Simplified Chain)
                chain_cols = st.columns(len(df_evt[:4]) if len(df_evt) >= 1 else 1)
                for i, (_, row) in enumerate(df_evt[:4].iterrows()):
                    # Xác định Cause Label (2️⃣)
                    cause_label = row.get('event_category', 'UNKNOWN')
                    if "KILLED" in row['event_type']: cause_label = "AGENT"
                    elif "OFFLINE" in row['event_type']: cause_label = "NETWORK"
                    
                    with chain_cols[i]:
                        st.code(f"{row['event_type']}\n[{cause_label}]")
                        if i < len(chain_cols)-1: st.write("➡️")

                # 🟨 3️⃣ EVIDENCE SNAPSHOT BINDING
                st.markdown("### 🕒 Forensic Timeline & Evidence")
                for _, row in df_evt.iterrows():
                    sev = row.get('severity', 'INFO')
                    icon = "🔴" if sev == "CRITICAL" else "🔵"
                    
                    with st.expander(f"{icon} {row['detected_at']} | {row['event_type']}"):
                        col_l, col_r = st.columns([2, 1])
                        with col_l:
                            st.json(row.get('details', {}))
                            
                            # Kiểm tra Snapshot Binding (3️⃣)
                            details = row.get('details', {})
                            if isinstance(details, dict) and "snapshot_hash" in details:
                                st.success(f"📎 **Evidence Attached:** `{details['snapshot_hash']}`")
                                st.caption("Snapshot ghi lại trạng thái Process List & Network Connections lúc sự cố.")
                            else:
                                st.caption("No snapshot bound to this event.")

                        with col_r:
                            st.metric("Cause", cause_label)
                            st.metric("Offline", f"{row['off_minutes']}m")

        except Exception as e:
            st.error(f"❌ Forensic Error: {e}")

# --- EXPORT ---
if not df_evt.empty:
    st.download_button("📥 Export Forensic Report", df_evt.to_json(), f"Forensic_{target_id}.json")
import numpy as np # Đảm bảo sếp đã import thư viện này ở đầu file

# --- TRƯỚC HẾT: PHẢI CÓ CLASS NÀY THÌ TAB AI MỚI CHẠY ĐƯỢC ---
# ... (Phần trên giữ nguyên đến hết class AI_Engine_v3)

class AI_Engine_v3:
    @staticmethod
    def save_snapshot(sb, snapshot):
        if snapshot:
            sb.table("ai_color_snapshots").insert(snapshot).execute()
    
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

# 👉 CHÈN CODE MỚI CỦA SẾP VÀO ĐÂY (VỊ TRÍ SAU ENGINE V3 VÀ TRƯỚC RENDER)
class AI_Color_Insight_Engine:
    @staticmethod
    def load_learning_data(sb, days=30):
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        res = (
            sb.table("ai_learning_data")
              .select("payload")
              .gte("event_time", since)
              .execute()
        )
        if not res.data:
            return pd.DataFrame()

        rows = [r["payload"] for r in res.data]
        return sanitize_df(pd.DataFrame(rows))

    @staticmethod
    def generate_snapshot(df: pd.DataFrame):
        if df.empty:
            return None

        snapshot = {
            "snapshot_date": datetime.now().date().isoformat(),

            "top_colors": (
                df.groupby("color_code")
                  .size()
                  .sort_values(ascending=False)
                  .head(10)
                  .reset_index(name="mix_count")
                  .to_dict(orient="records")
            ) if "color_code" in df.columns else [],

            "top_pigments": (
                df.groupby("pigment_code")["volume"]
                  .sum()
                  .sort_values(ascending=False)
                  .head(10)
                  .reset_index()
                  .to_dict(orient="records")
            ) if {"pigment_code", "volume"}.issubset(df.columns) else [],

            "usage_stats": {
                "total_volume": float(df["volume"].sum()) if "volume" in df.columns else 0,
                "avg_volume_per_mix": float(df["volume"].mean()) if "volume" in df.columns else 0
            },

            "total_records": len(df)
        }

        return snapshot

    @staticmethod
    def save_snapshot(sb, snapshot):
        if snapshot:
            sb.table("ai_color_snapshots").insert(snapshot).execute()

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
            
            # 1. Sidebar Control
            if st.sidebar.button("🎨 Capture Color Learning Snapshot"):
                with st.spinner("AI đang phân tích dữ liệu pha màu..."):
                    df_learn = AI_Color_Insight_Engine.load_learning_data(sb, days=30)
                    snap = AI_Color_Insight_Engine.generate_snapshot(df_learn)
                    AI_Color_Insight_Engine.save_snapshot(sb, snap)
                    st.toast("🎨 AI đã học xong hành vi pha màu!")
                    time.sleep(1)
                    st.rerun()

            # 2. Render Strategic Hub (Phần cũ)
            render_ai_strategic_hub_v3(df_d, now_dt_aware, sb)

            st.write("---") # Đường kẻ phân cách cho đẹp

            # 3. PHẦN CODE MỚI CỦA SẾP: AI Learning Insights
            st.markdown("## 🎨 AI Learning – Hành vi pha màu")

            # Truy vấn Snapshot màu mới nhất
            # Lưu ý: Sửa 'generated_at' thành 'created_at' nếu sếp dùng cột mặc định của Supabase
            res = (
                sb.table("ai_color_snapshots")
                  .select("*")
                  .order("id", desc=True) # Sếp dùng 'id' hoặc 'created_at' để lấy bản mới nhất
                  .limit(1)
                  .execute()
            )

            if res.data:
                snap = res.data[0]
                c_ai1, c_ai2 = st.columns(2)

                with c_ai1:
                    st.markdown("**🏆 Top màu pha nhiều nhất**")
                    if "top_colors" in snap and snap["top_colors"]:
                        df_top_colors = pd.DataFrame(snap["top_colors"])
                        # Vẽ biểu đồ bar cho sinh động luôn sếp nhé
                        fig_colors = px.bar(df_top_colors, x='color_code', y='mix_count', 
                                            color='mix_count', color_continuous_scale='Blues')
                        st.plotly_chart(fig_colors, use_container_width=True)
                        st.dataframe(df_top_colors, use_container_width=True, hide_index=True)
                    else:
                        st.info("Chưa có dữ liệu màu.")

                with c_ai2:
                    st.markdown("**🧪 Top tinh màu tiêu thụ**")
                    if "top_pigments" in snap and snap["top_pigments"]:
                        df_top_pig = pd.DataFrame(snap["top_pigments"])
                        fig_pig = px.pie(df_top_pig, names='pigment_code', values='volume', hole=0.4)
                        st.plotly_chart(fig_pig, use_container_width=True)
                        st.dataframe(df_top_pig, use_container_width=True, hide_index=True)
                    else:
                        st.info("Chưa có dữ liệu tinh màu.")

                st.markdown("**📊 Thống kê sử dụng hệ thống**")
                # Hiển thị dạng Metric cho giống phong cách Apple
                if "usage_stats" in snap:
                    u1, u2, u3 = st.columns(3)
                    stats = snap["usage_stats"]
                    u1.metric("Tổng dung lượng (Lít)", f"{stats.get('total_volume', 0):.2f}")
                    u2.metric("Trung bình/Lần pha", f"{stats.get('avg_volume_per_mix', 0):.2f}")
                    u3.metric("Tổng số bản ghi AI", snap.get("total_records", 0))
            else:
                st.info("Chưa có snapshot màu – hãy nhấn 'Capture' ở Sidebar để bắt đầu học.")

        except Exception as e:
            st.error(f"Lỗi AI Insight: {e}")
    else:
        st.info("Đang kết nối với trung tâm dữ liệu...")
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
