# RotiKebanggaan HRIS

Sistem HRIS internal yang dikembangkan untuk mendukung operasional RotiKebanggaan, khususnya dalam pengelolaan data karyawan dan absensi multi-cabang. Sistem ini dibuat untuk mengurangi proses rekap manual, meminimalkan kesalahan perhitungan, serta mempercepat proses monitoring dan pelaporan kehadiran karyawan.

## Tujuan Pengembangan

**HRIS ini dikembangkan secara internal untuk:**
- Mengelola data karyawan secara terpusat.
- Mengintegrasikan mesin absensi fingerprint langsung ke sistem.
- Mengotomatisasi perhitungan keterlambatan dan lembur.
- Mempermudah pengelolaan cabang yang terus bertambah.
- Menghilangkan proses rekap manual yang memakan waktu dan rawan error.


## Fitur Utama
### Manajemen Karyawan
- Input dan pengelolaan data karyawan.
- Pengaturan kontrak kerja.
- Penentuan shift kerja.
- Penempatan cabang.


### 3. Sistem Absensi Otomatis (ADMS)
- Integrasi langsung dengan mesin fingerprint (Solution/ZKTeco) menggunakan protokol PUSH SDK (ADMS).
- Sinkronisasi data otomatis tanpa perlu download log manual dari mesin.
- Deteksi cerdas status Check-in vs Check-out berdasarkan jam kerja.

### 4. Pelaporan Profesional
- Kalkulasi otomatis jam lembur dan menit keterlambatan.
- Laporan bulanan mendalam yang dapat difilter berdasarkan tanggal dan cabang.
- Ekspor laporan langsung ke format Excel (.xlsx) siap cetak.

---

## Stack Teknologi

Dibuat dengan pondasi yang ringan namun kuat untuk performa maksimal:
- **Backend:** Python 3.10 (Flask) + Gunicorn
- **Database:** MySQL 8.0
- **Frontend:** Vanilla HTML5, CSS3, & Modern JavaScript (ES6+)
- **Reverse Proxy:** Nginx
- **Containerization:** Docker & Docker Compose
- **Security:** Secret key encryption, Environment variables, & Cloudflare Tunnel support.

---

## Panduan Instalasi & Deployment

Ikuti langkah-langkah berikut untuk menjalankan sistem di lingkungan server atau lokal Anda:

### 1. Persiapan Environment
Clone repositori ini dan masuk ke direktori project:
```bash
git clone https://github.com/username/hris-website.git
cd hris-website
```

### 2. Konfigurasi Variabel Lingkungan
Buat file `.env` di direktori root dan sesuaikan nilainya:
```env
# Database
DB_HOST=db
DB_NAME=hris
DB_USER=admin_user
DB_PASSWORD=your_secure_password
DB_ROOT_PASSWORD=your_root_password
DB_PORT=3306

# Security
SECRET_KEY=isi_dengan_string_flask_secret_key
APP_DOMAIN=yourdomain.com

# Cloudflare (Opsional)
CLOUDFLARE_TUNNEL_TOKEN=token_tunnel_anda
```

> [!TIP]
> **Cara generat SECRET_KEY:** Jalankan perintah ini di terminal Anda:  
> `python3 -c 'import secrets; print(secrets.token_hex(32))'`

### 3. Jalankan dengan Docker Compose
Pastikan Docker dan Docker Compose sudah terinstall. Jalankan perintah berikut:
```bash
docker-compose up -d --build
```

### 4. Inisialisasi Database
Setelah container berjalan, jalankan script inisialisasi untuk membuat tabel dan user admin pertama:
```bash
docker-compose exec app python backend/init_db.py
```
*Username default: `admin` | Password default: `admin123`*

### 5. Data Dummy & Testing (Opsional)
Jika Anda ingin mencoba sistem dengan data simulasi (60+ karyawan & riwayat absensi), gunakan file SQL yang tersedia di folder `backend/`:
- **`seed_data.sql`**: Import file ini ke phpMyAdmin atau jalankan di MySQL untuk mengisi data dummy.
- **`cleanup_data.sql`**: Jalankan file ini jika ingin menghapus seluruh data dummy dari sistem.

---

## Gambaran Antarmuka

Berikut adalah struktur visual sistem:

| Halaman | Deskripsi |
| :--- | :--- |
| **Login Page** | Keamanan akses dengan latar belakang kustom dan responsif. |
| **Main Dashboard** | Menampilkan statistik cepat, status mesin, dan navigasi utama. |
| **Employee List** | Tabel interaktif untuk edit, hapus, dan tambah karyawan baru. |
| **Attendance Logs** | Riwayat mentah dari mesin beserta status deteksi otomatis. |
| **Monthly Report** | Ringkasan produktivitas, lembur, dan keterlambatan per periode. |

*(Anda dapat menyematkan screenshot di sini untuk mempercantik tampilan repositori)*

---

## Integrasi Mesin Fingerprint (ADMS)

Untuk menghubungkan mesin fingerprint Anda ke sistem ini:
1. Masuk ke menu **COMM/Network** di mesin.
2. Cari pengaturan **ADMS / Cloud Server**.
3. Masukkan **Server Address**: `http://domain-anda.com` (atau IP Server).
4. Masukkan **Server Port**: `80`.
5. Aktifkan fitur **Enable Proxy Server** jika diperlukan.

---

## Lisensi & Pengembang

Dikembangkan dengan dedikasi untuk efisiensi operasional.
**IT Division - HRIS Project - DnnTech**
© 2026 