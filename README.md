# HRIS ADMS Integration System

Sistem Informasi Manajemen Sumber Daya Manusia (HRIS) yang dirancang untuk mengelola data karyawan dan absensi secara efisien, terintegrasi dengan mesin fingerprint, serta mendukung operasional multi-cabang.

---

## Fitur Utama

Sistem ini dikembangkan untuk memberikan kemudahan bagi HR dan Operasional melalui fitur-fitur berikut:

### 1. Dashboard Monitoring Berbasis Cabang
- Ringkasan data kehadiran harian per cabang.
- Status koneksi mesin absensi secara *real-time*.
- Statistik keterlambatan dan jumlah karyawan aktif.

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
| **Login Page** | Keamanan akses dengan latar belakang kustom dan responsif. | ![Login](public/login.png) |
| **Main Dashboard** | Menampilkan statistik cepat, status mesin, dan navigasi utama. | ![Dashboard](public/dashboard.png) |
| **Employee List** | Tabel interaktif untuk edit, hapus, dan tambah karyawan baru. | ![Karyawan](public/karyawan.png) |
| **Attendance Logs** | Riwayat mentah dari mesin beserta status deteksi otomatis. | ![Absensi](public/absensi.png) |
| **Monthly Report** | Ringkasan produktivitas, lembur, dan keterlambatan per periode. | ![Attendance](public/attedance.png) ![Attendance 2](public/attedance2.png) |

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
