# VALIDASI 3 PERBANDINGAN PASANG SURUT TAHUN 2025

# 1. IMPORT LIBRARY
import re
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pyTMD

from pathlib import Path
from scipy import stats

try:
    from IPython.display import display
except ImportError:
    display = None

# 2. PENGATURAN UTAMA
YEAR = 2025
MODEL_A_NAME = "GOT4.10_nc"   # Goddard Ocean Tide model
MODEL_B_NAME = "EOT20"        # Empirical Ocean Tide model
STASIUN_KOORDINAT = {
    "GLGH": {"nama": "Glagah", "lon": 110.058879,  "lat": -7.91385926},
    "SADG": {"nama": "Sadeng", "lon": 110.7946504, "lat": -8.250601385},
}

VALIDATION_INTERVAL_MINUTES = 10
SHOW_PLOTS = False

# 3. FOLDER KERJA
MAGANG_DIR = Path(r"D:\MAGANG\A. Data\MAGANG")
MODEL_DIR = MAGANG_DIR / "pytmd_data"
OBS_DIR = MAGANG_DIR / "data_observasi_big"
HASIL_DIR = MAGANG_DIR / f"hasil_validasi_3perbandingan_{YEAR}"
CSV_DIR = HASIL_DIR / "csv"
GRAFIK_DIR = HASIL_DIR / "grafik"
for folder in [HASIL_DIR, CSV_DIR, GRAFIK_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print(f"VALIDASI 3 PERBANDINGAN: {MODEL_A_NAME} vs {MODEL_B_NAME} vs BIG - TAHUN {YEAR}")
print("=" * 70)
print("Folder data acuan BIG :", OBS_DIR)
print("Folder hasil validasi :", HASIL_DIR)
print("\nTitik koordinat yang dipakai untuk hitung model:")
for kode, info in STASIUN_KOORDINAT.items():
    print(f"  {kode} ({info['nama']}): lon={info['lon']}, lat={info['lat']}")

# 4. TEMUKAN & KELOMPOKKAN FILE DATA BIG PER STASIUN
FILENAME_PATTERN = re.compile(
    r"prediksi_pasut_([a-zA-Z0-9]+)_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})_series\.csv$"
)

if not OBS_DIR.exists():
    raise FileNotFoundError(
        f"Folder data acuan BIG tidak ditemukan:\n{OBS_DIR}\n\n"
        "Pastikan seluruh file 'prediksi_pasut_<stasiun>_*_series.csv' (GLGH, "
        "SADG, dan stasiun lain jika ada) sudah berada di folder ini."
    )

all_obs_files = sorted(OBS_DIR.glob("prediksi_pasut_*_series.csv"))
if not all_obs_files:
    raise FileNotFoundError(f"Tidak ada file 'prediksi_pasut_*_series.csv' di {OBS_DIR}")

stasiun_files = {}  # {KODE_STASIUN: [Path, Path, ...]}
for f in all_obs_files:
    m = FILENAME_PATTERN.match(f.name)
    if not m:
        print(f"  [dilewati] Nama file tidak sesuai pola resmi BIG: {f.name}")
        continue
    kode = m.group(1).upper()
    stasiun_files.setdefault(kode, []).append(f)

if not stasiun_files:
    raise FileNotFoundError("Tidak ada file yang cocok dengan pola nama resmi BIG.")

print(f"\nStasiun terdeteksi: {', '.join(sorted(stasiun_files.keys()))}")
for kode, files in sorted(stasiun_files.items()):
    print(f"  {kode}: {len(files)} file bulan ditemukan")

# 5. CEK KETERSEDIAAN KEDUA MODEL
# Catatan unduh model (jika belum ada di MODEL_DIR):
#   - GOT4.10 : bisa diunduh otomatis lewat pyTMD, sumber NASA GSFC.
#     Referensi: Ray, R.D. (1999), NASA Technical Memorandum NASA/TM-1999-209478.
#   - EOT20   : TIDAK bisa diunduh otomatis oleh pyTMD, harus manual dari PANGAEA:
#     https://doi.org/10.17882/79489 (Hart-Davis dkk., 2021, Earth System
#     Science Data, 13(8), 3869-3884, doi:10.5194/essd-13-3869-2021).
#     Ekstrak sehingga strukturnya menjadi:
#     MODEL_DIR/EOT20/ocean_tides/*.nc dan MODEL_DIR/EOT20/load_tides/*.nc

print("\n" + "=" * 70)
print("MEMERIKSA MODEL")
print("=" * 70)

model_tersedia = {}
for model_name in (MODEL_A_NAME, MODEL_B_NAME):
    try:
        model_tersedia[model_name] = pyTMD.io.model(directory=MODEL_DIR, verify=True).from_database(model_name)
        print(f"  [OK] Model {model_name} ditemukan.")
    except Exception as e:
        print(f"  [PERINGATAN] Model {model_name} tidak tersedia secara lokal ({e}).")
        #print(f"               Perbandingan yang melibatkan model ini akan dilewati.")

if not model_tersedia:
    raise RuntimeError("Tidak ada model yang tersedia. Unduh minimal satu model terlebih dahulu.")

ADA_GOT = MODEL_A_NAME in model_tersedia
ADA_EOT = MODEL_B_NAME in model_tersedia

# 6. FUNGSI BACA FILE PREDIKSI RESMI BIG (HEADER METADATA + TABEL DATA)
def baca_file_big(path):
    """
    Membaca satu file prediksi pasut resmi BIG.
    Header berisi metadata (Station Name, Lon, Lat, Datum), diikuti tabel data
    dengan kolom timestamp_utc, timestamp_local, predicted_height_m.
    Mengembalikan (lon_header, lat_header, datum, dataframe [datetime_utc, tide_m_big]).
    lon_header/lat_header hanya untuk dokumentasi - titik yang benar-benar
    dipakai untuk hitung model ditentukan lewat STASIUN_KOORDINAT (lihat bagian 2).
    """
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    lon = lat = datum = None
    header_data_idx = None
    for i, line in enumerate(lines):
        if line.startswith("Lon"):
            lon = float(line.split(":")[1].strip())
        elif line.startswith("Lat"):
            lat = float(line.split(":")[1].strip())
        elif line.startswith("Datum"):
            datum = line.split(":")[1].strip()
        elif line.startswith("timestamp_utc"):
            header_data_idx = i
            break

    if header_data_idx is None or lon is None or lat is None:
        raise ValueError(f"Format file BIG tidak dikenali: {path}")

    df = pd.read_csv(
        path,
        skiprows=header_data_idx,
        usecols=["timestamp_utc", "predicted_height_m"]
    )
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
    df = df.rename(columns={
        "timestamp_utc": "datetime_utc",
        "predicted_height_m": "tide_m_big"
    })
    df = df.dropna(subset=["tide_m_big"]).reset_index(drop=True)
    return lon, lat, datum, df

# 7. FUNGSI HITUNG PREDIKSI MODEL GLOBAL PADA WAKTU YANG SAMA PERSIS DENGAN DATA BIG
def predict_model_pada_waktu(lon, lat, waktu_series, model_name):
    time = np.array(pd.to_datetime(waktu_series).values)
    try:
        tide = pyTMD.compute.tide_elevations(
            np.array([lon]),
            np.array([lat]),
            time,
            directory=MODEL_DIR,
            model=model_name,
            crs=4326,
            type="time series",
            standard="datetime",
            method="nearest",
            extrapolate=True,
            cutoff=50.0
        )
    except Exception as e:
        print(f"      Gagal menghitung model {model_name}: {e}")
        return None

    try:
        tide_values = np.asarray(tide.values).squeeze()
    except Exception:
        tide_values = np.asarray(tide).squeeze()
    return np.asarray(tide_values, dtype=float).flatten()

# 8. FUNGSI METRIK VALIDASI
def hitung_metrik(acuan, dibandingkan):
    """
    RMSE, MAE, korelasi Pearson (r), dan Willmott's Index of Agreement (d)
    antara dua deret nilai elevasi pasut (acuan vs dibandingkan).
    """
    diff = dibandingkan - acuan
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    mae = float(np.mean(np.abs(diff)))

    if np.std(acuan) > 0 and np.std(dibandingkan) > 0:
        r_value, _ = stats.pearsonr(acuan, dibandingkan)
    else:
        r_value = np.nan

    acuan_mean = np.mean(acuan)
    numerator = np.sum(diff ** 2)
    denominator = np.sum(
        (np.abs(dibandingkan - acuan_mean) + np.abs(acuan - acuan_mean)) ** 2
    )
    willmott_d = 1 - (numerator / denominator) if denominator != 0 else np.nan

    return {
        "rmse_m": rmse,
        "mae_m": mae,
        "korelasi_r": float(r_value),
        "willmott_d": float(willmott_d),
        "n_data": len(acuan)
    }

# 9. FUNGSI GRAFIK 3 PERBANDINGAN (OVERLAY + SELISIH)
def plot_tiga_perbandingan(merged_df, station_code, month_label, metrik_list, graph_path):
    fig, axes = plt.subplots(2, 1, figsize=(16, 11))

    ax1 = axes[0]
    if "tide_m_got410" in merged_df:
        ax1.plot(merged_df["datetime_utc"], merged_df["tide_m_got410"],
                  label="GOT4.10", linewidth=1.1, color="tab:blue")
    if "tide_m_eot20" in merged_df:
        ax1.plot(merged_df["datetime_utc"], merged_df["tide_m_eot20"],
                  label="EOT20", linewidth=1.1, color="tab:orange", linestyle="--")
    ax1.plot(merged_df["datetime_utc"], merged_df["tide_m_big"],
              label="BIG (acuan)", linewidth=1.3, color="tab:green", linestyle=":")
    ax1.set_title(
        f"Perbandingan Prediksi Pasang Surut - {station_code}\n"
        f"{month_label} {YEAR} | GOT4.10 vs EOT20 vs Data Resmi BIG"
    )
    ax1.set_xlabel("Tanggal (UTC)")
    ax1.set_ylabel("Elevasi terhadap MSL (m)")
    ax1.legend(loc="upper right")
    ax1.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    ax2 = axes[1]
    warna_selisih = {
        "GOT4.10 vs BIG": ("selisih_got_big", "tab:blue"),
        "EOT20 vs BIG": ("selisih_eot_big", "tab:orange"),
        "GOT4.10 vs EOT20": ("selisih_got_eot", "tab:purple"),
    }
    subtitle_bagian = []
    for label, (kolom, warna) in warna_selisih.items():
        if kolom in merged_df:
            ax2.plot(merged_df["datetime_utc"], merged_df[kolom],
                      label=label, linewidth=1.0, color=warna)
    for m in metrik_list:
        subtitle_bagian.append(
            f"{m['perbandingan']}: RMSE={m['rmse_m']:.3f} m, r={m['korelasi_r']:.3f}"
        )
    ax2.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax2.set_title(" | ".join(subtitle_bagian), fontsize=10)
    ax2.set_xlabel("Tanggal (UTC)")
    ax2.set_ylabel("Selisih (m)")
    ax2.legend(loc="upper right")
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(graph_path, dpi=200, bbox_inches="tight")

    if SHOW_PLOTS:
        plt.show(block=False)
        plt.pause(0.5)
    else:
        plt.close(fig)

# 10. PROSES VALIDASI UNTUK SEMUA STASIUN x BULAN
all_metrics = []

for kode_stasiun, files in sorted(stasiun_files.items()):
    print("\n" + "#" * 70)
    print(f"STASIUN: {kode_stasiun}")
    print("#" * 70)

    # Titik yang dipakai untuk hitung model: koordinat terkoreksi jika ada,
    # jika tidak fallback ke Lon/Lat pada header file BIG stasiun ini.
    koordinat_terkoreksi = STASIUN_KOORDINAT.get(kode_stasiun)

    station_csv_dir = CSV_DIR / kode_stasiun.lower()
    station_graph_dir = GRAFIK_DIR / kode_stasiun.lower()
    station_csv_dir.mkdir(parents=True, exist_ok=True)
    station_graph_dir.mkdir(parents=True, exist_ok=True)

    for f in sorted(files):
        lon_header, lat_header, datum, big_df = baca_file_big(f)

        if koordinat_terkoreksi is not None:
            lon, lat = koordinat_terkoreksi["lon"], koordinat_terkoreksi["lat"]
        else:
            lon, lat = lon_header, lat_header
            print(f"  [info] {kode_stasiun} tidak ada di STASIUN_KOORDINAT, "
                  f"memakai Lon/Lat header file BIG (lon={lon}, lat={lat}).")

        if big_df.empty:
            print(f"  [dilewati] {f.name}: data kosong.")
            continue

        if VALIDATION_INTERVAL_MINUTES:
            mask = big_df["datetime_utc"].dt.minute % VALIDATION_INTERVAL_MINUTES == 0
            big_df = big_df.loc[mask].reset_index(drop=True)

        bulan_label = big_df["datetime_utc"].iloc[0].strftime("%B")
        bulan_angka = big_df["datetime_utc"].iloc[0].month

        print(
            f"\n  {kode_stasiun} | {bulan_label} {YEAR} | "
            f"{len(big_df)} titik data acuan (titik model: lon={lon}, lat={lat}, "
            f"datum BIG={datum})"
        )

        merged = big_df.copy()

        if ADA_GOT:
            print(f"    Menghitung {MODEL_A_NAME} ...")
            got_values = predict_model_pada_waktu(lon, lat, merged["datetime_utc"], MODEL_A_NAME)
            if got_values is not None and len(got_values) == len(merged):
                merged["tide_m_got410"] = got_values
            else:
                print("      Dilewati (jumlah data tidak sama atau gagal dihitung).")

        if ADA_EOT:
            print(f"    Menghitung {MODEL_B_NAME} ...")
            eot_values = predict_model_pada_waktu(lon, lat, merged["datetime_utc"], MODEL_B_NAME)
            if eot_values is not None and len(eot_values) == len(merged):
                merged["tide_m_eot20"] = eot_values
            else:
                print("      Dilewati (jumlah data tidak sama atau gagal dihitung).")

        kolom_wajib = ["tide_m_big"]
        if "tide_m_got410" in merged:
            kolom_wajib.append("tide_m_got410")
        if "tide_m_eot20" in merged:
            kolom_wajib.append("tide_m_eot20")

        merged = merged.replace([np.inf, -np.inf], np.nan).dropna(subset=kolom_wajib)
        if merged.empty:
            print("    Dilewati (tidak ada data valid setelah pembersihan).")
            continue

        # --- Hitung sampai 3 perbandingan yang tersedia ---
        metrik_bulan = []

        if "tide_m_got410" in merged:
            merged["selisih_got_big"] = merged["tide_m_got410"] - merged["tide_m_big"]
            m1 = hitung_metrik(merged["tide_m_big"].values, merged["tide_m_got410"].values)
            m1["perbandingan"] = "GOT4.10 vs BIG"
            metrik_bulan.append(m1)

        if "tide_m_eot20" in merged:
            merged["selisih_eot_big"] = merged["tide_m_eot20"] - merged["tide_m_big"]
            m2 = hitung_metrik(merged["tide_m_big"].values, merged["tide_m_eot20"].values)
            m2["perbandingan"] = "EOT20 vs BIG"
            metrik_bulan.append(m2)

        if "tide_m_got410" in merged and "tide_m_eot20" in merged:
            merged["selisih_got_eot"] = merged["tide_m_got410"] - merged["tide_m_eot20"]
            m3 = hitung_metrik(merged["tide_m_eot20"].values, merged["tide_m_got410"].values)
            m3["perbandingan"] = "GOT4.10 vs EOT20"
            metrik_bulan.append(m3)

        for m in metrik_bulan:
            m.update({
                "station": kode_stasiun,
                "month": bulan_label,
                "month_number": bulan_angka,
                "year": YEAR,
                "lon_model": lon,
                "lat_model": lat,
                "lon_header_big": lon_header,
                "lat_header_big": lat_header
            })
            print(
                f"    [{m['perbandingan']}] RMSE={m['rmse_m']:.4f} m | "
                f"MAE={m['mae_m']:.4f} m | r={m['korelasi_r']:.4f} | "
                f"Willmott d={m['willmott_d']:.4f} | n={m['n_data']}"
            )
            all_metrics.append(m)

        merged["station"] = kode_stasiun
        merged["month"] = bulan_label

        csv_out_path = (
            station_csv_dir /
            f"{YEAR}_{bulan_angka:02d}_{bulan_label}_got410_eot20_vs_big.csv"
        )
        merged.to_csv(csv_out_path, index=False)

        graph_out_path = (
            station_graph_dir /
            f"{YEAR}_{bulan_angka:02d}_{bulan_label}_3perbandingan.png"
        )
        plot_tiga_perbandingan(merged, kode_stasiun, bulan_label, metrik_bulan, graph_out_path)

# 11. SIMPAN RINGKASAN METRIK VALIDASI
metrics_df = pd.DataFrame(all_metrics)
metrics_file = HASIL_DIR / f"ringkasan_3perbandingan_{YEAR}.csv"
metrics_df.to_csv(metrics_file, index=False)

print("\n" + "=" * 70)
print("RINGKASAN VALIDASI 3 PERBANDINGAN")
print("=" * 70)
print("File:", metrics_file)

if not metrics_df.empty:
    print("\nRata-rata metrik per stasiun & jenis perbandingan (seluruh bulan):")
    ringkasan = (
        metrics_df.groupby(["station", "perbandingan"])[["rmse_m", "mae_m", "korelasi_r", "willmott_d"]]
        .mean()
        .round(4)
    )
    if display is not None:
        display(ringkasan)
    else:
        print(ringkasan.to_string())

    ringkasan_file = HASIL_DIR / "ringkasan_per_stasiun_perbandingan.csv"
    ringkasan.to_csv(ringkasan_file)
    print("\nRingkasan per stasiun & perbandingan disimpan ke:", ringkasan_file)
else:
    print("Tidak ada data validasi yang berhasil dihitung. Periksa kembali file input.")

# 12. METADATA / PROVENANCE
metadata = {
    "tanggal_proses": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
    "tujuan": (
        f"Validasi 3 arah antara dua model pasang surut global (GOT4.10, EOT20) "
        "dan data prediksi resmi Badan Informasi Geospasial (BIG) sebagai acuan "
        f"lapangan, di stasiun GLGH (Glagah), SADG (Sadeng), dan stasiun lain yang "
        f"tersedia, untuk tahun {YEAR}."
    ),
    "perbandingan_dihasilkan": [
        "GOT4.10 vs BIG", "EOT20 vs BIG", "GOT4.10 vs EOT20"
    ],
    "titik_koordinat_terkoreksi": STASIUN_KOORDINAT,
    "data_acuan_big": {
        "sumber": "Direktorat Sistem Referensi Geospasial, Badan Informasi Geospasial (BIG)",
        "kontak": "srgi@big.go.id",
        "jenis": "Prediksi pasang surut resmi per stasiun (interval 1 menit), datum MSL",
        "stasiun_ditemukan": sorted(stasiun_files.keys()),
        "catatan": (
            "Lon/Lat pada header file BIG dicatat sebagai lon_header_big/"
            "lat_header_big di ringkasan, tapi TIDAK dipakai untuk menghitung "
            "model - perhitungan model memakai STASIUN_KOORDINAT."
        )
    },
    "model_a": {
        "nama": "GOT4.10",
        "tersedia": ADA_GOT,
        "sumber_unduh": "NASA GSFC (via pyTMD)",
        "referensi": "Ray, R.D. (1999), NASA Technical Memorandum NASA/TM-1999-209478"
    },
    "model_b": {
        "nama": "EOT20",
        "tersedia": ADA_EOT,
        "sumber_unduh": "PANGAEA, https://doi.org/10.17882/79489 (unduhan manual)",
        "referensi": (
            "Hart-Davis, M.G., Piccioni, G., Dettmering, D., Schwatke, C., "
            "Passaro, M., Seitz, F. (2021), EOT20: a global ocean tide model "
            "from multi-mission satellite altimetry, Earth System Science Data, "
            "13(8), 3869-3884, doi:10.5194/essd-13-3869-2021"
        )
    },
    "interval_validasi_menit": VALIDATION_INTERVAL_MINUTES or 1,
    "metode_validasi": (
        "Perbandingan langsung nilai elevasi pasut pada timestamp UTC yang sama "
        "antara GOT4.10, EOT20, dan data prediksi resmi BIG; metrik yang "
        "dihitung untuk tiap pasangan: RMSE, MAE, korelasi Pearson (r), dan "
        "Willmott's Index of Agreement (d)."
    ),
    "versi_pytmd": getattr(pyTMD, "__version__", "tidak diketahui"),
    "jumlah_baris_ringkasan": len(metrics_df)
}

metadata_file = HASIL_DIR / "metadata_provenance_3perbandingan.json"
with open(metadata_file, "w", encoding="utf-8") as fh:
    json.dump(metadata, fh, indent=2, ensure_ascii=False)

print("\nMetadata provenance disimpan ke:", metadata_file)

print("\n" + "=" * 70)
print("VALIDASI 3 PERBANDINGAN SELESAI")
print("=" * 70)
print("Folder hasil:", HASIL_DIR)