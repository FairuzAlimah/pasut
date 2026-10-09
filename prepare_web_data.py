from pathlib import Path
import pandas as pd
import re
import shutil


# KONFIGURASI
MAGANG_DIR = Path(r"D:\MAGANG\A. Data\MAGANG")
OLAH_DIR = MAGANG_DIR / "OLAH"
WEB_DIR = Path(__file__).resolve().parent / "data"

YEARS = [2027, 2028, 2029]
BIG_YEAR = 2025

WEB_DIR.mkdir(parents=True, exist_ok=True)
(WEB_DIR / "validasi_big").mkdir(parents=True, exist_ok=True)

MONTHS = {
    "january":"January", "february":"February", "march":"March",
    "april":"April", "may":"May", "june":"June",
    "july":"July", "august":"August", "september":"September",
    "october":"October", "november":"November", "december":"December",
    "januari":"January", "februari":"February", "maret":"March",
    "mei":"May", "juni":"June", "juli":"July", "agustus":"August",
    "september":"September", "oktober":"October",
    "november":"November", "desember":"December",
}

def clean_station(name):
    s = str(name).strip()
    s = re.sub(r"\.(csv|CSV)$", "", s)
    s = s.replace("_", " ")
    return " ".join(s.split()).title()

def find_year(path):
    text = str(path)
    m = re.search(r"(2027|2028|2029)", text)
    return int(m.group(1)) if m else None

def read_csv_safe(path):
    try:
        df = pd.read_csv(path)
        if not df.empty:
            return df
    except Exception as e:
        print(f"  Lewati {path}: {e}")
    return None


# 1. KOORDINAT STASIUN
print("\n[1/4] Membaca koordinat stasiun...")

coord = None
coord_candidates = list(OLAH_DIR.rglob("koordinat_stasiun_*.csv"))

for p in coord_candidates:
    df = read_csv_safe(p)
    if df is not None:
        coord = df
        print("  ✓", p)
        break

if coord is None:
    raise FileNotFoundError(
        "File koordinat_stasiun_*.csv tidak ditemukan di folder OLAH."
    )

# Normalisasi nama kolom jika perlu
rename_coord = {}
for c in coord.columns:
    cl = c.strip().lower()
    if cl in ["nama_stasiun", "station_name", "stasiun"]:
        rename_coord[c] = "station"
    elif cl in ["lat", "latitude", "lintang"]:
        rename_coord[c] = "latitude"
    elif cl in ["lon", "lng", "longitude", "bujur"]:
        rename_coord[c] = "longitude"

coord = coord.rename(columns=rename_coord)

if "station" not in coord.columns:
    # Coba cari kolom teks pertama
    text_cols = [c for c in coord.columns if coord[c].dtype == "object"]
    if text_cols:
        coord = coord.rename(columns={text_cols[0]: "station"})

coord.to_csv(WEB_DIR / "stations.csv", index=False)
print("  ✓ stations.csv")

# 2. GOT4.10
print("\n[2/4] Membaca data GOT4.10...")

tide_frames = []

# Cari semua CSV di bawah hasil_pasut_2027/2028/2029
for year in YEARS:
    year_roots = list(OLAH_DIR.glob(f"hasil_pasut_{year}"))
    for root in year_roots:
        for p in root.rglob("*.csv"):
            if "koordinat_stasiun" in p.name.lower():
                continue

            df = read_csv_safe(p)
            if df is None:
                continue

            cols_lower = {c.lower(): c for c in df.columns}

            # Harus memiliki data waktu dan elevasi
            time_col = next(
                (cols_lower[c] for c in [
                    "datetime_wib", "datetime", "waktu", "timestamp"
                ] if c in cols_lower), None
            )
            tide_col = next(
                (cols_lower[c] for c in [
                    "tide_m", "elevasi", "tide", "water_level"
                ] if c in cols_lower), None
            )

            if time_col is None or tide_col is None:
                continue

            # Nama stasiun dari kolom jika tersedia
            station_col = next(
                (cols_lower[c] for c in [
                    "station", "stasiun", "nama_stasiun", "station_name"
                ] if c in cols_lower), None
            )

            if station_col:
                df["station"] = df[station_col].map(clean_station)
            else:
                # Ambil nama folder terdekat yang bukan csv
                df["station"] = clean_station(p.parent.name)

            df["year"] = year

            if time_col != "datetime_wib":
                df["datetime_wib"] = df[time_col]
            if tide_col != "tide_m":
                df["tide_m"] = df[tide_col]

            df["datetime_wib"] = pd.to_datetime(
                df["datetime_wib"], errors="coerce"
            )
            df["tide_m"] = pd.to_numeric(df["tide_m"], errors="coerce")
            df = df.dropna(subset=["datetime_wib", "tide_m"])

            if not df.empty:
                tide_frames.append(
                    df[["station", "year", "datetime_wib", "tide_m"]]
                )

