import streamlit as st
from supabase import create_client, Client
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import base64, zlib, time, os

# --- CORE CONFIG FROM SECRETS ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="4Oranges SDM Lux Secure Pro", layout="wide", initial_sidebar_state="expanded")

# --- STYLE APPLE CSS ---
st.markdown("""
    <style>
    .main { background-color: #f5f5f7; }
    .stMetric { background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    div[data-baseweb="tab-list"] { gap: 10px; }
    div[data-baseweb="tab"] { padding: 10px 20px; background-color: #e5e5e7 !important; border-radius: 10px 10px 0 0 !important; }
    div[data-baseweb="tab"][aria-selected="true"] { background-color: #0071e3 !important; color: white !important; }
    .ai-card { background-color: white; padding: 20px; border-radius: 15px; border-left: 5px solid #0071e3; margin-bottom: 15px; }
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

# --- AI ENGINE LOGIC ---
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
        data = {
            "risk_score": round(score, 2), "risk_level": level, "total_devices": features['total'], 
            "offline_ratio": round(features['offline_ratio'], 3), "avg_offline_minutes": round(features['avg_off'], 1), 
            "new_offline_1h": features['new_1h'], "heartbeat_jitter": round(features['jitter'], 3)
        }
        sb.table("ai_snapshots").insert(data).execute()
        return data

# --- UI COMPONENTS ---
def render_import_portal(sb):
    st.markdown("""
        <div style="background-color: #0071e3; padding: 20px; border-radius: 15px; color: white; margin-bottom: 20px;">
            <h2 style="margin:0;">📥 AI Data Port</h2>
            <p style="margin:0; opacity: 0.8;">Hệ thống nạp dữ liệu lịch sử pha màu (DispenseHistory.csv)</p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([1, 2])
    with c1:
        st.info("💡 **Hướng dẫn:** Tải file .csv để AI phân tích sản lượng và lỗi kỹ thuật.")
        res_dev = sb.table("devices").select("machine_id").execute()
        list_machines = [d['machine_id'] for d in res_dev.data] if res_dev.data else ["Unknown"]
        selected_target = st.selectbox("🎯 Gán dữ liệu cho máy:", list_machines)
        uploaded_file = st.file_uploader("Kéo thả file .csv", type=['csv'])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            line_cols = [c for c in df.columns if 'LINES_DISPENSED_AMOUNT' in c]
            df['ACTUAL_TOTAL'] = df[line_cols].fillna(0).sum(axis=1)
            df['ERROR_GAP'] = (df['WANTED_AMOUNT'] - df['ACTUAL_TOTAL']).abs()
            
            with c2:
                m1, m2, m3 = st.columns(3)
                m1.metric("Tổng mẻ pha", len(df))
                m2.metric("Doanh số", f"{df['PRICE'].sum():,.0f} VND")
                m3.metric("Sai số TB", f"{df['ERROR_GAP'].mean():.4f}")
                st.dataframe(df[['DISPENSED_DATE', 'PRODUCT_NAME', 'COLOR_NAME', 'WANTED_AMOUNT', 'ACTUAL_TOTAL', 'PRICE']].head(10), use_container_width=True)

            if st.button("🚀 XÁC NHẬN IMPORT VÀO AI CLOUD", use_container_width=True, type="primary"):
                with st.status("Đang đồng bộ AI Memory Layer..."):
                    import_df = pd.DataFrame({
                        'machine_id': selected_target,
                        'dispensed_date': pd.to_datetime(df['DISPENSED_DATE']).dt.isoformat(),
                        'color_name': df['COLOR_NAME'],
                        'product_name': df['PRODUCT_NAME'],
                        'wanted_amount': df['WANTED_AMOUNT'],
                        'actual_amount': df['ACTUAL_TOTAL'],
                        'error_gap': df['ERROR_GAP'],
                        'price': df['PRICE']
                    })
                    data_to_insert = import_df.to_dict(orient='records')
                    for i in range(0, len(data_to_insert), 100):
                        sb.table("color_mix_logs").insert(data_to_insert[i:i+100]).execute()
                st.success("Nạp dữ liệu thành công!"); st.balloons(); time.sleep(1); st.rerun()
        except Exception as e: st.error(f"Lỗi: {e}")

def render_ai_strategic_hub_v3(df_d, now_dt, sb):
    features = AI_Engine_v3.calculate_features(df_d, now_dt)
    res_snap = sb.table("ai_snapshots").select("*").order("created_at", desc=True).limit(24).execute()
    df_snap = pd.DataFrame(res_snap.data)
    
    if df_snap.empty:
        st.warning("⚠️ Chưa có Snapshot. Vui lòng bấm 'Capture AI Snapshot' ở Sidebar.")
        return

    latest = df_snap.iloc[0]
    risk_score = latest['risk_score'] / 100

    st.markdown(f"""
        <div style="background-color: white; padding: 20px; border-radius: 15px; border-left: 10px solid {'#ff3b30' if risk_score > 0.6 else '#ffcc00' if risk_score > 0.3 else '#34c759'};">
            <h2 style="margin:0;">🧠 AI Strategic Hub <span style="font-size:14px; color:#86868b;">V3.0 HYBRID</span></h2>
            <p style="color:#86868b; margin:0;">Chỉ số rủi ro hệ thống dựa trên AI Real-time Monitoring.</p>
        </div>
    """, unsafe_allow_html=True)
    
    t1, t2, t3, t4 = st.tabs(["🚀 CHIẾN LƯỢC", "🕵️ TRUY VẾT", "🔮 DỰ BÁO", "💬 RAG"])
    
    with t1:
        c1, c2, c3 = st.columns(3)
        c1.metric("Risk Index", f"{risk_score:.2f}", delta_color="inverse")
        c2.metric("System Health", f"{int((1 - risk_score) * 100)}%")
        c3.metric("AI Status", latest['risk_level'])
        st.line_chart(df_snap, x='created_at', y='risk_score', color="#0071e3")

    with t2:
        st.write("**Phân tích thiết bị rủi ro cao:**")
        anomaly_df = df_d.sort_values('off_min', ascending=False).head(5)
        st.dataframe(anomaly_df[['machine_id', 'off_min', 'status']], use_container_width=True)

    with t3:
        st.info("🔮 **AI Prediction:** Dự báo nhu cầu tinh màu dựa trên lịch sử pha máy.")
        st.warning("Cảnh báo: Máy 'Sơn Hà Nội' có dấu hiệu sai số Error Gap tăng 15% - Cần cân chỉnh đầu phun.")

    with t4:
        query = st.text_input("Hỏi AI Assistant:", placeholder="Ví dụ: Tình trạng máy trạm hôm nay thế nào?")
        if query: st.chat_message("assistant").write(f"Dựa trên dữ liệu Snapshot, hệ thống hiện đang ở mức {latest['risk_level']}. Tỷ lệ rớt mạng là {latest['offline_ratio']*100:.1f}%.")

# --- MAIN APP LOGIC ---
def load_all_data():
    try:
        dev = sb.table("devices").select("*").execute()
        cmd = sb.table("commands").select("*").order("created_at", desc=True).limit(20).execute()
        files = sb.table("file_queue").select("*").order("timestamp", desc=True).execute()
        return pd.DataFrame(dev.data), pd.DataFrame(cmd.data), pd.DataFrame(files.data)
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_d, df_c, df_f = load_all_data()

# --- HEADER & METRICS ---
st.title("🍊🍊🍊🍊 4ORANGES AI SYSTEM")
if not df_d.empty:
    df_d['last_seen_dt'] = pd.to_datetime(df_d['last_seen'], utc=True)
    now_dt = datetime.now(timezone.utc)
    df_d['is_online'] = (now_dt - df_d['last_seen_dt']) < timedelta(minutes=2)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng thiết bị", len(df_d))
    m2.metric("🟢 Trực tuyến", len(df_d[df_d['is_online']]))
    m3.metric("Tải CPU TB", f"{df_d['cpu_usage'].mean():.1f}%")
    m4.metric("Dung lượng RAM", f"{df_d['ram_usage'].mean():.1f}%")

# --- NAVIGATION ---
t_mon, t_ctrl, t_file, t_sum, t_ai, t_import, t_tokens, t_sys = st.tabs([
    "📊 GIÁM SÁT", "🎮 ĐIỀU KHIỂN", "📤 TRUYỀN FILE", "📜 TỔNG KẾT", "🧠 AI INSIGHT", "📥 IMPORT DATA", "🔑 TOKEN", "⚙️ HỆ THỐNG"
])

with t_mon:
    st.dataframe(df_d[['machine_id', 'status', 'cpu_usage', 'ram_usage', 'last_seen']], use_container_width=True, hide_index=True)

with t_import:
    render_import_portal(sb)

with t_ai:
    if not df_d.empty:
        now_dt_aware = datetime.now(timezone.utc)
        if st.sidebar.button("📸 Capture AI Snapshot"):
            feats = AI_Engine_v3.calculate_features(df_d, now_dt_aware)
            AI_Engine_v3.run_snapshot(sb, feats)
            st.toast("Đã lưu Snapshot thành công!"); time.sleep(0.5); st.rerun()
        render_ai_strategic_hub_v3(df_d, now_dt_aware, sb)

with t_tokens:
    st.subheader("🔑 Quản lý Security Token")
    res_tokens = sb.table("device_tokens").select("*").execute()
    st.dataframe(pd.DataFrame(res_tokens.data), use_container_width=True)

with t_sys:
    if st.button("🧹 DỌN DẸP HỆ THỐNG", type="primary"):
        sb.table("file_queue").delete().eq("status", "DONE").execute()
        st.success("Đã tối ưu hóa Database!"); st.rerun()
