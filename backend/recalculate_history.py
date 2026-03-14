import datetime
import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
_env_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_env_dir)
load_dotenv(os.path.join(_env_dir, '.env'))
load_dotenv(os.path.join(_root_dir, '.env'))

def get_db():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'hris'),
        port=int(os.getenv('DB_PORT', 3306))
    )

def to_minutes(time_val):
    if isinstance(time_val, datetime.timedelta):
        return int(time_val.total_seconds() // 60)
    if hasattr(time_val, 'hour') and hasattr(time_val, 'minute'):
        return time_val.hour * 60 + time_val.minute
    try:
        s_val = str(time_val)
        if ' ' in s_val: s_val = s_val.split(' ')[1]
        parts = s_val.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except:
        return 0

def calculate_diff_smart(time_val, ref_time, is_night_shift=False):
    t_min = to_minutes(time_val)
    r_min = to_minutes(ref_time)
    diff = t_min - r_min
    if is_night_shift:
        if diff < -720: diff += 1440
        elif diff > 720: diff -= 1440
    else:
        if diff < -1000: diff += 1440
        elif diff > 1000: diff -= 1440
    return diff

def sync_historical_data():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    print("Mendapatkan data absensi historical...")
    cursor.execute('''
        SELECT a.id, a.employee_id, a.date, a.check_in, a.check_out, 
               e.shift_start, e.shift_end
        FROM attendance a
        JOIN employees e ON a.employee_id = e.id
    ''')
    records = cursor.fetchall()
    
    updated_count = 0
    for row in records:
        shift_start = row['shift_start'] or '09:00'
        shift_end = row['shift_end'] or '17:00'
        is_night = to_minutes(shift_start) > to_minutes(shift_end)
        
        late = 0
        if row['check_in']:
            late = max(0, calculate_diff_smart(row['check_in'], shift_start, is_night))
            
        overtime = 0
        status = 'present'
        if row['check_out']:
            overtime = max(0, calculate_diff_smart(row['check_out'], shift_end, is_night))
            
            # Validasi durasi kerja jika ada check_in
            if row['check_in']:
                diff_work = calculate_diff_smart(row['check_out'], row['check_in'], is_night)
                if diff_work < 0:
                    status = 'invalid'
                    overtime = 0
        
        cursor.execute('''
            UPDATE attendance 
            SET late_minutes = %s, overtime_minutes = %s, status = %s
            WHERE id = %s
        ''', (late, overtime, status, row['id']))
        updated_count += 1
        
    conn.commit()
    conn.close()
    print(f"Selesai! {updated_count} data telah dihitung ulang.")

if __name__ == "__main__":
    sync_historical_data()
