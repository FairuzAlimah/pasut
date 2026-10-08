# Dashboard Pasang Surut — GitHub Pages

Versi static yang diselaraskan dengan dashboard Python Dash: kartu statistik, peta Leaflet dengan pin, statistik mingguan, validasi EOT20, validasi BIG 2025, Panduan Pemanfaatan, dan Informasi Analisis.

## Struktur
- `index.html`
- `style.css`
- `app.js`
- `data/` berisi CSV hasil `prepare_web_data.py`
- `assets/logo_brin.png` dan `assets/logo_dkp_diy.png` mengikuti nama file Python asli.

## Penting
Salin folder `data/` yang sudah berhasil dipakai pada dashboard static sebelumnya ke folder ini. Salin juga dua logo PNG asli ke `assets/`.

Untuk uji lokal, jalankan `python -m http.server 8000`, lalu buka `http://localhost:8000`.
