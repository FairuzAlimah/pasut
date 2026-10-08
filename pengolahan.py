#PENGOLAHAN 2027-2029

# 1. IMPORT LIBRARY
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

import pyTMD
import timescale

try:
    from IPython.display import display
except ImportError:
    display = None

# 2. PENGATURAN UMUM
YEARS = [2027, 2028, 2029]         # tahun yang diproses (prediksi + validasi)
YEAR = YEARS[0]                    # tahun berjalan; diganti otomatis di dalam loop
MODEL_A_NAME = "GOT4.10_nc"        # model utama
MODEL_DOWNLOAD_KEY = "GOT4.10"
MODEL_B_NAME = "EOT20"             # model pembanding (validasi silang)
SHOW_PLOTS = False
PREVIEW_ROWS = 20

# 2b. PALET WARNA (untuk grafik statis PNG)
COLOR_TIDE_LINE = "#1f6f8b"     # garis prediksi utama
COLOR_MODEL_A = "#1f6f8b"       # GOT4.10 pada grafik validasi
COLOR_MODEL_B = "#e08e2b"       # EOT20 pada grafik validasi
COLOR_RESIDUAL = "#8e44ad"      # selisih/residual (ungu)
COLOR_MSL = "#34495e"           # garis referensi MSL
COLOR_HIGH = "#1e8449"          # penanda pasang tertinggi
COLOR_LOW = "#c0392b"           # penanda surut terendah

# 3. FOLDER PENYIMPANAN OTOMATIS
MAGANG_DIR = Path(r"D:\MAGANG\A. Data\MAGANG")
MODEL_DIR = MAGANG_DIR / "pytmd_data"          # model tetap di folder MAGANG
OLAH_DIR = MAGANG_DIR / "OLAH"                 # semua hasil pengolahan disimpan di sini

# Folder hasil dibuat PER TAHUN, mis. OLAH/hasil_pasut_2027, OLAH/hasil_pasut_2028, dst.
# Variabel di bawah diisi ulang oleh set_year_folders() setiap pindah tahun.
OUTPUT_DIR = GRAPH_DIR = CSV_DIR = None
VALIDASI_DIR = CSV_VALIDASI_DIR = GRAFIK_VALIDASI_DIR = None

def set_year_folders(year):
    """Menentukan dan membuat folder hasil untuk satu tahun."""
    global YEAR, OUTPUT_DIR, GRAPH_DIR, CSV_DIR
    global VALIDASI_DIR, CSV_VALIDASI_DIR, GRAFIK_VALIDASI_DIR

    YEAR = year
    OUTPUT_DIR = OLAH_DIR / f"hasil_pasut_{year}"
    GRAPH_DIR = OUTPUT_DIR / "grafik_mingguan"
    CSV_DIR = OUTPUT_DIR / "csv"

    VALIDASI_DIR = OLAH_DIR / f"hasil_validasi_eot20_{year}"
    CSV_VALIDASI_DIR = VALIDASI_DIR / "csv"
    GRAFIK_VALIDASI_DIR = VALIDASI_DIR / "grafik"

    for folder in [OUTPUT_DIR, GRAPH_DIR, CSV_DIR,
                   VALIDASI_DIR, CSV_VALIDASI_DIR, GRAFIK_VALIDASI_DIR]:
        folder.mkdir(parents=True, exist_ok=True)

