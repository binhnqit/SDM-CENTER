import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import base64
import zlib
import time

# --- CONFIG (Giữ nguyên chuẩn kết nối) ---
SUPABASE_URL = "https://glzdktdphoydqhofszvh.supabase.co"
SUPABASE_KEY = "sb_publishable_MCfri2GPc3dn-bIcx_XJ_A_RxgsF1YU"
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="4Oranges SDM Pro AI v3.6", layout="wide")

# --- DATA ENGINE ---
def load_all_data():
    try:
        dev_res = sb.table("devices").select("*").execute()
        cmd_res = sb.table("commands").select("*").order("created_at", desc=True).limit(20).execute()
        file_res = sb.table("file_queue").select("*").order("timestamp", desc=True).execute()
        
        df_d = pd.DataFrame(dev_res.data) if dev_res.data else pd.DataFrame()
        df_c = pd.DataFrame(cmd_res.data) if cmd_res.data else pd.DataFrame()
        df_f = pd.DataFrame(file_res.data) if file_res.data else pd.DataFrame()
        return df_d, df_c, df_f
    except Exception as e:
        st.error(f"Lỗi DB: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_devices, df_commands, df_files = load_all_data()

# --- MAIN DASHBOARD ---
st.title("🛡️ 4Oranges SDM AI - Hệ thống Quản trị 5.000+")

# 1. METRICS TỔNG QUAN (Từ image_4fa45c.png)
if not df_devices.empty:
    df_devices['last_seen_dt'] = pd.to_datetime(df_devices['last_seen'])
    now = datetime.now(df_devices['last_seen_dt'].dt.tz)
    df_devices['is_online'] = (now - df_devices['last_seen_dt']) < timedelta(minutes=2)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Tổng thiết bị", len(df_devices))
    m2.metric("Online", len(df_devices[df_devices['is_online'] == True]))
    m3.metric("CPU TB", f"{df_devices['cpu_usage'].mean():.1f}%")

# --- HỆ THỐNG TABS ĐẦY ĐỦ (KHÔNG BỎ CHỨC NĂNG) ---
t_monitor, t_control, t_file, t_summary, t_ai = st.tabs([
    "📊 GIÁM SÁT", "🎮 ĐIỀU KHIỂN", "📤 TRUYỀN FILE", "📜 TỔNG KẾT", "🧠 AI INSIGHT"
])

# --- TAB 1: GIÁM SÁT (Phục hồi từ image_4fa45c.png) ---
with t_monitor:
    st.subheader("📡 Trạng thái thiết bị Real-time")
    st.dataframe(
        df_devices[['machine_id', 'status', 'last_seen', 'cpu_usage', 'ram_usage', 'agent_version']],
        column_config={
            "cpu_usage": st.column_config.ProgressColumn("CPU (%)", min_value=0, max_value=100),
            "ram_usage": st.column_config.ProgressColumn("RAM (%)", min_value=0, max_value=100),
        },
        use_container_width=True, hide_index=True
    )

# --- TAB 2: ĐIỀU KHIỂN (Phục hồi từ image_4fa45c.png) ---
with t_control:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("🚀 Gửi lệnh tức thì")
        targets = st.multiselect("Chọn máy mục tiêu:", df_devices['machine_id'].tolist() if not df_devices.empty else [])
        action = st.radio("Lệnh thực thi:", ["LOCK", "UNLOCK"], horizontal=True)
        if st.button("Gửi lệnh", type="primary"):
            if targets:
                new_cmds = [{"machine_id": t, "command": action, "is_executed": False} for t in targets]
                sb.table("commands").insert(new_cmds).execute()
                st.success(f"Đã đẩy lệnh {action}!")
                time.sleep(1); st.rerun()
    with c2:
        st.subheader("🕒 Lịch sử lệnh gần đây")
        st.dataframe(df_commands[['machine_id', 'command', 'created_at']], hide_index=True, use_container_width=True)

# --- TAB 3: TRUYỀN FILE (Chuẩn Agent v10.4) ---
with t_file:
    st.subheader("📦 Đẩy dữ liệu công thức đa điểm")
    up_file = st.file_uploader("Chọn file .SDF chính thức:", type=['sdf'])
    f_targets = st.multiselect("Chọn máy nhận (Nhóm đại lý):", df_devices['machine_id'].tolist() if not df_devices.empty else [])
    
    if st.button("🔥 BẮT ĐẦU ĐỒNG BỘ"):
        if up_file and f_targets:
            encoded = base64.b64encode(zlib.compress(up_file.getvalue())).decode('utf-8')
            chunk_size = 30000
            chunks = [encoded[i:i+chunk_size] for i in range(0, len(encoded), chunk_size)]
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            
            payload = []
            for m in f_targets:
                for i, c in enumerate(chunks):
                    payload.append({
                        "machine_id": m, "file_name": up_file.name, "data_chunk": c,
                        "part_info": f"PART_{i+1}/{len(chunks)}", "timestamp": ts,
                        "target_path": r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Updates",
                        "status": "PENDING"
                    })
            sb.table("file_queue").insert(payload).execute()
            st.success(f"Đã gửi bộ file {up_file.name} tới {len(f_targets)} máy!")

# --- TAB 4: TỔNG KẾT (MỚI - THEO DÕI PENDING/DONE) ---
with t_summary:
    st.subheader("📜 Trạng thái cập nhật chi tiết")
    if not df_files.empty:
        # Nhóm theo timestamp và machine để xem tiến độ từng máy
        view_df = df_files.groupby(['machine_id', 'file_name', 'status', 'timestamp']).size().reset_index(name='parts_received')
        st.dataframe(view_df, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ DỌN DẸP LỊCH SỬ THÀNH CÔNG"):
            sb.table("file_queue").delete().eq("status", "DONE").execute()
            st.rerun()
    else:
        st.info("Chưa có dữ liệu truyền file.")

# --- TAB 5: AI INSIGHT (NÂNG CẤP) ---
with t_ai:
    st.header("🧠 4Oranges AI Analyst")
    if not df_devices.empty:
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            fig_status = px.pie(df_devices, names='status', title="Phân bổ trạng thái thiết bị", color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_status, use_container_width=True)
        with col_a2:
            st.markdown("### 💡 Khuyến nghị vận hành")
            done_files = len(df_files[df_files['status'] == 'DONE'])
            total_files = len(df_files) if len(df_files) > 0 else 1
            rate = (done_files / total_files) * 100
            
            st.write(f"Tỷ lệ hoàn thành truyền tải: **{rate:.1f}%**")
            if rate < 100:
                st.warning("AI nhắc nhở: Một số máy đại lý chưa hoàn thành tải file. Hãy nhắc họ mở Agent.")
            else:
                st.success("Hệ thống đồng bộ hoàn hảo.")
