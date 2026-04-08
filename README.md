# HRIS ADMS Integration System

Sistem Informasi Manajemen Sumber Daya Manusia (HRIS) yang dirancang untuk mengelola data karyawan dan absensi secara efisien. Sistem ini terintegrasi langsung dengan mesin fingerprint dan mendukung operasional multi-cabang untuk pemantauan data yang tersentralisasi.

---

## Fitur Utama

Sistem ini dikembangkan untuk mengoptimalkan manajemen SDM melalui berbagai fitur strategis:

### 1. Dashboard Monitoring Real-Time
- Pemantauan kehadiran harian per cabang secara instan.
- Status konektivitas mesin absensi di seluruh lokasi.
- Ringkasan statistik keterlambatan dan jumlah SDM aktif.

### 2. Manajemen Karyawan Terintegrasi
- Pengelolaan profil dan basis data karyawan yang komprehensif.
- Administrasi kontrak kerja, konfigurasi shift, dan penempatan cabang.
- Struktur data yang fleksibel untuk kebutuhan organisasi yang dinamis.

### 3. Otomatisasi Absensi (ADMS)
- Integrasi penuh dengan mesin fingerprint (Solution/ZKTeco) via protokol PUSH SDK.
- Sinkronisasi data otomatis tanpa intervensi manual.
- Logika deteksi status check-in dan check-out yang adaptif berdasarkan jam kerja.

### 4. Pelaporan & Analitik Profesional
- Kalkulasi otomatis untuk lembur, keterlambatan, dan jam kerja efektif.
- Laporan bulanan mendalam dengan filter multidimensi (tanggal dan cabang).
- Ekspor data ke format Excel (.xlsx) dengan tata letak siap cetak.

---

## Stack Teknologi

Dibangun dengan arsitektur modern untuk memastikan performa dan skalabilitas:

- **Backend:** Python 3.10 (Flask) & Gunicorn
- **Database:** MySQL 8.0
- **Frontend:** Vanilla HTML5, CSS3, & Modern JavaScript (ES6+)
- **Reverse Proxy:** Nginx
- **Infrastructure:** Docker & Docker Compose
- **Security:** Data encryption, secure environment handling, & Cloudflare Tunnel support.

---

## Gambaran Antarmuka

Visualisasi antarmuka sistem yang dirancang untuk kemudahan penggunaan:

| Halaman | Deskripsi | Preview |
| :--- | :--- | :--- |
| **Login Page** | Akses aman dengan desain responsif. | ![Login](public/login.png) |
| **Main Dashboard** | Pusat kendali informasi dan status sistem. | ![Dashboard](public/dashboard.png) |
| **Employee List** | Manajemen data karyawan yang intuitif. | ![Karyawan](public/karyawan.png) |
| **Attendance Logs** | Rekam jejak absensi mentah dengan deteksi otomatis. | ![Absensi](public/absensi.png) |
| **Monthly Report** | Ringkasan kinerja dan kehadiran per periode. | ![Attendance](public/attedance.png) ![Attendance 2](public/attedance2.png) |

---

## Integrasi Mesin Fingerprint (ADMS)

Sistem menggunakan arsitektur PUSH untuk komunikasi dua arah antara server dan perangkat:

1. Konfigurasi **COMM/Network** pada perangkat fingerprint.
2. Pengaturan **ADMS / Cloud Server** mengarah ke domain atau IP server utama.
3. Penggunaan port standar atau kustom sesuai kebijakan keamanan jaringan.
4. Mendukung sinkronisasi data lintas jaringan melalui proxy atau tunnel.

---

## Lisensi & Pengembang

Dikembangkan untuk memberikan solusi manajemen SDM yang efisien dan andal.

**IT Division - HRIS Project - DnnTech**  
© 2026