for folder in [MAGANG_DIR, MODEL_DIR, OLAH_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

print("\n" + "=" * 70)
print("PENGATURAN FOLDER")
print("=" * 70)
print("Folder utama          :", MAGANG_DIR)
print("Folder model          :", MODEL_DIR)
print("Folder OLAH           :", OLAH_DIR)
print("Tahun yang diproses   :", YEARS)

# 4. CEK / DOWNLOAD GOT4.10
print("\n" + "=" * 70)
print("MEMERIKSA MODEL GOT4.10")
print("=" * 70)
try:
    pyTMD.datasets.fetch_gsfc_got(
        MODEL_DOWNLOAD_KEY,
        directory=MODEL_DIR,
        format="netcdf"
    )
    print("GOT4.10 tersedia.")
except Exception as e:
    print("Gagal memeriksa atau mengunduh GOT4.10.")
    print("Error:", e)
    raise

# 5. LOAD MODEL GOT4.10
model = pyTMD.io.model(directory=MODEL_DIR, verify=True).from_database(MODEL_A_NAME)
print("\nModel yang digunakan:")
print(model)

# 6. DATA 12 STASIUN
stations = {
    "Congot": (110.0313707, -7.903369915),
    "Glagah": (110.0588790, -7.913859260),
    "Bugel": (110.1509196, -7.952069022),
    "Trisik": (110.1838675, -7.971161565),
    "Ngenthak": (110.2193008, -7.991655391),
    "Kuwaru": (110.2245794, -7.993695320),
    "Goa Cemara": (110.2448847, -7.998691704),
    "Samas": (110.26560024564976, -8.013590714282591),
    "Depok": (110.23781750800629, -8.153363440048446),
    "Baron": (110.52563003777624, -8.261101090536497),
    "Jungwok": (110.69858329429373, -8.209346627259167),
    "Sadeng": (110.7946504, -8.200601385),
    "Gesing": (110.39911409816162, -8.227616940366815),
}

# 7. FUNGSI CEK MASK
def get_mask(lon, lat):
    mask = pyTMD.compute.tide_masks(
        np.array([lon]), np.array([lat]),
        directory=MODEL_DIR, model=MODEL_A_NAME,
        crs=4326, type="time series", method="nearest"
    )
    values = np.asarray(mask.values).squeeze()
    if values.size == 0:
        return False
    return bool(values.flat[0])

# 8. JARAK & 9. ARAH PENCARIAN TITIK LAUT
SEARCH_DISTANCES_DEG = [0.001, 0.002, 0.003, 0.004, 0.005, 0.007, 0.010,
                         0.015, 0.020, 0.025, 0.030, 0.040, 0.050]

_directions_raw = [
    (0, -1), (0, 1), (1, 0), (-1, 0),
    (1, -1), (-1, -1), (1, 1), (-1, 1),
    (0.5, -1), (-0.5, -1), (0.5, 1), (-0.5, 1),
    (1, -0.5), (-1, -0.5), (1, 0.5), (-1, 0.5),
]
SEARCH_DIRECTIONS = [(dlon / np.hypot(dlon, dlat), dlat / np.hypot(dlon, dlat))
                      for dlon, dlat in _directions_raw]

# 10. MENCARI TITIK LAUT TERDEKAT
def find_nearest_ocean_point(lon, lat):
    try:
        if get_mask(lon, lat):
            return (lon, lat, 0.0)
    except Exception:
        pass

    for distance in SEARCH_DISTANCES_DEG:
        candidates = []
        for dlon, dlat in SEARCH_DIRECTIONS:
            new_lon = lon + dlon * distance
            new_lat = lat + dlat * distance
            try:
                if get_mask(new_lon, new_lat):
                    distance_deg = np.hypot(new_lon - lon, new_lat - lat)
                    candidates.append((distance_deg, new_lon, new_lat))
            except Exception:
                continue
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return (candidates[0][1], candidates[0][2], candidates[0][0])

    return None

# 11. CEK DAN MENENTUKAN KOORDINAT AKHIR (sekali saja, berlaku untuk semua tahun)
print("\n" + "=" * 70)
print("CEK KOORDINAT STASIUN")
print("=" * 70)

valid_stations = {}
shift_info = {}

for station_name, (lon, lat) in stations.items():
    print(f"\n{station_name:<15}Lon={lon:.6f}, Lat={lat:.6f}")
    try:
        result = find_nearest_ocean_point(lon, lat)
        if result is None:
            print("  Tidak ditemukan titik laut dalam radius 0.05 derajat.")
            shift_info[station_name] = None
            continue
        new_lon, new_lat, distance = result
        distance_meter = distance * 111320
        valid_stations[station_name] = (new_lon, new_lat)
        shift_info[station_name] = distance_meter
        if distance == 0:
            print("  Menggunakan koordinat asli.")
        else:
            print("  Koordinat digeser ke titik laut terdekat.")
            print(f"  Lon = {new_lon:.6f}")
            print(f"  Lat = {new_lat:.6f}")
            print(f"  Jarak sekitar {distance_meter:.0f} meter")
    except Exception as e:
        print("  Error:", e)
        shift_info[station_name] = None

# 12. TAMPILKAN HASIL KOORDINAT
print("\n" + "=" * 70)
print("HASIL KOORDINAT")
print("=" * 70)
for name, (lon, lat) in valid_stations.items():
    distance = shift_info.get(name, 0)
    if distance is None:
        status = "gagal"
    elif distance == 0:
        status = "koordinat asli"
    else:
        status = f"digeser sekitar {distance:.0f} m"
    print(f"{name:<15}Lon={lon:.6f}  Lat={lat:.6f}  ({status})")

print("\nJumlah stasiun valid:", len(valid_stations))
print("Jumlah stasiun target:", len(stations))

# 13. TABEL KOORDINAT (disimpan ke CSV per tahun di dalam loop)
coord_rows = [
    {
        "station": name,
        "longitude": lon,
        "latitude": lat,
        "pergeseran_meter": shift_info.get(name, 0),
    }
    for name, (lon, lat) in valid_stations.items()
]
coord_df = pd.DataFrame(coord_rows)
if not coord_df.empty:
    print("\nTabel koordinat:")
    if display is not None:
        display(coord_df)
    else:
        print(coord_df.to_string(index=False))

# 14-15. MEMBUAT RENTANG & DAFTAR MINGGU SEPANJANG TAHUN
def create_monthly_weeks(year, month):
    start_month = pd.Timestamp(year=year, month=month, day=1)
    end_month = (pd.Timestamp(year=year + 1, month=1, day=1) if month == 12
                 else pd.Timestamp(year=year, month=month + 1, day=1))

    # Senin pertama pada atau sebelum awal bulan (awal minggu kalender ISO,
    # weekday(): Senin=0 ... Minggu=6)
    first_monday = start_month - pd.Timedelta(days=start_month.weekday())

    weeks = []
    current_monday = first_monday
    week_number = 1

    while current_monday < end_month:
        calendar_week_end = current_monday + pd.Timedelta(days=7)  # akhir minggu kalender penuh (Senin-Minggu)
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

def build_all_weeks(year):
    """Daftar minggu untuk 12 bulan pada satu tahun (nomor minggu tahunan mulai dari 1)."""
    all_weeks = {}
    global_week = 1
    for month in range(1, 13):
        month_name = pd.Timestamp(year=year, month=month, day=1).strftime("%B")
        weeks = create_monthly_weeks(year, month)
        for week in weeks:
            week["week_of_year"] = global_week
            global_week += 1
        all_weeks[month] = {"month_name": month_name, "weeks": weeks}
    return all_weeks

ALL_WEEKS_BY_MONTH = {}   # diisi ulang untuk setiap tahun di dalam loop

# 16. MEMBUAT WAKTU PREDIKSI
def make_monthly_time(year, month):
    start = pd.Timestamp(year=year, month=month, day=1)
    end = (pd.Timestamp(year=year + 1, month=1, day=1) if month == 12
           else pd.Timestamp(year=year, month=month + 1, day=1))
    time = timescale.time.date_range(
        start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), 1, "h"
    )
    return time[:-1]

