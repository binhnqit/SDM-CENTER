# --- TAB 3: LỊCH SỬ TRUYỀN TẢI (ĐÃ CẬP NHẬT THEO Ý SẾP) ---
with tab_history:
    st.subheader("📜 Nhật ký truyền tải dữ liệu")
    try:
        raw_logs = ws_formula.get_all_values()
        if len(raw_logs) > 1:
            header = raw_logs[0]
            # Xử lý dữ liệu để tránh lỗi hiển thị
            log_df = pd.DataFrame(raw_logs[1:], columns=header)
            
            # 1. Lọc và đổi tên cột để sếp dễ theo dõi
            # Tên máy | Tên công thức | Ngày tải | Trạng thái
            history_display = log_df[['MACHINE_ID', 'FILE_NAME', 'TIMESTAMP', 'STATUS']].copy()
            history_display.columns = ['🖥️ Tên Máy', '🧪 Tên Công Thức', '📅 Ngày Tải', '🔔 Trạng Thái']
            
            # 2. Định dạng màu sắc cho trạng thái
            def color_status(val):
                color = 'red' if val == 'PENDING' else 'green'
                return f'color: {color}'

            # 3. Hiển thị bảng tổng hợp
            st.dataframe(
                history_display.style.applymap(color_status, subset=['🔔 Trạng Thái']),
                use_container_width=True,
                hide_index=True
            )
            
            # 4. Thống kê nhanh cho sếp
            success_count = len(log_df[log_df['STATUS'] == 'DONE'])
            pending_count = len(log_df[log_df['STATUS'] == 'PENDING'])
            c1, c2 = st.columns(2)
            c1.info(f"✅ Đã hoàn thành: {success_count}")
            c2.warning(f"⏳ Đang chờ xử lý: {pending_count}")
            
        else:
            st.info("Chưa có lịch sử truyền tải nào được ghi nhận.")
    except Exception as e:
        st.error(f"Không thể tải lịch sử: {e}")
