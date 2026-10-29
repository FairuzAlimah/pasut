<div align="center">

# DASHBOARD PREDIKSI & VALIDASI PASANG SURUT LAUT
### di Wilayah Selatan Yogyakarta 2027–2029

Prediksi pasang surut berbasis **pyTMD** dengan model **GOT4.10** dan **EOT20** pada 13 titik stasiun di pesisir selatan Daerah Istimewa Yogyakarta, dilengkapi validasi silang antarmodel dan validasi terhadap data prediksi resmi **BIG 2025**.

**[Buka dashboard »](https://fairuzalimah.github.io/pasut/)**

</div>

---

## Daftar Isi

1. [Gambaran Umum](#1-gambaran-umum)
2. [Fitur Dashboard](#2-fitur-dashboard)
3. [Struktur Repositori](#3-struktur-repositori)
4. [Data dan Model](#4-data-dan-model)
5. [Metode Pengolahan](#5-metode-pengolahan)
6. [Pustaka dan Versi](#6-pustaka-dan-versi)
7. [Instalasi](#7-instalasi)
8. [Menyiapkan Folder Data](#8-menyiapkan-folder-data)
9. [Cara Menjalankan Pengolahan](#9-cara-menjalankan-pengolahan)
10. [Menjalankan Dashboard Secara Lokal](#10-menjalankan-dashboard-secara-lokal)
11. [Berkas Data pada Dashboard](#11-berkas-data-pada-dashboard)
12. [Keterbatasan](#12-keterbatasan)
13. [Referensi](#13-referensi)

---

## 1. Gambaran Umum

Dashboard ini menyajikan hasil prediksi pasang surut laut periode **2027–2029** di wilayah pesisir selatan Yogyakarta, beserta hasil validasinya. Seluruh perhitungan dilakukan secara *offline* dengan Python dan pustaka [pyTMD](https://github.com/pyTMD/pyTMD). Hasilnya diekspor ke berkas CSV, lalu ditampilkan pada halaman web statis (HTML, CSS, JavaScript) tanpa memerlukan server aplikasi.

| Komponen | Keterangan |
|---|---|
| Perangkat prediksi | pyTMD |
| Model utama | GOT4.10 (NASA GSFC) |
| Model pembanding | EOT20 (DGFI-TUM) |
| Cakupan stasiun | 13 titik di pesisir selatan DIY |
| Periode prediksi | 1 Januari 2027 – 31 Desember 2029, interval 1 jam |
| Data acuan validasi | Prediksi pasang surut resmi BIG tahun 2025 (stasiun GLGH dan SADG) |
| Zona waktu | Prediksi dalam WIB (UTC+7); validasi dalam UTC |
| Tampilan | Web statis, grafik Plotly, peta Leaflet |

**Stasiun:** Congot, Glagah, Bugel, Trisik, Ngenthak, Kuwaru, Goa Cemara, Samas, Depok, Baron, Gesing, Jungwok, dan Sadeng.

Prediksi ini dilakukan oleh Pusat Riset Iklim dan Atmosfer, BRIN, Homebase Yogyakarta, KST Ahmad Baiquni.

## 2. Fitur Dashboard

- **Ringkasan statistik**: elevasi minimum, maksimum, MSL (rata-rata), dan jumlah data per stasiun, bulan, dan tahun.
- **Peta interaktif**: sebaran stasiun pada peta Leaflet.
- **Grafik prediksi**: deret waktu elevasi terhadap MSL dengan penanda pasang tertinggi dan surut terendah.
- **Statistik mingguan**: minimum, maksimum, dan rata-rata per minggu kalender (Senin–Minggu).
- **Validasi silang GOT4.10 vs EOT20**: grafik, selisih, dan metrik (RMSE, MAE, r, Willmott's d).
- **Validasi 2025**: perbandingan GOT4.10, EOT20, dan data BIG pada stasiun GLGH dan SADG.
- **Panduan Pemanfaatan**: cara membaca grafik dan jadwal pasang-surut harian bagi nelayan, pemancing, wisatawan, dan pengelola kawasan pantai.
- **Informasi Analisis**: penjelasan model, metode, dan referensi.
- **Unduh PDF**: mencetak halaman yang sedang tampil melalui fitur cetak peramban.

## 3. Struktur Repositori

```
.
├── index.html              # Halaman utama dashboard
├── style.css               # Gaya tampilan
├── app.js                  # Logika dashboard (peta, grafik, tabel)
├── data/                   # Berkas CSV hasil pengolahan yang dibaca dashboard
├── assets/                 # Logo dan gambar
├── pengolahan.py           # Prediksi pasut 2027–2029 (GOT4.10) + validasi silang EOT20
├── 2025.py                 # Validasi GOT4.10, EOT20, dan data BIG tahun 2025
├── prepare_web_data.py     # Menyusun hasil olahan menjadi CSV untuk dashboard
├── requirements.txt        # Daftar pustaka Python beserta versinya
└── README.md
```

Folder `data/` sudah berisi hasil pengolahan, sehingga **dashboard dapat langsung dijalankan tanpa mengulang pengolahan** (lihat [bagian 10](#10-menjalankan-dashboard-secara-lokal)). Pengolahan ulang hanya diperlukan bila ingin mereproduksi atau memperbarui hasil.

## 4. Data dan Model

| Data | Sumber | Cara memperoleh |
|---|---|---|
| **GOT4.10** | Goddard Ocean Tide, NASA GSFC (Ray, 2013) | Diunduh **otomatis** oleh `pengolahan.py` melalui pyTMD |
| **EOT20** | Empirical Ocean Tide model, DGFI-TUM (Hart-Davis dkk., 2021) | Diunduh **manual** dari SEANOE, [doi:10.17882/79489](https://doi.org/10.17882/79489) (NetCDF, lisensi CC BY 4.0) |
| **Prediksi pasut resmi BIG 2025** | Badan Informasi Geospasial (Direktorat Sistem Referensi Geospasial) | Diminta dari BIG (kontak: srgi@big.go.id); hanya diperlukan untuk menjalankan `2025.py` |

Model pasut menyimpan konstanta harmonik (amplitudo dan fase tiap konstituen, misalnya M2, S2, K1, O1). pyTMD menjumlahkannya menjadi deret waktu elevasi muka laut pada koordinat dan waktu yang diminta.

## 5. Metode Pengolahan

### 5.1 Alur Kerja

```
GOT4.10 / EOT20 ──► pyTMD ──► pengolahan.py ─┐
                                              ├──► prepare_web_data.py ──► data/*.csv ──► Dashboard
Data BIG 2025 ───► pyTMD ──► 2025.py ─────────┘
```

### 5.2 Prediksi GOT4.10 (`pengolahan.py`)

1. **Memuat model.** GOT4.10 diperiksa pada folder model dan diunduh otomatis bila belum ada.
2. **Menyesuaikan titik stasiun.** GOT4.10 memiliki resolusi spasial kasar (sekitar 0,5°), sehingga titik yang berada di luar sel laut model akan gagal dihitung. Untuk tiap stasiun, skrip memeriksa masker laut model (`pyTMD.compute.tide_masks`). Jika titik bukan sel laut, skrip mencari titik laut terdekat ke 16 arah dengan jarak bertahap 0,001° hingga 0,05°. Titik dengan jarak terdekat dipakai, dan jaraknya dicatat.
3. **Membuat deret waktu.** Waktu dibangkitkan tiap 1 jam dalam UTC, per bulan, untuk setiap tahun (2027, 2028, 2029).
4. **Menghitung elevasi.** Elevasi pasut dihitung dengan `pyTMD.compute.tide_elevations` (CRS EPSG:4326, metode interpolasi `nearest`, ekstrapolasi aktif dengan batas 50 km).
5. **Konversi waktu.** Waktu UTC diubah ke WIB (`Asia/Jakarta`, UTC+7).
6. **Statistik mingguan.** Data dibagi per minggu kalender (Senin–Minggu) yang dipotong pada awal dan akhir bulan. Setiap minggu dihitung nilai minimum, maksimum, rata-rata, dan rentang (*range*). MSL ditampilkan sebagai rata-rata elevasi pada periode yang dipilih.
7. **Validasi silang EOT20.** Elevasi EOT20 dihitung pada titik dan waktu yang sama, lalu dibandingkan dengan GOT4.10 menggunakan metrik pada [5.4](#54-metrik-validasi).

Keluaran disimpan per tahun dalam `OLAH/hasil_pasut_<tahun>/` (CSV bulanan per stasiun, grafik mingguan, `koordinat_stasiun_<tahun>.csv`, `statistik_mingguan_<tahun>.csv`) dan `OLAH/hasil_validasi_eot20_<tahun>/` (CSV perbandingan, grafik, ringkasan metrik, dan metadata JSON).

### 5.3 Validasi dengan Data BIG 2025 (`2025.py`)

1. Membaca berkas prediksi resmi BIG `prediksi_pasut_<stasiun>_<tanggal-awal>_<tanggal-akhir>_series.csv` (header metadata + tabel waktu UTC dan tinggi prediksi).
2. Mengambil data pada interval 10 menit.
3. Menghitung GOT4.10 dan EOT20 pada **titik koordinat stasiun dan timestamp UTC yang sama persis** dengan data BIG (GLGH/Glagah dan SADG/Sadeng).
4. Menghitung tiga perbandingan per bulan: **GOT4.10 vs BIG**, **EOT20 vs BIG**, dan **GOT4.10 vs EOT20**.
5. Menyimpan CSV per bulan, grafik, ringkasan metrik, dan metadata provenance (JSON) ke `hasil_validasi_3perbandingan_2025/`.

### 5.4 Metrik Validasi

Dengan $O$ sebagai deret acuan, $P$ sebagai deret yang dibandingkan, dan $N$ jumlah data:

$$\mathrm{RMSE}=\sqrt{\frac{1}{N}\sum_{i=1}^{N}(P_i-O_i)^2}\qquad \mathrm{MAE}=\frac{1}{N}\sum_{i=1}^{N}\lvert P_i-O_i\rvert$$

$$r=\frac{\sum (O_i-\bar O)(P_i-\bar P)}{\sqrt{\sum (O_i-\bar O)^2}\sqrt{\sum (P_i-\bar P)^2}}\qquad d=1-\frac{\sum (P_i-O_i)^2}{\sum\left(\lvert P_i-\bar O\rvert+\lvert O_i-\bar O\rvert\right)^2}$$

Semakin kecil RMSE dan MAE, serta semakin dekat $r$ dan Willmott's $d$ ke 1, semakin konsisten kedua deret. Pada validasi GOT4.10 vs EOT20, EOT20 diperlakukan sebagai deret acuan; pada validasi 2025, data BIG menjadi acuan.

### 5.5 Penyusunan Data Web (`prepare_web_data.py`)

Skrip menelusuri folder hasil olahan, menyeragamkan nama stasiun, kolom, dan nama bulan, lalu menulis CSV ringkas ke `data/`. Di akhir, skrip memeriksa kelengkapan (13 stasiun × 3 tahun × 12 bulan untuk validasi EOT20, dan 12 bulan untuk tiap stasiun BIG) dan menampilkan peringatan bila ada data yang hilang.

## 6. Pustaka dan Versi

### 6.1 Pengolahan data (Python)

Versi di bawah adalah versi acuan yang tercantum pada `requirements.txt`. Fungsi pyTMD dan timescale yang dipakai skrip (`pyTMD.io.model().from_database`, `pyTMD.datasets.fetch_gsfc_got`, `pyTMD.compute.tide_elevations`, `pyTMD.compute.tide_masks`, `timescale.time.date_range`) tersedia pada versi tersebut.

| Pustaka | Versi acuan | Fungsi dalam proyek |
|---|---|---|
| Python | 3.12 | Bahasa pemrograman |
| [pyTMD](https://github.com/pyTMD/pyTMD) | 3.0.9 | Prediksi pasang surut dari konstanta harmonik model |
| [timescale](https://github.com/pyTMD/timescale) | 0.1.3 | Pembuatan deret waktu prediksi |
| [NumPy](https://numpy.org/) | 2.5.4 | Perhitungan numerik |
| [pandas](https://pandas.pydata.org/) | 3.1.0 | Pengolahan tabel dan waktu, baca/tulis CSV |
| [SciPy](https://scipy.org/) | 1.18.1 | Korelasi Pearson (`scipy.stats`) |
| [Matplotlib](https://matplotlib.org/) | 3.11.2 | Grafik statis (PNG) hasil pengolahan |

Dependensi lain (misalnya xarray, pyproj, h5netcdf) dipasang otomatis oleh pyTMD. IPython bersifat opsional, hanya untuk menampilkan tabel ringkasan di Jupyter/Spyder.

### 6.2 Dashboard web (dimuat dari CDN)

| Pustaka | Versi | Fungsi |
|---|---|---|
| [Plotly.js](https://plotly.com/javascript/) | 2.35.2 | Grafik interaktif |
| [Leaflet](https://leafletjs.com/) | 1.9.4 | Peta interaktif |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | - | Peta dasar (tile) |
| [Poppins](https://fonts.google.com/specimen/Poppins) | - | Huruf (Google Fonts) |

Dashboard memerlukan koneksi internet untuk memuat pustaka dan peta dasar tersebut.

## 7. Instalasi

```bash
# 1) Unduh repositori
git clone https://github.com/FairuzAlimah/pasut.git
cd pasut

# 2) Buat virtual environment (disarankan)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3) Pasang pustaka
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4) Verifikasi
python -c "import pyTMD; print(pyTMD.__version__)"
```

Alternatif dengan conda: `conda install -c conda-forge pytmd numpy pandas scipy matplotlib`.

## 8. Menyiapkan Folder Data

Berkas model dan data mentah berukuran besar sehingga **tidak disertakan** dalam repositori. Semuanya diletakkan dalam satu folder bernama `MAGANG` dengan struktur berikut:

```
MAGANG/
├── pytmd_data/                 # model pasut
│   └── EOT20/                  # EOT20 (unduh manual dan ekstrak)
│       ├── ocean_tides/*.nc
│       └── load_tides/*.nc
├── data_observasi_big/         # prediksi_pasut_<stasiun>_<tgl>_<tgl>_series.csv (data BIG)
└── OLAH/                       # hasil pengolahan (dibuat otomatis oleh skrip)
```

GOT4.10 akan terunduh sendiri ke `pytmd_data/` saat `pengolahan.py` pertama kali dijalankan.

Lokasi folder `MAGANG` ditentukan dengan urutan prioritas berikut:

1. Argumen terminal: `--data-dir "<lokasi folder MAGANG>"`
2. Environment variable `PASUT_DATA_DIR`
3. Variabel `DATA_DIR_MANUAL` di bagian pengaturan tiap skrip
4. Default: folder `MAGANG` di samping berkas skrip

Contoh pengaturan environment variable:

```bash
# Windows PowerShell
$env:PASUT_DATA_DIR = "E:\Data\MAGANG"
# Windows CMD
set PASUT_DATA_DIR=E:\Data\MAGANG
# macOS / Linux
export PASUT_DATA_DIR="$HOME/Data/MAGANG"
```

## 9. Cara Menjalankan Pengolahan

Jalankan berurutan dari folder repositori:

```bash
# 1) Prediksi pasut 2027–2029 (GOT4.10) dan validasi silang EOT20
python pengolahan.py

# 2) Validasi GOT4.10 vs EOT20 vs BIG tahun 2025
python 2025.py

# 3) Susun hasil menjadi CSV untuk dashboard (ditulis ke folder data/)
python prepare_web_data.py
```

Bila folder `MAGANG` tidak berada di samping skrip, tambahkan `--data-dir`:

```bash
python pengolahan.py --data-dir "E:\Data\MAGANG"
python 2025.py --data-dir "E:\Data\MAGANG"
python prepare_web_data.py --data-dir "E:\Data\MAGANG"
```

Catatan:

- Langkah 1 memerlukan koneksi internet pada proses pertama (mengunduh GOT4.10) dan model EOT20 yang sudah diletakkan di `MAGANG/pytmd_data/EOT20/`. Tanpa EOT20, prediksi GOT4.10 tetap dihitung, tetapi validasi silang dilewati.
- Langkah 2 memerlukan data BIG pada `MAGANG/data_observasi_big/`.
- Langkah 3 mencetak peringatan bila ada stasiun atau bulan yang belum lengkap. Periksa peringatan tersebut sebelum menggunakan hasilnya pada dashboard.
- Pengolahan 3 tahun × 13 stasiun memerlukan waktu cukup lama; hasil tiap bulan disimpan bertahap.

## 10. Menjalankan Dashboard Secara Lokal

Dashboard memuat CSV melalui `fetch`, sehingga harus dijalankan lewat server lokal dan tidak dapat dibuka dengan klik ganda pada `index.html`.

```bash
python -m http.server 8000
```

Kemudian buka <http://localhost:8000> pada peramban.

## 11. Berkas Data pada Dashboard

Berkas berikut dibaca oleh `app.js`. Nama berkas harus tetap sama agar dashboard dapat membacanya.

| Berkas | Isi |
|---|---|
| `data/stations.csv` | Nama dan koordinat (lintang, bujur) stasiun |
| `data/tide_all.csv` | Prediksi GOT4.10 per jam: `station`, `year`, `datetime_wib`, `tide_m` |
| `data/validation_eot20_all.csv` | Perbandingan GOT4.10 dan EOT20: `station`, `year`, `month`, `datetime_utc`, `tide_m_got410`, `tide_m_eot20`, `selisih_m` |
| `data/metrics_eot20_all.csv` | Ringkasan metrik validasi GOT4.10 vs EOT20 per stasiun, tahun, dan bulan |
| `data/metrics_validasi_big_2025.csv` | Ringkasan metrik validasi 2025 (tiga perbandingan) |
| `data/validasi_big_index.csv` | Indeks berkas validasi BIG: kode stasiun, bulan, nama berkas |
| `data/validasi_big/<kode-stasiun>/*.csv` | Deret waktu GOT4.10, EOT20, dan BIG per bulan |

## 12. Keterbatasan

- Hasil adalah **prediksi pasang surut astronomis** dari model global. Pengaruh cuaca (angin dan tekanan udara), gelombang, arus balik, dan kondisi lokal seperti muara atau teluk tidak dihitung, sehingga tinggi muka air sebenarnya dapat berbeda dari prediksi.
- GOT4.10 beresolusi spasial kasar (sekitar 0,5°). Titik stasiun yang berada di luar sel laut model digeser ke sel laut terdekat, sehingga hasil di titik tersebut merepresentasikan perairan sekitar, bukan tinggi muka air tepat di dermaga atau garis pantai. Hal ini berlaku terutama bagi Baron, Gesing, Jungwok, dan Sadeng.
- Elevasi dinyatakan terhadap MSL (rata-rata), bukan terhadap datum surut. Nilai nol bukan kondisi surut.
- Validasi dengan data BIG hanya mencakup dua stasiun (GLGH dan SADG) pada tahun 2025, dan data BIG sendiri merupakan prediksi, bukan hasil pengamatan langsung.
- Untuk pelayaran atau kegiatan berisiko tinggi, gunakan prediksi ini hanya sebagai referensi tambahan, dan rujuk tabel pasang surut resmi serta informasi cuaca maritim dari BMKG.

## 13. Referensi

1. Hart-Davis, M. G., Piccioni, G., Dettmering, D., Schwatke, C., Passaro, M., & Seitz, F. (2021). EOT20: a global ocean tide model from multi-mission satellite altimetry. *Earth System Science Data, 13*(8), 3869–3884. <https://doi.org/10.5194/essd-13-3869-2021>
2. Hart-Davis, M., Piccioni, G., Dettmering, D., Schwatke, C., Passaro, M., & Seitz, F. (2021). EOT20 - A global Empirical Ocean Tide model from multi-mission satellite altimetry [Data set]. SEANOE. <https://doi.org/10.17882/79489>
3. Ray, R. D. (1999). *A global ocean tide model from TOPEX/POSEIDON altimetry: GOT99.2* (NASA/TM-1999-209478). NASA Goddard Space Flight Center. (Model awal pada seri GOT.)
4. Ray, R. D. (2013). Precise comparisons of bottom-pressure and altimetric ocean tides. *Journal of Geophysical Research: Oceans, 118*, 4570–4584. <https://doi.org/10.1002/jgrc.20336>
5. Willmott, C. J. (1981). On the validation of models. *Physical Geography, 2*(2), 184–194. <https://doi.org/10.1080/02723646.1981.10642213>
6. pyTMD: Python-based tidal prediction software. <https://github.com/pyTMD/pyTMD> · Dokumentasi: <https://pytmd.readthedocs.io/>
7. Leaflet: <https://leafletjs.com/> · Plotly.js: <https://plotly.com/javascript/>

---

<div align="center">

Dashboard Prediksi & Validasi Pasang Surut Laut di Wilayah Selatan Yogyakarta 2027–2029<br>
Pusat Riset Iklim dan Atmosfer, BRIN · Homebase Yogyakarta, KST Ahmad Baiquni

</div>
