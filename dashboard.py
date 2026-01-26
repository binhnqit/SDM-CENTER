import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import plotly.express as px # Thêm thư viện biểu đồ chuyên nghiệp

# --- 1. CẤU HÌNH & GIAO DIỆN ---
st.set_page_config(page_title="4Oranges SDM - Platinum AI", layout="wide")

# Custom CSS cho phong cách Modern Dashboard
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 5px 5px 0 0; gap: 1px; padding-top: 10px; }
    .stTabs [aria-selected="true"] { background-color: #ff4b4b !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KẾT NỐI HỆ THỐNG ---
@st.cache_resource(ttl=60)
def get_gspread_client():
    k_name = next((k for k in st.secrets if "GCP" in k or "base64" in k), None)
    info = json.loads(base64.b64decode(st.secrets[k_name]).decode('utf-8'))
    creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

client = get_gspread_client()
SHEET_ID = "1LClTdR0z_FPX2AkYCfrbBRtWO8BWOG08hAEB8aq-TcI"
sh = client.open_by_key(SHEET_ID)
ws_main = sh.get_worksheet(0) # Sheet lệnh & trạng thái
ws_formula = sh.get_worksheet(1) if len(sh.worksheets()) > 1 else sh.add_worksheet("Formulas", 100, 5)

# --- 3. LOAD DỮ LIỆU ---
def load_data():
    data = ws_main.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])
    df['sheet_row'] = df.index + 2
    # Logic Actual Status
    now = datetime.now()
    df['ACTUAL_STATUS'] = df['LAST_SEEN'].apply(lambda x: "ONLINE" if (now - datetime.strptime(x, "%d/%m/%Y %H:%M:%S")).total_seconds() < 120 else "OFFLINE" if x else "OFFLINE")
    return df

df = load_data()

# --- 4. GIAO DIỆN TABS ---
st.title("🛡️ 4Oranges SDM - Platinum AI Command Center")

tab_control, tab_formula, tab_analytics, tab_ai = st.tabs([
    "🎮 ĐIỀU KHIỂN HỆ THỐNG", 
    "🧪 CẬP NHẬT CÔNG THỨC", 
    "📊 THỐNG KÊ SẢN LƯỢNG", 
    "🧠 AI INSIGHTS (BETA)"
])

# --- TAB 1: ĐIỀU KHIỂN (Giữ nguyên lõi V6.5) ---
with tab_control:
    # (Phần code điều khiển, tìm kiếm, metrics sếp đã dùng ở V6.5 PRO giữ nguyên ở đây)
    st.info("Quản lý trạng thái và phát lệnh khóa/mở thiết bị thời gian thực.")
    # [Code V6.5 PRO chèn tại đây]

# --- TAB 2: CẬP NHẬT CÔNG THỨC TỰ ĐỘNG (MỚI) ---
with tab_formula:
    st.subheader("🧬 Quản lý Công thức & Màu mới")
    col_f1, col_f2 = st.columns([1, 2])
    
    with col_f1:
        with st.form("formula_form"):
            new_code = st.text_input("Mã màu mới (Color Code):")
            new_formula = st.text_area("Thông số công thức (JSON/Text):")
            target_group = st.multiselect("Áp dụng cho:", df['MACHINE_ID'].unique(), default=None)
            submit_f = st.form_submit_button("📢 ĐẨY CÔNG THỨC XUỐNG CLIENT")
            
            if submit_f:
                # Ghi vào Sheet Formulas để Agent tự tải về
                for m_id in target_group:
                    ws_formula.append_row([m_id, new_code, new_formula, datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "PENDING"])
                st.success(f"Đã lên lịch cập nhật cho {len(target_group)} máy.")

    with col_f2:
        st.write("Nhật ký cập nhật gần đây")
        f_data = ws_formula.get_all_records()
        if f_data:
            st.table(pd.DataFrame(f_data).tail(10))

# --- TAB 3: THỐNG KÊ MÀU PHA (Dữ liệu từ HISTORY) ---
with tab_analytics:
    st.subheader("📊 Phân tích Sản lượng Màu pha")
    # Trích xuất dữ liệu từ cột HISTORY (Giả sử Agent gửi: "Pha màu: 7052 | Up: 1h")
    # Ở đây chúng ta parse dữ liệu để vẽ biểu đồ
    if not df.empty:
        # Demo dữ liệu thống kê (Trong thực tế sẽ parse từ cột HISTORY)
        color_counts = df['HISTORY'].str.extract(r'([A-Z0-9]{4,6})').value_counts().reset_index()
        color_counts.columns = ['Mã Màu', 'Số Lần Pha']
        
        c_an1, c_an2 = st.columns(2)
        with c_an1:
            fig = px.bar(color_counts.head(10), x='Mã Màu', y='Số Lần Pha', title="Top 10 Màu Pha Nhiều Nhất", color='Số Lần Pha')
            st.plotly_chart(fig, use_container_width=True)
        with c_an2:
            fig2 = px.pie(color_counts.head(5), values='Số Lần Pha', names='Mã Màu', title="Tỷ trọng dòng màu chủ lực")
            st.plotly_chart(fig2, use_container_width=True)

# --- TAB 4: GỢI Ý NÂNG CẤP AI (PHẦN SẾP CẦN) ---
with tab_ai:
    st.subheader("🧠 Trợ lý AI Dự báo & Tối ưu")
    
    st.markdown("""
    ### 🚩 Các hướng nâng cấp AI cho 4Oranges SDM:
    
    1. **AI Predictive Maintenance (Bảo trì dự báo):**
        * *Cách làm:* AI phân tích cột HISTORY. Nếu thấy CPU máy khách luôn > 90% hoặc thời gian pha màu một mã nhất định tăng đột biến -> Cảnh báo máy sắp hỏng linh kiện (bơm/kim phun) trước khi nó thực sự hỏng.
        
    2. **AI Stock Optimization (Tối ưu hóa mực màu):**
        * *Cách làm:* Dựa trên Tab Thống kê màu, AI sẽ dự báo: "Đại lý A sắp hết tinh màu Đỏ trong 3 ngày tới" dựa trên tốc độ pha màu thực tế. Tự động tạo đơn hàng gợi ý cho bộ phận Sales.
        
    3. **AI Anomaly Detection (Phát hiện gian lận):**
        * *Cách làm:* Nếu một máy pha màu vào lúc 2 giờ sáng (ngoài giờ làm việc) hoặc pha màu không có trong danh mục công thức -> Gửi cảnh báo "Hành vi bất thường" về Telegram sếp ngay lập tức.
        
    4. **Smart Search Natural Language:**
        * *Cách làm:* Cho phép sếp gõ: *"Liệt kê các máy ở khu vực miền Tây đang offline hơn 2 ngày"* thay vì phải lọc tay.
    """)
    
    if st.button("🪄 Chạy AI phân tích hệ thống (Demo)"):
        with st.spinner("AI đang quét dữ liệu..."):
            time.sleep(2)
            st.write("✅ **Phân tích AI:** Phát hiện máy `PC-XUONG1` có nhiệt độ vận hành cao hơn 15% so với trung bình. Đề xuất: Kiểm tra hệ thống làm mát.")