# 17. PREDIKSI SATU BULAN UNTUK SATU STASIUN (GOT4.10)
def predict_month(station_name, lon, lat, month_number):
    month_info = ALL_WEEKS_BY_MONTH[month_number]
    month_name = month_info["month_name"]
    print("\n" + "-" * 70)
    print(f"Prediksi {station_name} - {month_name} {YEAR}")
    print(f"Koordinat: Lon={lon:.6f}, Lat={lat:.6f}")

    time = make_monthly_time(YEAR, month_number)
    print("Jumlah waktu:", len(time))

    try:
        tide = pyTMD.compute.tide_elevations(
            np.array([lon]), np.array([lat]), time,
            directory=MODEL_DIR, model=MODEL_A_NAME, crs=4326,
            type="time series", standard="datetime", method="nearest",
            extrapolate=True, cutoff=50.0
        )
    except Exception as e:
        print("Gagal menghitung pasang surut.")
        print("Error:", e)
        return pd.DataFrame(), []

    try:
        tide_values = np.asarray(tide.values).squeeze()
    except Exception:
        tide_values = np.asarray(tide).squeeze()
    tide_values = np.asarray(tide_values, dtype=float).flatten()

    print("Jumlah nilai tide:", len(tide_values))
    if len(tide_values) != len(time):
        print("Jumlah data waktu dan hasil prediksi tidak sama.")
        print("Time:", len(time), "| Tide:", len(tide_values))
        return pd.DataFrame(), []

    df = pd.DataFrame({"datetime_utc": pd.to_datetime(time), "tide_m": tide_values})
    df["datetime_wib"] = (
        pd.to_datetime(df["datetime_utc"])
        .dt.tz_localize("UTC")
        .dt.tz_convert("Asia/Jakarta")
        .dt.tz_localize(None)
    )
    df["station"] = station_name

    before = len(df)
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["tide_m"]).reset_index(drop=True)
    removed = before - len(df)
    print("Data awal :", before)
    print("NaN/inf   :", removed)
    print("Data valid:", len(df))
    if df.empty:
        print(f"Tidak ada data valid untuk {station_name} - {month_name}.")
        return pd.DataFrame(), []

    # 18. MENENTUKAN MINGGU
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
    df["week_in_month"] = df["week_in_month"].astype(int)
    df["week_of_year"] = df["week_of_year"].astype(int)

    # 19. STATISTIK MINGGUAN
    stats_list = []
    for week in month_info["weeks"]:
        week_df = df[df["week_in_month"] == week["week_in_month"]]
        if week_df.empty:
            continue
        minimum, maximum, mean = week_df["tide_m"].min(), week_df["tide_m"].max(), week_df["tide_m"].mean()
        stats_list.append({
            "year": YEAR, "station": station_name, "month": month_name,
            "month_number": month_number, "week_in_month": week["week_in_month"],
            "week_of_year": week["week_of_year"],
            "start_date": week["week_start"].strftime("%Y-%m-%d"),
            "end_date": week["display_end"].strftime("%Y-%m-%d"),
            "jumlah_data_valid": len(week_df),
            "minimum_m": minimum, "maximum_m": maximum, "mean_m": mean,
            "range_m": maximum - minimum,
        })

    print(f"Min={df['tide_m'].min():.3f} m | Max={df['tide_m'].max():.3f} m | Mean={df['tide_m'].mean():.3f} m")
    return df, stats_list

