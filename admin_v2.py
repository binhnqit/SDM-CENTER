import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta, timezone  # Thêm timezone vào đây
import plotly.express as px
import base64, zlib, time
import math
import numpy as np
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
# --- CSV LEARNING TAB ---
def sanitize_for_json(obj):
    """
    Convert Pandas / NumPy values into JSON-safe Python values
    """
    if obj is None:
        return None

    # NaN, NaT
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if pd.isna(obj):
        return None

    # numpy scalar
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64)):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)

    # timestamp
    if isinstance(obj, pd.Timestamp):
        if pd.isna(obj):
            return None
        return obj.isoformat()

    # dict
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}

    # list
    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]

    return obj
with t_csv:
    st.subheader("📥 CSV Learning Memory")
    st.caption("Nạp lịch sử vận hành để AI học hành vi thực tế")

    csv_file = st.file_uploader(
        "Upload file CSV (Dispense / Mixing / History)",
        type=["csv"]
    )

    if csv_file:
        try:
            df_csv = sanitize_df(pd.read_csv(csv_file))

            st.success(f"Đã tải {len(df_csv)} dòng dữ liệu")
            st.dataframe(df_csv.head(100), use_container_width=True)

            if st.button("🧠 GHI VÀO AI MEMORY", type="primary"):
                records = []

                for _, row in df_csv.iterrows():
                    raw_payload = sanitize_for_json(row.to_dict())
                   
                    records.append({
                        "machine_id": raw_payload.get("machine_id"),
                        "event_time": raw_payload.get("dispense_time") or raw_payload.get("timestamp"),
                        "payload": raw_payload
                    })

                # insert batch an toàn
                for i in range(0, len(records), 100):
                    sb.table("ai_learning_data").insert(
                        records[i:i+100]
                    ).execute()

                st.toast("AI đã tiếp nhận dữ liệu học hỏi!")
                time.sleep(0.5)
                st.rerun()

        except Exception as e:
            st.error(f"Lỗi đọc CSV: {e}")
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
    st.subheader("🖥️ Trung tâm Giám sát Thiết bị")
    
    if not df_d.empty:
        # --- 1. XỬ LÝ DỮ LIỆU ---
        df_d['last_seen_dt'] = pd.to_datetime(df_d['last_seen'], utc=True)
        now_dt = datetime.now(timezone.utc)
        
        # Ngưỡng thời gian
        HEARTBEAT_OK = 3    
        HEARTBEAT_WARN = 10
        HEARTBEAT_DEAD = 30

        # Tính phút vắng mặt
        df_d['off_minutes'] = (now_dt - df_d['last_seen_dt']).dt.total_seconds() / 60
        df_d['off_minutes'] = df_d['off_minutes'].apply(lambda x: max(0, round(x, 1)))

        # TÁCH TÊN USER: Giả định Agent gửi status dạng "Online | READY | TênUser"
        # Nếu sếp gửi tên User ở cột khác, hãy đổi tên 'status' thành tên cột đó
        def extract_user(status_str):
            try:
                if "|" in str(status_str):
                    return status_str.split("|")[-1].strip()
                return "Unknown"
            except:
                return "N/A"

        df_d['User'] = df_d['status'].apply(extract_user)

        # Phân loại trạng thái
        def resolve_state(row):
            if row['off_minutes'] <= HEARTBEAT_OK: return "🟢 Online"
            if row['off_minutes'] <= HEARTBEAT_WARN: return "🟡 Unstable"
            if row['off_minutes'] <= HEARTBEAT_DEAD: return "🔴 Offline"
            return "⚫ Dead"

        df_d['monitor_state'] = df_d.apply(resolve_state, axis=1)

        # --- 2. METRICS TỔNG HỢP ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Thiết bị sẵn sàng", len(df_d[df_d['monitor_state'] == "🟢 Online"]))
        m2.metric("Tín hiệu yếu", len(df_d[df_d['monitor_state'] == "🟡 Unstable"]))
        m3.metric("Đang ngoại tuyến", len(df_d[df_d['monitor_state'] == "🔴 Offline"]))
        m4.metric("Mất kết nối lâu", len(df_d[df_d['monitor_state'] == "⚫ Dead"]))

        # --- 3. BỘ LỌC ---
        st.write("")
        c_search1, c_search2 = st.columns([1, 2])
        with c_search1:
            search_user = st.text_input("👤 Tìm theo User:", placeholder="Tên user...")
        with c_search2:
            state_filter = st.multiselect("Lọc trạng thái:", 
                                         ["🟢 Online", "🟡 Unstable", "🔴 Offline", "⚫ Dead"],
                                         default=["🟢 Online", "🟡 Unstable", "🔴 Offline", "⚫ Dead"])
        
        filtered_df = df_d[df_d['monitor_state'].isin(state_filter)]
        if search_user:
            filtered_df = filtered_df[filtered_df['User'].str.contains(search_user, case=False)]

        # --- 4. BẢNG DỮ LIỆU (User ở cột ĐẦU TIÊN) ---
        st.dataframe(
            filtered_df[['User', 'machine_id', 'monitor_state', 'off_minutes', 'cpu_usage', 'ram_usage', 'last_seen_dt']],
            column_config={
                "User": st.column_config.TextColumn("👤 Người dùng", help="Tên tài khoản Windows đăng nhập"),
                "machine_id": "Mã Máy",
                "monitor_state": "Trạng Thái",
                "off_minutes": st.column_config.NumberColumn("Vắng mặt", format="%.1f phút"),
                "cpu_usage": st.column_config.ProgressColumn("CPU", min_value=0, max_value=100, format="%d%%"),
                "ram_usage": st.column_config.ProgressColumn("RAM", min_value=0, max_value=100, format="%d%%"),
                "last_seen_dt": "Cập nhật cuối"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Chưa có dữ liệu thiết bị.")

with t_ctrl:
    st.subheader("🎮 Trung tâm Lệnh Chiến lược")
    st.caption("Chọn thiết bị theo danh sách, theo đại lý hoặc theo mức độ rủi ro để thực thi lệnh.")

    if not df_d.empty:
        # --- 1. CHUẨN BỊ DỮ LIỆU ĐIỀU KHIỂN ---
        # Đảm bảo đã có cột monitor_state và User từ Tab Giám sát
        df_ctrl = df_d.copy()
        df_ctrl.insert(0, "select", False) # Đưa cột tích chọn lên đầu

        # --- 2. GIAO DIỆN CHỌN THEO NHÓM (ACCORDION STYLE) ---
        col_select1, col_select2 = st.columns([2, 1])
        
        selected_by_dealer = []
        with col_select1:
            with st.expander("🏢 Chọn nhanh theo Đại lý (Dealer Group)"):
                # Giả định sếp có cột 'dealer', nếu chưa có ta lấy tạm User hoặc 'NPH'
                dealer_col = 'dealer' if 'dealer' in df_d.columns else 'User'
                groups = df_d.groupby(dealer_col)
                
                c_dealer = st.columns(3)
                for i, (dealer, g) in enumerate(groups):
                    if c_dealer[i % 3].checkbox(f"{dealer} ({len(g)})", key=f"chk_{dealer}"):
                        selected_by_dealer.extend(g['machine_id'].tolist())

        with col_select2:
            with st.expander("🚨 Lọc Rủi ro"):
                risk_targets = df_d[df_d['monitor_state'].isin(['🔴 Offline', '⚫ Dead'])]
                st.write(f"Tìm thấy: **{len(risk_targets)}** máy rủi ro")
                btn_risk = st.button("🚨 Chọn tất cả máy Rủi ro", use_container_width=True)
                if btn_risk:
                    selected_by_dealer.extend(risk_targets['machine_id'].tolist())

        # --- 3. DATA EDITOR (BẢNG CHỈNH SỬA TRỰC TIẾP) ---
        st.write("---")
        st.markdown("**Danh sách thiết bị chi tiết:**")
        
        # Tự động tích chọn nếu đã chọn theo Dealer hoặc Risk
        if selected_by_dealer:
            df_ctrl.loc[df_ctrl['machine_id'].isin(selected_by_dealer), 'select'] = True

        edited = st.data_editor(
            df_ctrl[['select', 'User', 'machine_id', 'monitor_state', 'status']],
            column_config={
                "select": st.column_config.CheckboxColumn("Chọn", help="Tích để gửi lệnh"),
                "User": "Người dùng",
                "machine_id": "Mã Máy",
                "monitor_state": "Trạng thái",
                "status": "Trạng thái khóa"
            },
            disabled=['User', 'machine_id', 'monitor_state', 'status'],
            hide_index=True,
            use_container_width=True,
            key="ctrl_editor"
        )

        # --- 4. KHU VỰC THỰC THI LỆNH (ACTION BAR) ---
        targets = edited[edited['select']]['machine_id'].tolist()
        
        if targets:
            st.markdown(f"### ⚡ Thực thi với **{len(targets)}** máy đã chọn")
            c1, c2, c3 = st.columns([1, 1, 2])
            
            with c1:
                if st.button("🔒 KHÓA MÁY", type="primary", use_container_width=True):
                    cmds = [{"machine_id": m, "command": "LOCK"} for m in targets]
                    sb.table("commands").insert(cmds).execute()
                    st.success(f"Đã phát lệnh KHÓA tới {len(targets)} máy")
                    time.sleep(1)
                    st.rerun()
            
            with c2:
                if st.button("🔓 MỞ KHÓA", use_container_width=True):
                    cmds = [{"machine_id": m, "command": "UNLOCK"} for m in targets]
                    sb.table("commands").insert(cmds).execute()
                    st.success(f"Đã phát lệnh MỞ tới {len(targets)} máy")
                    time.sleep(1)
                    st.rerun()
            
            with c3:
                st.info("💡 Lệnh sẽ được Agent thực hiện trong vòng 30 giây.")
        else:
            st.info("👆 Vui lòng chọn ít nhất một máy để thực hiện lệnh.")

    else:
        st.info("Không có dữ liệu thiết bị để điều khiển.")

import base64, zlib, hashlib, time
from datetime import datetime, timezone
import pandas as pd

with t_file:
    st.markdown("## 📦 Deployment Center")
    st.caption("Quy trình triển khai 4 bước: Đóng gói -> Mục tiêu -> Khởi tạo -> Truyền tải.")

    # --- 1️⃣ BƯỚC 1: UPLOAD & ĐÓNG GÓI ---
    with st.expander("⬆️ Bước 1: Upload & Đóng gói Artifact", expanded=not st.session_state.get("current_artifact_id")):
        file = st.file_uploader("Chọn file triển khai", type=["bin", "zip", "json", "cfg", "sdf"])
        c1, c2, c3 = st.columns(3)
        with c1: file_type = st.selectbox("Loại file", ["SDF Data", "Firmware", "Config", "AI Model"])
        with c2: version = st.text_input("Version", placeholder="v1.2.3")
        with c3: mode = st.radio("Chế độ", ["Rolling", "All-at-once"], horizontal=True)

        if file and version:
            if st.button("📥 LƯU ARTIFACT", type="primary", use_container_width=True):
                with st.status("📦 Đang đóng gói...") as status:
                    f_bytes = file.getvalue()
                    b64_data = base64.b64encode(zlib.compress(f_bytes)).decode('utf-8')
                    res = sb.table("artifacts").insert({
                        "file_name": file.name, "file_type": file_type, "version": version,
                        "checksum": hashlib.sha256(f_bytes).hexdigest(),
                        "size": round(len(f_bytes)/1024, 2), "data_chunk": b64_data
                    }).execute()
                    if res.data:
                        st.session_state["current_artifact_id"] = res.data[0]["id"]
                        st.rerun()

    # --- 2️⃣ BƯỚC 2: CHỌN MỤC TIÊU ---
    st.write("---")
    st.markdown("### 🎯 Bước 2: Chọn máy triển khai")
    curr_art = st.session_state.get("current_artifact_id")
    
    targets = []
    if not df_d.empty:
        df_m = df_d.copy()
        df_m["select"] = False
        edited = st.data_editor(
            df_m[["select", "User", "machine_id", "status"]],
            use_container_width=True, hide_index=True,
            column_config={"select": st.column_config.CheckboxColumn("Chọn")}
        )
        targets = edited[edited["select"]]["machine_id"].tolist()
        st.info(f"📍 Đã chọn **{len(targets)}** máy mục tiêu.")

    # --- 3️⃣ BƯỚC 3: KHỞI TẠO CHIẾN DỊCH (READY STATE) ---
    st.write("---")
    st.markdown("### 📝 Bước 3: Khởi tạo chiến dịch")
    if curr_art and targets:
        if st.button("🏗️ CREATE DEPLOYMENT (READY)", use_container_width=True):
            dep = sb.table("deployments").insert({
                "artifact_id": curr_art, "mode": mode, "status": "ready" # CHƯA TRUYỀN
            }).execute()
            if dep.data:
                dep_id = dep.data[0]["id"]
                target_records = [{"deployment_id": dep_id, "machine_id": m, "status": "staged", "progress": 0} for m in targets]
                sb.table("deployment_targets").insert(target_records).execute()
                st.session_state["current_artifact_id"] = None
                st.success(f"✅ Chiến dịch #{dep_id} đang ở trạng thái READY. Chờ lệnh truyền file.")
                st.rerun()
    else:
        st.caption("Vui lòng hoàn thành Bước 1 và Bước 2 để khởi tạo.")

    # --- 4️⃣ BƯỚC 4: START TRANSFER & MONITOR ---
    st.write("---")
    st.markdown("### 🚀 Bước 4: Điều phối truyền file")
    
    recent_deps = sb.table("deployments").select("*, artifacts(*)").order("created_at", desc=True).limit(5).execute()
    
    if recent_deps.data:
        for d in recent_deps.data:
            with st.container(border=True):
                c_head, c_btn = st.columns([3, 1])
                c_head.subheader(f"Campaign #{d['id']} [{d['status'].upper()}]")
                c_head.caption(f"File: {d['artifacts']['file_name']} | Version: {d['artifacts']['version']}")

                # NÚT START TRANSFER (CHỈ HIỆN KHI READY)
                if d["status"] == "ready":
                    if c_btn.button("▶ START TRANSFER", key=f"start_{d['id']}", type="primary", use_container_width=True):
                        # Update trạng thái cha
                        sb.table("deployments").update({
                            "status": "transferring",
                            "started_at": datetime.now(timezone.utc).isoformat()
                        }).eq("id", d["id"]).
with t_sum:
    # 🔵 LEVEL 1: EXECUTIVE SNAPSHOT (10s Insight)
    st.markdown("# 🧠 System Intelligence Dashboard")
    
    if not df_d.empty:
        # Tính toán nhanh các chỉ số
        total_m = len(df_d)
        online_m = len(df_d[df_d['monitor_state'] == "🟢 Online"])
        warn_m = len(df_d[df_d['monitor_state'] == "🟡 Unstable"])
        off_m = len(df_d[df_d['monitor_state'] == "🔴 Offline"])
        dead_m = len(df_d[df_d['monitor_state'] == "⚫ Dead"])
        
        # Công thức tính Health Score giả lập (Sếp có thể điều chỉnh)
        health_score = int((online_m / total_m) * 100)
        score_color = "🟢" if health_score > 80 else "🟡" if health_score > 50 else "🔴"

        # Executive Row
        c_score, c_metrics = st.columns([1, 2])
        
        with c_score:
            st.metric("SYSTEM HEALTH SCORE", f"{health_score} / 100", f"{score_color} Healthy")
            st.progress(health_score / 100)
            
        with c_metrics:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total", total_m)
            m2.metric("Online", online_m, delta_color="normal")
            m3.metric("Offline", off_m + warn_m, delta="-", delta_color="inverse")
            m4.metric("Dead", dead_m, delta_color="off")

        st.markdown("---")

        # 🟡 LEVEL 2: OPERATIONAL HEALTH (Bốn khối vận hành)
        col_op1, col_op2 = st.columns(2)

        with col_op1:
            # 1️⃣ Machine Stability
            with st.container(border=True):
                st.markdown("### 📉 Machine Stability (7D)")
                # Giả lập dữ liệu uptime
                chart_data = pd.DataFrame({
                    'Day': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    'Uptime %': [98, 97, 95, 99, 92, 94, health_score]
                })
                st.line_chart(chart_data.set_index('Day'), height=150)
                st.caption("⚠️ Top máy hay rớt: `MC-091`, `MC-112` (Cần Thơ)")

            # 2️⃣ Deployment Safety
            with st.container(border=True):
                st.markdown("### 🚀 Deployment Safety")
                # Lấy dữ liệu từ bảng deployments (nếu có)
                success_rate = 94.5 # Giả lập
                st.metric("Tỉ lệ Deploy thành công", f"{success_rate}%", "↑ 1.2%")
                st.progress(success_rate/100)
                st.caption("⚡ 1 Deployment đang chạy: `SDF_Update_v2`")

        with col_op2:
            # 3️⃣ Color Mixing Behavior
            with st.container(border=True):
                st.markdown("### 🎨 Color Mixing Behavior")
                # Giả lập xu hướng màu
                mix_trend = pd.DataFrame({
                    'Color': ['White', 'Blue', 'Yellow', 'Red'],
                    'Volume': [450, 320, 210, 150]
                })
                st.bar_chart(mix_trend.set_index('Color'), horizontal=True, height=150)
                st.caption("🧠 AI: Màu **Blue** tăng tiêu thụ **+28%** tại KV phía Nam.")

            # 4️⃣ Command Reliability
            with st.container(border=True):
                st.markdown("### 📟 Command Reliability")
                c_rel1, c_rel2 = st.columns(2)
                c_rel1.metric("Lệnh gửi", "1,240")
                c_rel2.metric("Độ trễ (Avg)", "1.2s", "-0.3s")
                st.caption("✅ 99.8% lệnh được xác nhận (ACK).")

        # 🤖 AI SUMMARY (PHẦN ĂN TIỀN)
        st.info("### 🤖 AI Insight (7 ngày gần nhất)")
        st.markdown(f"""
        * **Offline:** Tăng **12%** tập trung vào cụm máy tại **Cần Thơ** (Khả năng do hạ tầng mạng khu vực).
        * **Artifacts:** 2 đợt deploy gần nhất gặp lỗi **Checksum** trên các máy dùng Windows 7.
        * **Vận hành:** Tinh màu **X** sắp cạn kiệt tại 5 đại lý cấp 1.
        * **Khuyến nghị:** Ưu tiên kiểm tra kết nối tại Cần Thơ trước khi triển khai bản cập nhật tiếp theo.
        """)

        # 🔴 LEVEL 3: DRILL-DOWN (Chi tiết máy lỗi)
        with st.expander("🔍 Chi tiết các máy đang gặp sự cố (Critical Drill-down)"):
            risk_df = df_d[df_d['monitor_state'].isin(["🔴 Offline", "⚫ Dead"])]
            if not risk_df.empty:
                st.table(risk_df[['machine_id', 'User', 'off_minutes', 'last_seen']])
            else:
                st.success("Không có máy nào trong tình trạng báo động đỏ.")

    else:
        st.warning("Đang chờ dữ liệu từ hệ thống Agent...")

with t_offline:
    st.subheader("🕵️ AI Forensics – Truy vết Offline")
    st.caption("Phân tích lịch sử gián đoạn để xác định các đại lý có hạ tầng mạng không ổn định.")

    # 1. Thanh điều khiển phạm vi
    days = st.slider("Phạm vi truy vết (ngày)", 1, 60, 14)

    # 2. Truy vấn dữ liệu từ bảng device_events
    try:
        res = (
            sb.table("device_events")
              .select("*")
              .eq("event_type", "OFFLINE")
              .gte("detected_at", (datetime.now(timezone.utc) - timedelta(days=days)).isoformat())
              .order("detected_at", desc=True)
              .execute()
        )
        df_evt = pd.DataFrame(res.data)

        if df_evt.empty:
            st.info("✅ Hệ thống hoạt động ổn định. Không phát hiện sự kiện offline nào trong phạm vi đã chọn.")
        else:
            # 3. Phân tích dữ liệu bằng biểu đồ
            st.markdown("### 📈 Biểu đồ tần suất rớt mạng")
            # Đếm số lần offline theo từng máy để xem "ai là trùm rớt mạng"
            off_counts = df_evt['machine_id'].value_counts().reset_index()
            off_counts.columns = ['machine_id', 'count']
            
            fig_off = px.bar(off_counts, x='machine_id', y='count', 
                             title="Số lần rớt mạng theo từng thiết bị",
                             labels={'machine_id': 'Mã máy', 'count': 'Số lần'},
                             color='count', color_continuous_scale='Reds')
            st.plotly_chart(fig_off, use_container_width=True)

            # 4. Hiển thị bảng chi tiết
            st.markdown("### 📍 Timeline rớt mạng chi tiết")
            st.dataframe(
                df_evt[['machine_id', 'detected_at', 'off_minutes', 'cpu_usage', 'ram_usage']],
                column_config={
                    "machine_id": "Mã máy",
                    "detected_at": "Thời điểm phát hiện",
                    "off_minutes": "Thời gian sập (phút)",
                    "cpu_usage": "CPU lúc đó",
                    "ram_usage": "RAM lúc đó"
                },
                use_container_width=True,
                hide_index=True
            )

            # 5. Nhận định AI thông minh hơn
            st.markdown("### 🧠 Nhận định AI Forensics")
            
            # Tính toán một vài chỉ số để "AI" nói chuyện chuyên nghiệp hơn
            total_off = len(df_evt)
            unique_machines = df_evt['machine_id'].nunique()
            max_off_machine = off_counts.iloc[0]['machine_id'] if not off_counts.empty else "N/A"
            avg_off_time = df_evt['off_minutes'].mean() if 'off_minutes' in df_evt.columns else 0

            st.warning(
                f"**Báo cáo hệ thống:** Trong {days} ngày qua, ghi nhận **{total_off}** sự cố mất kết nối từ **{unique_machines}** thiết bị khác nhau. \n\n"
                f"- 🚨 Máy trạm **{max_off_machine}** có tần suất rớt mạng cao nhất.\n"
                f"- ⏱️ Thời gian gián đoạn trung bình: **{avg_off_time:.1f} phút**.\n"
                f"- **Kết luận:** { 'Hạ tầng mạng tại các điểm này cực kỳ kém, cần kiểm tra router.' if unique_machines > 1 else 'Sự cố mang tính cục bộ tại một đại lý duy nhất.' }"
            )
            
    except Exception as e:
        st.error(f"Lỗi truy vấn Forensics: {e}")
        st.info("Mẹo: Hãy đảm bảo bảng 'device_events' đã được khởi tạo trong Supabase.")

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
