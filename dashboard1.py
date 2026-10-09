# DASHBOARD PASANG SURUT

# 1. IMPORT LIBRARY
import io
import shutil
import threading
import webbrowser
from pathlib import Path
from urllib.parse import quote
import numpy as np
import pandas as pd
from dash import Dash, dcc, html, dash_table, Input, Output, State
import dash_leaflet as dl
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image as RLImage,
)

# 2. PENGATURAN UMUM
YEARS = [2027, 2028, 2029]
YEAR_LABEL = f"{YEARS[0]}-{YEARS[-1]}"

# 2b. PALET WARNA

COLOR_TIDE_LINE = "#1f6f8b"
COLOR_MODEL_A = "#1f6f8b"
COLOR_MODEL_B = "#e08e2b"
COLOR_RESIDUAL = "#8e44ad"
COLOR_MSL = "#34495e"
COLOR_HIGH = "#1e8449"
COLOR_LOW = "#c0392b"
COLOR_ACCENT = "#0D1C42"
COLOR_ACCENT_DARK = "#010736"

# Warna judul header 
COLOR_TITLE_MAIN = "#010736"
COLOR_TITLE_SUB = "#22396F"

UI_NAVY_DARK = "#010736"
UI_NAVY = "#0D1C42"
UI_NAVY_MID = "#22396F"
UI_BLUE_SOFT = "#2E4A8A"   # biru penutup gradient (pengganti biru terang)
UI_TINT = "#eef1f8"        # latar tipis
UI_LINE = "#e3e7f1"        # garis/border
UI_TEXT = "#33415c"        # teks isi
UI_MUTED = "#6b7590"       # teks keterangan

# 3. FOLDER HASIL
# Struktur:
#   MAGANG/pytmd_data                         -> model (tidak dipakai dashboard)
#   MAGANG/OLAH/hasil_pasut_{tahun}           -> hasil prediksi GOT4.10 per tahun
#   MAGANG/OLAH/hasil_validasi_eot20_{tahun}  -> hasil validasi GOT4.10 vs EOT20 per tahun
MAGANG_DIR = Path(r"D:\MAGANG\A. Data\MAGANG")
MODEL_DIR = MAGANG_DIR / "pytmd_data"
OLAH_DIR = MAGANG_DIR / "OLAH"

OUTPUT_DIR_BY_YEAR = {y: OLAH_DIR / f"hasil_pasut_{y}" for y in YEARS}
VALIDASI_DIR_BY_YEAR = {y: OLAH_DIR / f"hasil_validasi_eot20_{y}" for y in YEARS}

def csv_dir_prediksi(year):
    return OUTPUT_DIR_BY_YEAR[year] / "csv"

def csv_dir_validasi(year):
    return VALIDASI_DIR_BY_YEAR[year] / "csv"

def coord_file_year(year):
    return OUTPUT_DIR_BY_YEAR[year] / f"koordinat_stasiun_{year}.csv"

def statistics_file_year(year):
    return OUTPUT_DIR_BY_YEAR[year] / f"statistik_mingguan_{year}.csv"

def metrics_file_year(year):
    return VALIDASI_DIR_BY_YEAR[year] / f"ringkasan_validasi_eot20_vs_got410_{year}.csv"

print("\n" + "=" * 70)
print("DASHBOARD PASANG SURUT WILAYAH SELATAN YOGYAKARTA")
print("=" * 70)
print("Folder utama          :", MAGANG_DIR)
print("Folder OLAH           :", OLAH_DIR)
for _y in YEARS:
    print(f"Folder hasil {_y}      :", OUTPUT_DIR_BY_YEAR[_y])
    print(f"Folder validasi {_y}   :", VALIDASI_DIR_BY_YEAR[_y])

# 4. CEK FILE
# Koordinat stasiun sama untuk semua tahun; dipakai dari tahun pertama yang tersedia.
coord_file = next((coord_file_year(y) for y in YEARS if coord_file_year(y).exists()), None)
if coord_file is None:
    daftar_dicari = "\n".join(f"  {coord_file_year(y)}" for y in YEARS)
    raise FileNotFoundError(
        "File koordinat stasiun tidak ditemukan. Lokasi yang dicari:\n"
        f"{daftar_dicari}\n\n"
        "Jalankan dahulu skrip pengolahan pasut 2027-2029 "
        "supaya file koordinat dan hasil prediksi tersedia."
    )

STATISTICS_FILES_ADA = [statistics_file_year(y) for y in YEARS if statistics_file_year(y).exists()]
STATISTICS_FILE_ADA = len(STATISTICS_FILES_ADA) > 0
if not STATISTICS_FILE_ADA:
    print(
        "\nCatatan: file statistik mingguan tidak ditemukan di folder hasil_pasut_{tahun}_ "
        f"(dicari mis.: {statistics_file_year(YEARS[0])}).\n"
        "Tidak masalah - dashboard akan menghitung sendiri statistik "
        "mingguannya langsung dari data jam-jaman memakai fungsi "
        "create_monthly_weeks()."
    )

# 5. BACA KOORDINAT STASIUN
coord_df = pd.read_csv(coord_file)
valid_stations = {
    row["station"]: (row["longitude"], row["latitude"])
    for _, row in coord_df.iterrows()
}
if not valid_stations:
    raise RuntimeError(f"File koordinat stasiun kosong: {coord_file}")
print("\nJumlah stasiun terbaca dari file koordinat:", len(valid_stations))
print("File koordinat yang dipakai:", coord_file)
for name, (lon, lat) in valid_stations.items():
    print(f"  {name:<15}Lon={lon:.6f}  Lat={lat:.6f}")


# BAGIAN DASHBOARD

# 6. PENGATURAN DASHBOARD
DASHBOARD_DIR = OLAH_DIR / "dashboard"
DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
LOGO_BRIN = MAGANG_DIR / "logo_brin.png"
LOGO_DKP = MAGANG_DIR / "logo_dkp_diy.png"

# Folder foto untuk tab "Panduan Pemanfaatan" (opsional).
# Taruh file bernama: nelayan, pemancing, wisata, pengelola
# (ekstensi .jpg / .jpeg / .png / .webp). Bila belum ada, dashboard
# otomatis memakai ilustrasi pantai bawaan.
PANDUAN_IMG_DIR = MAGANG_DIR / "foto_panduan"

INSTANSI_NAMA = "Pusat Riset Iklim dan Atmosfer, BRIN"
INSTANSI_HOMEBASE = "Homebase Yogyakarta, KST Ahmad Baiquni"
KETERANGAN_MSL = (
    "Elevasi pasang surut ditampilkan sebagai deviasi terhadap "
    "MSL (Mean Sea Level/muka laut rata-rata), dalam satuan meter (m)."
)
KETERANGAN_PASANG_SURUT = (
    "Perlu diperhatikan: 0/MSL adalah muka laut RATA-RATA, bukan kondisi "
    "surut. Nilai di atas 0 (MSL) berarti muka laut sedang lebih TINGGI "
    "dari rata-rata, dan nilai di bawah 0 (MSL) berarti muka laut sedang "
    "lebih RENDAH dari rata-rata. Kondisi PASANG (high tide) yang "
    "sebenarnya adalah titik puncak tertinggi pada tiap siklus kurva, "
    "sedangkan SURUT (low tide) adalah titik lembah terendah pada tiap "
    "siklus dan keduanya ditandai pada grafik."
)
KETERANGAN_VALIDASI = (
    "Validasi silang membandingkan hasil prediksi model utama (GOT4.10) "
    "terhadap model independen EOT20 pada titik dan waktu yang sama. "
    "Semakin kecil RMSE/MAE dan semakin dekat r & Willmott's d ke angka 1, "
    "semakin konsisten kedua model."
)
KETERANGAN_VALIDASI_BIG = (
    "Menu ini membandingkan dua model pasang surut global (GOT4.10 dan EOT20) "
    "dengan data prediksi RESMI dari Badan Informasi Geospasial (BIG) sebagai "
    "acuan lapangan, pada stasiun dan waktu yang sama. Semakin kecil "
    "RMSE/MAE dan semakin dekat r & Willmott's d ke angka 1, semakin dekat "
    "model tersebut dengan data BIG."
)


# 6b. DAFTAR BULAN
month_order = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
month_indonesia = {
    "January": "Januari", "February": "Februari", "March": "Maret",
    "April": "April", "May": "Mei", "June": "Juni", "July": "Juli",
    "August": "Agustus", "September": "September", "October": "Oktober",
    "November": "November", "December": "Desember",
}
MONTH_NAME_TO_NUMBER = {name: i + 1 for i, name in enumerate(month_order)}

# 6b-2. FUNGSI DAFTAR MINGGU
# (sama dengan skrip pengolahan pasut 2027-2029: Senin s.d. Minggu)
def create_monthly_weeks(year, month):
    start_month = pd.Timestamp(year=year, month=month, day=1)
    end_month = (pd.Timestamp(year=year + 1, month=1, day=1) if month == 12
                 else pd.Timestamp(year=year, month=month + 1, day=1))

    # Senin pertama pada atau sebelum awal bulan (weekday(): Senin=0 ... Minggu=6)
    first_monday = start_month - pd.Timedelta(days=start_month.weekday())
    weeks = []
    current_monday = first_monday
    week_number = 1

    while current_monday < end_month:
        calendar_week_end = current_monday + pd.Timedelta(days=7)
        week_start = max(current_monday, start_month)
        week_end = min(calendar_week_end, end_month)
        if week_start < week_end:
            weeks.append({
                "week_in_month": week_number,
                "week_start": week_start,
                "week_end": week_end,
                "display_end": week_end - pd.Timedelta(hours=1),
            })
            week_number += 1
        current_monday = calendar_week_end
    return weeks

# 6b-3. MEMBANGUN DAFTAR MINGGU UNTUK SEMUA TAHUN
def build_all_weeks_by_year(years):
    all_weeks_by_year = {}
    for year in years:
        weeks_by_month = {}
        global_week = 1
        for month in range(1, 13):
            month_name = pd.Timestamp(year=year, month=month, day=1).strftime("%B")
            weeks = create_monthly_weeks(year, month)
            for week in weeks:
                week["week_of_year"] = global_week
                global_week += 1
            weeks_by_month[month] = {"month_name": month_name, "weeks": weeks}
        all_weeks_by_year[year] = weeks_by_month
    return all_weeks_by_year
ALL_WEEKS_BY_YEAR = build_all_weeks_by_year(YEARS)
_total_minggu_semua_tahun = sum(
    len(bulan_info["weeks"])
    for tahun_info in ALL_WEEKS_BY_YEAR.values()
    for bulan_info in tahun_info.values()
)

# 6b-4. FUNGSI PELABELAN MINGGU + STATISTIK MINGGUAN
def assign_weeks_and_stats(month_df, month_info, station_name, year, month_name, month_number):
    if month_df.empty or month_info is None:
        return month_df.copy(), []
    df = month_df.copy()
    week_numbers, week_of_years = [], []
    for dt in df["datetime_wib"]:
        assigned_week, assigned_global_week = None, None
        for week in month_info["weeks"]:
            if week["week_start"] <= dt < week["week_end"]:
                assigned_week = week["week_in_month"]
                assigned_global_week = week["week_of_year"]
                break
        week_numbers.append(assigned_week)
        week_of_years.append(assigned_global_week)
    df["week_in_month"] = week_numbers
    df["week_of_year"] = week_of_years
    df = df.dropna(subset=["week_in_month"]).reset_index(drop=True)
    if df.empty:
        return df, []
    df["week_in_month"] = df["week_in_month"].astype(int)
    df["week_of_year"] = df["week_of_year"].astype(int)
    stats_list = []
    for week in month_info["weeks"]:
        week_df = df[df["week_in_month"] == week["week_in_month"]]
        if week_df.empty:
            continue
        minimum = week_df["tide_m"].min()
        maximum = week_df["tide_m"].max()
        mean = week_df["tide_m"].mean()
        stats_list.append({
            "year": year,
            "station": station_name,
            "month": month_name,
            "month_number": month_number,
            "week_in_month": week["week_in_month"],
            "week_of_year": week["week_of_year"],
            "start_date": week["week_start"].strftime("%Y-%m-%d"),
            "end_date": week["display_end"].strftime("%Y-%m-%d"),
            "jumlah_data_valid": len(week_df),
            "minimum_m": minimum,
            "maximum_m": maximum,
            "mean_m": mean,
            "range_m": maximum - minimum,
        })
    return df, stats_list

# 6c. BACA STATISTIK DASHBOARD (gabungan file statistik per tahun)
if STATISTICS_FILE_ADA:
    statistics_dashboard = pd.concat(
        [pd.read_csv(f) for f in STATISTICS_FILES_ADA], ignore_index=True
    )
    if not statistics_dashboard.empty:
        statistics_dashboard["year"] = statistics_dashboard["year"].astype(int)
else:
    statistics_dashboard = pd.DataFrame(columns=[
        "year", "station", "month", "month_number", "week_in_month",
        "week_of_year", "start_date", "end_date", "jumlah_data_valid",
        "minimum_m", "maximum_m", "mean_m", "range_m",
    ])

# 7. BACA DATA CSV BULANAN GOT4.10
monthly_data = []
for station_name in valid_stations.keys():
    station_slug = station_name.lower().replace(" ", "_")
    for year in YEARS:
        year_csv_dir = csv_dir_prediksi(year) / station_slug
        if not year_csv_dir.exists():
            continue
        for csv_file in year_csv_dir.glob("*.csv"):
            try:
                temp_df = pd.read_csv(csv_file)
                if temp_df.empty:
                    continue
                temp_df["station"] = station_name
                if "year" not in temp_df.columns:
                    temp_df["year"] = year
                monthly_data.append(temp_df)
            except Exception as e:
                print(f"Gagal membaca {csv_file}: {e}")
if monthly_data:
    tide_dashboard_df = pd.concat(monthly_data, ignore_index=True)
else:
    tide_dashboard_df = pd.DataFrame()
if not tide_dashboard_df.empty:
    tide_dashboard_df["datetime_wib"] = pd.to_datetime(
        tide_dashboard_df["datetime_wib"], errors="coerce"
    )
    tide_dashboard_df["tide_m"] = pd.to_numeric(
        tide_dashboard_df["tide_m"], errors="coerce"
    )
    tide_dashboard_df["year"] = pd.to_numeric(
        tide_dashboard_df["year"], errors="coerce"
    )
    tide_dashboard_df = (
        tide_dashboard_df
        .replace([np.inf, -np.inf], np.nan)
        .dropna(subset=["datetime_wib", "tide_m", "year"])
        .copy()
    )
    tide_dashboard_df["year"] = tide_dashboard_df["year"].astype(int)

# 8. BACA DATA VALIDASI EOT20 (gabungan ringkasan metrik per tahun)
METRICS_FILES_ADA = [metrics_file_year(y) for y in YEARS if metrics_file_year(y).exists()]
if METRICS_FILES_ADA:
    metrics_dashboard_df = pd.concat(
        [pd.read_csv(f) for f in METRICS_FILES_ADA], ignore_index=True
    )
    if not metrics_dashboard_df.empty and "year" in metrics_dashboard_df.columns:
        metrics_dashboard_df["year"] = metrics_dashboard_df["year"].astype(int)
else:
    metrics_dashboard_df = pd.DataFrame()
    print(
        "\nCatatan: file ringkasan validasi EOT20 belum ditemukan di folder "
        "hasil_validasi_eot20_{tahun}_ (dicari mis.):\n ",
        metrics_file_year(YEARS[0]),
    )
    print(
        "Menu 'Validasi Silang: GOT4.10 vs EOT20' "
        "akan tampil kosong sampai file tersebut tersedia."
    )

# 8a. OPTIONS STASIUN DAN TAHUN
station_options = sorted(valid_stations.keys())
if not station_options:
    raise RuntimeError("Tidak ada stasiun pada file koordinat.")
if not tide_dashboard_df.empty:
    year_options = sorted(int(y) for y in tide_dashboard_df["year"].dropna().unique().tolist())
else:
    year_options = list(YEARS)
if not year_options:
    year_options = list(YEARS)

# 8b. BACA DATA VALIDASI BULANAN EOT20
validation_monthly_data = []
for station_name in station_options:
    station_slug = station_name.lower().replace(" ", "_")
    for year in YEARS:
        year_val_dir = csv_dir_validasi(year) / station_slug
        if not year_val_dir.exists():
            continue
        for csv_file in year_val_dir.glob("*_perbandingan.csv"):
            try:
                temp_df = pd.read_csv(csv_file, parse_dates=["datetime_utc"])
                if temp_df.empty:
                    continue
                if "year" not in temp_df.columns:
                    temp_df["year"] = year
                validation_monthly_data.append(temp_df)
            except Exception as e:
                print(f"Gagal membaca {csv_file}: {e}")
if validation_monthly_data:
    validation_dashboard_df = pd.concat(validation_monthly_data, ignore_index=True)
else:
    validation_dashboard_df = pd.DataFrame()
if not validation_dashboard_df.empty and "year" in validation_dashboard_df.columns:
    validation_dashboard_df["year"] = validation_dashboard_df["year"].astype(int)
VALIDASI_ADA_DATA = not validation_dashboard_df.empty