# 20. MEMBUAT GRAFIK BULANAN (STATIS/PNG)
def plot_station_month(month_df, month_info, station_name, graph_path):
    month_name = month_info["month_name"]
    if month_df.empty:
        return

    fig, ax = plt.subplots(figsize=(15, 7))
    ax.plot(month_df["datetime_wib"], month_df["tide_m"], linewidth=1.0,
            marker="o", markersize=1.8, color=COLOR_TIDE_LINE)

    # Garis referensi MSL (Mean Sea Level)
    msl_value = month_df["tide_m"].mean()
    ax.axhline(msl_value, color=COLOR_MSL, linestyle="--", linewidth=1.2, alpha=0.9,
               label=f"MSL (Mean Sea Level) = {msl_value:.3f} m")
    ax.legend(loc="upper right", fontsize=8)

    y_min, y_max = month_df["tide_m"].min(), month_df["tide_m"].max()
    y_span = (y_max - y_min) or 1.0

    idx_high, idx_low = month_df["tide_m"].idxmax(), month_df["tide_m"].idxmin()
    t_high, v_high = month_df.loc[idx_high, "datetime_wib"], month_df.loc[idx_high, "tide_m"]
    t_low, v_low = month_df.loc[idx_low, "datetime_wib"], month_df.loc[idx_low, "tide_m"]

    ax.plot(t_high, v_high, marker="^", markersize=9, color=COLOR_HIGH, linestyle="None", zorder=5)
    ax.annotate(f"Pasang tertinggi\n{v_high:.3f} m", xy=(t_high, v_high), xytext=(0, 10),
                textcoords="offset points", ha="center", fontsize=7, color=COLOR_HIGH, fontweight="bold")

    ax.plot(t_low, v_low, marker="v", markersize=9, color=COLOR_LOW, linestyle="None", zorder=5)
    ax.annotate(f"Surut terendah\n{v_low:.3f} m", xy=(t_low, v_low), xytext=(0, -22),
                textcoords="offset points", ha="center", fontsize=7, color=COLOR_LOW, fontweight="bold")

    for week in month_info["weeks"]:
        if week["week_in_month"] > 1:
            ax.axvline(week["week_start"], linestyle="--", linewidth=0.8, alpha=0.6)
        week_mid = week["week_start"] + (week["week_end"] - week["week_start"]) / 2
        ax.text(week_mid, y_max + 0.06 * y_span, f"Minggu {week['week_in_month']}",
                ha="center", va="bottom", fontsize=8)

    ax.set_title(f"Prediksi Pasang Surut GOT4.10 - {station_name}\n{month_name} {YEAR}")
    ax.set_xlabel("Tanggal (WIB)")
    ax.set_ylabel("Elevasi Pasang Surut terhadap MSL (m)")
    ax.set_ylim(y_min - 0.14 * y_span, y_max + 0.16 * y_span)
    ax.grid(True, alpha=0.3)

    fig.text(0.5, 0.01,
              "Pusat Riset Iklim dan Atmosfer, BRIN - Homebase Yogyakarta, "
              "KST Ahmad Baiquni | Elevasi dihitung terhadap MSL (Mean Sea Level)",
              ha="center", va="bottom", fontsize=7, style="italic")

    fig.autofmt_xdate(rotation=30)
    fig.tight_layout(rect=[0, 0.03, 1, 1])

    fig.savefig(graph_path, dpi=300, bbox_inches="tight")
    print("Grafik disimpan:")
    print(graph_path)

    if SHOW_PLOTS:
        plt.show(block=False)
        plt.pause(0.5)
    else:
        plt.close(fig)

# 21. TAMPILKAN PREVIEW CSV
def show_csv_preview(df, csv_path):
    print("\n" + "=" * 70)
    print("PREVIEW DATA CSV")
    print("=" * 70)
    print("File:", csv_path)
    print("Jumlah baris:", len(df))
    print("Jumlah kolom:", len(df.columns))
    preview = df.head(PREVIEW_ROWS)
    if display is not None:
        display(preview)
    else:
        print(preview.to_string(index=False))

