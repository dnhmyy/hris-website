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


### Sistem Absensi
- Integrasi mesin fingerprint (Solution / ZKTeco via ADMS).
- Dukungan input manual jika terjadi kendala mesin.
- Validasi data check-in dan check-out.


### Laporan & Perhitungan Otomatis
- Perhitungan keterlambatan berbasis shift.
- Perhitungan lembur berbasis jam shift selesai.
- Rekap absensi bulanan.
- Export laporan ke Excel.


### Monitoring Mesin
- Status mesin absensi (online / offline).
- Monitoring dari dashboard pusat.


## Arsitektur & Tech Stack
Dirancang sederhana, ringan, dan mudah dikelola oleh tim internal.
- Backend: Python (Flask) + MySQL
- Frontend: HTML, CSS, JavaScript (tanpa framework berat)
- Deployment: Dockerized
- Reverse Proxy: Nginx
- Remote Access: Cloudflare Tunnel
Fokus utama adalah stabilitas, kemudahan maintenance, dan efisiensi resource server.


## Cara Menjalankan (Development)
- Pastikan Docker sudah terpasang, kemudian:
- Salin file .env.example menjadi .env.
- Sesuaikan konfigurasi database dan environment.
- Jalankan:
docker-compose up -d --build
- Akses melalui:
http://localhost


## Integrasi Mesin Absensi (ADMS)
Untuk menghubungkan mesin fingerprint:
- Server Address: arahkan ke IP server HRIS.
- Push URL: http://<ip-server>/iclock/cdata
- Port default: 80
Pastikan server dapat diakses oleh mesin dalam jaringan yang sama atau melalui tunnel yang sudah dikonfigurasi.


## Pengembangan Internal
Sistem ini dikembangkan secara internal untuk mendukung kebutuhan operasional RotiKebanggaan yang memiliki beberapa cabang dan terus berkembang.

Tujuan utama:
mengurangi beban kerja manual HR, meningkatkan akurasi data, dan mempermudah proses monitoring lintas cabang.


👨‍💻Pengembang
Dikembangkan secara internal oleh:
DnnTech
RotiKebanggaan IT Division – 2026