# 8c. MENU VALIDASI TAHUN 2025
YEAR_VALIDASI_BIG = 2025
_nama_folder_validasi_big = f"hasil_validasi_3perbandingan_{YEAR_VALIDASI_BIG}"
_kandidat_folder_big = [
    OLAH_DIR / _nama_folder_validasi_big,
    MAGANG_DIR / _nama_folder_validasi_big,
]
HASIL_VALIDASI_BIG_DIR = next(
    (p for p in _kandidat_folder_big if p.exists()), _kandidat_folder_big[0]
)
CSV_VALIDASI_BIG_DIR = HASIL_VALIDASI_BIG_DIR / "csv"
METRICS_VALIDASI_BIG_FILE = (
    HASIL_VALIDASI_BIG_DIR / f"ringkasan_3perbandingan_{YEAR_VALIDASI_BIG}.csv"
)
VALIDASI_BIG_TERSEDIA = (
    METRICS_VALIDASI_BIG_FILE.exists() and CSV_VALIDASI_BIG_DIR.exists()
)
if VALIDASI_BIG_TERSEDIA:
    metrics_validasi_big_df = pd.read_csv(METRICS_VALIDASI_BIG_FILE)
    print("\n[Menu Validasi 2025] Ringkasan metrik dibaca dari:")
    print(" ", METRICS_VALIDASI_BIG_FILE)
else:
    metrics_validasi_big_df = pd.DataFrame()
    print(
        "\n[Menu Validasi 2025] Hasil validasi 3 perbandingan "
        f"(GOT4.10 vs EOT20 vs BIG) belum ditemukan di:\n  {HASIL_VALIDASI_BIG_DIR}"
    )
    print(
        "Jalankan dahulu script 'validasi_3perbandingan_2025.py'. "
        "Menu 'Validasi 2025' akan tetap muncul di dashboard tetapi "
        "menampilkan data kosong sampai file tersebut tersedia."
    )

# 8d. NAMA STASIUN VALIDASI BIG
VALIDASI_BIG_NAMA_STASIUN = {
    "GLGH": "Glagah",
    "SADG": "Sadeng",
}
def label_stasiun_validasi_big(kode):
    nama = VALIDASI_BIG_NAMA_STASIUN.get(kode)
    return f"{kode} - {nama}" if nama else kode

# 8e. INDEX FILE VALIDASI BIG
validasi_big_index = {}
if VALIDASI_BIG_TERSEDIA:
    for station_dir in sorted(CSV_VALIDASI_BIG_DIR.iterdir()):
        if not station_dir.is_dir():
            continue
        station_code = station_dir.name.upper()
        bulan_map = {}
        for csv_file in sorted(
            station_dir.glob(f"{YEAR_VALIDASI_BIG}_*_got410_eot20_vs_big.csv")
        ):
            parts = csv_file.stem.split("_")
            if len(parts) >= 3:
                bulan_nama = parts[2]
                bulan_map[bulan_nama] = csv_file
        if bulan_map:
            validasi_big_index[station_code] = bulan_map
validasi_big_station_options = sorted(validasi_big_index.keys())
def validasi_big_bulan_tersedia(station_code):
    bulan_map = validasi_big_index.get(station_code, {})
    return [m for m in month_order if m in bulan_map]

# 8f. LOAD CSV VALIDASI BIG
def load_validasi_big_csv(station_code, month_label):
    path = validasi_big_index.get(station_code, {}).get(month_label)
    if path is None or not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, parse_dates=["datetime_utc"])

# 8g. COMPUTE DATA VALIDASI BIG
def compute_validasi_big_dashboard(station_code, month_label):
    df = load_validasi_big_csv(station_code, month_label)
    if df.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="Data tidak tersedia untuk kombinasi stasiun/bulan ini",
            template="plotly_white",
            height=580,
        )
        return {"fig": empty_fig, "metrics": {}, "n_data": 0}
    df = df.sort_values("datetime_utc").copy()
    metrics = {}
    if not metrics_validasi_big_df.empty:
        sub = metrics_validasi_big_df[
            (metrics_validasi_big_df["station"] == station_code)
            & (metrics_validasi_big_df["month"] == month_label)
        ]
        for _, row in sub.iterrows():
            metrics[row["perbandingan"]] = row.to_dict()
    return {
        "fig": None,
        "metrics": metrics,
        "df": df,
        "n_data": len(df),
    }

# 8h. FUNGSI MEMBUAT INTERVAL SUMBU Y YANG PROPORSIONAL
def nice_tick_interval(min_value, max_value):
    span = max_value - min_value
    if not np.isfinite(span) or span <= 0:
        return max(abs(max_value) * 0.1, 0.001)
    raw_step = span / 4.0
    magnitude = 10 ** np.floor(np.log10(raw_step))
    normalized = raw_step / magnitude
    if normalized <= 1:
        nice_factor = 1
    elif normalized <= 2:
        nice_factor = 2
    elif normalized <= 5:
        nice_factor = 5
    else:
        nice_factor = 10
    return nice_factor * magnitude

# 8h-2. SKALA AKAR-KUADRAT BERTANDA (SIGNED SQUARE ROOT)
def signed_sqrt(value):
    return np.sign(value) * np.sqrt(np.abs(value))
def signed_sqrt_inverse(transformed_value):
    return np.sign(transformed_value) * (transformed_value ** 2)
def signed_sqrt_axis_ticks(y_min_real, y_max_real, n_pos=3, n_neg=3):
    y_min_t = signed_sqrt(y_min_real)
    y_max_t = signed_sqrt(y_max_real)
    tick_positions = [0.0]
    tick_values_real = [0.0]
    if y_max_t > 0:
        for frac in np.linspace(0, 1, n_pos + 1)[1:]:
            t = frac * y_max_t
            tick_positions.append(t)
            tick_values_real.append(signed_sqrt_inverse(t))
    if y_min_t < 0:
        for frac in np.linspace(0, 1, n_neg + 1)[1:]:
            t = frac * y_min_t
            tick_positions.append(t)
            tick_values_real.append(signed_sqrt_inverse(t))
    paired = sorted(zip(tick_positions, tick_values_real), key=lambda pair: pair[0])
    tick_positions = [p for p, _ in paired]
    tick_values_real = [r for _, r in paired]
    return tick_positions, tick_values_real

# 8i. FUNGSI RINGKASAN VISUAL MENU VALIDASI 2025
def build_validasi_big_summary(metrics, df):
    got_big = metrics.get("GOT4.10 vs BIG")
    eot_big = metrics.get("EOT20 vs BIG")
    got_eot = metrics.get("GOT4.10 vs EOT20")

    # TABEL METRIK
    metric_rows = [
        ("RMSE (m)", "rmse_m"),
        ("MAE (m)", "mae_m"),
        ("Korelasi (r)", "korelasi_r"),
        ("Willmott's d", "willmott_d"),
        ("Jumlah Data", "n_data"),
    ]
    def fmt(metrik_dict, key):
        if metrik_dict is None or key not in metrik_dict:
            return "-"
        value = metrik_dict[key]
        if pd.isna(value):
            return "-"
        if key == "n_data":
            return f"{int(value):,}"
        return f"{float(value):.4f}"
    table_data = []
    for label, key in metric_rows:
        table_data.append({
            "metrik": label,
            "got_big": fmt(got_big, key),
            "eot_big": fmt(eot_big, key),
            "got_eot": fmt(got_eot, key),
        })

    # GRAFIK BATANG - RATA-RATA ELEVASI
    bar_fig = go.Figure()
    bar_sources = []
    if "tide_m_got410" in df.columns:
        got_mean = pd.to_numeric(df["tide_m_got410"], errors="coerce").mean()
        if pd.notna(got_mean):
            bar_sources.append(("GOT4.10", float(got_mean), COLOR_MODEL_A))
    if "tide_m_eot20" in df.columns:
        eot_mean = pd.to_numeric(df["tide_m_eot20"], errors="coerce").mean()
        if pd.notna(eot_mean):
            bar_sources.append(("EOT20", float(eot_mean), COLOR_MODEL_B))
    if "tide_m_big" in df.columns:
        big_mean = pd.to_numeric(df["tide_m_big"], errors="coerce").mean()
        if pd.notna(big_mean):
            bar_sources.append(("BIG", float(big_mean), "#6c757d"))
    if bar_sources:
        values = [item[1] for item in bar_sources]
        min_value = min(values)
        max_value = max(values)
        span = max_value - min_value
        if span == 0:
            padding = max(abs(min_value) * 0.15, 0.005)
        else:
            padding = max(span * 0.50, 0.002)
        y_min_real = min_value - padding
        y_max_real = max_value + padding
        if y_min_real > 0:
            y_min_real = -padding
        if y_max_real < 0:
            y_max_real = padding

        # SATU TRACE PER SUMBER DATA (supaya muncul di legend)
        for label, real_value, color in bar_sources:
            bar_fig.add_trace(
                go.Bar(
                    x=[label],
                    y=[signed_sqrt(real_value)],
                    marker_color=color,
                    name=label,
                    text=[f"{real_value:.4f} m"],
                    textposition="outside",
                    cliponaxis=False,
                    customdata=[[real_value]],
                    hovertemplate=(
                        f"<b>{label}</b><br>"
                        "Rata-rata elevasi: %{customdata[0]:.4f} m"
                        "<extra></extra>"
                    ),
                    showlegend=True,
                )
            )

        # TICK SUMBU-Y
        tick_positions, tick_values_real = signed_sqrt_axis_ticks(y_min_real, y_max_real)
        max_abs_tick = max((abs(v) for v in tick_values_real), default=0.01)
        if max_abs_tick < 0.01:
            tick_fmt = "{:.4f}"
        elif max_abs_tick < 1:
            tick_fmt = "{:.3f}"
        else:
            tick_fmt = "{:.2f}"
        tick_text = [tick_fmt.format(v) for v in tick_values_real]
        y_axis_range = [signed_sqrt(y_min_real), signed_sqrt(y_max_real)]
    else:
        y_axis_range = None
        tick_positions = None
        tick_text = None

    # LAYOUT BAR
    bar_fig.update_layout(
        title=dict(
            text="Rata-rata Elevasi Pasang Surut — GOT4.10, EOT20, dan BIG",
            x=0.02,
            xanchor="left",
            font=dict(size=17, color="#0D1C42"),
        ),
        template="plotly_white",
        height=390,
        margin=dict(l=65, r=25, t=95, b=65),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Poppins, Arial, sans-serif", color="#33415c"),
        barmode="group",
        xaxis=dict(title="Sumber Data", showgrid=False, zeroline=False),
        yaxis=dict(
            title="Rata-rata Elevasi terhadap MSL (m)",
            showgrid=True,
            gridcolor="#edf1f3",
            zeroline=True,
            zerolinecolor="#b7c4cc",
            range=y_axis_range,
            tickvals=tick_positions,
            ticktext=tick_text,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,
            xanchor="right",
            x=0.99,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#d8e0e5",
            borderwidth=1,
            font=dict(size=11),
        ),
    )

    # GRAFIK GARIS - PERBANDINGAN DERET WAKTU
    line_fig = go.Figure()

    if "tide_m_got410" in df.columns:
        line_fig.add_trace(
            go.Scatter(
                x=df["datetime_utc"],
                y=df["tide_m_got410"],
                name="GOT4.10",
                mode="lines",
                line=dict(color=COLOR_MODEL_A, width=2.0),
                hovertemplate=(
                    "<b>GOT4.10</b><br>Waktu: %{x}<br>"
                    "Elevasi: %{y:.3f} m<extra></extra>"
                ),
            )
        )

    if "tide_m_eot20" in df.columns:
        line_fig.add_trace(
            go.Scatter(
                x=df["datetime_utc"],
                y=df["tide_m_eot20"],
                name="EOT20",
                mode="lines",
                line=dict(color=COLOR_MODEL_B, width=2.0, dash="dash"),
                hovertemplate=(
                    "<b>EOT20</b><br>Waktu: %{x}<br>"
                    "Elevasi: %{y:.3f} m<extra></extra>"
                ),
            )
        )

    if "tide_m_big" in df.columns:
        line_fig.add_trace(
            go.Scatter(
                x=df["datetime_utc"],
                y=df["tide_m_big"],
                name="BIG",
                mode="lines",
                line=dict(color="#6c757d", width=2.2, dash="dot"),
                hovertemplate=(
                    "<b>BIG</b><br>Waktu: %{x}<br>"
                    "Elevasi: %{y:.3f} m<extra></extra>"
                ),
            )
        )

    line_fig.update_yaxes(
        title_text="Elevasi terhadap MSL (m)",
        showgrid=True,
        gridcolor="#edf1f3",
        zeroline=True,
        zerolinecolor="#b7c4cc",
    )

    line_fig.update_xaxes(
        title_text="Tanggal dan Waktu (UTC)",
        showgrid=True,
        gridcolor="#edf1f3",
    )

    line_fig.update_layout(
        title=dict(
            text="Perbandingan Deret Waktu Pasang Surut — GOT4.10, EOT20, dan BIG",
            x=0.02,
            xanchor="left",
            font=dict(size=17, color="#0D1C42"),
        ),
        template="plotly_white",
        height=520,
        hovermode="x unified",
        margin=dict(l=65, r=25, t=90, b=70),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Poppins, Arial, sans-serif", color="#33415c"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.96)",
            bordercolor="#d8e0e5",
            borderwidth=1,
            font=dict(size=11),
        ),
    )

    return table_data, bar_fig, line_fig


# 9. FUNGSI KARTU STATISTIK
def create_card(title, value, unit="", accent=COLOR_ACCENT):
    return html.Div(
        [
            html.Div(
                title,
                style={
                    "fontSize": "13px",
                    "fontWeight": "600",
                    "color": "#5b6b73",
                    "marginBottom": "8px",
                    "textTransform": "uppercase",
                    "letterSpacing": "0.4px",
                },
            ),
            html.Div(
                f"{value} {unit}",
                style={"fontSize": "26px", "fontWeight": "700", "color": "#1c2b33"},
            ),
        ],
        className="stat-card",
        style={
            "backgroundColor": "white",
            "padding": "18px 20px",
            "borderRadius": "14px",
            "borderLeft": f"4px solid {accent}",
            "boxShadow": "0 2px 10px rgba(15, 60, 80, 0.08)",
            "textAlign": "left",
            "flex": "1",
            "minWidth": "170px",
        },
    )


def create_info_card(message, tone="info"):
    accent = COLOR_ACCENT if tone == "info" else "#c0392b"
    return html.Div(
        message,
        style={
            "backgroundColor": "#f7f8fd" if tone == "info" else "#fdf1f0",
            "border": f"1px dashed {accent}",
            "borderRadius": "12px",
            "padding": "18px 20px",
            "color": "#48606b" if tone == "info" else "#943126",
            "fontSize": "14px",
            "width": "100%",
        },
    )

# 9b. PETA LOKASI STASIUN
OSM_TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_ATTRIBUTION = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">'
    "OpenStreetMap</a> contributors"
)
STATION_MAP_CENTER = [
    sum(lat for _, lat in valid_stations.values()) / len(valid_stations),
    sum(lon for lon, _ in valid_stations.values()) / len(valid_stations),
]
STATION_MAP_ZOOM = 9
COLOR_PIN_SELECTED = "#c0392b"
COLOR_PIN_UNSELECTED = "#154360"
def _pin_icon_options(color, is_selected):
    width, height = (34, 46) if is_selected else (26, 36)
    svg = f"""
    <svg width="{width}" height="{height}" viewBox="0 0 30 42"
         xmlns="http://www.w3.org/2000/svg"
         style="filter: drop-shadow(0 2px 2px rgba(0,0,0,0.35));">
        <path d="M15 0C6.7 0 0 6.7 0 15c0 11.25 15 27 15 27s15-15.75 15-27C30 6.7 23.3 0 15 0z"
              fill="{color}" stroke="#ffffff" stroke-width="1.6"/>
        <circle cx="15" cy="15" r="6" fill="#ffffff"/>
    </svg>
    """
    return dict(
        html=svg,
        className="station-pin-icon",
        iconSize=[width, height],
        iconAnchor=[width / 2, height],
    )
def build_station_markers(selected_station=None):
    markers = []
    for name, (lon, lat) in valid_stations.items():
        is_selected = name == selected_station
        pin_color = COLOR_PIN_SELECTED if is_selected else COLOR_PIN_UNSELECTED
        markers.append(
            dl.DivMarker(
                position=[lat, lon],
                iconOptions=_pin_icon_options(pin_color, is_selected),
                children=[
                    dl.Tooltip(name),
                    dl.Popup(
                        html.Div([html.B(name), html.Br(), f"Lon: {lon:.6f}", html.Br(), f"Lat: {lat:.6f}"])
                    ),
                ],
            )
        )

    return markers
def build_station_map_layers(selected_station=None):
    return [dl.TileLayer(url=OSM_TILE_URL, attribution=OSM_ATTRIBUTION)] + build_station_markers(selected_station)

