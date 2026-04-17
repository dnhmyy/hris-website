from flask import Flask, jsonify, request, send_from_directory, send_file, session, redirect, url_for
from flask import render_template_string
import time
import mysql.connector
import os
from werkzeug.security import check_password_hash
from functools import wraps
import requests
from datetime import datetime, timedelta
from flask_cors import CORS
from dotenv import load_dotenv
import pandas as pd
from openpyxl.styles import Alignment, Font
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import ipaddress

# Muat variabel lingkungan
_env_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_env_dir)
load_dotenv(os.path.join(_env_dir, '.env'))
load_dotenv(os.path.join(_root_dir, '.env'))
load_dotenv(os.path.join(_env_dir, '.env.local'), override=True)
load_dotenv(os.path.join(_root_dir, '.env.local'), override=True)

app = Flask(__name__, static_folder='../frontend')
app.config['VERSION'] = str(int(time.time()))
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Pengaturan Session yang Aman
app.config.update(
    SESSION_COOKIE_SECURE=False, # Set ke True jika menggunakan HTTPS secara penuh di produksi
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

# SETUP RATE LIMITER
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# KECUALIKAN JALUR MESIN ABSEN DARI RATE LIMITER
@limiter.request_filter
def ip_whitelist():
    return request.path.startswith('/iclock')

#Cache Control Configration
@app.after_request
def add_cache_control(response):
    if (
        request.path.startswith('/api')
        or request.path == '/'
        or request.path.endswith('.html')
    ):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
    return response

app.secret_key = os.getenv('SECRET_KEY')
if not app.secret_key:
    # Fallback hanya untuk development: pastikan SECRET_KEY diset di .env produksi
    app.secret_key = 'dev-secret-key-replace-this-in-production'

# Folder simpan foto dari mesin absensi
UPLOAD_ATTENDANCE = os.path.join(os.path.dirname(__file__), 'uploads', 'attendance')
os.makedirs(UPLOAD_ATTENDANCE, exist_ok=True)

# FUNGSI AKSES PERANGKAT (SDK SOAP)
def send_soap_request(device_ip, payload):
    """Mengirim request SOAP ke mesin absensi via HTTP port 80"""
    url = f"http://{device_ip}/iWsService"
    headers = {'Content-Type': 'text/xml'}
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        return response.text
    except Exception as e:
        print(f"SOAP Error ({device_ip}): {e}")
        return None

# FUNGSI AKSES DATABASE & OTENTIKASI
def get_db():
    """Koneksi ke database MySQL"""
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'hris'),
        port=int(os.getenv('DB_PORT', 3306))
    )
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized', 'message': 'Please login first'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized', 'message': 'Please login first'}), 401
        if session.get('role') != 'admin':
            return jsonify({'error': 'Forbidden', 'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def is_private_ip(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private
    except ValueError:
        return False

# LOGIKA PERHITUNGAN WAKTU DAN SHIFT

def to_minutes(time_val):
    """Konversi jam (string 'AA:BB', timedelta, atau time object) ke menit integer"""
    if isinstance(time_val, timedelta):
        return int(time_val.total_seconds() // 60)
    if hasattr(time_val, 'hour') and hasattr(time_val, 'minute'):
        return time_val.hour * 60 + time_val.minute
    try:
        # Pastikan string, lalu split jam:menit
        s_val = str(time_val)
        if ' ' in s_val: s_val = s_val.split(' ')[1] # Handle 'YYYY-MM-DD HH:MM:SS'
        parts = s_val.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except:
        return 0

def calculate_diff_smart(time_val, ref_time, is_night_shift=False):
    """
    Menghitung selisih menit (time_val - ref_time).
    Menangani crossing midnight untuk shift malam.
    """
    t_min = to_minutes(time_val)
    r_min = to_minutes(ref_time)
    
    diff = t_min - r_min
    
    # Deteksi crossing midnight
    # Jika is_night_shift=True, kita gunakan threshold 12 jam (720 menit)
    if is_night_shift:
        if diff < -720:
            diff += 1440
        elif diff > 720:
            diff -= 1440
    else:
        # Untuk shift siang, kita lebih toleran (misal hingga 20 jam kerja)
        # Hanya crossing midnight jika selisih sangat ekstrim (misal < -1000)
        if diff < -1000:
            diff += 1440
        elif diff > 1000:
            diff -= 1440
        
    return diff

# ROUTE FRONTEND
@app.route('/')
def serve_frontend():
    with open('../frontend/index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    return render_template_string(html)

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve file CSS, JS, dll"""
    return send_from_directory('../frontend', filename)

# API ENDPOINTS (OTENTIKASI)

@app.route('/api/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
        
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        return jsonify({
            'message': 'Login successful',
            'user': {
                'username': user['username'],
                'role': user['role']
            }
        }), 200
    
    return jsonify({'error': 'Invalid username or password'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'username': session.get('username'),
                'role': session.get('role')
            }
        }), 200
    return jsonify({'authenticated': False}), 200


# --- ADMS Protocol Implementation (Solution X105 / ZKTeco) ---

def parse_attlog(data):
    """
    Parses ADMS ATTLOG data format.
    Standard format: PIN \t Timestamp \t Status \t VerifyMethod
    Example: 1\t2026-02-13 11:30:00\t0\t1
    """
    logs = []
    lines = data.strip().split('\n')
    for line in lines:
        parts = line.split('\t')
        if len(parts) >= 2:
            logs.append({
                'pin': parts[0].strip(),
                'timestamp': parts[1].strip(),
                'status': int(parts[2].strip()) if len(parts) > 2 else 0, # Index 2 is Status (0=Check-in, 1=Check-out)
                'verification': int(parts[3].strip()) if len(parts) > 3 else 1, # Index 3 is Verify Method
                'stamp': int(parts[4].strip()) if len(parts) > 4 else 0
            })
    return logs

@app.route('/iclock/cdata', methods=['POST', 'GET'])
def adms_cdata():
    """
    PUSH SDK Protocol Implementation
    Handles device handshake, configuration, and data uploads
    """
    sn = request.args.get('SN')
    options = request.args.get('options')
    table = request.args.get('table')
    
    if not sn:
        return "ERROR: SN required", 400
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT id, last_attlog_stamp, last_operlog_stamp, last_attphoto_stamp,
               push_delay, error_delay, realtime_mode, timezone_offset,
               trans_times, trans_interval, trans_flag
        FROM attendance_devices WHERE id = %s
    ''', (sn,))
    device = cursor.fetchone()
    
    if not device:
        # Mock device for unregistered SN allow
        device = {
            'last_attlog_stamp': 0, 'last_operlog_stamp': 0, 'last_attphoto_stamp': 0,
            'push_delay': 10, 'error_delay': 30, 'realtime_mode': 1, 'timezone_offset': 7,
            'trans_times': '00:00;14:05', 'trans_interval': 1, 'trans_flag': 'TransData AttLog OpLog'
        }

    # HANDSHAKE: Device requesting configuration (GET with options=all)
    if request.method == 'GET' and options == 'all':
        response_lines = [
            f"GET OPTION FROM: {sn}",
            f"ATTLOGStamp={device['last_attlog_stamp'] or 0}",
            f"OPERLOGStamp={device['last_operlog_stamp'] or 0}",
            f"ATTPHOTOStamp={device['last_attphoto_stamp'] or 0}",
            f"ErrorDelay={device['error_delay'] or 30}",
            f"Delay={device['push_delay'] or 10}",
            f"TransTimes={device['trans_times'] or '00:00;14:05'}",
            f"TransInterval={device['trans_interval'] or 1}",
            f"TransFlag={device['trans_flag'] or 'TransData AttLog OpLog'}",
            f"TimeZone={device['timezone_offset'] or 7}",
            f"Realtime={device['realtime_mode'] or 1}",
            "Encrypt=None", "ServerVer=3.0.0", "PushProtVer=2.2.14"
        ]
        
        cursor.execute('UPDATE attendance_devices SET last_sync = NOW() WHERE id = %s', (sn,))
        conn.commit()
        conn.close()
        
        response = app.response_class(response="\n".join(response_lines), status=200, mimetype='text/plain')
        response.headers['Pragma'] = 'no-cache'
        return response

    # DATA UPLOAD: Device sending attendance logs (POST with table=ATTLOG)
    if request.method == 'POST' and table == 'ATTLOG':
        try:
            raw_data = request.data.decode('utf-8')
            logs = parse_attlog(raw_data)
            
            max_stamp = int(device['last_attlog_stamp'] or 0)
            
            for log in logs:
                pin_val = log['pin']
                
                # Cari karyawan
                cursor.execute('SELECT id, shift_start, shift_end FROM employees WHERE id = %s OR device_pin = %s', (pin_val, pin_val))
                employee = cursor.fetchone()
                
                if employee:
                    employee_id = employee['id']
                    timestamp = log['timestamp']
                    raw_status = log['status']
                    
                    # LOGIC BARU: Tentukan Shift & Tanggal
                    shift_start = employee['shift_start'] or '09:00'
                    shift_end = employee['shift_end'] or '17:00'
                    
                    # Ambil tanggal langsung dari timestamp (tanpa logika shift malam)
                    ts_str = str(timestamp)
                    date_part = ts_str.split(' ')[0]
                    time_part = ts_str.split()[1] # HH:MM:SS
                    
                    # LOGIC BARU: Smart Status Detection
                    # Jika status mesin 0 (Check-in) tapi waktu dekat shift keluar -> Anggap Check-out
                    # Jika status mesin 1 (Check-out) tapi waktu dekat shift masuk -> Anggap Check-in
                    # Ambang batas toleransi: 120 menit (2 jam)
                    
                    is_night = to_minutes(shift_start) > to_minutes(shift_end)
                    diff_start = calculate_diff_smart(time_part, shift_start, is_night)
                    diff_end = calculate_diff_smart(time_part, shift_end, is_night)
                    
                    final_status = raw_status 
                    
                    # Aturan Smart Override:
                    # 1. Jika mesin bilang Check-out (1), tapi waktu absen sangat dekat Start (+- 2 jam) DAN jauh dari End -> Override jadi CHECK-IN
                    if raw_status != 0 and abs(diff_start) < 120 and abs(diff_end) > 120:
                        final_status = 0 # Force Check-in
                        print(f"INFO: Koreksi status otomatis PIN {pin_val} {time_part}: Status {raw_status} -> 0 (Check-in)")
                        
                    # 2. Jika mesin bilang Check-in (0), tapi waktu absen sangat dekat End (+- 2 jam) DAN jauh dari Start -> Override jadi CHECK-OUT
                    elif raw_status == 0 and abs(diff_end) < 120 and abs(diff_start) > 120:
                        final_status = 1 # Force Check-out
                        print(f"INFO: Koreksi status otomatis PIN {pin_val} {time_part}: Status {raw_status} -> 1 (Check-out)")
                    
                    
                    # 1. TETAP CATAT SEMUA KE TABEL LOG (HISTORI LENGKAP)
                    cursor.execute('''
                        INSERT INTO attendance_logs (employee_id, timestamp, status, device_id)
                        VALUES (%s, %s, %s, %s)
                    ''', (employee_id, timestamp, raw_status, sn))

                    # 2. UPDATE TABEL RANGKUMAN (LOGIK AWAL: TIMPA TERUS)
                    if final_status == 0: # Check-in
                        late = max(0, calculate_diff_smart(time_part, shift_start, is_night))
                        
                        # CLEANUP: Jika sebelumnya tercatat sebagai Check-out di jam yang sama (error mesin), hapus Check-outnya
                        cursor.execute('''
                            UPDATE attendance 
                            SET check_out = NULL, overtime_minutes = 0, status = 'present'
                            WHERE employee_id = %s AND date = %s AND check_out = %s
                        ''', (employee_id, date_part, time_part))

                        cursor.execute('''
                            INSERT INTO attendance (employee_id, date, check_in, late_minutes)
                            VALUES (%s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE 
                                check_in = VALUES(check_in), 
                                late_minutes = VALUES(late_minutes)
                        ''', (employee_id, date_part, time_part, late))
                        
                    else: # Check-out
                        overtime = max(0, calculate_diff_smart(time_part, shift_end, is_night))
                        
                        # CLEANUP: Jika sebelumnya tercatat sebagai Check-in di jam yang sama, hapus Check-innya
                        cursor.execute('''
                            UPDATE attendance 
                            SET check_in = NULL, late_minutes = 0
                            WHERE employee_id = %s AND date = %s AND check_in = %s
                        ''', (employee_id, date_part, time_part))
                        
                        cursor.execute('SELECT check_in FROM attendance WHERE employee_id=%s AND date=%s', (employee_id, date_part))
                        existing = cursor.fetchone()
                        
                        validation_status = 'present'
                        if existing and existing['check_in']:
                            diff_work = calculate_diff_smart(time_part, existing['check_in'], is_night)
                            if diff_work < 0:
                                validation_status = 'invalid'
                                overtime = 0
                        
                        cursor.execute('''
                            INSERT INTO attendance (employee_id, date, check_out, overtime_minutes, status)
                            VALUES (%s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE 
                                check_out = VALUES(check_out), 
                                overtime_minutes = VALUES(overtime_minutes),
                                status = VALUES(status)
                        ''', (employee_id, date_part, time_part, overtime, validation_status))

                # Track stamp
                if 'stamp' in log and log['stamp'] and int(log['stamp']) > max_stamp:
                    max_stamp = log['stamp']

            # Update device stamps and last sync
            if sn in [d['id'] for d in [device] if 'id' in d]: # Only update if it's a real device in DB
                cursor.execute('''
                    UPDATE attendance_devices 
                    SET last_sync = NOW(), last_attlog_stamp = %s 
                    WHERE id = %s
                ''', (max_stamp, sn))
                conn.commit()
            
            conn.close()
            # Return simple 'OK' as per common ADMS implementation to stop retries
            response = app.response_class(
                response="OK",
                status=200,
                mimetype='text/plain'
            )
            response.headers['Pragma'] = 'no-cache'
            response.headers['Cache-Control'] = 'no-store'
            return response
            
        except Exception as e:
            print(f"ADMS Error: {e}")
            conn.close()
            return "ERROR", 500

    # Default response for other requests
    conn.close()
    return "OK"

@app.route('/iclock/getrequest', methods=['GET'])
def adms_getrequest():
    """
    PUSH SDK: Device polling for commands
    Returns any pending commands for the device
    """
    sn = request.args.get('SN')
    if not sn:
        return "OK"
    
    # For now, return OK (no commands)
    # Future: implement command queue for remote management
    return "OK"

# --- SOAP Remote Management ---

@app.route('/api/devices/<string:device_id>/soap/sync-time', methods=['POST'])
@admin_required
def device_sync_time(device_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT device_ip, device_key FROM attendance_devices WHERE id = %s', (device_id,))
    device = cursor.fetchone()
    conn.close()

    if not device or not device['device_ip']:
        return jsonify({'error': 'Device not found or IP not set'}), 404

    now = datetime.now()
    time_str = now.strftime('%Y-%m-%d %H:%M:%S')
    payload = f"<SetDeviceTime><ArgComKey>{device['device_key'] or 0}</ArgComKey><Arg><Value>{time_str}</Value></Arg></SetDeviceTime>"
    
    result = send_soap_request(device['device_ip'], payload)
    if result and "OK" in result:
        return jsonify({'message': 'Time synchronized successfully'}), 200
    return jsonify({'error': 'Failed to sync time', 'details': result}), 500

@app.route('/api/devices/<string:device_id>/soap/clear-logs', methods=['POST'])
@admin_required
def device_clear_logs(device_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT device_ip, device_key FROM attendance_devices WHERE id = %s', (device_id,))
    device = cursor.fetchone()
    conn.close()

    if not device or not device['device_ip']:
        return jsonify({'error': 'Device not found'}), 404

    payload = f"<ClearLog><ArgComKey>{device['device_key'] or 0}</ArgComKey></ClearLog>"
    result = send_soap_request(device['device_ip'], payload)
    if result and "OK" in result:
        return jsonify({'message': 'Logs cleared successfully'}), 200
    return jsonify({'error': 'Failed to clear logs', 'details': result}), 500

@app.route('/api/devices/<string:device_id>/soap/restart', methods=['POST'])
@admin_required
def device_restart(device_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT device_ip, device_key FROM attendance_devices WHERE id = %s', (device_id,))
    device = cursor.fetchone()
    conn.close()

    if not device or not device['device_ip']:
        return jsonify({'error': 'Device not found'}), 404

    if not is_private_ip(device['device_ip']):
        return jsonify({'error': 'SSRF Protection: Device IP must be a private network IP'}), 403

    payload = f"<Restart><ArgComKey>{device['device_key'] or 0}</ArgComKey></Restart>"
    result = send_soap_request(device['device_ip'], payload)
    if result and "OK" in result:
        return jsonify({'message': 'Device is restarting'}), 200
    return jsonify({'error': 'Failed to restart device', 'details': result}), 500

@app.route('/api/devices/<string:device_id>/soap/upload-user', methods=['POST'])
@admin_required
def device_upload_user(device_id):
    data = request.json
    employee_id = data.get('employee_id')
    
    if not employee_id:
        return jsonify({'error': 'Employee ID required'}), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT device_ip, device_key FROM attendance_devices WHERE id = %s', (device_id,))
    device = cursor.fetchone()
    
    cursor.execute('SELECT name, device_pin FROM employees WHERE id = %s', (employee_id,))
    employee = cursor.fetchone()
    conn.close()

    if not device or not device['device_ip']:
        return jsonify({'error': 'Device not found'}), 404
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404

    pin = employee['device_pin'] or employee_id
    payload = f"<SetUserInfo><ArgComKey>{device['device_key'] or 0}</ArgComKey><Arg><PIN>{pin}</PIN><Name>{employee['name']}</Name></Arg></SetUserInfo>"
    
    result = send_soap_request(device['device_ip'], payload)
    if result and "OK" in result:
        return jsonify({'message': f'Employee {employee["name"]} uploaded to device'}), 200
    return jsonify({'error': 'Failed to upload user', 'details': result}), 500

# GET /api/attendance-devices - Daftar mesin absensi (untuk halaman monitoring)
@app.route('/api/attendance-devices', methods=['GET'])
@login_required
def get_attendance_devices():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT id, branch_id, device_name, device_ip, last_sync, status,
               serial_no, mac_address, model, platform, manufacturer
        FROM attendance_devices
        WHERE status = %s
        ORDER BY branch_id, device_name
    ''', ('active',))
    devices = cursor.fetchall()
    conn.close()
    # Format datetime untuk last_sync
    for d in devices:
        if d.get('last_sync'):
            d['last_sync'] = d['last_sync'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(d['last_sync'], 'strftime') else str(d['last_sync'])
        else:
            d['last_sync'] = None
    return jsonify(devices)


# --- Karyawan ---
@app.route('/api/employees/<string:employee_id>', methods=['PUT'])
@admin_required
def update_employee(employee_id):
    data = request.json
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Ambil data yang dikirim, hanya update field yang dikirim
    allowed_fields = [
        'name', 'position', 'department', 'branch_id', 
        'shift_start', 'shift_end', 'is_active', 
        'start_date', 'contract_duration_months', 'contract_end_date'
    ]
    
    update_data = {}
    for field in allowed_fields:
        if field in data:
            val = data[field]
            # Convert empty strings to None for date/int fields to avoid MySQL errors
            if field in ['start_date', 'contract_end_date', 'contract_duration_months'] and val == '':
                val = None
            update_data[field] = val
    
    if not update_data:
        return jsonify({'error': 'No data to update'}), 400
    
    try:
        # Gunakan list comprehension untuk membangun query dinamis
        set_clause = ', '.join([f"{field} = %s" for field in update_data.keys()])
        params = list(update_data.values())
        params.append(employee_id)
        
        sql = f"UPDATE employees SET {set_clause} WHERE id = %s"
        cursor.execute(sql, params)
        
        conn.commit()
        return jsonify({'message': 'Employee updated successfully'}), 200
    except mysql.connector.Error as err:
        return jsonify({'error': f'Database error: {err}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# DELETE: Nonaktifkan karyawan (soft delete)
@app.route('/api/employees/<string:employee_id>', methods=['DELETE'])
@admin_required
def delete_employee(employee_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE employees 
            SET is_active=0 
            WHERE id=%s
        ''', (employee_id,))
        conn.commit()
        return jsonify({'message': 'Employee deactivated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# GET: Ambil data absensi dengan filter
@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    date = request.args.get('date')
    branch = request.args.get('branch')

    query = '''
        SELECT a.*, e.name, e.branch_id, e.shift_start, e.shift_end
        FROM attendance a
        JOIN employees e ON a.employee_id = e.id
        WHERE 1=1
    '''
    params = []

    if date:
        query += ' AND a.date = %s'
        params.append(date)
    if branch:
        query += ' AND e.branch_id = %s'
        params.append(branch)

    query += ' ORDER BY a.date DESC, e.name'

    cursor.execute(query, params)
    rows = cursor.fetchall()

    attendance = []
    for row in rows:
        attendance.append({
            'employee_id': row['employee_id'],
            'name': row['name'],
            'branch_id': row['branch_id'],
            'shift_start': str(row['shift_start']) if row['shift_start'] else '-',
            'shift_end': str(row['shift_end']) if row['shift_end'] else '-',
            'check_in': str(row['check_in']) if row['check_in'] else '-',
            'check_out': str(row['check_out']) if row['check_out'] else '-',
            'date': str(row['date']),
            'overtime_minutes': row['overtime_minutes'] or 0,
            'late_minutes': row['late_minutes'] or 0
        })

    conn.close()
    return jsonify(attendance)

# GET /api/attendance/logs - Mengambil SEMUA riwayat fingerprint (Log Mentah)
@app.route('/api/attendance/logs', methods=['GET'])
@login_required
def get_attendance_logs():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    date = request.args.get('date')
    employee_id = request.args.get('employee_id')
    
    query = '''
        SELECT l.*, e.name as employee_name, e.branch_id
        FROM attendance_logs l
        JOIN employees e ON l.employee_id = e.id
        WHERE 1=1
    '''
    params = []
    
    if date:
        query += ' AND DATE(l.timestamp) = %s'
        params.append(date)
    if employee_id:
        query += ' AND l.employee_id = %s'
        params.append(employee_id)
        
    query += ' ORDER BY l.timestamp DESC LIMIT 500'
    
    cursor.execute(query, params)
    logs = cursor.fetchall()
    conn.close()
    
    # Format timestamp
    for l in logs:
        if l['timestamp'] and hasattr(l['timestamp'], 'strftime'):
            l['timestamp'] = l['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        else:
            l['timestamp'] = str(l['timestamp'])
            
    return jsonify(logs)

# POST: Tambah data absensi
@app.route('/api/attendance', methods=['POST'])
def add_attendance():
    data = request.json
    required_fields = ['employee_id', 'date']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Cek apakah karyawan ada
    cursor.execute('SELECT id FROM employees WHERE id=%s', (data['employee_id'],))
    if not cursor.fetchone():
        return jsonify({'error': 'Employee not found'}), 404
    
    # Cek apakah sudah ada data attendance di tanggal tersebut untuk karyawan tersebut
    cursor.execute('''
        SELECT id FROM attendance 
        WHERE employee_id=%s AND date=%s
    ''', (data['employee_id'], data['date']))
    
    existing = cursor.fetchone()
    
    try:
        if existing:
            # Update
            update_fields = []
            values = []
            for field in ['check_in', 'check_out', 'overtime_minutes', 'late_minutes', 'status']:
                if field in data:
                    update_fields.append(f"{field}=%s")
                    values.append(data[field])
            values.append(existing['id'])
            cursor.execute(f'''
                UPDATE attendance 
                SET {', '.join(update_fields)}
                WHERE id=%s
            ''', values)
            message = 'Attendance updated'
        else:
            # Insert
            cursor.execute('''
                INSERT INTO attendance (employee_id, date, check_in, check_out, overtime_minutes, late_minutes, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                data['employee_id'],
                data['date'],
                data.get('check_in'),
                data.get('check_out'),
                data.get('overtime_minutes', 0),
                data.get('late_minutes', 0),
                data.get('status', 'present')
            ))
            message = 'Attendance added'
        
        conn.commit()
        return jsonify({'message': message}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# GET /api/employees
@app.route('/api/employees', methods=['GET'])
@login_required
def get_all_employees():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Ambil parameter filter
    branch = request.args.get('branch')
    active = request.args.get('active')
    
    query = 'SELECT * FROM employees'
    conditions = []
    params = []
    
    if branch:
        conditions.append('branch_id=%s')
        params.append(branch)
    if active is not None:
        if active.lower() == 'true':
            conditions.append('is_active=1')
        elif active.lower() == 'false':
            conditions.append('is_active=0')
    
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    
    query += ' ORDER BY name'
    
    cursor.execute(query, params)
    employees = cursor.fetchall()
    
    conn.close()
    return jsonify(employees)
    
# POST /api/employees
@app.route('/api/employees', methods=['POST'])
@admin_required
def add_employee():
    # Ambil data dari frontend (JSON)
    data = request.json
    
    # Validasi
    if not data or 'id' not in data or 'name' not in data:
        return jsonify({'error': 'ID dan Nama wajib diisi'}), 400
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Hitung contract_end_date jika ada start_date dan contract_duration_months
        contract_end_date = None
        start_date = data.get('start_date')
        if not start_date: # Handle empty string or None
            start_date = None
            
        contract_duration = data.get('contract_duration_months')
        if contract_duration == '':
            contract_duration = None

        if start_date and contract_duration:
            from datetime import datetime, timedelta
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                # Approximate: 1 month = 30 days
                months = int(contract_duration)
                end = start + timedelta(days=months * 30)
                contract_end_date = end.strftime('%Y-%m-%d')
            except ValueError:
                start_date = None # Invalid format, treat as None
        
        cursor.execute('''
            INSERT INTO employees (id, name, position, department, branch_id, shift_start, shift_end, 
                                   start_date, contract_duration_months, contract_end_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data['id'],
            data['name'],
            data.get('position', ''),
            data.get('department', ''),
            data.get('branch_id', 'sorrento'),
            data.get('shift_start', '09:00'),
            data.get('shift_end', '17:00'),
            start_date,
            contract_duration,
            contract_end_date
        ))
        
        conn.commit()
        return jsonify({'message': 'Karyawan berhasil ditambahkan!', 'id': data['id']}), 201
        
    except mysql.connector.IntegrityError:
        return jsonify({'error': 'ID karyawan sudah ada!'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# --- Cabang ---
# GET /api/branches
@app.route('/api/branches', methods=['GET'])
def get_branches():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT id, name, color_class FROM branches ORDER BY name')
    rows = cursor.fetchall()
    conn.close()

    # Format sama dengan config.js: id, name, colorClass
    branches = [
        {
            'id': row['id'],
            'name': row['name'],
            'colorClass': row['color_class'] or row['id']
        }
        for row in rows
    ]
    return jsonify(branches)

# --- Dashboard ---
# GET /api/dashboard/stats
@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():  
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Total karyawan aktif
    cursor.execute("SELECT COUNT(*) as total FROM employees WHERE is_active = 1")
    total = cursor.fetchone()['total']
    
    # Hadir hari ini (Sudah check-in tapi BELUM check-out)
    cursor.execute('''
        SELECT COUNT(*) as present 
        FROM attendance 
        WHERE date = CURDATE() 
        AND check_in IS NOT NULL 
        AND check_out IS NULL
    ''')
    present = cursor.fetchone()['present']

    # Hadir per cabang (untuk update card dashboard)
    cursor.execute('''
        SELECT e.branch_id, COUNT(a.id) as count
        FROM employees e
        JOIN attendance a ON e.id = a.employee_id
        WHERE a.date = CURDATE() 
        AND a.check_in IS NOT NULL 
        AND a.check_out IS NULL
        GROUP BY e.branch_id
    ''')
    branch_counts = {row['branch_id']: row['count'] for row in cursor.fetchall()}
    
    conn.close()
    
    return jsonify({
        'total_employees': total,
        'present_today': present,
        'branch_counts': branch_counts
    })

# GET /api/attendance/today
@app.route('/api/attendance/today', methods=['GET'])
@login_required
def attendance_today():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Gabungkan data karyawan dengan absensi
    cursor.execute('''
        SELECT e.id as employee_id, e.name, e.branch_id, e.shift_start, e.shift_end,
               a.check_in, a.check_out, a.late_minutes, a.overtime_minutes,
               COALESCE(a.date, CURDATE()) as record_date
        FROM employees e
        LEFT JOIN attendance a ON e.id = a.employee_id AND a.date = CURDATE()
    '''
    # REMOVED: WHERE e.is_active = 1 (Agar data hari ini terlihat untuk semua termasuk yang baru resign)
    )
    
    attendance = []
    for row in cursor.fetchall():
        attendance.append({
            'employee_id': row['employee_id'],
            'name': row['name'],
            'branch_id': row['branch_id'],
            'shift_start': str(row['shift_start']) if row['shift_start'] else '-',
            'shift_end': str(row['shift_end']) if row['shift_end'] else '-',
            'check_in': str(row['check_in']) if row['check_in'] else '-',
            'check_out': str(row['check_out']) if row['check_out'] else '-',
            'date': str(row['record_date']),
            'overtime_minutes': row['overtime_minutes'] or 0,
            'late_minutes': row['late_minutes'] or 0
        })
    
    conn.close()
    return jsonify(attendance)

# GET /api/reports/monthly - Laporan dengan date range
@app.route('/api/reports/monthly', methods=['GET'])
@login_required
def monthly_report():
    """
    Endpoint untuk laporan dengan date range
    Query params:
    - start_date: format YYYY-MM-DD (contoh: 2026-02-01)
    - end_date: format YYYY-MM-DD (contoh: 2026-02-28)
    - branch: optional, filter by branch_id
    """
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    branch = request.args.get('branch')
    
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date parameters required (format: YYYY-MM-DD)'}), 400
    
    # Query untuk mengambil data detail absensi di range tanggal tersebut
    query = '''
        SELECT 
            a.date,
            e.id,
            e.name,
            e.position,
            e.branch_id,
            e.shift_start,
            e.shift_end,
            a.check_in,
            a.check_out,
            a.late_minutes,
            a.overtime_minutes
        FROM employees e
        JOIN attendance a ON e.id = a.employee_id 
        WHERE a.date BETWEEN %s AND %s
    '''
    # REMOVED: AND e.is_active = 1 (Agar data history tetap muncul)
    
    params = [start_date, end_date]
    
    if branch:
        query += ' AND e.branch_id = %s'
        params.append(branch)
    
    query += ' ORDER BY a.date DESC, e.branch_id, e.name'
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    # Format hasil
    report_data = []
    total_present = 0
    total_overtime = 0
    total_late = 0
    unique_employees = set()
    
    for row in rows:
        unique_employees.add(row['id'])
        total_present += 1
        total_overtime += row['overtime_minutes'] or 0
        total_late += row['late_minutes'] or 0
        
        report_data.append({
            'date': row['date'],
            'employee_id': row['id'],
            'name': row['name'],
            'position': row['position'],
            'branch_id': row['branch_id'],
            'shift_start': str(row['shift_start']),
            'shift_end': str(row['shift_end']),
            'check_in': str(row['check_in']) if row['check_in'] else '-',
            'check_out': str(row['check_out']) if row['check_out'] else '-',
            'late_minutes': row['late_minutes'] or 0,
            'overtime_minutes': row['overtime_minutes'] or 0
        })
    
    # Summary per cabang
    branch_summary_query = '''
        SELECT 
            e.branch_id,
            COUNT(DISTINCT e.id) as total_employees,
            COUNT(a.id) as total_attendance,
            COALESCE(SUM(a.overtime_minutes), 0) as total_overtime,
            COUNT(CASE WHEN a.late_minutes > 0 THEN 1 END) as total_late_count
        FROM employees e
        LEFT JOIN attendance a ON e.id = a.employee_id 
            AND a.date BETWEEN %s AND %s
    '''
    # REMOVED: WHERE e.is_active = 1 (Agar statistik data sejarah tetap lengkap)
    
    branch_params = [start_date, end_date]
    if branch:
        branch_summary_query += ' AND e.branch_id = %s'
        branch_params.append(branch)
    
    branch_summary_query += ' GROUP BY e.branch_id'
    
    cursor.execute(branch_summary_query, branch_params)
    branch_rows = cursor.fetchall()
    
    branch_summary = []
    for row in branch_rows:
        # Hitung persentase kehadiran berdasarkan jumlah hari di range
        from datetime import datetime
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        working_days = (end - start).days + 1
        attendance_rate = (row['total_attendance'] / (row['total_employees'] * working_days) * 100) if row['total_employees'] > 0 else 0
        
        branch_summary.append({
            'branch_id': row['branch_id'],
            'total_employees': row['total_employees'],
            'attendance_rate': round(attendance_rate, 1),
            'total_overtime_hours': round(row['total_overtime'] / 60, 1),
            'total_late_count': row['total_late_count']
        })
    
    conn.close()
    
    return jsonify({
        'start_date': start_date,
        'end_date': end_date,
        'summary': {
            'total_employees': len(unique_employees),
            'total_present': total_present,
            'total_overtime_hours': round(float(total_overtime) / 60.0, 1),
            'total_late_minutes': total_late
        },
        'employees': report_data,
        'branch_summary': branch_summary
    })

# GET /api/reports/export - Export Laporan ke Excel
@app.route('/api/reports/export', methods=['GET'])
@login_required
def export_report():
    from io import BytesIO

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    branch = request.args.get('branch')
    
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date required'}), 400

    # Gunakan logic query yang sama dengan monthly_report
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    query = '''
        SELECT 
            a.date,
            e.id,
            e.name,
            e.position,
            e.department,
            e.branch_id,
            e.shift_start,
            e.shift_end,
            a.check_in,
            a.check_out,
            a.late_minutes,
            a.overtime_minutes,
            (SELECT GROUP_CONCAT(DATE_FORMAT(timestamp, '%H:%i') ORDER BY timestamp SEPARATOR ', ') 
             FROM attendance_logs 
             WHERE employee_id = e.id AND DATE(timestamp) = a.date) as all_taps
        FROM employees e
        JOIN attendance a ON e.id = a.employee_id 
        WHERE a.date BETWEEN %s AND %s
    '''
    # REMOVED: AND e.is_active = 1 (Agar export data sejarah tetap lengkap)
    
    params = [start_date, end_date]
    if branch:
        query += ' AND e.branch_id = %s'
        params.append(branch)
    
    query += ' ORDER BY a.date DESC, e.branch_id, e.name'
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Siapkan data untuk DataFrame
    data = []
    for idx, row in enumerate(rows, 1):
        data.append({
            'No': idx,
            'Tanggal': row['date'],
            'ID Karyawan': row['id'],
            'Nama Lengkap': row['name'],
            'Cabang': row['branch_id'],
            'Shift Masuk': str(row['shift_start']),
            'Shift Keluar': str(row['shift_end']),
            'Check-In': str(row['check_in']) if row['check_in'] else '-',
            'Check-Out': str(row['check_out']) if row['check_out'] else '-',
            'Keterlambatan (Menit)': row['late_minutes'] or 0,
            'Lembur (Menit)': row['overtime_minutes'] or 0,
            'Semua Riwayat Tap': row['all_taps'] or '-'
        })

    # Buat DataFrame
    if not data:
        df = pd.DataFrame(columns=['No', 'Tanggal', 'ID Karyawan', 'Nama Lengkap', 'Cabang', 'Shift Masuk', 'Shift Keluar', 'Check-In', 'Check-Out', 'Keterlambatan (Menit)', 'Lembur (Menit)', 'Semua Riwayat Tap'])
    else:
        df = pd.DataFrame(data)
    
    # Export ke Excel di memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Laporan Absensi')
        
        # Auto-adjust column width and styling
        ws = writer.sheets['Laporan Absensi']
        
        # Style for Header
        header_font = Font(bold=True)
        center_alignment = Alignment(horizontal='center', vertical='center')
        left_alignment = Alignment(horizontal='left', vertical='center')

        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                # Apply alignment
                if cell.row == 1:
                    cell.alignment = center_alignment
                    cell.font = header_font
                else:
                    cell.alignment = left_alignment
                
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = max(len(str(column[0].value)) + 4, int(max_length) + 2)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    filename = f"Laporan_Absensi_{start_date}_sd_{end_date}.xlsx"
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

# GET /api/reports/export-logs - Export SEMUA LOG MENTAH ke Excel
@app.route('/api/reports/export-logs', methods=['GET'])
@login_required
def export_raw_logs():
    from io import BytesIO

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    query = '''
        SELECT l.timestamp, l.employee_id, e.name, e.branch_id, 
               CASE WHEN l.status = 0 THEN 'Check-in' ELSE 'Check-out' END as status_desc,
               l.device_id
        FROM attendance_logs l
        JOIN employees e ON l.employee_id = e.id
        WHERE DATE(l.timestamp) BETWEEN %s AND %s
        ORDER BY l.timestamp DESC
    '''
    cursor.execute(query, [start_date, end_date])
    rows = cursor.fetchall()
    conn.close()

    data = []
    for idx, row in enumerate(rows, 1):
        data.append({
            'No': idx,
            'Waktu Tap': str(row['timestamp']),
            'ID Karyawan': row['employee_id'],
            'Nama Lengkap': row['name'],
            'Cabang': row['branch_id'],
            'Aksi': row['status_desc'],
            'ID Mesin': row['device_id']
        })

    df = pd.DataFrame(data) if data else pd.DataFrame(columns=['No', 'Waktu Tap', 'ID Karyawan', 'Nama Lengkap', 'Cabang', 'Aksi', 'ID Mesin'])
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Semua Histori Absensi')
        
        ws = writer.sheets['Semua Histori Absensi']
        header_font = Font(bold=True)
        center_alignment = Alignment(horizontal='center', vertical='center')
        left_alignment = Alignment(horizontal='left', vertical='center')
        
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                if cell.row == 1:
                    cell.alignment = center_alignment
                    cell.font = header_font
                else:
                    cell.alignment = left_alignment
                
                try:
                    val = str(cell.value) if cell.value is not None else ""
                    if len(val) > max_length:
                        max_length = len(val)
                except:
                    pass
            
            adjusted_width = max(len(str(column[0].value)) + 4, int(max_length) + 2)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    filename = f"Histori_Lengkap_Absensi_{start_date}_sd_{end_date}.xlsx"
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=filename)

# JALANKAN SERVER
if __name__ == '__main__':
    # Cek koneksi database MySQL
    try:
        conn = get_db()
        conn.ping(reconnect=True)
        conn.close()
        print("Koneksi database berhasil")
    except Exception as e:
        print(f"Koneksi database gagal: {e}")
    
    print("\n" + "-"*50)
    print("SERVER HRIS BERJALAN")
    print("-"*50)
    
    app_domain = os.getenv('APP_DOMAIN', 'hris.tamvan.web.id')
    print(f"Production: https://{app_domain}")
    
if __name__ == '__main__':
    # Listen di 0.0.0.0 agar bisa diakses dari luar container Docker
    app.run(host='0.0.0.0', port=5000)
