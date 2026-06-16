"""
preprocessing_service.py - Wrapper service untuk preprocessing pipeline.
Menambahkan tracking step-by-step untuk visualisasi before/after di web UI.
"""

import logging
import numpy as np
import pandas as pd
from pathlib import Path

from app.core.preprocessing import run_preprocessing
from app.models.session_data import session_data
from app.services.db_service import save_result


logger = logging.getLogger("lansia.service.preprocessing")


def process_upload(filepath: Path) -> dict:
    """
    Jalankan preprocessing dan simpan hasilnya ke session_data.

    Returns:
        dict dengan info status dan statistik
    """
    try:
        # Baca raw preview (5 baris pertama dari sheet pertama)
        try:
            xl = pd.ExcelFile(filepath)
            first_sheet = xl.sheet_names[0]
            raw_preview = pd.read_excel(xl, sheet_name=first_sheet, nrows=50)
            session_data.df_raw_preview = raw_preview
        except Exception:
            session_data.df_raw_preview = None

        # Jalankan pipeline preprocessing (PRESERVED - tidak diubah)
        df_clean, stats = run_preprocessing(filepath)

        if df_clean.empty:
            return {"success": False, "error": "Data kosong setelah preprocessing"}

        # ── BARU: simpan ke MySQL ──
        batch = save_result(df_clean, stats, filepath.name)
        session_data.current_batch_id = batch.id

        # Hitung missing values info
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()
        missing_info = {}
        for col in numeric_cols:
            n_missing = int(df_clean[col].isna().sum())
            if n_missing > 0:
                missing_info[col] = n_missing

        # Simpan ke session
        session_data.df_clean = df_clean
        session_data.preprocessing_stats = stats
        session_data.missing_after = missing_info
        session_data.filename = filepath.name

        logger.info(f"Preprocessing selesai: {len(df_clean)} baris, {len(df_clean.columns)} kolom")

        return {
            "success": True,
            "batch_id": batch.id,
            "total_rows": len(df_clean),
            "total_cols": len(df_clean.columns),
            "stats": stats,
            "columns": list(df_clean.columns),
        }

    except Exception as e:
        logger.error(f"Error preprocessing: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


def get_preprocessing_summary() -> dict:
    """Ambil ringkasan data preprocessing untuk ditampilkan."""
    if session_data.df_clean is None:
        return None

    df = session_data.df_clean
    stats = session_data.preprocessing_stats or {}

    # Statistik deskriptif
    numeric_cols = ["umur", "imt", "sistol", "diastol",
                    "hb", "kolesterol", "gula_darah", "asam_urat"]
    numeric_cols = [c for c in numeric_cols if c in df.columns]

    desc_stats = {}
    for col in numeric_cols:
        s = df[col].dropna()
        desc_stats[col] = {
            "count": int(len(s)),
            "mean": round(float(s.mean()), 2) if len(s) > 0 else 0,
            "std": round(float(s.std()), 2) if len(s) > 0 else 0,
            "min": round(float(s.min()), 2) if len(s) > 0 else 0,
            "max": round(float(s.max()), 2) if len(s) > 0 else 0,
            "median": round(float(s.median()), 2) if len(s) > 0 else 0,
        }

    # Data per desa
    desa_counts = df["desa"].value_counts().to_dict() if "desa" in df.columns else {}

    # Outlier info
    n_outlier = 0

    return {
        "total_rows": len(df),
        "total_cols": len(df.columns),
        "stats": stats,
        "desc_stats": desc_stats,
        "desa_counts": desa_counts,
        "n_outlier": n_outlier,
        "columns": list(df.columns),
        "filename": session_data.filename,
    }