# 10. FUNGSI DATA DASHBOARD - PREDIKSI GOT4.10
def compute_dashboard_data(selected_station, selected_year, selected_month):
    station_df = tide_dashboard_df[
        (tide_dashboard_df["station"] == selected_station)
        & (tide_dashboard_df["year"] == selected_year)
    ].copy()
    if selected_month:
        station_df["month_name"] = station_df["datetime_wib"].dt.strftime("%B")
        month_df = station_df[station_df["month_name"] == selected_month].copy()
    else:
        month_df = station_df.copy()
    if month_df.empty:

        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="Data tidak tersedia",
            xaxis_title="Waktu",
            yaxis_title="Elevasi terhadap MSL (m)",
            template="plotly_white",
        )

        return {
            "minimum": None, "maximum": None, "mean": None, "msl": None,
            "jumlah_data": 0, "tide_fig": empty_fig, "weekly_fig": empty_fig,
            "table_df": pd.DataFrame(),
        }

    minimum = month_df["tide_m"].min()
    maximum = month_df["tide_m"].max()
    mean = month_df["tide_m"].mean()
    msl = mean
    jumlah_data = len(month_df)

    # GRAFIK PASUT
    tide_fig = go.Figure()
    tide_fig.add_trace(
        go.Scatter(
            x=month_df["datetime_wib"],
            y=month_df["tide_m"],
            mode="lines",
            name="Prediksi Pasut",
            line={"width": 2, "color": COLOR_TIDE_LINE},
            hovertemplate="<b>Waktu:</b> %{x}<br><b>Elevasi:</b> %{y:.3f} m<extra></extra>",
        )
    )

    tide_fig.add_trace(
        go.Scatter(
            x=[month_df["datetime_wib"].min(), month_df["datetime_wib"].max()],
            y=[msl, msl],
            mode="lines",
            name=f"MSL (Mean Sea Level) = {msl:.3f} m",
            line=dict(color=COLOR_MSL, dash="dash", width=1.6),
            visible="legendonly",
            hovertemplate=f"MSL (Mean Sea Level): {msl:.3f} m<extra></extra>",
        )
    )

    idx_high = month_df["tide_m"].idxmax()
    idx_low = month_df["tide_m"].idxmin()
    t_high = month_df.loc[idx_high, "datetime_wib"]
    v_high = month_df.loc[idx_high, "tide_m"]
    t_low = month_df.loc[idx_low, "datetime_wib"]
    v_low = month_df.loc[idx_low, "tide_m"]
    tide_fig.add_trace(
        go.Scatter(
            x=[t_high], y=[v_high], mode="markers+text", name="Pasang tertinggi",
            marker={"symbol": "triangle-up", "size": 12, "color": COLOR_HIGH},
            text=[f"Pasang tertinggi: {v_high:.3f} m"], textposition="top center",
            textfont={"size": 10, "color": COLOR_HIGH},
            hovertemplate="<b>Pasang tertinggi</b><br>Waktu: %{x}<br>Elevasi: %{y:.3f} m<extra></extra>",
        )
    )
    tide_fig.add_trace(
        go.Scatter(
            x=[t_low], y=[v_low], mode="markers+text", name="Surut terendah",
            marker={"symbol": "triangle-down", "size": 12, "color": COLOR_LOW},
            text=[f"Surut terendah: {v_low:.3f} m"], textposition="bottom center",
            textfont={"size": 10, "color": COLOR_LOW},
            hovertemplate="<b>Surut terendah</b><br>Waktu: %{x}<br>Elevasi: %{y:.3f} m<extra></extra>",
        )
    )
    tide_fig.update_layout(
        title=(
            f"Prediksi Pasang Surut GOT4.10 - {selected_station} "
            f"{month_indonesia[selected_month]} {selected_year} "
            "(elevasi terhadap MSL, satuan meter)"
        ),
        xaxis_title="Tanggal dan Waktu (WIB)",
        yaxis_title="Elevasi Pasang Surut terhadap MSL (m)",
        hovermode="x unified",
        template="plotly_white",
        height=550,
        legend=dict(bgcolor="rgba(255,255,255,0.85)", bordercolor="#dfe6e9", borderwidth=1),
        font=dict(family="Poppins, Arial, sans-serif"),
    )

    # STATISTIK MINGGUAN
    month_number = MONTH_NAME_TO_NUMBER[selected_month]
    month_info_tahun_ini = ALL_WEEKS_BY_YEAR.get(selected_year, {}).get(month_number)
    if month_info_tahun_ini is not None:
        _, weekly_stats_live = assign_weeks_and_stats(
            month_df, month_info_tahun_ini, selected_station, selected_year,
            selected_month, month_number,
        )
        weekly_df = pd.DataFrame(weekly_stats_live)
    else:
        weekly_df = pd.DataFrame()
    weekly_fig = go.Figure()
    if not weekly_df.empty:
        weekly_fig.add_trace(
            go.Bar(
                x=weekly_df["week_in_month"], y=weekly_df["minimum_m"], name="Minimum (m)",
                marker_color="#5dade2",
                hovertemplate="Minggu %{x}<br>Minimum: %{y:.3f} m<extra></extra>",
            )
        )
        weekly_fig.add_trace(
            go.Bar(
                x=weekly_df["week_in_month"], y=weekly_df["maximum_m"], name="Maksimum (m)",
                marker_color="#f5b041",
                hovertemplate="Minggu %{x}<br>Maksimum: %{y:.3f} m<extra></extra>",
            )
        )
        weekly_fig.add_trace(
            go.Scatter(
                x=weekly_df["week_in_month"], y=weekly_df["mean_m"], mode="lines+markers",
                name="Rata-rata mingguan (m)", line=dict(color="#117864", width=2),
                hovertemplate="Minggu %{x}<br>Rata-rata: %{y:.3f} m<extra></extra>",
            )
        )
        weekly_fig.add_trace(
            go.Scatter(
                x=[weekly_df["week_in_month"].min(), weekly_df["week_in_month"].max()],
                y=[msl, msl],
                mode="lines",
                name=f"MSL bulanan = {msl:.3f} m",
                line=dict(color=COLOR_MSL, dash="dot", width=1.6),
                visible="legendonly",
                hovertemplate=f"MSL bulanan: {msl:.3f} m<extra></extra>",
            )
        )
    weekly_fig.update_layout(
        title=(
            f"Statistik Mingguan - {selected_station} - "
            f"{month_indonesia[selected_month]} {selected_year} "
            "(satuan: meter terhadap MSL)"
        ),
        xaxis_title="Minggu",
        yaxis_title="Elevasi terhadap MSL (m)",
        barmode="group",
        template="plotly_white",
        height=500,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1,
            bgcolor="rgba(255,255,255,0.85)", bordercolor="#dfe6e9", borderwidth=1,
        ),
        font=dict(family="Poppins, Arial, sans-serif"),
    )

    # TABEL MINGGUAN
    table_df = weekly_df.copy()
    if not table_df.empty:
        for col in ["minimum_m", "maximum_m", "mean_m", "range_m"]:
            table_df[col] = table_df[col].round(3)
        table_df = table_df[
            ["week_in_month", "week_of_year", "start_date", "end_date", "jumlah_data_valid",
             "minimum_m", "maximum_m", "mean_m", "range_m"]
        ]

    return {
        "minimum": minimum, "maximum": maximum, "mean": mean, "msl": msl,
        "jumlah_data": jumlah_data, "tide_fig": tide_fig, "weekly_fig": weekly_fig,
        "table_df": table_df,
    }

# 11. FUNGSI DATA VALIDASI SILANG EOT20
def compute_validation_data(selected_station, selected_year, selected_month):
    if not VALIDASI_ADA_DATA:
        return None
    station_val_df = validation_dashboard_df[
        (validation_dashboard_df["station"] == selected_station)
        & (validation_dashboard_df["year"] == selected_year)
        & (validation_dashboard_df["month"] == selected_month)
    ].copy()
    if station_val_df.empty:
        return None
    station_val_df = station_val_df.sort_values("datetime_utc")
    if not metrics_dashboard_df.empty:
        metric_row = metrics_dashboard_df[
            (metrics_dashboard_df["station"] == selected_station)
            & (metrics_dashboard_df["year"] == selected_year)
            & (metrics_dashboard_df["month"] == selected_month)
        ]
    else:
        metric_row = pd.DataFrame()
    if metric_row.empty:
        diff = station_val_df["tide_m_got410"] - station_val_df["tide_m_eot20"]
        metrik = {
            "rmse_m": float(np.sqrt(np.mean(diff ** 2))),
            "mae_m": float(np.mean(np.abs(diff))),
            "korelasi_r": float(
                station_val_df["tide_m_got410"].corr(station_val_df["tide_m_eot20"])
            ),
            "willmott_d": np.nan,
            "n_data": len(station_val_df),
        }
    else:
        metrik = metric_row.iloc[0].to_dict()

    # FIGURE VALIDASI EOT20
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35],
        vertical_spacing=0.10,
        subplot_titles=("Perbandingan GOT4.10 vs EOT20", "Selisih (GOT4.10 - EOT20)"),
    )
    fig.add_trace(
        go.Scatter(
            x=station_val_df["datetime_utc"], y=station_val_df["tide_m_got410"],
            name="GOT4.10", line=dict(color=COLOR_MODEL_A, width=2),
            hovertemplate="<b>GOT4.10</b><br>Waktu: %{x}<br>Elevasi: %{y:.3f} m<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=station_val_df["datetime_utc"], y=station_val_df["tide_m_eot20"],
            name="EOT20", line=dict(color=COLOR_MODEL_B, width=2, dash="dash"),
            hovertemplate="<b>EOT20</b><br>Waktu: %{x}<br>Elevasi: %{y:.3f} m<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=station_val_df["datetime_utc"], y=station_val_df["selisih_m"],
            name="Selisih", line=dict(color=COLOR_RESIDUAL, width=1.5), fill="tozeroy",
            hovertemplate="Waktu: %{x}<br>Selisih: %{y:.3f} m<extra></extra>",
        ),
        row=2, col=1,
    )
    fig.add_hline(y=0, line_dash="dot", line_color="#95a5a6", row=2, col=1)
    fig.update_yaxes(title_text="Elevasi terhadap MSL (m)", row=1, col=1)
    fig.update_yaxes(title_text="Selisih (m)", row=2, col=1)
    fig.update_xaxes(title_text="Tanggal dan Waktu (UTC)", row=2, col=1)
    fig.update_layout(
        title=(
            f"Validasi Silang - {selected_station} - "
            f"{month_indonesia[selected_month]} {selected_year}"
        ),
        template="plotly_white",
        height=580,
        hovermode="x unified",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.08, xanchor="right", x=1,
            bgcolor="rgba(255,255,255,0.85)", bordercolor="#dfe6e9", borderwidth=1,
        ),
        font=dict(family="Poppins, Arial, sans-serif"),
    )

    return {"fig": fig, "metrik": metrik, "table_df": station_val_df}

# 12. FUNGSI BUAT PDF
def build_pdf_report(selected_station, selected_year, selected_month, data, validation_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontSize=16, spaceAfter=4)
    subtitle_style = ParagraphStyle(
        "SubtitleCustom", parent=styles["Normal"], fontSize=11, alignment=1, spaceAfter=2
    )
    instansi_style = ParagraphStyle(
        "InstansiCustom", parent=styles["Normal"], fontSize=9, alignment=1,
        textColor=rl_colors.HexColor("#555555"), spaceAfter=2,
    )
    heading_style = styles["Heading2"]
    elements = []
    # LOGO
    logo_row = []
    if LOGO_BRIN.exists():
        logo_row.append(RLImage(str(LOGO_BRIN), width=2.2 * cm, height=2.2 * cm))
    if LOGO_DKP.exists():
        logo_row.append(RLImage(str(LOGO_DKP), width=2.2 * cm, height=2.2 * cm))
    if logo_row:
        logo_table = Table([logo_row])
        logo_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        elements.append(logo_table)
        elements.append(Spacer(1, 0.3 * cm))

    # JUDUL PDF
    elements.append(Paragraph("DASHBOARD PREDIKSI & VALIDASI PASANG SURUT LAUT", title_style))
    elements.append(
        Paragraph(f"Model GOT4.10 (utama) & EOT20 (validasi) - Tahun {YEAR_LABEL}", subtitle_style)
    )
    elements.append(Paragraph("13 Stasiun Pantai Selatan Daerah Istimewa Yogyakarta", subtitle_style))
    elements.append(
        Paragraph(f"Prediksi ini dilakukan oleh {INSTANSI_NAMA} - {INSTANSI_HOMEBASE}", instansi_style)
    )
    elements.append(Spacer(1, 0.4 * cm))
    station_lon, station_lat = valid_stations.get(selected_station, (None, None))
    if station_lon is not None and station_lat is not None:
        koordinat_text = f"Lon <b>{station_lon:.6f}</b>, Lat <b>{station_lat:.6f}</b>"
    else:
        koordinat_text = "-"
    elements.append(
        Paragraph(
            f"Stasiun: <b>{selected_station}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Tahun: <b>{selected_year}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Bulan: <b>{month_indonesia[selected_month]}</b>",
            styles["Normal"],
        )
    )
    elements.append(
        Paragraph(f"Koordinat Stasiun: {koordinat_text}", styles["Normal"])
    )
    elements.append(Spacer(1, 0.2 * cm))
    elements.append(Paragraph(KETERANGAN_MSL, styles["Normal"]))
    elements.append(Spacer(1, 0.4 * cm))
    # RINGKASAN STATISTIK
    elements.append(Paragraph("Ringkasan Statistik Prediksi", heading_style))
    if data["jumlah_data"] > 0:
        summary_table_data = [
            ["Minimum (m)", "Maksimum (m)", "MSL/Rata-rata (m)", "Jumlah Data"],
            [f"{data['minimum']:.3f}", f"{data['maximum']:.3f}", f"{data['msl']:.3f}", f"{data['jumlah_data']:,}"],
        ]
    else:
        summary_table_data = [
            ["Minimum (m)", "Maksimum (m)", "MSL/Rata-rata (m)", "Jumlah Data"],
            ["-", "-", "-", "0"],
        ]
    summary_table = Table(summary_table_data, hAlign="LEFT")
    summary_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#eef1f8")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5 * cm))

    # GRAFIK PREDIKSI
    elements.append(Paragraph("Grafik Prediksi Pasang Surut", heading_style))

    try:
        tide_png = data["tide_fig"].to_image(format="png", width=900, height=450, scale=2)
        elements.append(RLImage(io.BytesIO(tide_png), width=17 * cm, height=8.5 * cm))
    except Exception as e:
        elements.append(
            Paragraph(f"Grafik tidak dapat disertakan (paket 'kaleido' belum terpasang): {e}", styles["Normal"])
        )

    elements.append(Spacer(1, 0.5 * cm))

    # VALIDASI EOT20
    elements.append(Paragraph("Validasi Silang: GOT4.10 vs EOT20", heading_style))
    elements.append(Paragraph(KETERANGAN_VALIDASI, styles["Normal"]))
    elements.append(Spacer(1, 0.2 * cm))

    if validation_data is not None:

        metrik = validation_data["metrik"]

        val_table_data = [
            ["RMSE (m)", "MAE (m)", "Korelasi (r)", "Willmott's d", "Jumlah Data"],
            [
                f"{metrik['rmse_m']:.4f}",
                f"{metrik['mae_m']:.4f}",
                f"{metrik['korelasi_r']:.4f}",
                "-" if pd.isna(metrik.get("willmott_d")) else f"{metrik['willmott_d']:.4f}",
                f"{int(metrik['n_data']):,}",
            ],
        ]
        val_table = Table(val_table_data, hAlign="LEFT")
        val_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#eef1f8")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        elements.append(val_table)
        elements.append(Spacer(1, 0.4 * cm))
        try:
            val_png = validation_data["fig"].to_image(format="png", width=900, height=480, scale=2)
            elements.append(RLImage(io.BytesIO(val_png), width=17 * cm, height=9 * cm))
        except Exception as e:
            elements.append(
                Paragraph(
                    f"Grafik validasi tidak dapat disertakan (paket 'kaleido' belum terpasang): {e}",
                    styles["Normal"],
                )
            )
    else:
        elements.append(
            Paragraph(
                "Data validasi EOT20 belum tersedia untuk kombinasi stasiun, tahun, dan bulan ini.",
                styles["Normal"],
            )
        )

    elements.append(Spacer(1, 0.5 * cm))

    # STATISTIK MINGGUAN
    elements.append(Paragraph("Statistik Mingguan (dihitung langsung oleh dashboard)", heading_style))
    elements.append(Spacer(1, 0.2 * cm))

    try:
        weekly_png = data["weekly_fig"].to_image(format="png", width=900, height=420, scale=2)
        elements.append(RLImage(io.BytesIO(weekly_png), width=17 * cm, height=7.9 * cm))
    except Exception as e:
        elements.append(
            Paragraph(f"Grafik tidak dapat disertakan (paket 'kaleido' belum terpasang): {e}", styles["Normal"])
        )

    elements.append(Spacer(1, 0.5 * cm))

    # TABEL STATISTIK MINGGUAN
    elements.append(Paragraph("Tabel Statistik Mingguan", heading_style))
    table_df = data["table_df"]
    if not table_df.empty:
        header = [
            "Minggu", "Tanggal Mulai", "Tanggal Akhir", "Jumlah Data",
            "Min (m)", "Maks (m)", "MSL/Rata-rata (m)", "Range (m)",
        ]
        rows = table_df.drop(columns=["week_of_year"]).values.tolist()
        pdf_table = Table([header] + rows, hAlign="LEFT", repeatRows=1)
        pdf_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#eef1f8")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(pdf_table)

    else:
        elements.append(Paragraph("Tidak ada data untuk bulan ini.", styles["Normal"]))

    elements.append(Spacer(1, 0.5 * cm))

    # INFORMASI ANALISIS
    elements.append(Paragraph("Informasi Analisis", heading_style))
    elements.append(Paragraph("Model utama: GOT4.10. Model validasi silang: EOT20.", styles["Normal"]))
    elements.append(
        Paragraph("Data diproses menggunakan pyTMD dengan interval prediksi 1 jam.", styles["Normal"])
    )
    elements.append(
        Paragraph("Waktu prediksi ditampilkan dalam WIB; waktu validasi dalam UTC.", styles["Normal"])
    )
    elements.append(Paragraph(KETERANGAN_MSL, styles["Normal"]))
    elements.append(Paragraph(KETERANGAN_PASANG_SURUT, styles["Normal"]))
    elements.append(Paragraph(KETERANGAN_VALIDASI, styles["Normal"]))
    elements.append(
        Paragraph(f"Prediksi ini dilakukan oleh {INSTANSI_NAMA}, {INSTANSI_HOMEBASE}.", styles["Normal"])
    )

    doc.build(elements)
    buffer.seek(0)

    return buffer

