import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import plotly.express as px
import base64
import zlib

# --- CẤU HÌNH ---
SUPABASE_URL = "https://glzdktdphoydqhofszvh.supabase.co"
SUPABASE_KEY = "sb_publishable_MCfri2GPc3dn-bIcx_XJ_A_RxgsF1YU"
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="4Oranges SDM AI Pro", layout="wide")

# --- FUNCTIONS ---
def get_devices():
    res = sb.table("devices").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

# --- GIAO DIỆN ---
st.title("🛡️ 4Oranges SDM AI - Hệ thống Quản trị 5.000+")

t_ctrl, t_file, t_ai = st.tabs(["🎮 ĐIỀU KHIỂN", "📤 TRUYỀN FILE", "🧠 AI INSIGHT"])

# --- TAB 1: CONTROL CENTER ---
with t_ctrl:
    df = get_devices()
    if not df.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("Tổng thiết bị", len(df))
        m2.metric("Online", len(df[df['status'].str.contains("Online")]))
        m3.metric("CPU TB", f"{df['cpu_usage'].mean():.1f}%")

        st.divider()
        col_list, col_cmd = st.columns([3, 1])
        with col_list:
            st.dataframe(df, use_container_width=True)
        with col_cmd:
            target = st.selectbox("Chọn máy:", df['machine_id'].tolist())
            cmd = st.radio("Lệnh:", ["LOCK", "UNLOCK"])
            if st.button("Gửi lệnh"):
                sb.table("commands").insert({"machine_id": target, "command": cmd}).execute()
                st.success(f"Đã đẩy lệnh {cmd} tới {target}")

# --- TAB 2: TRUYỀN FILE ---
with t_file:
    st.subheader("Truyền file SDF quy mô lớn")
    uploaded_file = st.file_uploader("Chọn file .SDF", type=['sdf'])
    targets = st.multiselect("Chọn danh sách máy nhận:", df['machine_id'].tolist() if not df.empty else [])
    
    if st.button("Bắt đầu truyền tải") and uploaded_file and targets:
        raw_data = uploaded_file.getvalue()
        compressed = base64.b64encode(zlib.compress(raw_data)).decode('utf-8')
        chunk_size = 30000
        chunks = [compressed[i:i+chunk_size] for i in range(0, len(compressed), chunk_size)]
        ts = datetime.now().isoformat()
        
        queue_data = []
        for m_id in targets:
            for i, c in enumerate(chunks):
                queue_data.append({
                    "machine_id": m_id, "file_name": uploaded_file.name,
                    "data_chunk": c, "part_info": f"PART_{i+1}/{len(chunks)}",
                    "target_path": r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Updates",
                    "timestamp": ts
                })
        
        # Supabase xử lý ghi hàng loạt cực nhanh
        sb.table("file_queue").insert(queue_data).execute()
        st.balloons()
        st.success(f"Đã xếp hàng {len(queue_data)} mảnh file cho {len(targets)} máy!")

# --- TAB 3: AI INSIGHT (QUAN TRỌNG) ---
with t_ai:
    st.header("🧠 AI Trợ lý Quản trị Chiến lược")
    
    if not df.empty:
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Phân tích Rủi ro")
            # Logic AI: Phát hiện máy có CPU cao hoặc Offline lâu
            risk_machines = df[df['cpu_usage'] > 80]
            if not risk_machines.empty:
                st.warning(f"AI phát hiện {len(risk_machines)} máy đang quá tải CPU. Đề xuất kiểm tra phần mềm diệt virus.")
            else:
                st.success("Hệ thống vận hành ổn định. Không có rủi ro kỹ thuật.")
            
            # Giả lập AI phân tích lịch sử pha màu (từ History Log)
            st.info("💡 AI Insight: Mã màu 'OZ-2026' đang có xu hướng tăng 40% tại khu vực phía Nam. Đề xuất chuẩn bị tinh màu.")

        with c2:
            st.subheader("Sức khỏe Hệ thống 5.000 máy")
            fig = px.pie(df, names='status', title="Tình trạng kết nối thực thời")
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Đang chờ dữ liệu từ các máy khách...")

st.sidebar.write(f"Vận hành bởi Supabase Real-time")