if tide_frames:
    tide = pd.concat(tide_frames, ignore_index=True).drop_duplicates(
        subset=["station", "year", "datetime_wib"]
    )
    tide["datetime_wib"] = tide["datetime_wib"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )
else:
    tide = pd.DataFrame(
        columns=["station", "year", "datetime_wib", "tide_m"]
    )

tide.to_csv(WEB_DIR / "tide_all.csv", index=False)
print(f"  ✓ tide_all.csv: {len(tide):,} baris")


# 3. VALIDASI GOT4.10 vs EOT20
print("\n[3/4] Mencari data validasi EOT20 secara rekursif...")

val_frames = []
metric_frames = []

# Cari SEMUA file *_perbandingan.csv di OLAH.
# Ini sengaja tidak bergantung pada nama folder hasil_validasi_eot20_2027.
for p in OLAH_DIR.rglob("*_perbandingan.csv"):
    # Hindari file perbandingan BIG jika ada
    if "got410_eot20_vs_big" in p.name.lower():
        continue

    df = read_csv_safe(p)
    if df is None:
        continue

    cols_lower = {c.lower(): c for c in df.columns}

    time_col = next(
        (cols_lower[c] for c in [
            "datetime_utc", "datetime", "waktu", "timestamp"
        ] if c in cols_lower), None
    )

    got_col = next(
        (cols_lower[c] for c in [
            "tide_m_got410", "got410", "got4.10", "got4_10"
        ] if c in cols_lower), None
    )

    eot_col = next(
        (cols_lower[c] for c in [
            "tide_m_eot20", "eot20"
        ] if c in cols_lower), None
    )

    if time_col is None or got_col is None or eot_col is None:
        continue

    station_col = next(
        (cols_lower[c] for c in [
            "station", "stasiun", "nama_stasiun", "station_name"
        ] if c in cols_lower), None
    )

    if station_col:
        df["station"] = df[station_col].map(clean_station)
    else:
        # Folder stasiun biasanya berada satu level di atas file
        df["station"] = clean_station(p.parent.name)

    year = find_year(p)
    if "year" in cols_lower:
        year_values = pd.to_numeric(df[cols_lower["year"]], errors="coerce")
        df["year"] = year_values.fillna(year)
    else:
        df["year"] = year

    df["datetime_utc"] = pd.to_datetime(
        df[time_col], errors="coerce"
    )
    df["tide_m_got410"] = pd.to_numeric(
        df[got_col], errors="coerce"
    )
    df["tide_m_eot20"] = pd.to_numeric(
        df[eot_col], errors="coerce"
    )

    if "selisih_m" in cols_lower:
        df["selisih_m"] = pd.to_numeric(
            df[cols_lower["selisih_m"]], errors="coerce"
        )
    else:
        df["selisih_m"] = df["tide_m_got410"] - df["tide_m_eot20"]

    df["month"] = df["datetime_utc"].dt.month_name()

    df = df.dropna(
        subset=["datetime_utc", "tide_m_got410", "tide_m_eot20"]
    )

    if not df.empty:
        val_frames.append(
            df[
                [
                    "station", "year", "month", "datetime_utc",
                    "tide_m_got410", "tide_m_eot20", "selisih_m"
                ]
            ]
        )

# Cari semua ringkasan metrik validasi EOT20
for p in OLAH_DIR.rglob("ringkasan_validasi_eot20_vs_got410_*.csv"):
    df = read_csv_safe(p)
    if df is not None:
        metric_frames.append(df)

if val_frames:
    validation = pd.concat(val_frames, ignore_index=True).drop_duplicates(
        subset=["station", "year", "month", "datetime_utc"]
    )
