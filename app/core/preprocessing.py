"""
preprocessing.py - Pipeline preprocessing data lansia dari dataset ind_pkg_elderly.xlsx
Membaca file Excel flat (satu sheet) dengan kolom terpilih,
membersihkan, encode, dan menghasilkan DataFrame siap clustering.
"""

# Standard Library
from collections import defaultdict
from datetime import datetime
import logging
from pathlib import Path
import re

# Third Party
import numpy as np
import pandas as pd

# Local
from app.core.config import (
    USECOLS_EXCEL,
    COLUMN_RENAME_MAP,
    COL_MISSING_THRESHOLD,
    ROW_MISSING_THRESHOLD,
)

logger = logging.getLogger("lansia.preprocessing")


# ══════════════════════════════════════════════════════════════════════════════
# 1. Membaca Data
# ══════════════════════════════════════════════════════════════════════════════

def baca_data(filepath: Path) -> pd.DataFrame:
    """
    Baca file Excel hanya kolom yang diperlukan menggunakan `usecols`.
    Mengembalikan DataFrame mentah dengan kolom terpilih.
    """
    filepath = Path(filepath) if not isinstance(filepath, Path) else filepath
    logger.info(f"📂 Membaca file: {filepath.name}")

    df = pd.read_excel(filepath, usecols=USECOLS_EXCEL)

    logger.info(f"   Kolom dimuat: {len(df.columns)}")
    logger.info(f"   Baris terbaca: {len(df)}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 2. Memilih & Mengganti Nama Kolom
# ══════════════════════════════════════════════════════════════════════════════

def pilih_dan_rename_kolom(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename kolom Excel asli menjadi format snake_case yang ringkas
    sesuai COLUMN_RENAME_MAP di config.
    """
    df = df.rename(columns=COLUMN_RENAME_MAP)
    logger.info(f"   Kolom setelah rename: {list(df.columns)}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 3. Membersihkan Data (Cleaning & Validasi Tipe)
# ══════════════════════════════════════════════════════════════════════════════

def bersihkan_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pembersihan data:
    - Strip whitespace pada kolom string
    - Konversi kolom numerik dengan pd.to_numeric(errors='coerce')
    - Hapus karakter non-numerik pada kolom angka jika diperlukan
    - Hapus duplikat berdasarkan NIK
    """
    df = df.copy()

    # --- Bersihkan kolom string ---
    str_cols = ["kecamatan", "desa", "nama", "nik"]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            # Ganti string 'nan' / 'None' hasil konversi menjadi NaN
            df[col] = df[col].replace({"nan": np.nan, "None": np.nan, "": np.nan})

    # --- Konversi kolom numerik ---
    numeric_cols = [
        "berat_badan", "tinggi_badan",
        "sistolik", "diastolik",
        "gds_1", "gds_2", "gdp", "gd2pp",
        "kolesterol",
    ]
    for col in numeric_cols:
        if col in df.columns:
            # Hapus karakter non-numerik (kecuali titik dan minus)
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"[^\d.\-]", "", regex=True)
                .replace({"": np.nan, "nan": np.nan})
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # --- Ganti nilai 0 pada kolom gula darah menjadi NaN ---
    # (pada dataset ini, 0 berarti tidak diperiksa, bukan hasil 0)
    gula_darah_cols = ["gds_1", "gds_2", "gdp", "gd2pp"]
    for col in gula_darah_cols:
        if col in df.columns:
            df.loc[df[col] == 0, col] = np.nan

    # --- Konversi tanggal_lahir ---
    if "tanggal_lahir" in df.columns:
        df["tanggal_lahir"] = pd.to_datetime(df["tanggal_lahir"], errors="coerce")

    # --- Hapus duplikat berdasarkan NIK ---
    n_before = len(df)
    df = df.drop_duplicates(subset="nik", keep="first")
    n_dup = n_before - len(df)
    if n_dup > 0:
        logger.info(f"   🗑  Hapus {n_dup} baris duplikat (berdasarkan NIK)")

    # --- Filter hanya Kecamatan Maesan ---
    if "kecamatan" in df.columns:
        n_before_filter = len(df)
        df = df[df["kecamatan"].astype(str).str.strip().str.upper() == "MAESAN"]
        n_filtered = n_before_filter - len(df)
        if n_filtered > 0:
            logger.info(f"   🗑  Filter Kecamatan: Mengabaikan {n_filtered} data lansia di luar Kecamatan Maesan")

    logger.info(f"   Baris setelah cleaning & filtering: {len(df)}")
    return df.reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Feature Engineering (Umur & IMT)
# ══════════════════════════════════════════════════════════════════════════════

def buat_fitur_baru(df: pd.DataFrame) -> pd.DataFrame:
    """
    Membuat fitur turunan:
    - umur  = tahun_sekarang - tahun_lahir
    - imt   = berat_badan / (tinggi_badan_meter ** 2)
    """
    df = df.copy()
    tahun_sekarang = datetime.now().year

    # --- Umur ---
    if "tanggal_lahir" in df.columns:
        df["umur"] = tahun_sekarang - df["tanggal_lahir"].dt.year
        # Validasi range: umur harus masuk akal (40–120)
        df.loc[(df["umur"] < 40) | (df["umur"] > 120), "umur"] = np.nan
        logger.info(f"   Umur dihitung: {df['umur'].notna().sum()} valid, "
                    f"{df['umur'].isna().sum()} invalid/null")
    else:
        df["umur"] = np.nan
        logger.warning("   ⚠ Kolom 'tanggal_lahir' tidak ditemukan!")

    # --- IMT ---
    if "berat_badan" in df.columns and "tinggi_badan" in df.columns:
        tinggi_m = df["tinggi_badan"] / 100  # cm → m
        df["imt"] = df["berat_badan"] / (tinggi_m ** 2)
        df["imt"] = df["imt"].round(2)
        # Validasi range IMT: 10–60
        df.loc[(df["imt"] < 10) | (df["imt"] > 60), "imt"] = np.nan
        logger.info(f"   IMT dihitung: {df['imt'].notna().sum()} valid, "
                    f"{df['imt'].isna().sum()} invalid/null")
    else:
        df["imt"] = np.nan
        logger.warning("   ⚠ Kolom berat_badan / tinggi_badan tidak ditemukan!")

    return df


# ══════════════════════════════════════════════════════════════════════════════
# 5. Encoding Variabel Kategorikal
# ══════════════════════════════════════════════════════════════════════════════

def encode_kategorikal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Encoding biner untuk variabel kategorikal:
    - jenis_kelamin: Laki-laki → 1, Perempuan → 0
    - riwayat_hipertensi: Ya → 1, Tidak → 0
    - gangguan_kognitif: "Kemungkinan ada gangguan kognitif" → 1, lainnya → 0
    - malnutrisi: "Berisiko Malnutrisi" → 1, "Status Gizi Normal" → 0
    - depresi: ada gejala → 1, tidak ada → 0, null → tetap null
    """
    df = df.copy()

    # --- Jenis Kelamin ---
    if "jenis_kelamin" in df.columns:
        jk_map = {"Laki-laki": 1, "Perempuan": 0}
        df["jenis_kelamin"] = (
            df["jenis_kelamin"]
            .astype(str)
            .str.strip()
            .map(jk_map)
        )
        # Nilai yang tidak cocok mapping → NaN, isi default 0
        df["jenis_kelamin"] = df["jenis_kelamin"].fillna(0).astype(int)

    # --- Riwayat Hipertensi ---
    if "riwayat_hipertensi" in df.columns:
        ht_map = {"Ya": 1, "Tidak": 0}
        df["riwayat_hipertensi"] = (
            df["riwayat_hipertensi"]
            .astype(str)
            .str.strip()
            .map(ht_map)
        )
        # NaN tetap NaN (jika data kosong di Excel)
        logger.info(f"   Riwayat hipertensi: "
                    f"Ya={int((df['riwayat_hipertensi'] == 1).sum())}, "
                    f"Tidak={int((df['riwayat_hipertensi'] == 0).sum())}, "
                    f"null={int(df['riwayat_hipertensi'].isna().sum())}")

    # --- Gangguan Kognitif ---
    if "gangguan_kognitif" in df.columns:
        def _encode_kognitif(val):
            if pd.isna(val):
                return np.nan
            s = str(val).strip().lower()
            if "ada gangguan" in s and "tidak" not in s:
                return 1
            elif "tidak ada gangguan" in s:
                return 0
            return np.nan

        df["gangguan_kognitif"] = df["gangguan_kognitif"].apply(_encode_kognitif)
        logger.info(f"   Gangguan kognitif: "
                    f"1={int((df['gangguan_kognitif'] == 1).sum())}, "
                    f"0={int((df['gangguan_kognitif'] == 0).sum())}, "
                    f"null={int(df['gangguan_kognitif'].isna().sum())}")

    # --- Malnutrisi ---
    if "malnutrisi" in df.columns:
        def _encode_malnutrisi(val):
            if pd.isna(val):
                return np.nan
            s = str(val).strip().lower()
            if "berisiko" in s or "malnutrisi" in s and "normal" not in s:
                return 1
            elif "normal" in s:
                return 0
            return np.nan

        df["malnutrisi"] = df["malnutrisi"].apply(_encode_malnutrisi)
        logger.info(f"   Malnutrisi: "
                    f"1={int((df['malnutrisi'] == 1).sum())}, "
                    f"0={int((df['malnutrisi'] == 0).sum())}, "
                    f"null={int(df['malnutrisi'].isna().sum())}")

    # --- Depresi ---
    if "depresi" in df.columns:
        def _encode_depresi(val):
            if pd.isna(val):
                return np.nan
            s = str(val).strip().lower()
            if s in ("nan", "none", ""):
                return np.nan
            if "ada" in s and "tidak" not in s:
                return 1
            elif "tidak" in s:
                return 0
            # Fallback: jika ada konten, anggap ada gejala
            return 1 if s else np.nan

        df["depresi"] = df["depresi"].apply(_encode_depresi)
        logger.info(f"   Depresi: "
                    f"1={int((df['depresi'] == 1).sum())}, "
                    f"0={int((df['depresi'] == 0).sum())}, "
                    f"null={int(df['depresi'].isna().sum())}")

    return df


# ══════════════════════════════════════════════════════════════════════════════
# 6. Penanganan Missing Value (TANPA IMPUTASI)
# ══════════════════════════════════════════════════════════════════════════════

def tangani_missing_value(df: pd.DataFrame) -> pd.DataFrame:
    """
    Penanganan missing value TANPA imputasi:
    - Hapus kolom jika proporsi null > COL_MISSING_THRESHOLD
    - Hapus baris jika proporsi null > ROW_MISSING_THRESHOLD
    Ambang batas didefinisikan di config.py agar mudah diubah.
    """
    df = df.copy()

    # Kolom yang dianalisis untuk missing (hanya fitur numerik + biner)
    fitur_cols = [
        "umur", "jenis_kelamin", "imt",
        "sistolik", "diastolik",
        "gds_1", "gds_2", "gdp", "gd2pp",
        "kolesterol",
        "riwayat_hipertensi", "gangguan_kognitif", "malnutrisi", "depresi",
    ]
    fitur_exist = [c for c in fitur_cols if c in df.columns]

    # --- Hapus KOLOM dengan terlalu banyak null ---
    logger.info(f"📉 Analisis missing value per kolom (threshold: {COL_MISSING_THRESHOLD:.0%}):")
    cols_to_drop = []
    for col in fitur_exist:
        n_miss = df[col].isna().sum()
        pct = n_miss / len(df) if len(df) > 0 else 0
        logger.info(f"   {col:<25}: {n_miss:>4} missing ({pct:.1%})")
        if pct > COL_MISSING_THRESHOLD:
            cols_to_drop.append(col)

    if cols_to_drop:
        logger.info(f"🗑  Kolom dihapus (null > {COL_MISSING_THRESHOLD:.0%}): {cols_to_drop}")
        df = df.drop(columns=cols_to_drop)
    else:
        logger.info("   ✅ Tidak ada kolom yang dihapus")

    # Update daftar fitur yang tersisa
    fitur_exist = [c for c in fitur_exist if c in df.columns]

    # --- Hapus BARIS dengan terlalu banyak null ---
    if fitur_exist:
        n_fitur = len(fitur_exist)
        row_null_count = df[fitur_exist].isna().sum(axis=1)
        row_null_ratio = row_null_count / n_fitur
        rows_to_drop = row_null_ratio > ROW_MISSING_THRESHOLD

        n_drop = rows_to_drop.sum()
        if n_drop > 0:
            logger.info(f"🗑  Hapus {n_drop} baris (null > {ROW_MISSING_THRESHOLD:.0%} "
                        f"dari {n_fitur} fitur)")
            df = df[~rows_to_drop].reset_index(drop=True)
        else:
            logger.info("   ✅ Tidak ada baris yang dihapus karena missing value")

    logger.info(f"   Baris setelah penanganan missing: {len(df)}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 7. Validasi Data Akhir
# ══════════════════════════════════════════════════════════════════════════════

def validasi_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validasi akhir:
    - Pastikan kolom numerik benar-benar numerik
    - Pastikan kolom biner hanya bernilai 0 atau 1 (atau NaN)
    - Validasi range untuk kolom kesehatan
    """
    df = df.copy()

    # --- Pastikan tipe numerik ---
    numeric_cols = [
        "umur", "imt", "berat_badan", "tinggi_badan",
        "sistolik", "diastolik",
        "gds_1", "gds_2", "gdp", "gd2pp",
        "kolesterol",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # --- Validasi range ---
    ranges = {
        "umur":      (40, 120),
        "imt":       (10, 60),
        "sistolik":  (60, 300),
        "diastolik": (30, 200),
        "gds_1":     (20, 800),
        "gds_2":     (20, 800),
        "gdp":       (20, 800),
        "gd2pp":     (20, 800),
        "kolesterol": (50, 600),
    }
    for col, (lo, hi) in ranges.items():
        if col in df.columns:
            outlier_mask = (df[col] < lo) | (df[col] > hi)
            n_outlier = outlier_mask.sum()
            if n_outlier > 0:
                logger.info(f"   ⚠ {col}: {n_outlier} nilai di luar range "
                            f"[{lo}, {hi}] → NaN")
                df.loc[outlier_mask, col] = np.nan

    # --- Pastikan encoding biner hanya 0 atau 1 ---
    binary_cols = [
        "jenis_kelamin", "riwayat_hipertensi",
        "gangguan_kognitif", "malnutrisi", "depresi",
    ]
    for col in binary_cols:
        if col in df.columns:
            valid_mask = df[col].isna() | df[col].isin([0, 1])
            n_invalid = (~valid_mask).sum()
            if n_invalid > 0:
                logger.warning(f"   ⚠ {col}: {n_invalid} nilai bukan 0/1 → NaN")
                df.loc[~valid_mask, col] = np.nan

    logger.info("   ✅ Validasi data selesai")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 8. Menyimpan / Menyiapkan Hasil Preprocessing
# ══════════════════════════════════════════════════════════════════════════════

def siapkan_output(df: pd.DataFrame) -> pd.DataFrame:
    """
    Menyiapkan DataFrame akhir:
    - Urutkan berdasarkan desa, kecamatan
    - Hapus kolom bantu (tanggal_lahir)
    - Reset index
    """
    df = df.copy()

    # Urutkan
    sort_cols = []
    if "desa" in df.columns:
        sort_cols.append("desa")
    if "kecamatan" in df.columns:
        sort_cols.append("kecamatan")
    if sort_cols:
        df = df.sort_values(sort_cols).reset_index(drop=True)

    # Hapus kolom bantu
    drop_cols = ["tanggal_lahir"]
    for col in drop_cols:
        if col in df.columns:
            df = df.drop(columns=[col])

    logger.info(f"   Kolom final ({len(df.columns)}): {list(df.columns)}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# Pipeline Utama
# ══════════════════════════════════════════════════════════════════════════════

def run_preprocessing(input_file) -> tuple:
    """
    Jalankan seluruh pipeline preprocessing.

    Kembalikan:
        (df_clean, stats_dict)
        df_clean : DataFrame bersih siap clustering
        stats    : dict statistik untuk laporan akhir
    """
    input_file = Path(input_file) if not isinstance(input_file, Path) else input_file

    logger.info("=" * 60)
    logger.info("  PREPROCESSING DATA PKG LANSIA")
    logger.info("=" * 60)

    stats = defaultdict(int)

    # ── Tahap 1: Baca data ──
    logger.info("TAHAP 1: Membaca data...")
    df = baca_data(input_file)
    stats["total_baris_mentah"] = len(df)

    if df.empty:
        logger.error("Tidak ada data yang berhasil dibaca!")
        return pd.DataFrame(), dict(stats)

    # ── Tahap 2: Pilih & rename kolom ──
    logger.info("TAHAP 2: Rename kolom...")
    df = pilih_dan_rename_kolom(df)

    # ── Tahap 3: Cleaning ──
    logger.info("TAHAP 3: Membersihkan data...")
    df = bersihkan_data(df)

    # ── Tahap 4: Feature engineering ──
    logger.info("TAHAP 4: Feature engineering (umur, IMT)...")
    df = buat_fitur_baru(df)

    # ── Tahap 5: Encoding kategorikal ──
    logger.info("TAHAP 5: Encoding variabel kategorikal...")
    df = encode_kategorikal(df)

    # ── Tahap 6: Penanganan missing value ──
    logger.info("TAHAP 6: Penanganan missing value...")
    df = tangani_missing_value(df)

    # ── Tahap 7: Validasi data ──
    logger.info("TAHAP 7: Validasi data akhir...")
    df = validasi_data(df)

    # ── Tahap 8: Siapkan output ──
    logger.info("TAHAP 8: Menyiapkan output...")
    df = siapkan_output(df)

    # Statistik akhir
    stats["total_valid"] = len(df)
    stats["baris_dihapus"] = stats["total_baris_mentah"] - stats["total_valid"]
    stats["sheets_diproses"] = 1  # Dataset flat, 1 sheet
    stats["umur_invalid"] = int(df["umur"].isna().sum()) if "umur" in df.columns else 0
    stats["imt_invalid"] = int(df["imt"].isna().sum()) if "imt" in df.columns else 0
    stats["td_invalid"] = int(df["sistolik"].isna().sum()) if "sistolik" in df.columns else 0

    # Distribusi per desa
    logger.info("📋 Jumlah data per desa:")
    for desa, count in df.groupby("desa").size().items():
        logger.info(f"   {desa}: {count}")

    logger.info(f"📊 Total data bersih: {len(df)} baris, {len(df.columns)} kolom")
    logger.info("=" * 60)

    return df, dict(stats)