# 13. MEMBUAT APLIKASI DASHBOARD
app = Dash(
    __name__,
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap",
        "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
    ],
)

app.title = f"Dashboard Prediksi & Validasi Pasang Surut {YEAR_LABEL}"


# 13b. INDEX STRING
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                margin: 0;
                background: linear-gradient(180deg, #eef1f8 0%, #e3e8f2 100%);
            }
            .stat-card {
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }
            .stat-card:hover {
                transform: translateY(-3px);
                box-shadow: 0 8px 18px rgba(13, 28, 66, 0.18);
            }
            ::-webkit-scrollbar { height: 8px; width: 8px; }
            ::-webkit-scrollbar-thumb { background: #b7c4cc; border-radius: 4px; }
            .station-pin-icon { background: transparent; border: none; }
            /* --- Informasi Analisis --- */
            .info-grid { display: grid; gap: 18px; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); }
            .info-grid-3 { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); }
            .info-summary {
                display: flex; align-items: center; justify-content: space-between;
                padding: 18px 28px; border-radius: 14px; cursor: pointer; list-style: none;
                box-shadow: 0 4px 14px rgba(13, 28, 66, 0.20);
                transition: box-shadow 0.2s ease, filter 0.2s ease; user-select: none;
            }
            .info-summary::-webkit-details-marker { display: none; }
            .info-summary::marker { content: ""; }
            .info-summary:hover { filter: brightness(1.07); box-shadow: 0 6px 18px rgba(13, 28, 66, 0.28); }
            .info-summary:focus-visible { outline: 3px solid rgba(13, 28, 66, 0.35); outline-offset: 2px; }
            .info-chevron-wrap {
                width: 34px; height: 34px; border-radius: 50%; background: rgba(255,255,255,0.18);
                display: flex; align-items: center; justify-content: center; flex: 0 0 34px;
            }
            .info-chevron {
                width: 9px; height: 9px; border-right: 2px solid #ffffff; border-bottom: 2px solid #ffffff;
                transform: rotate(45deg); margin-top: -4px; transition: transform 0.25s ease, margin 0.25s ease;
            }
            .info-details[open] .info-chevron { transform: rotate(-135deg); margin-top: 4px; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""


# 14. HEADER LOGO
logo_components = []
if LOGO_BRIN.exists():
    logo_components.append(html.Img(src="/assets/logo_brin.png", style={"height": "58px", "objectFit": "contain"}))
if LOGO_DKP.exists():
    logo_components.append(html.Img(src="/assets/logo_dkp_diy.png", style={"height": "75px", "objectFit": "contain"}))

FONT_FAMILY = "'Poppins', 'Segoe UI', Arial, sans-serif"

# 14b. FUNGSI CONTAINER
def section_container(children):
    return html.Div(
        children,
        style={
            "backgroundColor": "white",
            "padding": "24px",
            "borderRadius": "16px",
            "boxShadow": "0 4px 16px rgba(15, 60, 80, 0.08)",
            "marginBottom": "25px",
        },
    )

def section_title(text, subtitle=None):

    children = [
        html.H2(
            text,
            style={
                "margin": "0 0 4px 0",
                "fontSize": "20px",
                "color": "#0D1C42",
                "paddingLeft": "12px",
            },
        )
    ]
    if subtitle:
        children.append(
            html.P(subtitle, style={"fontSize": "12.5px", "color": "#6b7590", "margin": "6px 0 14px 17px"})
        )
    else:
        children.append(html.Div(style={"marginBottom": "10px"}))

    return html.Div(children)

# 14c. KOMPONEN TAMPILAN "INFORMASI ANALISIS"
INFO_TEXT = "#33415c"
INFO_MUTED = "#6b7590"

def _id_num(value, digits=2):
    """Format angka desimal dengan koma (gaya penulisan Indonesia)."""
    return f"{value:.{digits}f}".replace(".", ",")

def cite(*nums):
    """Penanda sitasi [n] yang menaut ke daftar referensi di bagian bawah."""
    parts = []
    for i, n in enumerate(nums):
        if i:
            parts.append(", ")
        parts.append(
            html.A(
                str(n), href=f"#ref-{n}",
                style={"color": COLOR_ACCENT, "textDecoration": "none", "fontWeight": "700"},
            )
        )
    return html.Sup(["[", *parts, "]"], style={"fontSize": "11px", "marginLeft": "2px"})

def ext_link(text, url):
    return html.A(
        text, href=url, target="_blank", rel="noopener noreferrer",
        style={"color": COLOR_ACCENT, "fontWeight": "600", "wordBreak": "break-word"},
    )

def code_tag(text):
    return html.Code(
        text,
        style={
            "backgroundColor": "#eef1f8", "padding": "1px 6px", "borderRadius": "5px",
            "fontSize": "12.5px", "color": "#0D1C42",
        },
    )

def info_heading(title):
    return html.H3(
        title,
        style={
            "margin": "30px 0 14px 0", "paddingBottom": "8px", "fontSize": "16px",
            "color": "#0D1C42", "borderBottom": "1px solid #e3e7f1",
        },
    )

def info_chip(text, bg="#eef1f8", color="#0D1C42", border="#d6dcec"):
    return html.Span(
        text,
        style={
            "display": "inline-block", "backgroundColor": bg, "color": color,
            "border": f"1px solid {border}", "fontSize": "12.5px", "fontWeight": "600",
            "padding": "5px 12px", "borderRadius": "999px", "margin": "0 6px 8px 0",
        },
    )

def info_para(children, **extra_style):
    style = {"fontSize": "14px", "lineHeight": "1.7", "color": INFO_TEXT, "margin": "0 0 12px 0"}
    style.update(extra_style)
    return html.P(children, style=style)

def info_kv(rows):
    """Daftar 'label - isi' bergaya tabel ringan di dalam kartu."""
    items = []
    for label, value in rows:
        items.append(
            html.Div(
                [
                    html.Div(
                        label,
                        style={
                            "fontSize": "11.5px", "fontWeight": "700", "color": INFO_MUTED,
                            "textTransform": "uppercase", "letterSpacing": "0.4px",
                            "marginBottom": "3px",
                        },
                    ),
                    html.Div(value, style={"fontSize": "13.5px", "color": "#33415c", "lineHeight": "1.6"}),
                ],
                style={"padding": "10px 0", "borderTop": "1px solid #edf1f3"},
            )
        )
    return html.Div(items, style={"marginTop": "14px"})

def info_card(children, accent=COLOR_ACCENT):
    return html.Div(
        children,
        style={
            "backgroundColor": "white", "padding": "20px 22px", "borderRadius": "14px",
            "border": "1px solid #e3e7f1", "borderTop": f"4px solid {accent}",
            "boxShadow": "0 2px 10px rgba(15, 60, 80, 0.06)",
        },
    )

def info_callout(title, children, tone="info"):
    palette = {
        "info": ("#eef1f8", COLOR_ACCENT),
        "warn": ("#fff8e6", "#d68910"),
        "alert": ("#fdf1f0", "#c0392b"),
    }
    background, accent = palette[tone]
    return html.Div(
        [
            html.Div(
                title,
                style={"fontWeight": "700", "fontSize": "14px", "color": accent, "marginBottom": "6px"},
            ),
            html.Div(children, style={"fontSize": "13.5px", "lineHeight": "1.7", "color": INFO_TEXT}),
        ],
        style={
            "backgroundColor": background, "borderLeft": f"4px solid {accent}",
            "borderRadius": "10px", "padding": "14px 18px",
        },
    )

def model_card(label, color, title, subtitle, description, rows):
    return info_card(
        [
            html.Div(
                label,
                style={"fontSize": "11px", "fontWeight": "700", "letterSpacing": "1px", "color": color},
            ),
            html.H4(title, style={"margin": "6px 0 2px 0", "fontSize": "20px", "color": "#0D1C42"}),
            html.Div(subtitle, style={"fontSize": "12.5px", "color": INFO_MUTED, "marginBottom": "12px"}),
            info_para(description, margin="0"),
            info_kv(rows),
        ],
        accent=color,
    )

def step_card(number, title, text):
    return html.Div(
        [
            html.Div(
                str(number),
                style={
                    "width": "28px", "height": "28px", "borderRadius": "50%",
                    "backgroundColor": "#eef1f8", "color": COLOR_ACCENT_DARK, "fontWeight": "700",
                    "display": "flex", "alignItems": "center", "justifyContent": "center",
                    "marginBottom": "8px", "fontSize": "13px",
                },
            ),
            html.Div(title, style={"fontWeight": "700", "fontSize": "13.5px", "color": "#0D1C42", "marginBottom": "4px"}),
            html.Div(text, style={"fontSize": "12.5px", "lineHeight": "1.6", "color": "#5b6b73"}),
        ],
        style={
            "backgroundColor": "#f7f8fd", "border": "1px solid #e3e7f1", "borderRadius": "12px",
            "padding": "14px 16px",
        },
    )

def ref_item(number, children):
    return html.Div(
        [
            html.Div(
                f"[{number}]",
                style={
                    "flex": "0 0 auto", "backgroundColor": COLOR_ACCENT_DARK, "color": "white",
                    "fontWeight": "700", "fontSize": "12px", "padding": "3px 9px",
                    "borderRadius": "6px", "height": "fit-content", "marginTop": "2px",
                },
            ),
            html.Div(children, style={"fontSize": "13.3px", "lineHeight": "1.7", "color": INFO_TEXT}),
        ],
        id=f"ref-{number}",
        style={"display": "flex", "gap": "12px", "padding": "12px 0", "borderTop": "1px solid #edf1f3"},
    )

def build_info_analisis_section():
    """Bagian 'Informasi Analisis' (ditampilkan langsung di tab sendiri)."""

    # data dinamis dari file koordinat
    n_stasiun = len(valid_stations)
    stasiun_urut = sorted(valid_stations, key=lambda nama: valid_stations[nama][0])
    lon_semua = [lon for lon, _ in valid_stations.values()]
    lat_semua = [lat for _, lat in valid_stations.values()]
    lon_min, lon_max = min(lon_semua), max(lon_semua)
    lat_min, lat_max = abs(max(lat_semua)), abs(min(lat_semua))

    # 1. PASANG SURUT & AREA KAJIAN
    kartu_pasut = info_card(
        [
            html.H4("Apa itu pasang surut?", style={"margin": "0 0 10px 0", "fontSize": "17px", "color": "#0D1C42"}),
            info_para(
                "Pasang surut (pasut) adalah naik-turunnya permukaan laut secara berkala, terutama "
                "akibat gaya tarik gravitasi Bulan dan Matahari pada Bumi yang berputar. Titik "
                "tertinggi dalam satu siklus disebut pasang (high tide), dan titik terendahnya "
                "disebut surut (low tide)."
            ),
            info_para(
                [
                    "Karena bersifat astronomis dan sangat teratur, pasut dapat dihitung jauh hari "
                    "sebelumnya. Pasut diuraikan menjadi konstituen harmonik (misalnya M2, S2, K1, "
                    "dan O1) yang masing-masing punya amplitudo dan fase. Model pasut global "
                    "menyimpan konstanta harmonik itu, lalu perangkat lunak pyTMD",
                    cite(2),
                    " menjumlahkannya menjadi deret waktu elevasi muka laut.",
                ],
                margin="0",
            ),
        ],
    )

    kartu_area = info_card(
        [
            html.H4("Area kajian", style={"margin": "0 0 10px 0", "fontSize": "17px", "color": "#0D1C42"}),
            info_para(
                f"Kajian mencakup {n_stasiun} titik stasiun di pesisir selatan Daerah Istimewa "
                "Yogyakarta yang menghadap Samudra Hindia, membentang dari Kulon Progo di barat "
                f"hingga Gunungkidul di timur (sekitar {_id_num(lon_min)}°-{_id_num(lon_max)}° BT "
                f"dan {_id_num(lat_min)}°-{_id_num(lat_max)}° LS)."
            ),
            html.Div([info_chip(nama) for nama in stasiun_urut], style={"marginTop": "6px"}),
        ],
        accent="#117864",
    )

    # 2. MODEL PASUT
    kartu_got = model_card(
        "MODEL UTAMA", COLOR_MODEL_A, "GOT4.10", "Goddard Ocean Tide, NASA Goddard Space Flight Center (GSFC)",
        [
            "Model pasut laut global dari NASA GSFC yang diturunkan dari analisis harmonik data "
            "altimetri satelit, dibangun dari seri satelit Topex/Poseidon, Jason-1, dan Jason-2",
            cite(3, 5),
            ". Model ini dipakai sebagai sumber prediksi utama pada dashboard.",
        ],
        [
            ("Pengembang", ["Richard D. Ray, NASA GSFC", cite(3, 5)]),
            ("Basis data", ["Altimetri satelit Topex/Poseidon, Jason-1, dan Jason-2", cite(5)]),
            ("Resolusi spasial",
             ["±0,5° (seri GOT4). Cukup kasar untuk perairan dekat pantai, sehingga titik stasiun "
              "disesuaikan ke sel laut terdekat", cite(5)]),
            ("Sumber unduhan",
             ["Server NASA GSFC, diunduh otomatis lewat fungsi ", code_tag("fetch_gsfc_got()"),
              " milik pyTMD", cite(2)]),
        ],
    )

    kartu_eot = model_card(
        "MODEL PEMBANDING", COLOR_MODEL_B, "EOT20", "Empirical Ocean Tide model, DGFI-TUM (Jerman)",
        [
            "Model pasut global terbaru dalam seri model DGFI-TUM. EOT20 dibuat dengan analisis "
            "pasut residual data altimetri multi-misi periode 1992-2019 (11 misi satelit) dengan "
            "FES2014b sebagai model acuan",
            cite(1, 4),
            ". Model ini dipakai untuk validasi silang terhadap GOT4.10.",
        ],
        [
            ("Pengembang",
             ["M. Hart-Davis, G. Piccioni, D. Dettmering, C. Schwatke, M. Passaro, F. Seitz", cite(1)]),
            ("Cakupan dan resolusi",
             ["66°LS-66°LU (lintang lebih tinggi diisi FES2014b), grid 1/8° (0,125°)", cite(1)]),
            ("17 konstituen",
             [html.Div(
                 [info_chip(c, bg="#fdf3e4", color="#8a5a12", border="#f0d9b0")
                  for c in ["2N2", "J1", "K1", "K2", "M2", "M4", "MF", "MM", "N2",
                            "O1", "P1", "Q1", "S1", "S2", "SA", "SSA", "T2"]]
                 + [cite(1)],
                 style={"marginTop": "4px"},
             )]),
            ("Sumber unduhan",
             ["Repositori SEANOE (DOI 10.17882/79489), NetCDF, akses terbuka, lisensi CC BY 4.0. ", cite(1)]),
        ],
    )

    # 3. PERANGKAT LUNAK & ALUR
    kartu_pytmd = info_card(
        [
            html.H4("pyTMD: perangkat lunak prediksi", style={"margin": "0 0 10px 0", "fontSize": "17px", "color": "#0D1C42"}),
            info_para(
                [
                    "pyTMD adalah perangkat lunak prediksi pasut berbasis Python untuk memperkirakan "
                    "pasut laut, load tide, solid Earth tide, dan pole tide, berlisensi MIT",
                    cite(2),
                    ". Pada kajian ini, pyTMD membaca konstanta harmonik GOT4.10 dan EOT20 lalu "
                    "menghitung elevasi pasut per jam di setiap titik stasiun.",
                ],
                margin="0",
            ),
        ],
        accent="#5d6d7e",
    )

    langkah = [
        (1, "Muat model", "GOT4.10 diunduh otomatis lewat pyTMD, sedangkan EOT20 diunduh manual dari SEANOE."),
        (2, "Sesuaikan titik stasiun",
         "Titik yang tidak berada di sel laut model digeser ke sel laut terdekat (radius maksimum 0,05°)."),
        (3, "Prediksi per jam",
         f"Elevasi dihitung tiap 1 jam dalam UTC, per bulan, untuk tahun {YEAR_LABEL}."),
        (4, "Konversi dan statistik",
         "Waktu diubah ke WIB (UTC+7), dibagi per minggu kalender (Senin-Minggu), lalu dihitung nilai minimum, maksimum, dan rata-rata."),
        (5, "Validasi silang",
         "GOT4.10 dibandingkan dengan EOT20 pada waktu dan titik yang sama memakai RMSE, MAE, korelasi (r), dan Willmott's d."),
    ]

    # 4. CATATAN
    catatan_astronomis = info_callout(
        "Prediksi astronomis, bukan pengamatan",
        "Hasil pada dashboard adalah prediksi pasut astronomis dari model global. Pengaruh cuaca "
        "(angin dan tekanan udara), gelombang, dan kondisi lokal seperti muara atau teluk tidak "
        "ikut dihitung, sehingga tinggi muka air sebenarnya dapat berbeda dari prediksi.",
        tone="warn",
    )
    catatan_spasial = info_callout(
        "Catatan spasial",
        "Titik Baron, Gesing, Jungwok, dan Sadeng memiliki posisi koordinat yang relatif lebih jauh dari "
        "garis pantai dibandingkan beberapa titik lainnya. Oleh karena itu, ketiga titik tersebut "
        "perlu diperlakukan sebagai titik representasi perairan lepas pantai, bukan sebagai lokasi "
        "pengamatan pasang surut tepat di garis pantai. Pada proses pemodelan, koordinat dapat "
        "mengalami penyesuaian menuju grid laut terdekat GOT4.10 apabila koordinat awal tidak "
        "berada pada sel laut model. Hasil pada ketiga lokasi tersebut perlu diinterpretasikan "
        "sebagai representasi kondisi pasang surut pada area perairan sekitar titik, bukan sebagai "
        "tinggi muka air tepat di dermaga atau garis pantai.",
        tone="warn",
    )
    catatan_waktu = info_callout(
        "Zona waktu",
        "Waktu prediksi ditampilkan dalam Waktu Indonesia Barat (WIB), sedangkan waktu pada "
        "validasi silang memakai UTC. Interval prediksi 1 jam.",
        tone="info",
    )

    # 5. REFERENSI
    referensi_utama = [
        ref_item(
            1,
            [
                "Hart-Davis, M., Piccioni, G., Dettmering, D., Schwatke, C., Passaro, M., & Seitz, F. (2021). "
                "EOT20 - A global Empirical Ocean Tide model from multi-mission satellite altimetry [Data set]. "
                "SEANOE. ",
                ext_link("https://www.seanoe.org/data/00683/79489/", "https://www.seanoe.org/data/00683/79489/"),
            ],
        ),
        ref_item(
            2,
            [
                "GitHub - pyTMD/pyTMD: Python-based tidal prediction software. ",
                ext_link("https://github.com/pyTMD/pyTMD", "https://github.com/pyTMD/pyTMD"),
            ],
        ),
    ]
    referensi_pendukung = [
        ref_item(
            3,
            [
                "Ray, R. D. (2013). Precise comparisons of bottom-pressure and altimetric ocean tides. ",
                html.Em("Journal of Geophysical Research: Oceans, 118"),
                ", 4570-4584. ",
                ext_link("https://doi.org/10.1002/jgrc.20336", "https://doi.org/10.1002/jgrc.20336"),
            ],
        ),
        ref_item(
            4,
            [
                "Hart-Davis, M. G., Piccioni, G., Dettmering, D., Schwatke, C., Passaro, M., & Seitz, F. (2021). "
                "EOT20: a global ocean tide model from multi-mission satellite altimetry. ",
                html.Em("Earth System Science Data, 13"),
                "(8), 3869-3884. ",
                ext_link("https://doi.org/10.5194/essd-13-3869-2021", "https://doi.org/10.5194/essd-13-3869-2021"),
            ],
        ),
        ref_item(
            5,
            [
                "Ray, R. D. (2025). ",
                html.Em("Documentation for Goddard Ocean Tide Solution GOT5: Global Tides from Multimission "
                        "Satellite Altimetry"),
                " (NASA TM-20250002085). NASA Goddard Space Flight Center. ",
                ext_link(
                    "https://ntrs.nasa.gov/api/citations/20250002085/downloads/GOT5-TechMemo.pdf",
                    "https://ntrs.nasa.gov/api/citations/20250002085/downloads/GOT5-TechMemo.pdf",
                ),
            ],
        ),
    ]

    isi = html.Div(
        [
            # JUDUL UTAMA INFORMASI ANALISIS
            html.Div(
                [
                    html.Div(
                        "INFORMASI ANALISIS",
                        style={
                            "fontSize": "11px",
                            "fontWeight": "700",
                            "letterSpacing": "2px",
                            "color": COLOR_ACCENT,
                            "marginBottom": "6px",
                        },
                    ),
                    html.H2(
                        "Pasang Surut dan Area Kajian",
                        style={
                            "margin": "0",
                            "fontSize": "27px",
                            "fontWeight": "700",
                            "color": "#0D1C42",
                        },
                    ),
                    html.P(
                        "Informasi mengenai konsep pasang surut dan area kajian "
                        "yang digunakan dalam analisis.",
                        style={
                            "margin": "8px 0 20px 0",
                            "fontSize": "14px",
                            "lineHeight": "1.6",
                            "color": "#6b7590",
                        },
                    ),
                ],
                style={
                    "padding": "6px 0 4px 0",
                    "marginBottom": "8px",
                },
            ),

            # KARTU PASANG SURUT & AREA KAJIAN
            html.Div(
                [kartu_pasut, kartu_area],
                className="info-grid",
            ),

            info_heading("Model Pasang Surut yang Digunakan"),
            html.Div([kartu_got, kartu_eot], className="info-grid"),

            info_heading("Perangkat Lunak dan Alur Pengolahan"),
            kartu_pytmd,
            html.Div(
                [step_card(n, t, x) for n, t, x in langkah],
                className="info-grid-3",
                style={"marginTop": "14px"},
            ),

            info_heading("Cara Membaca Hasil"),
            html.Div(
                [
                    info_callout("Acuan nol (MSL) dan kondisi pasang surut",
                                 [html.P(KETERANGAN_MSL, style={"margin": "0 0 8px 0"}),
                                  html.P(KETERANGAN_PASANG_SURUT, style={"margin": "0"})]),
                    info_callout("Minggu dan validasi",
                                 [html.P("Minggu dihitung berdasarkan kalender riil (Senin s.d. Minggu) dan dipotong "
                                         "pada batas awal dan akhir bulan.", style={"margin": "0 0 8px 0"}),
                                  html.P(KETERANGAN_VALIDASI, style={"margin": "0"})]),
                ],
                style={"display": "flex", "flexDirection": "column", "gap": "12px"},
            ),

            info_heading("Catatan dan Keterbatasan"),
            html.Div(
                [catatan_astronomis, catatan_spasial, catatan_waktu],
                style={"display": "flex", "flexDirection": "column", "gap": "12px"},
            ),

            info_heading("Referensi"),
            html.Div(referensi_utama),
            html.Details(
                [
                    html.Summary(
                        "Rujukan pendukung (rincian model GOT4.10 dan EOT20)",
                        style={"cursor": "pointer", "fontWeight": "600", "color": COLOR_ACCENT_DARK,
                               "fontSize": "13px", "padding": "10px 0"},
                    ),
                    html.Div(referensi_pendukung),
                ],
                open=True,
                style={"marginTop": "4px"},
            ),

            html.P(
                f"Prediksi ini dilakukan oleh {INSTANSI_NAMA}, {INSTANSI_HOMEBASE}.",
                style={"fontStyle": "italic", "color": "#6b7590", "fontSize": "13px",
                       "marginTop": "22px", "paddingTop": "14px", "borderTop": "1px solid #edf1f3"},
            ),
        ],
        style={"paddingTop": "6px"},
    )

    return section_container([isi])

# 14d. TAB: PANDUAN PEMANFAATAN (palet navy seragam + aksen oranye)
from datetime import date as _date

# Palet khusus tab Panduan, disamakan dengan palet UI utama
PG_BLUE = UI_BLUE_SOFT
PG_NAVY = UI_NAVY
PG_NAVY2 = UI_NAVY_MID
PG_ORANGE = "#F68048"
PG_TEXT = UI_TEXT
PG_MUTED = UI_MUTED
PG_LINE = UI_LINE
PG_GRID = "#e8ebf4"
# Warna data (pasang/surut/MSL) - tidak diubah
PG_HIGH = "#3f7d5a"
PG_LOW = "#a8453a"
PG_MSL = "#4a5578"

# ---------------------------------------------------------------------
# GAMBAR PANDUAN
# Prioritas: foto milik Anda di folder `foto_panduan` (nelayan, pemancing,
# wisata, pengelola). Bila tidak ada, dipakai ilustrasi pantai bawaan (SVG).
# ---------------------------------------------------------------------
PANDUAN_IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")

def find_panduan_image(name):
    for ext in PANDUAN_IMG_EXT:
        for candidate in (name + ext, name + ext.upper()):
            p = PANDUAN_IMG_DIR / candidate
            if p.exists():
                return p
    return None

def _svg_data_uri(svg):
    return "data:image/svg+xml;utf8," + quote(svg)

def _scene_svg(kind):
    cfg = {
        "hero":      dict(t="#22396F", b="#F9C9A8", sea1="#16295f", sea2="#0D1C42", sun="#FBD6B8", sx=560, sy=210, sr=52),
        "nelayan":   dict(t="#2E4A8A", b="#F6A57A", sea1="#22396F", sea2="#0D1C42", sun="#FDE3CC", sx=590, sy=200, sr=46),
        "pemancing": dict(t="#6f86bd", b="#dfe6fb", sea1="#2E4A8A", sea2="#22396F", sun="#fff1e6", sx=610, sy=170, sr=40),
        "wisata":    dict(t="#93a5d3", b="#fde6d2", sea1="#3b5aa3", sea2="#2E4A8A", sun="#fff3e6", sx=170, sy=150, sr=44),
        "pengelola": dict(t="#5a6fa8", b="#dfe4f7", sea1="#22396F", sea2="#0D1C42", sun="#fbe3d0", sx=640, sy=190, sr=38),
    }[kind]

    waves = (
        '<g fill="none" stroke="#ffffff" stroke-opacity="0.22" stroke-width="2">'
        '<path d="M0 285 Q50 275 100 285 T200 285 T300 285 T400 285 T500 285 T600 285 T700 285 T800 285"/>'
        '<path d="M0 318 Q60 306 120 318 T240 318 T360 318 T480 318 T600 318 T720 318 T840 318"/>'
        '<path d="M0 352 Q70 338 140 352 T280 352 T420 352 T560 352 T700 352 T840 352"/>'
        '</g>'
    )

    extra = ""
    if kind == "hero":
        extra = (
            '<path d="M0 420 L0 215 L70 190 L130 220 L200 250 L260 420 Z" fill="#0d1a4a"/>'
            '<path d="M800 420 L800 235 L730 215 L670 245 L610 290 L580 420 Z" fill="#14246b"/>'
            '<path d="M0 420 L0 380 Q200 360 400 385 T800 375 L800 420 Z" fill="#080f33" opacity="0.55"/>'
        )
    elif kind == "nelayan":
        extra = (
            '<path d="M230 262 L470 262 L436 300 L266 300 Z" fill="#0d1a4a"/>'
            '<rect x="346" y="150" width="4" height="114" fill="#0d1a4a"/>'
            '<path d="M352 158 L352 252 L420 252 Z" fill="#ecdfc6"/>'
            '<path d="M346 150 L346 160 L322 155 Z" fill="#F68048"/>'
            '<path d="M200 318 Q330 306 470 318" stroke="#ffffff" stroke-opacity="0.18" stroke-width="3" fill="none"/>'
        )
    elif kind == "pemancing":
        extra = (
            '<path d="M0 420 L0 245 L80 228 L150 258 L225 300 L300 420 Z" fill="#2a3156"/>'
            '<path d="M0 420 L0 320 L120 310 L200 340 L250 420 Z" fill="#1f2544"/>'
            '<circle cx="118" cy="190" r="9" fill="#0d1a4a"/>'
            '<path d="M118 200 L118 238 M118 210 L138 222 M118 238 L108 262 M118 238 L130 262" stroke="#0d1a4a" stroke-width="5" stroke-linecap="round" fill="none"/>'
            '<path d="M134 214 L352 108" stroke="#0d1a4a" stroke-width="2.5" fill="none"/>'
            '<path d="M352 108 L352 296" stroke="#ffffff" stroke-opacity="0.7" stroke-width="1" fill="none"/>'
            '<circle cx="352" cy="296" r="4" fill="#F68048"/>'
        )
    elif kind == "wisata":
        extra = (
            '<path d="M0 420 L0 338 Q200 316 420 336 T800 322 L800 420 Z" fill="#e6d3a8"/>'
            '<path d="M0 420 L0 372 Q240 352 480 374 T800 362 L800 420 Z" fill="#d9c391"/>'
            '<path d="M0 338 Q200 316 420 336 T800 322" stroke="#ffffff" stroke-opacity="0.65" stroke-width="3" fill="none"/>'
            '<path d="M520 300 Q580 238 660 300 Z" fill="#b5503f"/>'
            '<path d="M560 300 Q590 252 620 300 Z" fill="#f2e6cf"/>'
            '<path d="M590 262 L590 372" stroke="#6b5a45" stroke-width="4"/>'
            '<ellipse cx="520" cy="384" rx="70" ry="9" fill="#bda87a" opacity="0.5"/>'
        )
    elif kind == "pengelola":
        extra = (
            '<path d="M0 420 L0 352 Q200 332 420 354 T800 342 L800 420 Z" fill="#d8c9a3"/>'
            '<path d="M470 352 L490 200 M550 352 L530 200" stroke="#16204f" stroke-width="6" fill="none"/>'
            '<path d="M480 300 L540 300 M484 262 L536 262" stroke="#16204f" stroke-width="3"/>'
            '<rect x="466" y="160" width="88" height="44" fill="#16204f"/>'
            '<rect x="476" y="170" width="68" height="20" fill="#c9d6dc" opacity="0.85"/>'
            '<path d="M458 160 L510 128 L562 160 Z" fill="#a8453a"/>'
            '<path d="M510 128 L510 98" stroke="#16204f" stroke-width="3"/>'
            '<path d="M510 98 L540 108 L510 118 Z" fill="#F68048"/>'
            '<circle cx="300" cy="340" r="24" fill="none" stroke="#f4f0e6" stroke-width="10"/>'
            '<path d="M300 316 A24 24 0 0 1 324 340 M300 364 A24 24 0 0 1 276 340" stroke="#a8453a" stroke-width="10" fill="none"/>'
        )

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 420" preserveAspectRatio="xMidYMid slice">'
        f'<defs><linearGradient id="sk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{cfg["t"]}"/>'
        f'<stop offset="1" stop-color="{cfg["b"]}"/></linearGradient></defs>'
        '<rect width="800" height="420" fill="url(#sk)"/>'
        f'<circle cx="{cfg["sx"]}" cy="{cfg["sy"]}" r="{cfg["sr"]}" fill="{cfg["sun"]}" opacity="0.92"/>'
        f'<rect y="250" width="800" height="170" fill="{cfg["sea1"]}"/>'
        f'<rect y="310" width="800" height="110" fill="{cfg["sea2"]}"/>'
        + waves + extra +
        '</svg>'
    )
    return svg

