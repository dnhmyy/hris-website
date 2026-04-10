# backend/init_db.py
import mysql.connector
import os
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

_env_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_env_dir)
load_dotenv(os.path.join(_env_dir, '.env'))
load_dotenv(os.path.join(_root_dir, '.env'))
load_dotenv(os.path.join(_env_dir, '.env.local'), override=True)
load_dotenv(os.path.join(_root_dir, '.env.local'), override=True)

def init_database():
    # Koneksi ke layanan database MySQL
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        port=int(os.getenv('DB_PORT', 3306))
    )
    cursor = conn.cursor()

    # Buat database
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {os.getenv('DB_NAME', 'hris')}")
    cursor.execute(f"USE {os.getenv('DB_NAME', 'hris')}")

    # Buat tabel employees
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            position VARCHAR(255),
            department VARCHAR(255),
            is_active TINYINT(1) DEFAULT 1,
            branch_id VARCHAR(50),
            shift_start VARCHAR(10) DEFAULT '09:00',
            shift_end VARCHAR(10) DEFAULT '17:00',
            start_date DATE,
            contract_duration_months INT,
            contract_end_date DATE
        )
    ''')

    # Buat tabel attendance
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50),
            date DATE DEFAULT (CURRENT_DATE),
            check_in TIME,
            check_out TIME,
            overtime_minutes INT DEFAULT 0,
            late_minutes INT DEFAULT 0,
            status VARCHAR(50) DEFAULT 'present',
            FOREIGN KEY (employee_id) REFERENCES employees(id),
            UNIQUE KEY (employee_id, date)
        )
    ''')

    # Buat tabel branches (jika ingin menyimpan cabang di database)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS branches (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            color_class VARCHAR(50)
        )
    ''')

    # Buat tabel log absensi (untuk mencatat SEMUA fingerprint tanpa terkecuali)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id VARCHAR(50),
            timestamp DATETIME,
            status INT, -- 0: Check-in, 1: Check-out
            device_id VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    ''')

    # Insert data contoh untuk branches (sesuai dengan config.js)
    branches = [
        ('sorrento', 'Sorrento', 'sorrento'),
        ('beryl', 'Beryl', 'beryl'),
        ('downtown', 'Downtown', 'downtown'),
        ('greenlake', 'Greenlake', 'greenlake'),
        ('mkg', 'MKG', 'mkg'),
        ('grandindonesia', 'Grand Indonesia', 'grandindonesia'),
        ('p9', 'P9', 'p9'),
        ('dapursolvang', 'Dapur Solvang', 'dapursolvang'),
        ('pastrysolvang', 'Pastry Solvang', 'pastrysolvang'),
        ('enchante', 'Enchante', 'enchante'),
    ]
    cursor.executemany('INSERT IGNORE INTO branches (id, name, color_class) VALUES (%s, %s, %s)', branches)

    # Insert data contoh untuk employees (branch_id harus ada di tabel branches)
    employees = [
    ]
    cursor.executemany('INSERT IGNORE INTO employees (id, name, position, department, is_active, branch_id, shift_start, shift_end) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', employees)

    # Buat tabel users untuk login
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'admin'
        )
    ''')

    # Akun administrator default
    cursor.execute('SELECT id FROM users WHERE username = %s', ('admin',))
    admin_exists = cursor.fetchone()
    if not admin_exists:
        hashed_pw = generate_password_hash('admin123')
        cursor.execute('INSERT INTO users (username, password, role) VALUES (%s, %s, %s)', ('admin', hashed_pw, 'admin'))

    # device_key = kunci otentikasi unik untuk setiap mesin absensi.
    # device_ip = alamat host atau IP mesin (digunakan sebagai referensi).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_devices (
            id VARCHAR(50) PRIMARY KEY,
            branch_id VARCHAR(50),
            device_name VARCHAR(255),
            device_ip VARCHAR(50),
            last_sync TIMESTAMP,
            status VARCHAR(50) DEFAULT 'active',
            serial_no VARCHAR(100),
            mac_address VARCHAR(50),
            model VARCHAR(100),
            platform VARCHAR(100),
            manufacturer VARCHAR(100),
            device_key VARCHAR(255)
        )
    ''')

    # Kolom tambahan jika tabel sudah ada (migrasi)
    for col, defn in [
        ('serial_no', 'VARCHAR(100)'),
        ('mac_address', 'VARCHAR(50)'),
        ('model', 'VARCHAR(100)'),
        ('platform', 'VARCHAR(100)'),
        ('manufacturer', 'VARCHAR(100)'),
        ('device_key', 'VARCHAR(255)'),
        # PUSH SDK Protocol: Stamp tracking
        ('last_attlog_stamp', 'INT DEFAULT 0'),
        ('last_operlog_stamp', 'INT DEFAULT 0'),
        ('last_attphoto_stamp', 'INT DEFAULT 0'),
        # PUSH SDK Protocol: Configuration parameters
        ('push_delay', 'INT DEFAULT 10'),
        ('error_delay', 'INT DEFAULT 30'),
        ('realtime_mode', 'TINYINT DEFAULT 1'),
        ('timezone_offset', 'INT DEFAULT 7'),
        ('trans_times', 'VARCHAR(100) DEFAULT "00:00;14:05"'),
        ('trans_interval', 'INT DEFAULT 1'),
        ('trans_flag', 'VARCHAR(255) DEFAULT "TransData AttLog OpLog"'),
    ]:
        try:
            print(f"Adding column {col}...")
            cursor.execute(f'ALTER TABLE attendance_devices ADD COLUMN {col} {defn}')
        except mysql.connector.Error as err:
            print(f"Column {col} might already exist or error: {err}")
            pass

    try:
        cursor.execute('ALTER TABLE employees ADD COLUMN device_pin VARCHAR(50)')
    except mysql.connector.Error:
        pass  # Kolom sudah ada

    # Migrasi kolom durasi kontrak & start_date
    for col, defn in [
        ('start_date', 'DATE'),
        ('contract_duration_months', 'INT'),
        ('contract_end_date', 'DATE'),
    ]:
        try:
            cursor.execute(f'ALTER TABLE employees ADD COLUMN {col} {defn}')
        except mysql.connector.Error:
            pass

    # Konfigurasi perangkat/mesin absensi
    app_domain = os.getenv('APP_DOMAIN', 'hris.tamvan.web.id')
    devices = [
        # Template mesin X105 (Solution)
        (
            'CKEB223560955',            # id: serial number
            'p9',                       # branch_id
            'X105 Fingerprint',         # device_name
            app_domain,                 # device_ip/domain
            'YOUR_SECRET_DEVICE_KEY', # device_key
            'CKEB223560955',            # serial_no
            '00:17:61:12:7e:04',        # mac_address
            'X105',                     # model
            'ZLM60_TFT',                # platform
            'Solution',                 # manufacturer
        ),
    ]
    for d in devices:
        cursor.execute('''
            INSERT INTO attendance_devices 
            (id, branch_id, device_name, device_ip, device_key, serial_no, mac_address, model, platform, manufacturer)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            branch_id = VALUES(branch_id),
            device_name = VALUES(device_name),
            device_ip = VALUES(device_ip),
            device_key = VALUES(device_key),
            serial_no = VALUES(serial_no),
            mac_address = VALUES(mac_address),
            model = VALUES(model),
            platform = VALUES(platform),
            manufacturer = VALUES(manufacturer)
        ''', d)

    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_database()