# 25. CEK KETERSEDIAAN MODEL EOT20 (tidak bisa diunduh otomatis oleh pyTMD)
print("\n" + "=" * 70)
print("VALIDASI SILANG: GOT4.10 vs EOT20")
print("=" * 70)

EOT20_DIR = MODEL_DIR / "EOT20" / "ocean_tides"
VALIDASI_TERSEDIA = EOT20_DIR.exists() and any(EOT20_DIR.glob("*.nc"))

if not VALIDASI_TERSEDIA:
    print(
        "\nModel EOT20 belum ditemukan di:\n"
        f"  {EOT20_DIR}\n\n"
        "pyTMD TIDAK memiliki fungsi unduh otomatis untuk EOT20\n"
        "(berbeda dengan GOT4.10 yang bisa lewat fetch_gsfc_got).\n"
        "EOT20 (Hart-Davis dkk., 2021) hanya tersedia via PANGAEA:\n\n"
        "  https://doi.org/10.17882/79489\n\n"
        "Langkah unduh manual:\n"
        "  1. Buka DOI di atas, unduh arsip EOT20 (ocean_tides + load_tides).\n"
        "  2. Ekstrak sehingga struktur foldernya menjadi:\n"
        f"     {MODEL_DIR / 'EOT20' / 'ocean_tides'}/*.nc\n"
        f"     {MODEL_DIR / 'EOT20' / 'load_tides'}/*.nc\n"
        "  3. Jalankan ulang script ini setelah file tersedia.\n\n"
        "Bagian validasi silang akan DILEWATI - hanya hasil prediksi\n"
        "GOT4.10 yang diproses.\n"
    )
else:
    print("Model EOT20 ditemukan.")
    model_eot20 = pyTMD.io.model(directory=MODEL_DIR, verify=True).from_database(MODEL_B_NAME)
    print("\nModel pembanding yang digunakan:")
    print(model_eot20)

# 26. FUNGSI PREDIKSI EOT20 PER BULAN
def predict_eot20_month(station_name, lon, lat, month_number):
    time = make_monthly_time(YEAR, month_number)
    try:
        tide = pyTMD.compute.tide_elevations(
            np.array([lon]), np.array([lat]), time,
            directory=MODEL_DIR, model=MODEL_B_NAME, crs=4326,
            type="time series", standard="datetime", method="nearest",
            extrapolate=True, cutoff=50.0
        )
    except Exception as e:
        print(f"  Gagal menghitung EOT20 untuk {station_name} bulan {month_number}: {e}")
        return pd.DataFrame()

    try:
        tide_values = np.asarray(tide.values).squeeze()
    except Exception:
        tide_values = np.asarray(tide).squeeze()
    tide_values = np.asarray(tide_values, dtype=float).flatten()

    if len(tide_values) != len(time):
        print(f"  Jumlah data waktu dan hasil EOT20 tidak sama untuk {station_name}.")
        return pd.DataFrame()

    df = pd.DataFrame({"datetime_utc": pd.to_datetime(time), "tide_m_eot20": tide_values})
    return df.replace([np.inf, -np.inf], np.nan).dropna(subset=["tide_m_eot20"]).reset_index(drop=True)

# 27. FUNGSI METRIK VALIDASI
def hitung_metrik(observed, predicted):
    """
    observed  : acuan pembanding (EOT20)
    predicted : model yang divalidasi (GOT4.10)
    Mengembalikan RMSE, MAE, korelasi Pearson (r), dan Willmott's Index
    of Agreement (d), metrik umum pada literatur validasi model pasut.
    """
    diff = predicted - observed
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    mae = float(np.mean(np.abs(diff)))

    if np.std(observed) > 0 and np.std(predicted) > 0:
        r_value, _ = stats.pearsonr(observed, predicted)
    else:
        r_value = np.nan

    obs_mean = np.mean(observed)
    numerator = np.sum(diff ** 2)
    denominator = np.sum((np.abs(predicted - obs_mean) + np.abs(observed - obs_mean)) ** 2)
    willmott_d = 1 - (numerator / denominator) if denominator != 0 else np.nan

    return {
        "rmse_m": rmse, "mae_m": mae,
        "korelasi_r": float(r_value), "willmott_d": float(willmott_d),
        "n_data": len(observed),
    }