def panduan_image_url(name):
    p = find_panduan_image(name)
    if p is not None:
        return f"/assets/panduan/{p.name}"
    return _svg_data_uri(_scene_svg(name))


# CSS tambahan (disisipkan ke index_string yang sudah ada)
PANDUAN_CSS = """
            /* --- Tab Panduan Pemanfaatan --- */
            .pg-hero {
                position: relative; overflow: hidden; border-radius: 18px; padding: 34px 38px;
                color: #ffffff; margin: 25px 0 25px 0;
                background: linear-gradient(135deg, #010736 0%, #0D1C42 55%, #22396F 100%);
                box-shadow: 0 8px 24px rgba(13, 28, 66, 0.28);
            }
            .pg-hero::before, .pg-hero::after {
                content: ""; position: absolute; border-radius: 50%; background: rgba(255,255,255,0.07);
            }
            .pg-hero::before { width: 320px; height: 320px; right: -80px; top: -140px; }
            .pg-hero::after  { width: 220px; height: 220px; right: 140px; bottom: -150px; }
            .pg-hero-eyebrow { font-size: 11.5px; font-weight: 700; letter-spacing: 2px; opacity: 0.8; }
            .pg-hero h2 { margin: 8px 0 10px 0; font-size: 27px; font-weight: 700; line-height: 1.3; max-width: 760px; }
            .pg-hero p  { margin: 0 0 18px 0; font-size: 14.5px; line-height: 1.7; max-width: 720px; opacity: 0.93; }
            .pg-hero-chip {
                display: inline-block; margin: 0 8px 8px 0; padding: 6px 14px; border-radius: 999px;
                font-size: 12.5px; font-weight: 600; background: rgba(255,255,255,0.16);
                border: 1px solid rgba(255,255,255,0.28);
            }
            .pg-grid-4 { display: grid; gap: 18px; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
            .pg-grid-steps { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }
            .pg-user-card {
                background: #ffffff; border: 1px solid #e3e7f1; border-radius: 16px; padding: 22px 22px 20px 22px;
                box-shadow: 0 2px 10px rgba(13, 28, 66, 0.06); overflow: hidden;
                transition: transform 0.18s ease, box-shadow 0.18s ease;
            }
            .pg-user-card:hover { transform: translateY(-4px); box-shadow: 0 12px 26px rgba(46, 74, 138, 0.16); }
            .pg-card-img {
                height: 150px; margin: -22px -22px 16px -22px; background-size: cover; background-position: center;
            }
            .pg-user-card h4 { margin: 0 0 2px 0; font-size: 18px; color: #0D1C42; }
            .pg-tagline { font-size: 12.5px; color: #6b7590; margin-bottom: 12px; }
            .pg-user-card ul { margin: 0 0 14px 0; padding-left: 18px; }
            .pg-user-card li { font-size: 13.3px; line-height: 1.65; color: #33415c; margin-bottom: 6px; }
            .pg-caution {
                font-size: 12.5px; line-height: 1.6; color: #7a3a14; background: #fff4ec;
                border-left: 3px solid #F68048; border-radius: 8px; padding: 9px 12px;
            }
            .pg-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13.3px; }
            .pg-table th {
                text-align: left; background: #0D1C42; color: #ffffff; padding: 12px 14px; font-weight: 600;
            }
            .pg-table th:first-child { border-top-left-radius: 10px; }
            .pg-table th:last-child { border-top-right-radius: 10px; }
            .pg-table td { padding: 12px 14px; border-bottom: 1px solid #e8ebf4; color: #33415c; vertical-align: top; line-height: 1.6; }
            .pg-table tr:nth-child(even) td { background: #f7f8fd; }
            .pg-table td:first-child { font-weight: 600; color: #0D1C42; white-space: nowrap; }
            .pg-check { list-style: none; margin: 0; padding: 0; }
            .pg-check li {
                display: flex; gap: 14px; align-items: flex-start; padding: 12px 4px;
                border-top: 1px solid #e8ebf4; font-size: 13.7px; line-height: 1.65; color: #33415c;
            }
            .pg-check li:first-child { border-top: none; }
            .pg-check-num {
                flex: 0 0 28px; height: 28px; border-radius: 50%; background: #eef1f8; color: #0D1C42;
                font-weight: 700; font-size: 13px; display: flex; align-items: center; justify-content: center;
            }
            .pg-event {
                display: flex; align-items: center; gap: 14px; padding: 12px 16px; border-radius: 12px;
                background: #ffffff; border: 1px solid #e3e7f1; margin-bottom: 10px;
                box-shadow: 0 1px 6px rgba(13, 28, 66, 0.05);
            }
            .pg-event-icon {
                width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center;
                justify-content: center; font-weight: 700; font-size: 15px; flex: 0 0 36px;
            }
            .pg-event-time { font-size: 18px; font-weight: 700; color: #0D1C42; min-width: 110px; }
            .pg-event-type { font-size: 13px; font-weight: 600; flex: 1; }
            .pg-event-height { font-size: 13.5px; color: #5a6384; font-weight: 600; }
"""
app.index_string = app.index_string.replace("</style>", PANDUAN_CSS + "\n        </style>", 1)