else:
    validation = pd.DataFrame(
        columns=[
            "station", "year", "month", "datetime_utc",
            "tide_m_got410", "tide_m_eot20", "selisih_m"
        ]
    )

validation.to_csv(WEB_DIR / "validation_eot20_all.csv", index=False)

if metric_frames:
    metrics = pd.concat(metric_frames, ignore_index=True).drop_duplicates()
else:
    metrics = pd.DataFrame()

metrics.to_csv(WEB_DIR / "metrics_eot20_all.csv", index=False)

print(f"  ✓ validation_eot20_all.csv: {len(validation):,} baris")
print(f"  ✓ metrics_eot20_all.csv: {len(metrics):,} baris")

if validation.empty:
    print("\n  ⚠ DATA VALIDASI MASIH KOSONG.")
    print("  File *_perbandingan.csv tidak ditemukan atau kolomnya berbeda.")
else:
    print(
        "  ✓ Stasiun validasi:",
        ", ".join(sorted(validation["station"].dropna().unique()))
    )
    print(
        "  ✓ Tahun validasi:",
        sorted(pd.to_numeric(validation["year"], errors="coerce").dropna().astype(int).unique())
    )


# 4. VALIDASI BIG 2025
print("\n[4/4] Mencari validasi BIG 2025...")

big_candidates = [
    OLAH_DIR / f"hasil_validasi_3perbandingan_{BIG_YEAR}",
    MAGANG_DIR / f"hasil_validasi_3perbandingan_{BIG_YEAR}",
]

big = next((p for p in big_candidates if p.exists()), None)

if big is None:
    big_files = list(
        OLAH_DIR.rglob(f"{BIG_YEAR}_*_got410_eot20_vs_big.csv")
    )
else:
    big_files = list(
        big.rglob(f"{BIG_YEAR}_*_got410_eot20_vs_big.csv")
    )

idx = []

# Bersihkan hasil lama agar tidak menampilkan file basi
for old in (WEB_DIR / "validasi_big").glob("*.csv"):
    old.unlink()

for p in sorted(big_files):
    # Ambil station code dari folder
    station_code = p.parent.name.upper()

    # Format nama file umumnya:
    # 2025_01_Januari_got410_eot20_vs_big.csv
    # atau 2025_01_got410_eot20_vs_big.csv
    parts = p.stem.split("_")
    month = ""

    if len(parts) >= 2:
        month_raw = parts[1].lower().strip()

        # Jika bagian kedua berupa nomor bulan (01-12), ubah ke nama bulan
        month_number_map = {
            "01": "January", "02": "February", "03": "March",
            "04": "April", "05": "May", "06": "June",
            "07": "July", "08": "August", "09": "September",
            "10": "October", "11": "November", "12": "December",
        }

        month = month_number_map.get(month_raw)

        # Jika bukan angka, coba nama bulan pada bagian kedua
        if month is None:
            month = MONTHS.get(month_raw)

        # Jika masih kosong, cek bagian ketiga (misalnya Januari)
        if not month and len(parts) >= 3:
            month_raw_3 = parts[2].lower().strip()
            month = MONTHS.get(month_raw_3, month_raw_3)

        if not month:
            month = parts[1]

    target = WEB_DIR / "validasi_big" / p.name
    shutil.copy2(p, target)

    idx.append({
        "station_code": station_code,
        "month": month,
        "filename": p.name
    })

m_candidates = []
if big is not None:
    m_candidates.append(big / f"ringkasan_3perbandingan_{BIG_YEAR}.csv")
m_candidates += list(
    OLAH_DIR.rglob(f"ringkasan_3perbandingan_{BIG_YEAR}.csv")
)

metrics_big = next(
    (p for p in m_candidates if p.exists()), None
)

if metrics_big:
    shutil.copy2(
        metrics_big,
        WEB_DIR / "metrics_validasi_big_2025.csv"
    )
    print("  ✓", metrics_big)
else:
    pd.DataFrame().to_csv(
        WEB_DIR / "metrics_validasi_big_2025.csv",
        index=False
    )

pd.DataFrame(idx).to_csv(
    WEB_DIR / "validasi_big_index.csv",
    index=False
)

print(f"  ✓ File validasi BIG: {len(idx)}")
print("SELESAI")
print("Data website berada di:", WEB_DIR)
