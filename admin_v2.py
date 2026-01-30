# --- GIỮ NGUYÊN TOÀN BỘ PHẦN IMPORT VÀ LOGIN CỦA SẾP ---
import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import base64, zlib, time

SUPABASE_URL = "https://glzdktdphoydqhofszvh.supabase.co"
SUPABASE_KEY = "sb_publishable_MCfri2GPc3dn-bIcx_XJ_A_RxgsF1YU"
ADMIN_PASSWORD = "Qb1100589373@" 
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="4Oranges SDM Lux Secure Pro", layout="wide", initial_sidebar_state="expanded")

# --- STYLE APPLE CSS (Giữ nguyên của sếp) ---
st.markdown("<style>...</style>", unsafe_allow_html=True) 

# --- LOGIN LOGIC (Giữ nguyên của sếp) ---
# ... (Phần code login sếp giữ nguyên nhé)

# --- TRANG CHÍNH ---
def load_all_data():
    try:
        dev = sb.table("devices").select("*").execute()
        cmd = sb.table("commands").select("*").order("created_at", desc=True).limit(20).execute()
        files = sb.table("file_queue").select("*").order("timestamp", desc=True).execute()
        return pd.DataFrame(dev.data), pd.DataFrame(cmd.data), pd.DataFrame(files.data)
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_d, df_c, df_f = load_all_data()

# --- CÁC TABS CHIẾN LƯỢC ---
t_mon, t_ctrl, t_file, t_sum, t_offline, t_ai, t_sys = st.tabs([
    "📊 GIÁM SÁT", "🎮 ĐIỀU KHIỂN", "📤 TRUYỀN FILE", "📜 TỔNG KẾT", "🕵️ TRUY VẾT", "🧠 AI INSIGHT", "⚙️ HỆ THỐNG"
])

# (Sếp giữ nguyên nội dung tab t_mon, t_ctrl, t_offline, t_ai)

with t_file:
    st.subheader("Phát hành bộ dữ liệu SDF")
    file_up = st.file_uploader("Kéo thả file .SDF", type=['sdf'])
    active_machines = df_d['machine_id'].unique().tolist() if not df_d.empty else []
    f_targets = st.multiselect("Đại lý nhận mục tiêu:", active_machines)
    
    if st.button("🚀 KÍCH HOẠT ĐỒNG BỘ") and file_up and f_targets:
        with st.status("Đang xử lý dữ liệu..."):
            encoded = base64.b64encode(zlib.compress(file_up.getvalue())).decode('utf-8')
            chunk_size = 100000 
            chunks = [encoded[i:i+chunk_size] for i in range(0, len(encoded), chunk_size)]
            ts = datetime.now().strftime("%Y%m%d%H%M%S") # Mã phiên duy nhất
            
            for m in f_targets:
                payload = [{"machine_id": m, "file_name": file_up.name, "data_chunk": c, 
                           "part_info": f"PART_{i+1}/{len(chunks)}", "timestamp": ts, "status": "PENDING"} 
                           for i, c in enumerate(chunks)]
                for j in range(0, len(payload), 50):
                    sb.table("file_queue").insert(payload[j:j+50]).execute()
            st.success("Đã phát lệnh!")
            st.rerun()

with t_sum:
    st.subheader("📜 Nhật ký vận hành hệ thống")
    if not df_f.empty:
        # CHỖ NÀY QUAN TRỌNG: Gộp các mảnh lại để hiện 1 dòng mỗi file
        display_df = df_f.drop_duplicates(subset=['machine_id', 'timestamp']).copy()
        display_df['Trạng thái'] = display_df['status'].apply(lambda x: "✅ Đã nhận" if x == "DONE" else "⏳ Đang gửi")
        st.dataframe(display_df[['machine_id', 'file_name', 'timestamp', 'Trạng thái']], use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có lịch sử.")

# (Sếp giữ nguyên tab t_sys và t_ai phía dưới)