# ---------------------------------------------------------------------
# Fungsi bantu: deteksi puncak pasang & lembah surut dari data per jam
# ---------------------------------------------------------------------
def detect_tide_extrema(times, heights):
    """Cari puncak (pasang) dan lembah (surut) dari deret per jam.

    Waktu & tinggi diperhalus dengan interpolasi parabola 3 titik, sehingga
    estimasi waktu tidak terkunci pada jam bulat.
    Mengembalikan list dict: {jenis, waktu, tinggi}.
    """
    events = []
    y = np.asarray(heights, dtype=float)
    for i in range(1, len(y) - 1):
        y0, y1, y2 = y[i - 1], y[i], y[i + 1]
        is_high = (y1 > y0) and (y1 >= y2)
        is_low = (y1 < y0) and (y1 <= y2)
        if not (is_high or is_low):
            continue
        denom = y0 - 2 * y1 + y2
        offset = 0.0 if denom == 0 else 0.5 * (y0 - y2) / denom
        offset = float(np.clip(offset, -1.0, 1.0))
        peak_value = y1 - 0.25 * (y0 - y2) * offset
        events.append({
            "jenis": "Pasang" if is_high else "Surut",
            "waktu": times.iloc[i] + pd.Timedelta(minutes=offset * 60),
            "tinggi": float(peak_value),
        })
    return events


# Komponen tampilan khusus tab Panduan
def pg_section_container(children):
    return html.Div(
        children,
        style={
            "backgroundColor": "white", "padding": "24px", "borderRadius": "16px",
            "boxShadow": "0 4px 16px rgba(13, 28, 66, 0.08)", "marginBottom": "25px",
        },
    )


def pg_section_title(text, subtitle=None):
    children = [
        html.H2(
            text,
            style={"margin": "0 0 4px 0", "fontSize": "20px", "color": PG_NAVY, "paddingLeft": "12px"},
        )
    ]
    if subtitle:
        children.append(
            html.P(subtitle, style={"fontSize": "12.5px", "color": PG_MUTED, "margin": "6px 0 14px 17px"})
        )
    else:
        children.append(html.Div(style={"marginBottom": "10px"}))
    return html.Div(children)


def pg_heading(title):
    return html.H3(
        title,
        style={
            "margin": "30px 0 14px 0", "paddingBottom": "8px", "fontSize": "16px",
            "color": PG_NAVY, "borderBottom": f"1px solid {PG_LINE}",
        },
    )


def pg_step_card(number, title, text):
    return html.Div(
        [
            html.Div(
                str(number),
                style={
                    "width": "28px", "height": "28px", "borderRadius": "50%",
                    "backgroundColor": UI_TINT, "color": PG_NAVY, "fontWeight": "700",
                    "display": "flex", "alignItems": "center", "justifyContent": "center",
                    "marginBottom": "8px", "fontSize": "13px",
                },
            ),
            html.Div(title, style={"fontWeight": "700", "fontSize": "13.5px", "color": PG_NAVY, "marginBottom": "4px"}),
            html.Div(text, style={"fontSize": "12.5px", "lineHeight": "1.6", "color": "#5a6384"}),
        ],
        style={
            "backgroundColor": "#f7f8fd", "border": f"1px solid {PG_LINE}", "borderRadius": "12px",
            "padding": "14px 16px",
        },
    )


def pg_callout(title, children, tone="info"):
    palette = {
        "info": ("#eef1f8", PG_BLUE),
        "warn": ("#fff4ec", "#c4561a"),
        "alert": ("#fdf1f0", "#c0392b"),
    }
    background, accent = palette[tone]
    return html.Div(
        [
            html.Div(
                title,
                style={"fontWeight": "700", "fontSize": "14px", "color": accent, "marginBottom": "6px"},
            ),
            html.Div(children, style={"fontSize": "13.5px", "lineHeight": "1.7", "color": PG_TEXT}),
        ],
        style={
            "backgroundColor": background, "borderLeft": f"4px solid {accent}",
            "borderRadius": "10px", "padding": "14px 18px",
        },
    )


def pg_info_card(message):
    return html.Div(
        message,
        style={
            "backgroundColor": "#f7f8fd", "border": f"1px dashed {PG_BLUE}", "borderRadius": "12px",
            "padding": "18px 20px", "color": PG_TEXT, "fontSize": "14px", "width": "100%",
        },
    )


def pg_stat_card(title, value, unit="", accent=PG_BLUE):
    return html.Div(
        [
            html.Div(
                title,
                style={
                    "fontSize": "13px", "fontWeight": "600", "color": "#5a6384", "marginBottom": "8px",
                    "textTransform": "uppercase", "letterSpacing": "0.4px",
                },
            ),
            html.Div(f"{value} {unit}", style={"fontSize": "26px", "fontWeight": "700", "color": PG_NAVY}),
        ],
        className="stat-card",
        style={
            "backgroundColor": "white", "padding": "18px 20px", "borderRadius": "14px",
            "borderLeft": f"4px solid {accent}", "boxShadow": "0 2px 10px rgba(13, 28, 66, 0.08)",
            "textAlign": "left", "flex": "1", "minWidth": "170px",
        },
    )


def pg_user_card(image_name, title, tagline, points, caution):
    return html.Div(
        [
            html.Div(
                className="pg-card-img",
                style={"backgroundImage": f"url('{panduan_image_url(image_name)}')"},
            ),
            html.H4(title),
            html.Div(tagline, className="pg-tagline"),
            html.Ul([html.Li(p) for p in points]),
            html.Div([html.B("Perhatikan: "), caution], className="pg-caution"),
        ],
        className="pg-user-card",
    )


def pg_check_item(number, text):
    return html.Li([html.Div(str(number), className="pg-check-num"), html.Div(text)])


def pg_table(header, rows):
    return html.Div(
        html.Table(
            [
                html.Thead(html.Tr([html.Th(h) for h in header])),
                html.Tbody([html.Tr([html.Td(c) for c in row]) for row in rows]),
            ],
            className="pg-table",
        ),
        style={"overflowX": "auto", "border": f"1px solid {PG_LINE}", "borderRadius": "10px"},
    )


def build_panduan_section():
    # HERO
    hero = html.Div(
        [
            html.Div("PANDUAN PEMANFAATAN", className="pg-hero-eyebrow"),
            html.H2("Memanfaatkan Prediksi Pasang Surut untuk Aktivitas di Pesisir Selatan DIY"),
            html.P(
                "Prediksi pasang surut membantu menentukan waktu yang tepat untuk berangkat, "
                "kembali, dan beraktivitas di pantai. Halaman ini membantu memahami cara membaca "
                "grafik dashboard untuk nelayan, pemancing, wisatawan, dan pengelola kawasan pantai."
            ),
            html.Div(
                [
                    html.Span("Nelayan", className="pg-hero-chip"),
                    html.Span("Pemancing", className="pg-hero-chip"),
                    html.Span("Wisata Pantai", className="pg-hero-chip"),
                    html.Span("Pengelola & Petugas", className="pg-hero-chip"),
                ]
            ),
        ],
        className="pg-hero",
    )

    # PERINGATAN UTAMA
    peringatan = pg_callout(
        "Pasang surut bukan satu-satunya penentu keselamatan",
        [
            html.P(
                "Dashboard hanya memuat prediksi pasang surut astronomis. Tinggi gelombang, angin, "
                "cuaca, dan arus balik (rip current) tidak termasuk di dalamnya. Pantai selatan "
                "menghadap Samudra Hindia dengan gelombang yang dapat membesar sewaktu-waktu, "
                "sehingga kondisi laut bisa berbahaya meskipun jadwal pasang surut terlihat "
                "\"aman\".",
                style={"margin": "0 0 8px 0"},
            ),
            html.P(
                "Selalu cek prakiraan tinggi gelombang dan cuaca maritim dari BMKG pada hari "
                "yang sama, serta ikuti imbauan petugas di lokasi.",
                style={"margin": "0"},
            ),
        ],
        tone="alert",
    )

    # CARA MEMBACA
    langkah = [
        (1, "Pilih stasiun terdekat", "Gunakan titik yang paling dekat dengan lokasi kegiatan Anda."),
        (2, "Cari puncak dan lembah", "Puncak kurva adalah pasang tertinggi, lembah adalah surut terendah pada tiap siklus."),
        (3, "Catat jamnya", "Waktu pada dashboard sudah dalam WIB, jadi bisa langsung dipakai."),
        (4, "Lihat selisihnya", "Selisih pasang dan surut yang besar berarti muka air berubah lebih cepat."),
    ]

    # KARTU PENGGUNA
    kartu = [
        pg_user_card(
            "nelayan", "Nelayan", "Merencanakan berangkat dan pulang",
            [
                "Gunakan jam puncak pasang dan lembah surut untuk menentukan waktu keluar dan "
                "masuk, terutama bila melewati muara, alur sempit, atau dermaga.",
                "Kedalaman alur dan sandar kapal berubah mengikuti tinggi muka air. Saat surut "
                "rendah, area dangkal bisa menyulitkan kapal berdraft dalam.",
                "Siapkan jam kembali yang longgar, tidak mepet dengan perubahan kondisi laut.",
            ],
            "keputusan melaut tetap bertumpu pada prakiraan gelombang dan angin BMKG, bukan pada "
            "jadwal pasang surut.",
        ),
        pg_user_card(
            "pemancing", "Pemancing", "Memilih waktu dan lokasi memancing",
            [
                "Banyak pemancing memilih waktu saat air sedang bergerak (peralihan antara pasang "
                "dan surut). Kebiasaan ini bervariasi antar lokasi dan jenis ikan, jadi anggap "
                "sebagai acuan, bukan kepastian.",
                "Memancing di karang atau batu: surut rendah membuka area lebih luas, tetapi saat "
                "air kembali naik jalur pulang bisa tertutup. Tentukan batas jam kembali sebelum "
                "air naik.",
                "Pantau terus gelombang yang datang, terutama saat berdiri di batu atau tebing.",
            ],
            "korban terseret gelombang sering terjadi pada pemancing di karang dan tebing. "
            "Gunakan pelampung dan jangan memancing sendirian saat gelombang tinggi.",
        ),
        pg_user_card(
            "wisata", "Wisata Pantai", "Berlibur dengan lebih aman",
            [
                "Saat surut, area pantai dan karang tampak lebih luas. Saat pasang, garis air maju "
                "dan area berpasir menyempit. Atur waktu bermain, foto, atau berjalan di tepi "
                "pantai sesuai kondisi ini.",
                "Hindari berjalan jauh ke area karang menjelang air naik karena jalur kembali bisa "
                "terputus.",
                "Untuk berenang, patuhi bendera dan zona yang ditetapkan petugas. Pasang surut "
                "tidak menggambarkan keberadaan arus balik.",
            ],
            "jangan masuk ke air bila ada larangan atau peringatan, walaupun air tampak tenang "
            "dari tepi.",
        ),
        pg_user_card(
            "pengelola", "Pengelola & Petugas", "Patroli, informasi, dan kesiapsiagaan",
            [
                "Susun jadwal patroli dan penempatan petugas dengan mempertimbangkan jam pasang "
                "tertinggi, saat muka air paling maju ke arah daratan.",
                "Gunakan grafik dan jadwal harian sebagai bahan informasi bagi pengunjung dan "
                "nelayan di papan pengumuman atau kanal komunikasi setempat.",
                "Manfaatkan untuk kegiatan pesisir lain seperti penataan sarana wisata, kerja "
                "bakti pantai, atau acara masyarakat.",
            ],
            "prediksi tidak memuat pengaruh cuaca ekstrem atau gelombang. Gabungkan dengan "
            "peringatan resmi BMKG.",
        ),
    ]

    # TABEL PERTIMBANGAN CEPAT
    tabel = pg_table(
        ["Kondisi", "Arti", "Dampak praktis"],
        [
            ["Mendekati puncak", "Pasang tertinggi pada siklus tersebut",
             "Garis air paling maju. Area berpasir atau karang yang rendah tertutup lebih luas."],
            ["Mendekati lembah", "Surut terendah pada siklus tersebut",
             "Karang dan dasar dangkal terbuka. Alur dan area sandar menjadi lebih dangkal."],
            ["Kurva naik atau turun curam", "Muka air berubah cepat",
             "Arus pasut umumnya lebih terasa. Perlu lebih waspada saat beraktivitas dekat air."],
            ["Kurva melandai di puncak atau lembah", "Perubahan muka air sesaat melambat",
             "Umumnya fase arus pasut lebih lemah, namun kondisi gelombang tetap perlu dipantau."],
            ["Selisih pasang-surut harian besar", "Rentang naik-turun lebih lebar",
             "Perubahan area terbuka dan tertutup lebih besar. Beri cadangan waktu lebih longgar."],
        ],
    )

    # CHECKLIST
    checklist = html.Ul(
        [
            pg_check_item(1, "Cek jadwal pasang surut stasiun terdekat untuk tanggal kegiatan (menu jadwal harian di atas)."),
            pg_check_item(2, "Cek prakiraan tinggi gelombang, angin, dan cuaca maritim dari BMKG pada hari yang sama."),
            pg_check_item(3, "Tentukan batas jam terakhir untuk kembali atau keluar dari area karang, beri cadangan waktu yang cukup."),
            pg_check_item(4, "Beritahu keluarga atau rekan tentang lokasi dan perkiraan jam kembali."),
            pg_check_item(5, "Gunakan pelampung dan perlengkapan keselamatan, lalu hentikan kegiatan bila kondisi laut berubah."),
        ],
        className="pg-check",
    )

    # JADWAL HARIAN INTERAKTIF
    if not tide_dashboard_df.empty:
        tgl_min = tide_dashboard_df["datetime_wib"].min().date()
        tgl_max = tide_dashboard_df["datetime_wib"].max().date()
    else:
        tgl_min, tgl_max = _date(YEARS[0], 1, 1), _date(YEARS[-1], 12, 31)

    kontrol = html.Div(
        [
            html.Div(
                [
                    html.Label("Pilih Stasiun", style={"fontWeight": "600", "color": PG_TEXT}),
                    dcc.Dropdown(
                        id="pg-station",
                        options=[{"label": s, "value": s} for s in station_options],
                        value=station_options[0],
                        clearable=False,
                    ),
                ],
                style={"flex": "1"},
            ),
            html.Div(
                [
                    html.Label("Pilih Tanggal", style={"fontWeight": "600", "color": PG_TEXT, "display": "block"}),
                    dcc.DatePickerSingle(
                        id="pg-date",
                        min_date_allowed=tgl_min,
                        max_date_allowed=tgl_max,
                        initial_visible_month=tgl_min,
                        date=tgl_min,
                        display_format="DD/MM/YYYY",
                        style={"width": "100%"},
                    ),
                ],
                style={"flex": "0 0 220px"},
            ),
        ],
        style={
            "display": "flex", "gap": "20px", "alignItems": "flex-end", "backgroundColor": "#f7f8fd",
            "padding": "16px 18px", "borderRadius": "12px", "border": f"1px solid {PG_LINE}",
            "marginBottom": "18px",
        },
    )

    jadwal = pg_section_container([
        pg_section_title(
            "Jadwal Pasang dan Surut Harian",
            "Pilih stasiun dan tanggal untuk melihat jam perkiraan pasang tertinggi dan surut "
            "terendah pada hari tersebut (WIB).",
        ),
        kontrol,
        html.Div(id="pg-summary", style={"display": "flex", "gap": "18px", "flexWrap": "wrap", "marginBottom": "18px"}),
        dcc.Graph(id="pg-graph"),
        html.H3("Jam Pasang dan Surut", style={"fontSize": "16px", "color": PG_NAVY, "margin": "10px 0 12px 0"}),
        html.Div(id="pg-events"),
        html.P(
            "Jam dan tinggi puncak diestimasi dari data per jam dengan interpolasi, sehingga dapat "
            "bergeser beberapa menit hingga puluhan menit dari kondisi sebenarnya. Gunakan sebagai "
            "gambaran perencanaan.",
            style={"fontSize": "12.5px", "color": PG_MUTED, "fontStyle": "italic", "margin": "12px 0 0 0"},
        ),
    ])

    keterbatasan = pg_callout(
        "Keterbatasan data",
        [
            html.P(
                "Prediksi pasang surut menggunakan model global GOT4.10 yang memiliki resolusi spasial relatif kasar, "
                "terutama untuk wilayah dekat pantai. Titik Baron, Gesing, Jungwok, dan Sadeng merupakan titik "
                "representasi perairan sekitar, bukan lokasi di dermaga atau garis pantai.",
                style={"margin": "0 0 8px 0"},
            ),
            html.P(
                "Untuk kegiatan pelayaran atau aktivitas dengan risiko tinggi, gunakan prediksi ini sebagai referensi "
                "tambahan dan tetap mengacu pada tabel pasang surut resmi dari instansi berwenang serta informasi dan peringatan cuaca laut dari BMKG.",
                style={"margin": "0"},
            ),
        ],
        tone="warn",
    )

    return html.Div(
        [
            hero,
            peringatan,
            html.Div(
                [
                    pg_heading("Cara Membaca Grafik untuk Kegiatan Anda"),
                    html.Div([pg_step_card(n, t, x) for n, t, x in langkah], className="pg-grid-steps"),
                ],
                style={"marginTop": "6px"},
            ),
            pg_heading("Manfaat untuk Setiap Pengguna"),
            html.Div(kartu, className="pg-grid-4"),
            html.Div(style={"height": "26px"}),
            jadwal,
            pg_section_container([
                pg_section_title(
                    "Pertimbangan Cepat",
                    "Rangkuman hubungan bentuk kurva dengan kondisi di lapangan.",
                ),
                tabel,
            ]),
            pg_section_container([
                pg_section_title(
                    "Panduan Singkat Sebelum Beraktivitas di Laut",
                    "Lima langkah singkat sebelum melaut, memancing, atau berwisata.",
                ),
                checklist,
                html.Div(style={"height": "14px"}),
                keterbatasan,
            ]),
            html.P(
                f"Prediksi ini dilakukan oleh {INSTANSI_NAMA}, {INSTANSI_HOMEBASE}.",
                style={"fontStyle": "italic", "color": PG_MUTED, "fontSize": "13px", "margin": "0 4px 20px 4px"},
            ),
        ]
    )


