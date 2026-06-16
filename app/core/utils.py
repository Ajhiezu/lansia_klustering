"""
utils.py - Fungsi-fungsi utilitas umum
(Preserved from original project - NO logic changes)
"""

import re
import logging
import numpy as np
from pathlib import Path


def setup_logger(name: str, log_dir: Path) -> logging.Logger:
    """Buat logger profesional ke file dan konsol."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:          # hindari duplikasi handler
        return logger

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                             datefmt="%Y-%m-%d %H:%M:%S")

    # File handler
    fh = logging.FileHandler(log_dir / "process.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def clean_header(col: str) -> str:
    """
    Bersihkan nama kolom menjadi snake_case yang konsisten.

    Contoh:
        "Jenis Kelamin"  → "jenis_kelamin"
        "Gangguan\\nGinjal" → "gangguan_ginjal"
        "TD (mmHg)"      → "td_mmhg"
    """
    if not isinstance(col, str):
        col = str(col)
    col = col.lower()
    col = re.sub(r"[\n\r\t]+", " ", col)          # newline → spasi
    col = re.sub(r"[^a-z0-9\s_]", " ", col)       # buang karakter aneh
    col = re.sub(r"\s+", "_", col.strip())         # spasi → underscore
    col = re.sub(r"_+", "_", col)                  # underscore ganda
    return col


def normalize_jenis_kelamin(val) -> float:
    """L/Laki-laki → 1.0, P/Perempuan → 0.0, lainnya → NaN."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return np.nan
    s = str(val).strip().upper()
    if s in {"L", "LAKI-LAKI", "LAKI", "1"}:
        return 1.0
    if s in {"P", "PEREMPUAN", "PR", "0"}:
        return 0.0
    return np.nan


def normalize_boolean(val, kunjungan: bool = False) -> float:
    """
    Normalisasi nilai boolean dari data Puskesmas.

    kunjungan=True  → V/BARU bernilai 1, semua lain 0
    kunjungan=False → Y/YA/V/BARU → 1, T/TIDAK → 0
    """
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return 0.0
    s = str(val).strip().upper()
    if s in {"V", "BARU", "LAMA"}:
        return 1.0
    if kunjungan:
        return 0.0
    if s in {"Y", "YA", "1", "TRUE", "YES", "*"}:
        return 1.0
    if s in {"T", "TIDAK", "0", "FALSE", "NO"}:
        return 0.0
    # Jika ada angka, coba parse
    try:
        return float(bool(float(s)))
    except ValueError:
        return 0.0


def parse_imt(val, bb=None, tb=None) -> float:
    """
    Hitung/ekstrak IMT.

    Prioritas:
    1. BB + TB tersedia  → IMT = BB / (TB/100)²
    2. Val string "20(N)" → ambil angka
    3. Val numerik langsung
    """
    # Hitung dari BB / TB
    try:
        bb_f = float(str(bb).replace(",", "."))
        tb_f = float(str(tb).replace(",", "."))
        if tb_f > 3:           # TB dalam cm
            tb_f = tb_f / 100
        imt = bb_f / (tb_f ** 2)
        if 10 <= imt <= 60:
            return round(imt, 2)
    except Exception:
        pass

    # Ekstrak angka dari string "20(N)" atau "30(K)"
    if val is not None and not (isinstance(val, float) and np.isnan(val)):
        s = str(val).strip()
        nums = re.findall(r"[\d]+(?:[.,]\d+)?", s)
        if nums:
            try:
                imt = float(nums[0].replace(",", "."))
                if 10 <= imt <= 60:
                    return round(imt, 2)
            except ValueError:
                pass

    return np.nan


def parse_td(val) -> tuple:
    """
    Pisahkan tekanan darah menjadi (sistolik, diastolik).

    Mendukung format: "120/80", "120-80", "120 80", "138,77"
    Kembalikan (nan, nan) jika tidak valid.
    """
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return np.nan, np.nan

    s = str(val).strip().replace(",", "/").replace("-", "/").replace(" ", "/")
    parts = s.split("/")
    parts = [p.strip() for p in parts if p.strip()]

    try:
        sis = float(parts[0])
        dia = float(parts[1]) if len(parts) > 1 else np.nan
    except (ValueError, IndexError):
        return np.nan, np.nan

    SIS_MIN, SIS_MAX = 50, 300
    DIA_MIN, DIA_MAX = 30, 200
    sis = sis if SIS_MIN <= sis <= SIS_MAX else np.nan
    dia = dia if (not np.isnan(dia) and DIA_MIN <= dia <= DIA_MAX) else np.nan

    return sis, dia


def detect_outliers_iqr(series):
    """
    Deteksi outlier menggunakan metode IQR.
    Kembalikan boolean Series: True = outlier.
    """
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    return (series < lower) | (series > upper)


def calculate_individual_risk(row) -> dict:
    """
    Calculate individual risk score and risk level based on clinical thresholds.
    Score ranges from 0 to 5.
    """
    import pandas as pd
    score = 0
    reasons = []
    
    # 1. Umur (>= 60 tahun)
    umur = row.get("umur")
    if pd.notna(umur) and umur >= 60:
        score += 1
        reasons.append("Lansia (umur >= 60)")
        
    # 2. IMT (Kurus < 18.5 atau Obesitas >= 27)
    imt = row.get("imt")
    if pd.notna(imt):
        if imt < 18.5:
            score += 1
            reasons.append("Underweight/Malnutrisi (IMT < 18.5)")
        elif imt >= 27.0:
            score += 1
            reasons.append("Overweight/Obesitas (IMT >= 27.0)")
            
    # 3. Tekanan Darah (Sistolik >= 140 atau Diastolik >= 90)
    sis = row.get("sistol")
    dia = row.get("diastol")
    bp_high = False
    if pd.notna(sis) and sis >= 140:
        bp_high = True
    if pd.notna(dia) and dia >= 90:
        bp_high = True
    if bp_high:
        score += 1
        reasons.append("Hipertensi (TD >= 140/90)")
        
    # 4. Gula Darah (>= 140 mg/dL)
    gd = row.get("gula_darah")
    if pd.notna(gd) and gd >= 140:
        score += 1
        reasons.append("Hiperglikemia/DM (GD >= 140)")
        
    # 5. Kolesterol (>= 200 mg/dL)
    kol = row.get("kolesterol")
    if pd.notna(kol) and kol >= 200:
        score += 1
        reasons.append("Hiperkolesterolemia (Kolesterol >= 200)")

    if score >= 3:
        level = "Tinggi"
        color = "danger"
    elif score >= 1:
        level = "Sedang"
        color = "warning"
    else:
        level = "Sehat"
        color = "success"
        
    return {
        "score": score,
        "level": level,
        "color": color,
        "reasons": reasons
    }