# 28. FUNGSI GRAFIK PERBANDINGAN (STATIS/PNG)
def plot_perbandingan(merged_df, station_name, month_name, metrik, graph_path):
    fig, axes = plt.subplots(2, 1, figsize=(15, 10))

    ax1 = axes[0]
    ax1.plot(merged_df["datetime_utc"], merged_df["tide_m_got410"],
              label="GOT4.10", linewidth=1.2, color=COLOR_MODEL_A)
    ax1.plot(merged_df["datetime_utc"], merged_df["tide_m_eot20"],
              label="EOT20", linewidth=1.2, color=COLOR_MODEL_B, linestyle="--")
    ax1.set_title(f"Perbandingan Prediksi Pasang Surut - {station_name}\n"
                  f"{month_name} {YEAR} | GOT4.10 vs EOT20")
    ax1.set_xlabel("Tanggal (UTC)")
    ax1.set_ylabel("Elevasi terhadap MSL (m)")
    ax1.legend(loc="upper right")
    ax1.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    ax2 = axes[1]
    ax2.plot(merged_df["datetime_utc"], merged_df["selisih_m"], color=COLOR_RESIDUAL, linewidth=1.0)
    ax2.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax2.set_title(f"Selisih (GOT4.10 - EOT20)  |  RMSE={metrik['rmse_m']:.3f} m, "
                  f"MAE={metrik['mae_m']:.3f} m, r={metrik['korelasi_r']:.3f}, "
                  f"Willmott d={metrik['willmott_d']:.3f}")
    ax2.set_xlabel("Tanggal (UTC)")
    ax2.set_ylabel("Selisih (m)")
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(graph_path, dpi=200, bbox_inches="tight")
    if SHOW_PLOTS:
        plt.show(block=False)
        plt.pause(0.5)
    else:
        plt.close(fig)


# PROSES UTAMA: ULANGI UNTUK SETIAP TAHUN (2027, 2028, 2029)
if not valid_stations:
    raise RuntimeError("Tidak ada stasiun yang mendapatkan titik laut valid GOT4.10.")