# Callback jadwal harian
@app.callback(
    Output("pg-summary", "children"),
    Output("pg-graph", "figure"),
    Output("pg-events", "children"),
    Input("pg-station", "value"),
    Input("pg-date", "date"),
)
def update_panduan_harian(station, date_str):
    empty_fig = go.Figure()
    empty_fig.update_layout(template="plotly_white", height=360, title="Data tidak tersedia")
    info_kosong = pg_info_card("Data prediksi belum tersedia untuk stasiun dan tanggal ini.")

    if not station or not date_str or tide_dashboard_df.empty:
        return [info_kosong], empty_fig, []

    day_start = pd.Timestamp(date_str).normalize()
    day_end = day_start + pd.Timedelta(days=1)
    margin = pd.Timedelta(hours=3)  # data tambahan agar puncak di tepi hari tetap terdeteksi

    sdf = tide_dashboard_df[
        (tide_dashboard_df["station"] == station)
        & (tide_dashboard_df["datetime_wib"] >= day_start - margin)
        & (tide_dashboard_df["datetime_wib"] <= day_end + margin)
    ].sort_values("datetime_wib").drop_duplicates("datetime_wib").reset_index(drop=True)

    day_df = sdf[(sdf["datetime_wib"] >= day_start) & (sdf["datetime_wib"] < day_end)]
    if day_df.empty:
        return [info_kosong], empty_fig, []

    events_all = detect_tide_extrema(sdf["datetime_wib"], sdf["tide_m"])
    events = sorted(
        [e for e in events_all if day_start <= e["waktu"] < day_end],
        key=lambda e: e["waktu"],
    )
    highs = [e for e in events if e["jenis"] == "Pasang"]
    lows = [e for e in events if e["jenis"] == "Surut"]

    h_max = float(day_df["tide_m"].max())
    h_min = float(day_df["tide_m"].min())
    cards = [
        pg_stat_card("Elevasi Tertinggi", f"{h_max:.3f}", "m", accent=PG_HIGH),
        pg_stat_card("Elevasi Terendah", f"{h_min:.3f}", "m", accent=PG_LOW),
        pg_stat_card("Selisih Harian", f"{h_max - h_min:.3f}", "m", accent=PG_BLUE),
        pg_stat_card("Jumlah Pasang", f"{len(highs)}", "kali", accent=PG_MSL),
    ]

    # GRAFIK
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=day_df["datetime_wib"], y=day_df["tide_m"], mode="lines", name="Prediksi Pasut",
        line=dict(color=PG_BLUE, width=3, shape="spline", smoothing=0.8),
        fill="tozeroy", fillcolor="rgba(46, 74, 138, 0.10)",
        hovertemplate="<b>%{x|%H:%M} WIB</b><br>Elevasi: %{y:.3f} m<extra></extra>",
    ))
    if highs:
        fig.add_trace(go.Scatter(
            x=[e["waktu"] for e in highs], y=[e["tinggi"] for e in highs],
            mode="markers+text", name="Pasang",
            marker=dict(symbol="triangle-up", size=13, color=PG_HIGH, line=dict(color="white", width=1.5)),
            text=[e["waktu"].strftime("%H:%M") for e in highs], textposition="top center",
            textfont=dict(size=11, color=PG_HIGH),
            hovertemplate="<b>Pasang</b><br>%{text} WIB<br>%{y:.3f} m<extra></extra>",
        ))
    if lows:
        fig.add_trace(go.Scatter(
            x=[e["waktu"] for e in lows], y=[e["tinggi"] for e in lows],
            mode="markers+text", name="Surut",
            marker=dict(symbol="triangle-down", size=13, color=PG_LOW, line=dict(color="white", width=1.5)),
            text=[e["waktu"].strftime("%H:%M") for e in lows], textposition="bottom center",
            textfont=dict(size=11, color=PG_LOW),
            hovertemplate="<b>Surut</b><br>%{text} WIB<br>%{y:.3f} m<extra></extra>",
        ))
    fig.add_hline(y=0, line_dash="dot", line_color="#95a5a6")
    pad = max((h_max - h_min) * 0.18, 0.05)
    fig.update_layout(
        title=dict(
            text=f"Pasang Surut Harian - {station} - {day_start.strftime('%d/%m/%Y')}",
            x=0.02, xanchor="left", font=dict(size=17, color=PG_NAVY),
        ),
        template="plotly_white", height=420,
        xaxis=dict(title="Jam (WIB)", tickformat="%H:%M", dtick=3 * 3600 * 1000,
                   range=[day_start, day_end], gridcolor=PG_GRID),
        yaxis=dict(title="Elevasi terhadap MSL (m)", range=[h_min - pad, h_max + pad],
                   gridcolor=PG_GRID, zeroline=False),
        hovermode="x unified",
        margin=dict(l=65, r=25, t=80, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=1),
        font=dict(family="Poppins, Arial, sans-serif"),
    )

    # DAFTAR JAM
    if not events:
        event_children = [pg_info_card("Tidak ada puncak atau lembah terdeteksi pada tanggal ini.")]
    else:
        event_children = []
        for e in events:
            is_high = e["jenis"] == "Pasang"
            warna = PG_HIGH if is_high else PG_LOW
            event_children.append(
                html.Div(
                    [
                        html.Div("\u25B2" if is_high else "\u25BC", className="pg-event-icon",
                                 style={"backgroundColor": f"{warna}22", "color": warna}),
                        html.Div(f"{e['waktu'].strftime('%H:%M')} WIB", className="pg-event-time"),
                        html.Div("Pasang tertinggi" if is_high else "Surut terendah",
                                 className="pg-event-type", style={"color": warna}),
                        html.Div(f"{e['tinggi']:.3f} m", className="pg-event-height"),
                    ],
                    className="pg-event",
                    style={"borderLeft": f"4px solid {warna}"},
                )
            )

    return cards, fig, event_children


# Isi dua tab baru
tab_panduan_children = [build_panduan_section()]
tab_informasi_children = [
    html.Div(style={"height": "25px"}),
    build_info_analisis_section(),
]

# 15a. KONTEN TAB 1
tab_utama_children = [
    # FILTER
    html.Div(
        [
            html.Div(
                [
                    html.Label("Pilih Stasiun", style={"fontWeight": "600", "color": "#33415c"}),
                    dcc.Dropdown(
                        id="station-dropdown",
                        options=[{"label": s, "value": s} for s in station_options],
                        value=station_options[0],
                        clearable=False,
                    ),
                ],
                style={"flex": "1"},
            ),
            html.Div(
                [
                    html.Label("Pilih Bulan", style={"fontWeight": "600", "color": "#33415c"}),
                    dcc.Dropdown(
                        id="month-dropdown",
                        options=[{"label": month_indonesia[m], "value": m} for m in month_order],
                        value="January",
                        clearable=False,
                    ),
                ],
                style={"flex": "1"},
            ),
            html.Div(
                [
                    html.Label("Pilih Tahun", style={"fontWeight": "600", "color": "#33415c"}),
                    dcc.Dropdown(
                        id="year-dropdown",
                        options=[{"label": str(y), "value": y} for y in year_options],
                        value=year_options[0],
                        clearable=False,
                    ),
                ],
                style={"flex": "1"},
            ),
            html.Div(
                [
                    html.Label("\u00a0", style={"display": "block"}),
                    html.Button(
                        "\U0001F4E5 Unduh PDF",
                        id="btn-download-pdf",
                        n_clicks=0,
                        style={
                            "width": "100%", "padding": "10px 16px",
                            "backgroundColor": COLOR_ACCENT_DARK, "color": "white",
                            "border": "none", "borderRadius": "10px", "fontWeight": "600",
                            "cursor": "pointer", "fontFamily": FONT_FAMILY,
                        },
                    ),
                    dcc.Download(id="download-pdf"),
                ],
                style={"flex": "0 0 180px"},
            ),
        ],
        style={
            "display": "flex", "gap": "20px", "marginTop": "25px", "marginBottom": "10px",
            "alignItems": "flex-end", "backgroundColor": "white", "padding": "18px 20px",
            "borderRadius": "14px", "boxShadow": "0 2px 10px rgba(15, 60, 80, 0.06)",
        },
    ),

    # KETERANGAN MSL
    html.Div(
        html.P(KETERANGAN_MSL, style={"margin": "0"}),
        style={"fontSize": "13px", "color": "#6b7590", "fontStyle": "italic", "margin": "16px 4px 22px 4px"},
    ),

    # PETA
    section_container([
        # Judul dan tombol HOME sejajar dalam satu baris
        html.Div(
            [
                section_title(
                    "Peta Lokasi Stasiun",
                    "Sebaran 13 titik stasiun pengamatan pasang surut di pantai selatan DIY.",
                ),
                html.Button(
                    "Kembali ke Tampilan Awal",
                    id="btn-map-home",
                    n_clicks=0,
                    title="Kembalikan peta ke posisi dan zoom awal",
                    style={
                        "padding": "9px 18px",
                        "backgroundColor": COLOR_ACCENT_DARK,
                        "color": "white",
                        "border": "none",
                        "borderRadius": "8px",
                        "fontWeight": "600",
                        "fontSize": "13px",
                        "cursor": "pointer",
                        "fontFamily": FONT_FAMILY,
                        "boxShadow": "0 2px 6px rgba(15, 60, 80, 0.18)",
                        "whiteSpace": "nowrap",
                        "flex": "0 0 auto",
                    },
                ),
            ],
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "flex-start",
                "gap": "16px",
                "flexWrap": "wrap",
            },
        ),
        dl.Map(
            id="station-map",
            center=STATION_MAP_CENTER,
            zoom=STATION_MAP_ZOOM,
            viewport=dict(center=STATION_MAP_CENTER, zoom=STATION_MAP_ZOOM),
            style={"width": "100%", "height": "560px", "borderRadius": "12px", "zIndex": 0},
            children=build_station_map_layers(None),
        ),
    ]),

    # SUMMARY CARDS
    html.Div(id="summary-cards", style={"display": "flex", "gap": "18px", "flexWrap": "wrap", "marginBottom": "25px"}),

    # GRAFIK PREDIKSI
    section_container([
        section_title("Grafik Prediksi Pasang Surut"),
        dcc.Graph(id="tide-graph"),
    ]),

    # VALIDASI EOT20
    section_container([
        section_title("Validasi Silang: GOT4.10 vs EOT20", KETERANGAN_VALIDASI),
        html.Div(id="validation-cards", style={"display": "flex", "gap": "18px", "flexWrap": "wrap", "marginBottom": "18px"}),
        html.Div(id="validation-graph-wrapper"),
    ]),

    # STATISTIK MINGGUAN
    section_container([
        section_title("Statistik Mingguan"),
        dcc.Graph(id="weekly-graph"),
    ]),

    # TABEL MINGGUAN
    section_container([
        section_title(
            "Tabel Statistik Mingguan",
            "Seluruh nilai elevasi (min, maks, rata-rata/MSL, range) dalam satuan meter (m), "
            "beserta daftar rentang tanggal tiap minggu yang dihitung langsung oleh dashboard.",
        ),
        dash_table.DataTable(
            id="statistics-table",
            columns=[
                {"name": "Minggu ke-", "id": "week_in_month"},
                {"name": "Tanggal Mulai", "id": "start_date"},
                {"name": "Tanggal Akhir", "id": "end_date"},
                {"name": "Jumlah Data", "id": "jumlah_data_valid"},
                {"name": "Minimum (m)", "id": "minimum_m"},
                {"name": "Maksimum (m)", "id": "maximum_m"},
                {"name": "MSL / Rata-rata (m)", "id": "mean_m"},
                {"name": "Range (m)", "id": "range_m"},
            ],
            data=[],
            page_size=10,
            sort_action="native",
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "center", "padding": "10px", "fontSize": "13px", "fontFamily": FONT_FAMILY},
            style_header={"fontWeight": "700", "backgroundColor": "#eef1f8", "color": "#0D1C42"},
            style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#f7f8fd"}],
        ),
    ]),
]


# 15b. KONTEN TAB 2 - VALIDASI BIG
_default_station_big = validasi_big_station_options[0] if validasi_big_station_options else None
_default_bulan_big = (
    validasi_big_bulan_tersedia(_default_station_big)[0] if _default_station_big else "January"
)

