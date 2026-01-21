import streamlit as st
import pandas as pd
import requests

st.title("🧪 Kiểm tra kết nối & Cấu trúc (Public CSV)")

# 1. BƯỚC 1: KIỂM TRA KẾT NỐI
# Sử dụng link CSV sếp vừa cung cấp
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRb0o4_waLhyj-CGEpnF-VdA7s9kykCxSKD2K85Rx-DJwLhUDd-R81lvFcPw1fzZTz2n7Dip0c3kkfH/pub?gid=0&single=true&output=csv"

try:
    # Thử tải file CSV từ link
    response = requests.get(CSV_URL)
    
    if response.status_code == 200:
        st.success("✅ BƯỚC 1: KẾT NỐI ĐẾN FILE CSV THÀNH CÔNG!")
        
        # 2. BƯỚC 2: IN TÊN CÁC CỘT
        # Đọc dữ liệu vào DataFrame của Pandas
        # Lưu ý: Link này trả về CSV nên dùng pd.read_csv
        from io import StringIO
        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data)
        
        headers = df.columns.tolist()
        
        if headers:
            st.write("### 📋 BƯỚC 2: DANH SÁCH CỘT TÌM THẤY")
            for i, col_name in enumerate(headers):
                st.info(f"Cột {i+1}: **{col_name}**")
        else:
            st.warning("⚠️ Kết nối được nhưng file không có tiêu đề cột.")
            
    else:
        st.error(f"❌ Bước 1 thất bại: Link trả về lỗi {response.status_code}")

except Exception as e:
    st.error(f"❌ Lỗi hệ thống: {str(e)}")
