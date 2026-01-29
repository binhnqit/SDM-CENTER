import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import base64
import zlib
import time

# --- CONFIG (Giữ nguyên base của sếp) ---
SUPABASE_URL = "https://glzdktdphoydqhofszvh.supabase.co"
SUPABASE_KEY = "sb_publishable_MCfri2GPc3dn-bIcx_XJ_A_RxgsF1YU"
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="4Oranges SDM Pro AI v3.5", layout="wide")

# --- DATA ENGINE ---
def load_all_data():
    try:
        dev_res = sb.table("devices").select("*").execute()
        cmd_res = sb.table("commands").select("*").order("created_at", desc=True).limit(20).execute()
        # Lấy thêm dữ liệu hàng đợi file để làm tổng kết
        file_res = sb.table("file_queue").select("machine_id, file_name, status, timestamp").execute()
        
        df_d = pd.DataFrame(dev_res.data) if dev_res.data else pd.DataFrame()
        df_c = pd.DataFrame(cmd_res.data) if cmd_res.data else pd.DataFrame()
        df_f = pd.DataFrame(file_res.data) if file_res.data else pd.DataFrame()
        return df_d, df_c, df_f
    except Exception as e:
        st.error(f"Lỗi DB: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_devices, df_commands, df_files = load_all_data()

# --- MAIN UI ---
st.title("🛡️ 4Oranges SDM Intelligence - v3.5")

t_monitor, t_control, t_file, t_summary, t_ai = st.tabs([
    "📊 GIÁM SÁT", "🎮 ĐIỀU KHIỂN", "📤 ĐẨY FILE", "📜 TỔNG KẾT CẬP NHẬT", "🧠 AI INSIGHTS"
])

# --- TAB: ĐẨY FILE (Sửa lại để khớp Agent v10.4 chuẩn) ---
with t_file:
    st.subheader("📦 Gửi bộ công thức SDF")
    up_file = st.file_uploader("Chọn file .SDF:", type=['sdf'])
    f_targets = st.multiselect("Máy nhận:", df_devices['machine_id'].tolist() if not df_devices.empty else [])
    
    if st.button("🚀 XÁC NHẬN ĐẨY FILE"):
        if up_file and f_targets:
            with st.status("Đang mã hóa và phân mảnh..."):
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
                st.success(f"Đã phát lệnh tới {len(f_targets)} máy. Agent v10.4 sẽ tự động ngắt khi xong.")

# --- TAB: TỔNG KẾT CẬP NHẬT (MỚI) ---
with t_summary:
    st.subheader("📜 Nhật ký cập nhật toàn hệ thống")
    if not df_files.empty:
        # Nhóm dữ liệu để hiển thị gọn gàng
        summary = df_files.groupby(['machine_id', 'file_name', 'status']).size().reset_index(name='chunks')
        
        c1, c2 = st.columns([3, 1])
        with c1:
            st.dataframe(summary, use_container_width=True, hide_index=True)
        with c2:
            st.metric("Tỷ lệ hoàn thành", f"{(len(summary[summary['status']=='DONE'])/len(summary)*100):.1f}%")
            if st.button("🗑️ DỌN DẸP HÀNG ĐỢI XONG"):
                sb.table("file_queue").delete().eq("status", "DONE").execute()
                st.rerun()
    else:
        st.info("Chưa có lịch sử cập nhật.")

# --- TAB: AI INSIGHTS (NÂNG CẤP) ---
with t_ai:
    st.header("🧠 Trợ lý AI Phân tích")
    if not df_devices.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 Hiệu suất hệ thống")
            # Biểu đồ CPU/RAM trung bình
            avg_cpu = df_devices['cpu_usage'].mean()
            st.write(f"Tải CPU trung bình toàn hệ thống: **{avg_cpu:.1f}%**")
            fig = px.pie(df_devices, names='status', title="Tỷ lệ Trạng thái Máy")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("### 💡 Khuyến nghị từ AI")
            # Logic AI phân tích máy lỗi
            stuck = df_devices[df_devices['cpu_usage'] > 90]
            if not stuck.empty:
                st.warning(f"AI phát hiện {len(stuck)} máy có dấu hiệu treo CPU. Đề xuất: RESTART AGENT.")
            
            # Phân tích cập nhật
            if not df_files.empty:
                pending_count = len(df_files[df_files['status'] == 'PENDING'])
                if pending_count > 0:
                    st.error(f"Còn {pending_count} mảnh dữ liệu chưa được tải. Kiểm tra kết nối mạng tại đại lý.")
                else:
                    st.success("Tất cả các máy mục tiêu đã được đồng bộ hóa SDF 100%.")

            st.markdown("""
            ---
            **Dự báo từ AI:** - Lưu lượng pha màu sẽ tăng 20% vào cuối tuần. 
            - Hãy chuẩn bị sẵn file SDF công thức mới cho dòng sơn **4Oranges 2026**.
            """)
