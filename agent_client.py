import fdb # Thư viện đọc file .fdb
import pandas as pd
import os

def get_tinting_history():
    # Đường dẫn mặc định của file History trên máy khách
    db_path = r'C:\ProgramData\Fast and Fluid Management\PrismaPro\History.fdb'
    
    if not os.path.exists(db_path):
        return None

    try:
        # Kết nối vào database Firebird
        conn = fdb.connect(
            database=db_path,
            user='SYSDBA',      # User mặc định của Firebird
            password='masterkey' # Password mặc định
        )
        query = "SELECT FIRST 10 * FROM TINTING_HISTORY ORDER BY DATE_TIME DESC"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Lỗi đọc DB: {e}")
        return None