tab_validasi_big_children = [

    # KETERANGAN
    html.Div(
        html.P(
            f"Menu ini membaca hasil validasi 3 perbandingan tahun {YEAR_VALIDASI_BIG} yang diproses "
            "menggunakan data GOT4.10 vs EOT20 vs data BIG.",
            style={"margin": "0"},
        ),
        style={"fontSize": "13px", "color": "#6b7590", "fontStyle": "italic", "margin": "16px 4px 22px 4px"},
    ),

    # INFO JIKA DATA TIDAK ADA
    (
        section_container([
            create_info_card(
                "Hasil validasi 3 perbandingan (GOT4.10 vs EOT20 vs BIG) tahun "
                f"{YEAR_VALIDASI_BIG} belum ditemukan di folder "
                f"'hasil_validasi_3perbandingan_{YEAR_VALIDASI_BIG}'. Jalankan dahulu script "
                "'validasi_3perbandingan_2025.py', lalu buka ulang dashboard ini.",
                tone="warning",
            )
        ])
        if not VALIDASI_BIG_TERSEDIA
        else html.Div()
    ),

    # FILTER VALIDASI BIG
    html.Div(
        [
            html.Div(
                [
                    html.Label("Pilih Stasiun", style={"fontWeight": "600", "color": "#33415c"}),
                    dcc.Dropdown(
                        id="validasi-big-station-dropdown",
                        options=[
                            {"label": label_stasiun_validasi_big(s), "value": s}
                            for s in validasi_big_station_options
                        ],
                        value=_default_station_big,
                        clearable=False,
                        placeholder="Tidak ada data stasiun",
                    ),
                ],
                style={"flex": "1"},
            ),
            html.Div(
                [
                    html.Label("Pilih Bulan", style={"fontWeight": "600", "color": "#33415c"}),
                    dcc.Dropdown(
                        id="validasi-big-month-dropdown",
                        options=[
                            {"label": month_indonesia[m], "value": m}
                            for m in validasi_big_bulan_tersedia(_default_station_big)
                        ],
                        value=_default_bulan_big,
                        clearable=False,
                        placeholder="Tidak ada data bulan",
                    ),
                ],
                style={"flex": "1"},
            ),
            html.Div(
                [
                    html.Label(
                        "Tahun",
                        style={"fontWeight": "600", "color": "#33415c", "display": "block", "textAlign": "center"},
                    ),
                    html.Div(
                        str(YEAR_VALIDASI_BIG),
                        style={
                            "backgroundColor": "#eef1f8",
                            "borderRadius": "8px",
                            "fontWeight": "600",
                            "color": "#0D1C42",
                            "border": "1px solid #dfe6e9",
                            "height": "38px",
                            "boxSizing": "border-box",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                        },
                    ),
                ],
                style={"flex": "0 0 140px"},
            ),
        ],
        style={
            "display": "flex", "gap": "20px", "marginBottom": "10px", "alignItems": "flex-end",
            "backgroundColor": "white", "padding": "18px 20px", "borderRadius": "14px",
            "boxShadow": "0 2px 10px rgba(15, 60, 80, 0.06)",
        },
    ),

    # TABEL METRIK
    section_container([
        section_title(
            f"Validasi {YEAR_VALIDASI_BIG}: GOT4.10 vs EOT20 vs Data BIG",
            "Ringkasan metrik dan perbandingan deret waktu pada stasiun serta bulan yang dipilih.",
        ),
        dash_table.DataTable(
            id="validasi-big-table",
            columns=[
                {"name": "Metrik", "id": "metrik"},
                {"name": "GOT4.10 vs BIG", "id": "got_big"},
                {"name": "EOT20 vs BIG", "id": "eot_big"},
                {"name": "GOT4.10 vs EOT20", "id": "got_eot"},
            ],
            data=[],
            style_table={
                "overflowX": "auto", "border": "1px solid #dfe6e9",
                "borderRadius": "10px", "overflow": "hidden",
            },
            style_cell={
                "textAlign": "center", "padding": "12px 14px", "fontSize": "13px",
                "fontFamily": FONT_FAMILY, "color": "#33415c", "border": "none",
                "borderBottom": "1px solid #edf1f3", "height": "44px",
            },
            style_cell_conditional=[
                {
                    "if": {"column_id": "metrik"},
                    "textAlign": "left", "fontWeight": "600", "color": "#0D1C42",
                    "backgroundColor": "#f7f8fd", "minWidth": "170px",
                },
            ],
            style_header={
                "fontWeight": "700", "backgroundColor": "#0D1C42", "color": "white",
                "border": "none", "height": "48px", "fontSize": "13px",
            },
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#fbfcfd"},
                {"if": {"column_id": "got_big"}, "fontWeight": "600"},
                {"if": {"column_id": "eot_big"}, "fontWeight": "600"},
                {"if": {"column_id": "got_eot"}, "fontWeight": "600"},
            ],
        ),
    ]),

    # GRAFIK BATANG
    section_container([
        section_title(
            "Grafik Perbandingan Statistik",
            "Rata-rata elevasi dari tiga sumber data pada periode yang dipilih: GOT4.10, EOT20, dan "
            "data BIG, terhadap MSL (0). Batang naik di atas 0 berarti elevasi rata-rata lebih "
            "tinggi dari MSL, batang turun di bawah 0 berarti lebih rendah dari MSL.",
        ),
        html.Div(
            dcc.Graph(id="validasi-big-bar-graph"),
            style={"backgroundColor": "#ffffff", "border": "1px solid #e3e8eb", "borderRadius": "12px", "padding": "8px"},
        ),
    ]),

    # GRAFIK DERET WAKTU
    section_container([
        section_title(
            "Grafik Deret Waktu",
            "Perbandingan langsung GOT4.10, EOT20, dan data BIG pada stasiun dan bulan yang dipilih.",
        ),
        html.Div(
            dcc.Graph(id="validasi-big-graph"),
            style={"backgroundColor": "#ffffff", "border": "1px solid #e3e8eb", "borderRadius": "12px", "padding": "8px"},
        ),
    ]),

    # INFORMASI VALIDASI BIG
    section_container([
        html.H3("Informasi Menu Validasi 2025", style={"color": "#0D1C42", "marginTop": "0"}),
        html.P(KETERANGAN_VALIDASI_BIG),
        html.P("Data acuan: prediksi pasang surut resmi Badan Informasi Geospasial (BIG)."),
        html.P("Model yang dibandingkan: GOT4.10 (Goddard Ocean Tide model) dan EOT20 (Empirical Ocean Tide model)."),
        html.P(
            f"Prediksi ini dilakukan oleh {INSTANSI_NAMA}, {INSTANSI_HOMEBASE}.",
            style={"fontStyle": "italic", "color": "#6b7590"},
        ),
    ]),
]


# 15c. LAYOUT UTAMA
_TAB_STYLE = {"fontFamily": FONT_FAMILY, "fontWeight": "600", "padding": "12px"}
_TAB_SELECTED_STYLE = {
    "fontFamily": FONT_FAMILY, "fontWeight": "700", "padding": "12px",
    "borderTop": f"3px solid {COLOR_ACCENT}", "color": COLOR_ACCENT_DARK,
}

app.layout = html.Div(
    [
        # HEADER
        html.Div(
            [
                html.Div(logo_components, style={"display": "flex", "gap": "20px", "alignItems": "center"}),
                html.Div(
                    [
                        html.H1(
                            "DASHBOARD PREDIKSI & VALIDASI PASANG SURUT LAUT",
                            style={"margin": "0", "fontSize": "26px", "color": COLOR_TITLE_MAIN, "fontWeight": "700"},
                        ),
                        html.H3(
                            f"Model Utama GOT4.10 | Validasi Silang EOT20 Tahun {YEAR_LABEL} | "
                            f"Validasi {YEAR_VALIDASI_BIG}",
                            style={"margin": "8px 0 0 0", "fontWeight": "500", "color": COLOR_TITLE_SUB},
                        ),
                        html.P(
                            "13 Stasiun Pantai Selatan Daerah Istimewa Yogyakarta",
                            style={"margin": "5px 0 0 0", "color": "#4a5c64"},
                        ),
                        html.P(
                            f"Prediksi ini dilakukan oleh {INSTANSI_NAMA} - {INSTANSI_HOMEBASE}",
                            style={"margin": "6px 0 0 0", "fontSize": "13px", "color": "#8a9aa1", "fontStyle": "italic"},
                        ),
                    ],
                    style={"textAlign": "center", "flex": "1"},
                ),
            ],
            style={
                "display": "flex", "alignItems": "center", "gap": "30px", "padding": "22px 35px",
                "backgroundColor": "white", "borderRadius": "16px",
                "boxShadow": "0 4px 16px rgba(15, 60, 80, 0.10)", "borderTop": f"5px solid {COLOR_ACCENT}",
            },
        ),

        # TABS
        dcc.Tabs(
            id="main-nav-tabs",
            value="tab-utama",
            style={"marginTop": "22px"},
            colors={"border": "#dfe6e9", "primary": COLOR_ACCENT, "background": "#f7f8fd"},
            children=[
                dcc.Tab(
                    label="Dashboard Prediksi & Validasi EOT20",
                    value="tab-utama",
                    children=tab_utama_children,
                    style=_TAB_STYLE,
                    selected_style=_TAB_SELECTED_STYLE,
                ),
                dcc.Tab(
                    label=f"Validasi {YEAR_VALIDASI_BIG}: GOT4.10 vs EOT20 vs BIG",
                    value="tab-validasi-big",
                    children=tab_validasi_big_children,
                    style=_TAB_STYLE,
                    selected_style=_TAB_SELECTED_STYLE,
                ),
                dcc.Tab(
                    label="Panduan Pemanfaatan",
                    value="tab-panduan",
                    children=tab_panduan_children,
                    style=_TAB_STYLE,
                    selected_style=_TAB_SELECTED_STYLE,
                ),
                dcc.Tab(
                    label="Informasi Analisis",
                    value="tab-informasi",
                    children=tab_informasi_children,
                    style=_TAB_STYLE,
                    selected_style=_TAB_SELECTED_STYLE,
                ),
            ],
        ),
    ],
    style={"minHeight": "100vh", "padding": "30px 5%", "fontFamily": FONT_FAMILY},
)


# 16. CALLBACK UTAMA
@app.callback(
    Output("summary-cards", "children"),
    Output("tide-graph", "figure"),
    Output("validation-cards", "children"),
    Output("validation-graph-wrapper", "children"),
    Output("weekly-graph", "figure"),
    Output("statistics-table", "data"),
    Input("station-dropdown", "value"),
    Input("month-dropdown", "value"),
    Input("year-dropdown", "value"),
)
def update_dashboard(selected_station, selected_month, selected_year):
    data = compute_dashboard_data(selected_station, selected_year, selected_month)
    validation_data = compute_validation_data(selected_station, selected_year, selected_month)
    # SUMMARY CARDS
    if data["jumlah_data"] == 0:
        cards = [
            create_card("Minimum", "-", "m"),
            create_card("Maksimum", "-", "m"),
            create_card("MSL/Rata-rata", "-", "m"),
            create_card("Jumlah Data", "0", "data"),
        ]
        table_data = []
    else:
        cards = [
            create_card("Elevasi Minimum", f"{data['minimum']:.3f}", "m", accent="#5dade2"),
            create_card("Elevasi Maksimum", f"{data['maximum']:.3f}", "m", accent="#f5b041"),
            create_card("MSL (Mean Sea Level)", f"{data['msl']:.3f}", "m", accent=COLOR_MSL),
            create_card("Jumlah Data", f"{data['jumlah_data']:,}", "data", accent=COLOR_ACCENT),
        ]
        table_data = data["table_df"].to_dict("records")

    # VALIDASI EOT20
    if validation_data is None:
        validation_cards = [
            create_info_card(
                "Data validasi EOT20 belum tersedia untuk kombinasi stasiun, tahun, dan bulan ini. "
                "Pastikan model EOT20 sudah diunduh secara manual dan proses validasi telah dijalankan."
            )
        ]
        empty_val_fig = go.Figure()
        empty_val_fig.update_layout(title="Data validasi tidak tersedia", template="plotly_white", height=300)
        validation_graph = dcc.Graph(figure=empty_val_fig)
    else:
        metrik = validation_data["metrik"]
        willmott_display = "-" if pd.isna(metrik.get("willmott_d")) else f"{metrik['willmott_d']:.4f}"
        validation_cards = [
            create_card("RMSE", f"{metrik['rmse_m']:.4f}", "m", accent=COLOR_MODEL_A),
            create_card("MAE", f"{metrik['mae_m']:.4f}", "m", accent=COLOR_MODEL_B),
            create_card("Korelasi (r)", f"{metrik['korelasi_r']:.4f}", "", accent=COLOR_RESIDUAL),
            create_card("Willmott's d", willmott_display, "", accent=COLOR_ACCENT),
            create_card("Jumlah Data Cocok", f"{int(metrik['n_data']):,}", "", accent="#7f8c8d"),
        ]

        validation_graph = dcc.Graph(figure=validation_data["fig"])

    return cards, data["tide_fig"], validation_cards, validation_graph, data["weekly_fig"], table_data

# 16b. CALLBACK PETA (highlight pin sesuai stasiun terpilih)
@app.callback(Output("station-map", "children"), Input("station-dropdown", "value"))
def update_station_map(selected_station):
    return build_station_map_layers(selected_station)

# 16c. CALLBACK TOMBOL HOME PETA
@app.callback(
    Output("station-map", "viewport"),
    Input("btn-map-home", "n_clicks"),
    prevent_initial_call=True,
)
def reset_station_map_view(n_clicks):
    return dict(center=STATION_MAP_CENTER, zoom=STATION_MAP_ZOOM, transition="flyTo")

# 16d. CALLBACK DROPDOWN BULAN VALIDASI BIG
@app.callback(
    Output("validasi-big-month-dropdown", "options"),
    Output("validasi-big-month-dropdown", "value"),
    Input("validasi-big-station-dropdown", "value"),
)
def update_validasi_big_month_options(selected_station):
    bulan_list = validasi_big_bulan_tersedia(selected_station) if selected_station else []
    options = [{"label": month_indonesia[m], "value": m} for m in bulan_list]
    value = bulan_list[0] if bulan_list else None
    return options, value

# 16e. CALLBACK TAB 2 - TABEL + GRAFIK BATANG + GRAFIK DERET WAKTU
@app.callback(
    Output("validasi-big-table", "data"),
    Output("validasi-big-bar-graph", "figure"),
    Output("validasi-big-graph", "figure"),
    Input("validasi-big-station-dropdown", "value"),
    Input("validasi-big-month-dropdown", "value"),
)
def update_validasi_big_page(selected_station, selected_month):
    empty_bar_fig = go.Figure()
    empty_bar_fig.update_layout(
        title="Pilih stasiun dan bulan untuk menampilkan grafik", template="plotly_white", height=390
    )
    empty_line_fig = go.Figure()
    empty_line_fig.update_layout(
        title="Pilih stasiun dan bulan untuk menampilkan data", template="plotly_white", height=520
    )
    if not selected_station or not selected_month:
        return [], empty_bar_fig, empty_line_fig
    hasil = compute_validasi_big_dashboard(selected_station, selected_month)
    if hasil["n_data"] == 0:
        return [], empty_bar_fig, hasil["fig"]
    table_data, bar_fig, line_fig = build_validasi_big_summary(hasil["metrics"], hasil["df"])
    return table_data, bar_fig, line_fig

# 17. CALLBACK DOWNLOAD PDF
@app.callback(
    Output("download-pdf", "data"),
    Input("btn-download-pdf", "n_clicks"),
    State("station-dropdown", "value"),
    State("month-dropdown", "value"),
    State("year-dropdown", "value"),
    prevent_initial_call=True,
)
def download_pdf(n_clicks, selected_station, selected_month, selected_year):
    data = compute_dashboard_data(selected_station, selected_year, selected_month)
    validation_data = compute_validation_data(selected_station, selected_year, selected_month)
    pdf_buffer = build_pdf_report(selected_station, selected_year, selected_month, data, validation_data)
    filename = (
        f"dashboard_pasut_{selected_station}_{selected_year}_{selected_month}.pdf".replace(" ", "_")
    )
    return dcc.send_bytes(pdf_buffer.getvalue(), filename=filename)

# 18. SALIN LOGO & FOTO PANDUAN KE ASSETS
ASSETS_DIR = Path(app.server.root_path) / "assets"
ASSETS_DIR.mkdir(exist_ok=True)
if LOGO_BRIN.exists():
    shutil.copy2(LOGO_BRIN, ASSETS_DIR / "logo_brin.png")
if LOGO_DKP.exists():
    shutil.copy2(LOGO_DKP, ASSETS_DIR / "logo_dkp_diy.png")

(ASSETS_DIR / "panduan").mkdir(exist_ok=True)
_foto_ditemukan = []
for _nama in ("nelayan", "pemancing", "wisata", "pengelola"):
    _p = find_panduan_image(_nama)
    if _p is not None:
        shutil.copy2(_p, ASSETS_DIR / "panduan" / _p.name)
        _foto_ditemukan.append(_nama)

# 19. MENJALANKAN DASHBOARD
print("\n" + "=" * 70)
print("DASHBOARD INTERAKTIF :)")
print("=" * 70)
print("Dashboard membaca data GOT4.10 dari folder :", OLAH_DIR, "(hasil_pasut_{tahun}/csv)")
print(
    "Dashboard membaca data validasi EOT20 dari :",
    [str(f) for f in METRICS_FILES_ADA] if METRICS_FILES_ADA else "(belum tersedia)",
)
print(
    "Dashboard membaca data validasi 2025 dari  :",
    METRICS_VALIDASI_BIG_FILE if VALIDASI_BIG_TERSEDIA
    else "(belum tersedia - jalankan validasi_3perbandingan_2025.py)",
)
print("Tahun tersedia pada menu prediksi          :", year_options)
print(
    "Stasiun tersedia pada menu Validasi 2025   :",
    validasi_big_station_options if validasi_big_station_options else "(tidak ada)",
)
print(
    "Foto panduan terpakai                      :",
    _foto_ditemukan if _foto_ditemukan else f"(belum ada; memakai ilustrasi bawaan. Taruh foto di {PANDUAN_IMG_DIR})",
)
print("\nDashboard akan dibuka pada:")
print("http://127.0.0.1:8050/")

# 20. OTOMATIS BUKA BROWSER
def open_browser():
    webbrowser.open("http://127.0.0.1:8050/")
threading.Timer(1.5, open_browser).start()

# 21. RUN DASH
app.run(debug=False, port=8050)