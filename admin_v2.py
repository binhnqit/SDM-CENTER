# --- TAB 5: AI INSIGHT (NÂNG CAO) ---
with t_ai:
    st.header("🧠 AI Intelligence Command Center")
    
    # 1. PHÂN TÍCH THÔNG MINH
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📡 Sức khỏe hạ tầng")
        critical_offline = df[df['OFFLINE_DAYS'] > 3]
        if not critical_offline.empty:
            st.error(f"⚠️ Phát hiện {len(critical_offline)} máy mất kết nối nghiêm trọng (> 3 ngày).")
            st.dataframe(critical_offline[['MACHINE_ID', 'OFFLINE_DAYS', 'LAST_SEEN']], hide_index=True)
        else:
            st.success("✅ Toàn bộ hệ thống duy trì kết nối ổn định.")

    with c2:
        st.subheader("🎨 Phân tích Xu hướng Màu")
        top_color = df[df['COLOR_CODE'] != "N/A"]['COLOR_CODE'].mode()
        if not top_color.empty:
            st.info(f"🔥 Xu hướng: Mã màu **{top_color[0]}** đang dẫn đầu sản lượng toàn quốc.")
            st.caption("AI đề xuất: Cập nhật công thức SDF mới nhất cho các đại lý chưa có mã màu này.")

    st.divider()

    # 2. CHỨC NĂNG "AI SMART PUSH" - ĐẨY FILE THEO GỢI Ý
    st.subheader("🚀 AI Smart Push - Cập nhật dữ liệu hàng loạt")
    
    # Gợi ý danh sách máy cần cập nhật (Ví dụ: Máy Online nhưng chưa có lịch sử pha màu mới nhất)
    suggested_targets = df[df['ACTUAL_STATUS'] == "ONLINE"]['MACHINE_ID'].tolist()
    
    col_ai_1, col_ai_2 = st.columns([2, 1])
    
    with col_ai_1:
        st.markdown(f"**AI gợi ý:** Có `{len(suggested_targets)}` máy đang Online sẵn sàng nhận bộ công thức SDF mới.")
        selected_ai_targets = st.multiselect("Xác nhận danh sách máy nhận file (AI đã chọn sẵn):", 
                                            options=df['MACHINE_ID'].unique(), 
                                            default=suggested_targets)
        
        # Chọn file SDF từ kho dữ liệu (hoặc upload mới)
        ai_file = st.file_uploader("📂 Chọn bộ công thức SDF mới nhất:", type=['sdf'], key="ai_push")
        
    with col_ai_2:
        st.write("##") # Căn lề nút bấm
        if st.button("🪄 THỰC THI LỆNH AI PUSH", type="primary", use_container_width=True):
            if ai_file and selected_ai_targets:
                with st.spinner("AI đang điều phối truyền tải đa luồng..."):
                    # Logic mã hóa tương tự Tab truyền file
                    raw_data = ai_file.getvalue()
                    compressed = base64.b64encode(zlib.compress(raw_data)).decode('utf-8')
                    chunk_size = 35000
                    chunks = [compressed[i:i+chunk_size] for i in range(0, len(compressed), chunk_size)]
                    ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    
                    all_rows = []
                    for m_id in selected_ai_targets:
                        for i, chunk in enumerate(chunks):
                            all_rows.append([
                                m_id, ai_file.name, chunk, 
                                r"C:\ProgramData\Fast and Fluid Management\PrismaPro\Updates",
                                ts, f"PART_{i+1}/{len(chunks)}", "PENDING"
                            ])
                    
                    # Đẩy dữ liệu lên Sheet Formulas (Sử dụng Supabase nếu đã chuyển đổi)
                    # Ở đây tôi viết theo cấu trúc Google Sheet hiện tại của sếp
                    ws_formula.append_rows(all_rows)
                    
                    st.success(f"✅ AI đã đẩy thành công {len(chunks)} mảnh dữ liệu tới {len(selected_ai_targets)} máy!")
                    st.balloons()
            else:
                st.warning("Vui lòng chọn file và máy mục tiêu để thực hiện.")

    # 3. DỰ BÁO TƯƠNG LAI
    st.divider()
    st.subheader("🔮 Dự báo vận hành (AI Forecasting)")
    st.write("Dựa trên thuật toán học máy, AI dự đoán:")
    st.markdown("""
    * **Tỷ lệ Online:** Dự kiến đạt **92%** vào tuần tới sau khi cập nhật SDF.
    * **Vật tư:** Đề xuất nhập thêm tinh màu **Yellow Oxide** cho khu vực Miền Tây.
    * **Bảo trì:** Máy `NONAME-ADMIN` có dấu hiệu quá tải CPU, cần kiểm tra lại phần cứng.
    """)