for year in YEARS:
    set_year_folders(year)                      # mengisi YEAR, OUTPUT_DIR, VALIDASI_DIR, dst.
    ALL_WEEKS_BY_MONTH = build_all_weeks(YEAR)  # daftar minggu khusus tahun ini

    print("\n" + "@" * 70)
    print(f"MEMPROSES TAHUN {YEAR}")
    print("@" * 70)
    print("Folder hasil GOT4.10  :", OUTPUT_DIR)
    print("Folder grafik         :", GRAPH_DIR)
    print("Folder CSV            :", CSV_DIR)
    print("Folder hasil validasi :", VALIDASI_DIR)

    total_weeks = sum(len(info["weeks"]) for info in ALL_WEEKS_BY_MONTH.values())
    print(f"\nTotal rentang minggu tahun {YEAR}: {total_weeks}")

    # 13. SIMPAN KOORDINAT (per tahun)
    coord_file = OUTPUT_DIR / f"koordinat_stasiun_{YEAR}.csv"
    coord_df.to_csv(coord_file, index=False)
    print("\nKoordinat disimpan ke:")
    print(coord_file)

    # 22. PROSES SEMUA STASIUN (GOT4.10)
    all_week_statistics = []

    for station_name, (lon, lat) in valid_stations.items():
        print("\n" + "#" * 70)
        print(f"STASIUN: {station_name} | TAHUN {YEAR}")
        print("#" * 70)

        station_slug = station_name.lower().replace(" ", "_")
        station_graph_dir = GRAPH_DIR / station_slug
        station_csv_dir = CSV_DIR / station_slug
        station_graph_dir.mkdir(parents=True, exist_ok=True)
        station_csv_dir.mkdir(parents=True, exist_ok=True)

        for month_number in range(1, 13):
            month_name = ALL_WEEKS_BY_MONTH[month_number]["month_name"]
            print("\n" + "-" * 70)
            print(f"{station_name} | {month_name} {YEAR}")

            month_df, week_stats = predict_month(station_name, lon, lat, month_number)
            all_week_statistics.extend(week_stats)

            if month_df.empty:
                print("Data tidak tersedia. CSV dan grafik bulan ini dilewati.")
                continue

            csv_filename = f"{YEAR}_{month_number:02d}_{month_name}.csv"
            csv_path = station_csv_dir / csv_filename
            month_df.to_csv(csv_path, index=False)
            print("\nCSV disimpan:")
            print(csv_path)

            graph_filename = f"{YEAR}_{month_number:02d}_{month_name}.png"
            graph_path = station_graph_dir / graph_filename
            plot_station_month(month_df, ALL_WEEKS_BY_MONTH[month_number], station_name, graph_path)

            print("\nRingkasan:")
            print(f"{len(month_df)} data valid | {month_df['week_in_month'].nunique()} minggu terisi | "
                  f"Min={month_df['tide_m'].min():.3f} m | Max={month_df['tide_m'].max():.3f} m")

    # 23. SIMPAN STATISTIK MINGGUAN
    statistics_df = pd.DataFrame(all_week_statistics)
    statistics_file = OUTPUT_DIR / f"statistik_mingguan_{YEAR}.csv"
    statistics_df.to_csv(statistics_file, index=False)

    print("\n" + "=" * 70)
    print(f"STATISTIK MINGGUAN {YEAR}")
    print("=" * 70)
    print("File:", statistics_file)

    if statistics_df.empty:
        print("Tidak ada statistik yang berhasil dibuat.")
    else:
        print("Jumlah baris:", len(statistics_df))
        print("Jumlah stasiun:", statistics_df["station"].nunique())
        print("Jumlah kombinasi stasiun x minggu:",
              statistics_df[["station", "week_of_year"]].drop_duplicates().shape[0])
        if display is not None:
            display(statistics_df.head(PREVIEW_ROWS))
        else:
            print(statistics_df.head(PREVIEW_ROWS).to_string(index=False))

    # 24. RINGKASAN AKHIR PREDIKSI
    print("\n" + "=" * 70)
    print(f"ANALISIS PREDIKSI {YEAR} SELESAI")
    print("=" * 70)
    print("Stasiun berhasil :", len(valid_stations), "/", len(stations))
    print("Folder grafik    :", GRAPH_DIR)
    print("Folder CSV       :", CSV_DIR)
    print("CSV statistik    :", statistics_file)

    gagal = [name for name in stations if name not in valid_stations]
    if gagal:
        print("\nStasiun yang belum mendapatkan titik laut valid:")
        for name in gagal:
            print("-", name)
    else:
        print("\nSemua 12 stasiun mendapatkan titik laut valid.")

    print("\n" + "=" * 70)
    print(f"SEMUA HASIL PREDIKSI {YEAR} TELAH DISIMPAN")
    print("=" * 70)
    print("Lokasi utama :", OUTPUT_DIR)
    print("Grafik       :", GRAPH_DIR)
    print("CSV          :", CSV_DIR)
    print("Koordinat    :", coord_file)
    print("Statistik    :", statistics_file)

    # 29. PROSES VALIDASI UNTUK SEMUA STASIUN x BULAN
    all_metrics = []
    metrics_file = VALIDASI_DIR / f"ringkasan_validasi_eot20_vs_got410_{YEAR}.csv"

    if VALIDASI_TERSEDIA:
        for station_name, (lon, lat) in valid_stations.items():
            print("\n" + "#" * 70)
            print(f"VALIDASI STASIUN: {station_name} | TAHUN {YEAR}")
            print("#" * 70)

            station_slug = station_name.lower().replace(" ", "_")
            station_csv_dir_got = CSV_DIR / station_slug
            if not station_csv_dir_got.exists():
                print(f"  Tidak ada data GOT4.10 untuk {station_name}, dilewati.")
                continue

            station_csv_validasi_dir = CSV_VALIDASI_DIR / station_slug
            station_graph_validasi_dir = GRAFIK_VALIDASI_DIR / station_slug
            station_csv_validasi_dir.mkdir(parents=True, exist_ok=True)
            station_graph_validasi_dir.mkdir(parents=True, exist_ok=True)

            for month_number in range(1, 13):
                month_name = ALL_WEEKS_BY_MONTH[month_number]["month_name"]
                got_csv_path = station_csv_dir_got / f"{YEAR}_{month_number:02d}_{month_name}.csv"
                if not got_csv_path.exists():
                    continue

                print(f"\n  {station_name} | {month_name} {YEAR}")

                got_df = pd.read_csv(got_csv_path, parse_dates=["datetime_utc"])
                got_df = got_df.rename(columns={"tide_m": "tide_m_got410"})

                eot20_df = predict_eot20_month(station_name, lon, lat, month_number)
                if eot20_df.empty:
                    print("    Data EOT20 kosong, bulan ini dilewati.")
                    continue

                merged = pd.merge(
                    got_df[["datetime_utc", "tide_m_got410"]],
                    eot20_df[["datetime_utc", "tide_m_eot20"]],
                    on="datetime_utc", how="inner"
                )
                if merged.empty:
                    print("    Tidak ada timestamp yang cocok, bulan ini dilewati.")
                    continue

                merged["selisih_m"] = merged["tide_m_got410"] - merged["tide_m_eot20"]
                merged["station"] = station_name
                merged["month"] = month_name

                metrik = hitung_metrik(merged["tide_m_eot20"].values, merged["tide_m_got410"].values)
                metrik.update({"station": station_name, "month": month_name,
                                "month_number": month_number, "year": YEAR})

                print(f"    RMSE={metrik['rmse_m']:.4f} m | MAE={metrik['mae_m']:.4f} m | "
                      f"r={metrik['korelasi_r']:.4f} | Willmott d={metrik['willmott_d']:.4f} | "
                      f"n={metrik['n_data']}")

                all_metrics.append(metrik)

                csv_out_path = station_csv_validasi_dir / f"{YEAR}_{month_number:02d}_{month_name}_perbandingan.csv"
                merged.to_csv(csv_out_path, index=False)

                graph_out_path = station_graph_validasi_dir / f"{YEAR}_{month_number:02d}_{month_name}_perbandingan.png"
                plot_perbandingan(merged, station_name, month_name, metrik, graph_out_path)

    # 30. SIMPAN RINGKASAN METRIK VALIDASI
    metrics_df = pd.DataFrame(all_metrics)
    metrics_df.to_csv(metrics_file, index=False)

    print("\n" + "=" * 70)
    print(f"RINGKASAN VALIDASI SILANG {YEAR}")
    print("=" * 70)
    print("File:", metrics_file)

    if not metrics_df.empty:
        print("\nRata-rata metrik seluruh stasiun & bulan:")
        print(f"  RMSE rata-rata    : {metrics_df['rmse_m'].mean():.4f} m")
        print(f"  MAE rata-rata     : {metrics_df['mae_m'].mean():.4f} m")
        print(f"  Korelasi rata-rata: {metrics_df['korelasi_r'].mean():.4f}")
        print(f"  Willmott d rata2  : {metrics_df['willmott_d'].mean():.4f}")

        ringkasan_stasiun = (
            metrics_df.groupby("station")[["rmse_m", "mae_m", "korelasi_r", "willmott_d"]]
            .mean().round(4)
        )
        print("\nRingkasan per stasiun:")
        if display is not None:
            display(ringkasan_stasiun)
        else:
            print(ringkasan_stasiun.to_string())

        ringkasan_stasiun_file = VALIDASI_DIR / f"ringkasan_per_stasiun_{YEAR}.csv"
        ringkasan_stasiun.to_csv(ringkasan_stasiun_file)
        print("\nRingkasan per stasiun disimpan ke:", ringkasan_stasiun_file)
    else:
        print("Tidak ada data validasi yang berhasil dihitung (EOT20 tidak tersedia atau tidak ada data cocok).")

    # 31. METADATA/PROVENANCE VALIDASI
    metadata = {
        "tanggal_proses": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tahun_prediksi": YEAR,
        "validasi_dijalankan": bool(VALIDASI_TERSEDIA),
        "tujuan": (
            "Validasi silang (cross-validation) antar-model pasang surut global "
            "untuk menunjukkan konsistensi hasil prediksi GOT4.10."
        ),
        "model_utama": {
            "nama": "GOT4.10",
            "deskripsi": "Goddard Ocean Tide model",
            "sumber_unduh": "NASA GSFC (via pyTMD.datasets.fetch_gsfc_got)",
            "referensi": "Ray, R.D. (1999), NASA Technical Memorandum NASA/TM-1999-209478",
        },
        "model_pembanding": {
            "nama": "EOT20",
            "deskripsi": "Empirical Ocean Tide model, multi-mission satellite altimetry",
            "sumber_unduh": "PANGAEA, https://doi.org/10.17882/79489 (unduhan manual)",
            "referensi": (
                "Hart-Davis, M.G., Piccioni, G., Dettmering, D., Schwatke, C., "
                "Passaro, M., Seitz, F. (2021), EOT20: a global ocean tide model "
                "from multi-mission satellite altimetry, Earth System Science Data, "
                "13(8), 3869-3884, doi:10.5194/essd-13-3869-2021"
            ),
        },
        "metode_validasi": (
            "Perbandingan langsung nilai elevasi pasut pada timestamp UTC yang sama "
            "(interval 1 jam) di 12 titik stasiun; metrik: RMSE, MAE, korelasi "
            "Pearson (r), dan Willmott's Index of Agreement (d)."
        ),
        "versi_pytmd": getattr(pyTMD, "__version__", "tidak diketahui"),
        "jumlah_stasiun_divalidasi": int(metrics_df["station"].nunique()) if not metrics_df.empty else 0,
        "jumlah_kombinasi_stasiun_bulan": len(metrics_df),
    }

    metadata_file = VALIDASI_DIR / f"metadata_provenance_validasi_{YEAR}.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print("\nMetadata provenance disimpan ke:", metadata_file)

    print("\n" + "=" * 70)
    print(f"VALIDASI SILANG {YEAR} SELESAI")
    print("=" * 70)

print("\n" + "=" * 70)
print(f"SEMUA TAHUN SELESAI DIPROSES: {YEARS}")
print("=" * 70)