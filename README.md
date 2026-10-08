# Dashboard Pasang Surut

Dashboard pasang surut (pasut) versi *static* yang diselaraskan dengan dashboard Python Dash. Fitur:

- Kartu statistik
- Peta Leaflet dengan pin stasiun
- Statistik mingguan
- Validasi EOT20
- Validasi BIG 2025
- Panduan Pemanfaatan
- Informasi Analisis

Prediksi pasut dihitung dengan **[pyTMD](https://github.com/pyTMD/pyTMD)** (Python-based tidal prediction software), lalu hasilnya diekspor ke CSV dan dibaca langsung oleh halaman web (tanpa server).

---

## Struktur Folder

```
.
├── index.html            # Halaman utama dashboard
├── style.css             # Tampilan
├── app.js                # Logika dashboard (peta, grafik, tabel)
├── data/                 # CSV hasil pengolahan (dibaca oleh app.js)
├── assets/
│   ├── logo_brin.png
│   └── logo_dkp_diy.png
├── pengolahan.py         # Prediksi pasut 2027–2029 (GOT + EOT20, 13 stasiun)
├── 2025.py               # Validasi data BIG tahun 2025
├── prepare_web_data.py   # Mengubah hasil olahan menjadi CSV untuk web
└── README.md
```

> **Penting:** salin folder `data/` yang sudah berhasil dipakai pada dashboard static sebelumnya ke folder ini. Salin juga dua logo PNG asli ke `assets/` dengan nama file yang sama seperti di atas.

---

## Pengolahan Data (pyTMD)

Seluruh perhitungan pasut dilakukan dengan pyTMD. Ada dua skrip pengolahan:

| Skrip | Fungsi |
|---|---|
| `pengolahan.py` | Prediksi pasut periode **2027–2029** menggunakan model **GOT** dan **EOT20** untuk **13 titik stasiun** |
| `2025.py` | Pengolahan **validasi data BIG tahun 2025** (membandingkan prediksi model dengan data pengamatan BIG) |

`prepare_web_data.py` kemudian merapikan hasilnya menjadi CSV di folder `data/` agar bisa dipakai dashboard.

### Alur singkat

```
Model pasut (GOT / EOT20)  ──►  pyTMD (pengolahan.py, 2025.py)  ──►  prepare_web_data.py  ──►  data/*.csv  ──►  Dashboard
```

---

## Instalasi Python

### 1. Siapkan Python

Gunakan Python 3.9 atau lebih baru. Cek versi:

```bash
python --version
```

### 2. (Disarankan) Buat virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install pyTMD

Via pip:

```bash
python -m pip install --upgrade pip
python -m pip install pyTMD
```

Untuk sekalian memasang semua dependensi opsional:

```bash
python -m pip install pyTMD[all]
```

Atau via conda / mamba (conda-forge):

```bash
conda install -c conda-forge pytmd
# atau
mamba install -c conda-forge pytmd
```

Versi pengembangan langsung dari GitHub (opsional):

```bash
python -m pip install git+https://github.com/pyTMD/pyTMD.git
```

### 4. Install library pendukung skrip

pyTMD akan memasang dependensi intinya sendiri. Untuk skrip di repo ini, pastikan library umum berikut juga terpasang (sesuaikan dengan bagian `import` di `pengolahan.py` dan `2025.py`):

```bash
python -m pip install numpy pandas scipy matplotlib
```

### 5. Siapkan data model pasut

pyTMD hanya **perangkat hitung**; file model pasut harus diunduh terpisah dan diletakkan di folder lokal:

- **GOT** (Goddard Ocean Tide)
- **EOT20** (Empirical Ocean Tide 2020)

Atur lokasi folder model di bagian konfigurasi di `pengolahan.py` / `2025.py` (variabel direktori model), lalu pastikan struktur folder sesuai yang diharapkan pyTMD. Panduan format model ada di dokumentasi: <https://pytmd.readthedocs.io/>

### 6. Cek instalasi

```bash
python -c "import pyTMD; print(pyTMD.__version__)"
```

---

## Menjalankan Pengolahan

```bash
# Prediksi pasut 2027–2029 (GOT + EOT20, 13 stasiun)
python pengolahan.py

# Validasi data BIG 2025
python 2025.py

# Ekspor ke CSV untuk dashboard web
python prepare_web_data.py
```

---

## Cara Update Data (Singkat)

Intinya: **olah dulu, baru ganti di file web.**

1. **Olah data baru** dengan `pengolahan.py` (prediksi) atau `2025.py` (validasi BIG).
2. **Jalankan** `prepare_web_data.py` agar hasilnya menjadi CSV.
3. **Ganti file CSV lama** di folder `data/` dengan CSV baru (nama file harus sama supaya terbaca `app.js`).
4. **Cek `index.html`** — jika ada perubahan periode/tahun, jumlah stasiun, atau keterangan, sesuaikan teksnya.
5. **Uji lokal**, lalu *commit* dan *push* ke GitHub.

---

## Uji Lokal

Dashboard memuat CSV lewat `fetch`, jadi tidak bisa dibuka dengan klik dua kali pada `index.html`. Jalankan server lokal:

```bash
python -m http.server 8000
```

Lalu buka <http://localhost:8000>.

---

## Deploy ke GitHub Pages

1. *Push* seluruh isi folder ke repository GitHub.
2. Buka **Settings → Pages**.
3. Pada **Source**, pilih branch `main` dan folder `/ (root)`, lalu simpan.
4. Tunggu beberapa menit; dashboard akan tersedia di `https://<username>.github.io/<nama-repo>/`.

---

## Referensi

- pyTMD: <https://github.com/pyTMD/pyTMD>
- Dokumentasi pyTMD: <https://pytmd.readthedocs.io/>
