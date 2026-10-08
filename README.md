<div align="center">

# DASHBOARD PREDIKSI & VALIDASI PASANG SURUT LAUT
### di Wilayah Selatan Yogyakarta 2027–2029

Prediksi pasang surut berbasis **pyTMD** dengan model **GOT** dan **EOT20** pada 13 titik stasiun, dilengkapi validasi terhadap data pengamatan **BIG 2025**.
<br>
</div>

---

## Daftar Isi

1. [Gambaran Umum](#1-gambaran-umum)
2. [Fitur Dashboard](#2-fitur-dashboard)
3. [Struktur Repositori](#3-struktur-repositori)
4. [Metodologi Pengolahan](#4-metodologi-pengolahan)
5. [Persiapan Lingkungan Python](#5-persiapan-lingkungan-python)
6. [Menjalankan Pengolahan Data](#6-menjalankan-pengolahan-data)
7. [Prosedur Pembaruan Data](#7-prosedur-pembaruan-data)
8. [Menjalankan Dashboard Secara Lokal](#8-menjalankan-dashboard-secara-lokal)
9. [Publikasi melalui GitHub Pages](#9-publikasi-melalui-github-pages)
10. [Referensi](#10-referensi)

---

## 1. Gambaran Umum

Dashboard ini menyajikan hasil prediksi pasang surut laut periode **2027–2029** di wilayah pesisir selatan Yogyakarta serta hasil validasinya. Seluruh perhitungan dilakukan secara *offline* menggunakan Python dan pustaka [pyTMD](https://github.com/pyTMD/pyTMD), kemudian hasilnya diekspor ke berkas CSV dan ditampilkan pada halaman web statis (HTML, CSS, JavaScript) tanpa membutuhkan server aplikasi.

| Komponen | Keterangan |
|---|---|
| Perangkat prediksi | pyTMD |
| Model pasut | GOT dan EOT20 |
| Cakupan stasiun | 13 titik stasiun |
| Periode prediksi | 2027–2029 |
| Data validasi | Data pengamatan BIG tahun 2025 |
| Platform tampilan | Web statis (GitHub Pages), peta menggunakan Leaflet |
| Tautan website | <https://fairuzalimah.github.io/pasut/> |

## 2. Fitur Dashboard

- **Kartu statistik**: ringkasan nilai utama pasang surut.
- **Peta interaktif**: sebaran stasiun dalam bentuk pin pada peta Leaflet.
- **Statistik mingguan**: ringkasan pasut per pekan.
- **Validasi EOT20**: perbandingan hasil prediksi dengan model EOT20.
- **Validasi BIG 2025**: perbandingan prediksi dengan data pengamatan BIG tahun 2025.
- **Panduan Pemanfaatan**: petunjuk penggunaan informasi pasut.
- **Informasi Analisis**: penjelasan metode dan data yang dipakai.

## 3. Struktur Repositori

```
.
├── index.html              # Halaman utama dashboard
├── style.css               # Gaya tampilan
├── app.js                  # Logika dashboard (peta, grafik, tabel)
├── data/                   # Berkas CSV hasil pengolahan
├── assets/
│   ├── logo_brin.png
│   └── logo_dkp_diy.png
├── pengolahan.py           # Prediksi pasut 2027–2029 (GOT + EOT20, 13 stasiun)
├── 2025.py                 # Pengolahan validasi data BIG 2025
├── prepare_web_data.py     # Konversi hasil olahan menjadi CSV untuk web
└── README.md
```


## 4. Metodologi Pengolahan

Pengolahan terbagi menjadi dua skrip utama:

| Skrip | Tujuan |
|---|---|
| `pengolahan.py` | Menghitung prediksi pasang surut **2027–2029** menggunakan model **GOT** dan **EOT20** pada **13 titik stasiun** |
| `2025.py` | Mengolah **validasi data BIG tahun 2025** dengan membandingkan hasil prediksi terhadap data pengamatan |

Alur kerja:

```
Model GOT / EOT20 ──► pyTMD ──► pengolahan.py / 2025.py ──► prepare_web_data.py ──► data/*.csv ──► Dashboard
```

## 5. Persiapan Lingkungan Python

### 5.1 Prasyarat

- Python 3.9 atau lebih baru
- `pip` (atau `conda`/`mamba`)
- Berkas model pasut GOT dan EOT20 yang telah diunduh

Periksa versi Python:

```bash
python --version
```

### 5.2 Membuat Virtual Environment (disarankan)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 5.3 Instalasi pyTMD

**Menggunakan pip**

```bash
python -m pip install --upgrade pip
python -m pip install pyTMD
```

Untuk menyertakan seluruh dependensi opsional:

```bash
python -m pip install pyTMD[all]
```

**Menggunakan conda / mamba (conda-forge)**

```bash
conda install -c conda-forge pytmd
# atau
mamba install -c conda-forge pytmd
```

**Versi pengembangan dari GitHub (opsional)**

```bash
python -m pip install git+https://github.com/pyTMD/pyTMD.git
```

### 5.4 Pustaka Pendukung

pyTMD memasang dependensi intinya secara otomatis. Untuk skrip pada repositori ini, pastikan pustaka umum berikut tersedia (sesuaikan dengan bagian `import` pada `pengolahan.py` dan `2025.py`):

```bash
python -m pip install numpy pandas scipy matplotlib
```

### 5.5 Data Model Pasut

pyTMD merupakan perangkat hitung; **berkas model harus disediakan secara terpisah**. Unduh model **GOT** dan **EOT20**, simpan pada folder lokal, lalu atur lokasi direktori model pada bagian konfigurasi di `pengolahan.py` dan `2025.py`. Format dan struktur direktori model mengikuti dokumentasi pyTMD: <https://pytmd.readthedocs.io/>

### 5.6 Verifikasi Instalasi

```bash
python -c "import pyTMD; print(pyTMD.__version__)"
```

## 6. Menjalankan Pengolahan Data

```bash
# 1) Prediksi pasut 2027–2029 (GOT + EOT20, 13 stasiun)
python pengolahan.py

# 2) Validasi data BIG 2025
python 2025.py

# 3) Ekspor hasil ke CSV untuk dashboard
python prepare_web_data.py
```

## 7. Prosedur Pembaruan Data

Prinsip utamanya: **data diolah terlebih dahulu, kemudian berkas pada dashboard diganti.**

1. Jalankan pengolahan data baru melalui `pengolahan.py` (prediksi) dan/atau `2025.py` (validasi BIG).
2. Jalankan `prepare_web_data.py` untuk menghasilkan CSV.
3. Ganti berkas CSV lama di folder `data/` dengan CSV baru, dengan **nama berkas yang sama** agar tetap terbaca oleh `app.js`.
4. Periksa `index.html`; apabila terdapat perubahan periode, tahun, jumlah stasiun, atau keterangan, perbarui teks yang relevan.
5. Uji secara lokal, kemudian lakukan *commit* dan *push* ke GitHub.

## 8. Menjalankan Dashboard Secara Lokal

Dashboard memuat CSV melalui `fetch`, sehingga harus dijalankan melalui server lokal (tidak dapat dibuka langsung dengan klik ganda pada `index.html`).

```bash
python -m http.server 8000
```

Kemudian buka <http://localhost:8000> pada peramban.

## 9. Publikasi melalui GitHub Pages

1. *Push* seluruh isi folder ke repositori GitHub.
2. Buka **Settings → Pages**.
3. Pada **Source**, pilih branch `main` dan folder `/ (root)`, lalu simpan.
4. Dashboard akan tersedia di <https://fairuzalimah.github.io/pasut/> setelah proses *deploy* selesai.

## 10. Referensi

- Website dashboard: <https://fairuzalimah.github.io/pasut/>
- pyTMD: <https://github.com/pyTMD/pyTMD>
- Dokumentasi pyTMD: <https://pytmd.readthedocs.io/>
- Leaflet: <https://leafletjs.com/>

---

<div align="center">

Dashboard Prediksi & Validasi Pasang Surut Laut di Wilayah Selatan Yogyakarta 2027–2029

</div>
