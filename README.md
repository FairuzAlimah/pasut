# Dashboard Prediksi Pasang Surut Pantai Selatan DIY

Dashboard ini merupakan aplikasi berbasis web untuk menampilkan hasil prediksi pasang surut di 13 stasiun pantai selatan Daerah Istimewa Yogyakarta (DIY).

Pengolahan data pasang surut dilakukan menggunakan **pyTMD (Python-based Tidal Prediction Software)** dengan model pasang surut **GOT4.10** dan **EOT20**. Hasil pengolahan kemudian digunakan sebagai sumber data pada dashboard berbasis HTML, CSS, dan JavaScript yang dapat dijalankan secara statis melalui GitHub Pages.

---

## 1. Deskripsi Proyek

Dashboard digunakan untuk memvisualisasikan prediksi pasang surut pada wilayah pantai selatan DIY, mulai dari wilayah Kulon Progo hingga Gunungkidul.

Terdapat 13 stasiun pengamatan/prediksi yang digunakan dalam pengolahan data, yaitu:

1. Congot
2. Glagah
3. Bugel
4. Trisik
5. Ngenthak
6. Kuwaru
7. Goa Cemara
8. Samas
9. Depok
10. Ngrenehan
11. Baron
12. Sadeng
13. [Stasiun ke-13 sesuai data pengolahan]

Dashboard menampilkan:

- Prediksi pasang surut tahun 2027–2029
- Grafik pasang surut
- Statistik mingguan
- Tabel data pasang surut
- Validasi silang GOT4.10 dan EOT20
- Validasi terhadap data BIG tahun 2025
- Informasi stasiun
- Peta lokasi stasiun
- Panduan pemanfaatan informasi pasang surut
- Informasi metode analisis

---

# 2. Tujuan

Tujuan utama proyek ini adalah:

1. Menghasilkan prediksi pasang surut untuk wilayah pantai selatan DIY.
2. Mengolah data prediksi menggunakan model GOT4.10 melalui pyTMD.
3. Melakukan validasi silang hasil GOT4.10 dengan model EOT20.
4. Melakukan validasi tambahan menggunakan data BIG tahun 2025.
5. Menyediakan informasi hasil prediksi dalam bentuk dashboard yang mudah digunakan.
6. Menyediakan visualisasi spasial lokasi stasiun melalui peta interaktif.
7. Menyediakan informasi pasang dan surut yang dapat digunakan sebagai bahan pendukung perencanaan aktivitas di wilayah pesisir.

---

# 3. Teknologi yang Digunakan

## Pengolahan Data

Pengolahan data dilakukan menggunakan:

- Python
- pyTMD
- GOT4.10
- EOT20
- NumPy
- Pandas
- SciPy
- Matplotlib
- Timescale

## Dashboard

Dashboard menggunakan:

- HTML
- CSS
- JavaScript
- Leaflet
- Plotly
- CSV

## Deployment

Dashboard dipublikasikan menggunakan:

- GitHub
- GitHub Pages

---

# 4. pyTMD

## Apa itu pyTMD?

**pyTMD** merupakan perangkat lunak berbasis Python yang digunakan untuk melakukan prediksi pasang surut serta analisis berbagai komponen pasang surut.

Pada proyek ini, pyTMD digunakan sebagai library utama untuk melakukan pengolahan prediksi pasang surut menggunakan model:

- GOT4.10
- EOT20

pyTMD digunakan pada tahap pengolahan data Python. Hasil pengolahan kemudian disimpan dalam bentuk file CSV yang digunakan oleh dashboard.

Dokumentasi dan source code pyTMD tersedia pada GitHub resmi pyTMD.

---

# 5. Persiapan Python

Untuk menjalankan proses pengolahan data, diperlukan Python.

Disarankan menggunakan Python versi **3.11** agar lingkungan pengolahan lebih mudah dikontrol.

Python dapat diinstal terlebih dahulu pada komputer.

Setelah instalasi selesai, buka:

- Command Prompt
- Anaconda Prompt
- atau terminal

Kemudian cek instalasi Python dengan:

```bash
python --version
