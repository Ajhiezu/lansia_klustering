"""
Semua operasi baca/tulis ke MySQL.
"""
# Standard Library
from datetime import datetime
import logging

# Third Party
import numpy as np
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

# Local
from app.extensions import db
from app.models.lansia import LansiaRecord, UploadBatch

logger = logging.getLogger("lansia.db_service")

# Kolom yang valid di tabel lansia_record
_RECORD_COLS = {
    c.name for c in LansiaRecord.__table__.columns
} - {"id", "batch_id", "created_at"}


def _safe(v):
    """Konversi NaN / inf → None agar MySQL tidak error."""
    if v is None:
        return None
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
        return None
    return v


def _infer_bulan(filename: str) -> str:
    bulan_map = {
        "januari":"Januari","februari":"Februari","maret":"Maret",
        "april":"April","mei":"Mei","juni":"Juni","juli":"Juli",
        "agustus":"Agustus","september":"September","oktober":"Oktober",
        "november":"November","desember":"Desember",
    }
    fn = filename.lower()
    for k, v in bulan_map.items():
        if k in fn:
            return v
    return None


# ── SIMPAN ────────────────────────────────────────────────────────────────────

def save_result(df: pd.DataFrame, stats: dict, filename: str) -> UploadBatch:
    """
    Simpan DataFrame hasil preprocessing ke MySQL.
    Dipanggil dari preprocessing_service.process_upload().
    """
    batch = UploadBatch(
        filename    = filename,
        bulan       = _infer_bulan(filename),
        uploaded_at = datetime.utcnow(),
        total_rows  = len(df),
        total_desa  = int(df["desa"].nunique()) if "desa" in df.columns else 0,
        status      = "success",
        stats_json  = stats,
    )
    db.session.add(batch)
    db.session.flush()   # dapatkan batch.id sebelum commit

    # Bulk insert per 500 baris
    records = []
    for _, row in df.iterrows():
        data = {"batch_id": batch.id}
        for col in _RECORD_COLS:
            if col in row.index:
                data[col] = _safe(row[col])
        records.append(LansiaRecord(**data))

    CHUNK = 500
    for i in range(0, len(records), CHUNK):
        db.session.bulk_save_objects(records[i : i + CHUNK])

    db.session.commit()
    logger.info(f"Saved: batch_id={batch.id}, {len(records)} records")
    return batch


# ── QUERY ─────────────────────────────────────────────────────────────────────

def get_latest_batch() -> UploadBatch:
    return UploadBatch.query.order_by(UploadBatch.uploaded_at.desc()).first()


def get_all_batches() -> list:
    return UploadBatch.query.order_by(UploadBatch.uploaded_at.desc()).all()


def get_df_by_batch(batch_id: int) -> pd.DataFrame:
    """Ambil semua record satu batch sebagai DataFrame."""
    rows = LansiaRecord.query.filter_by(batch_id=batch_id).all()
    return pd.DataFrame([r.to_dict() for r in rows]) if rows else pd.DataFrame()


def get_df_by_desa(desa: str, batch_id: int = None) -> pd.DataFrame:
    q = LansiaRecord.query.filter_by(desa=desa)
    if batch_id:
        q = q.filter_by(batch_id=batch_id)
    rows = q.all()
    return pd.DataFrame([r.to_dict() for r in rows]) if rows else pd.DataFrame()


def get_summary(batch_id: int = None) -> dict:
    """Statistik ringkasan untuk dashboard."""
    if batch_id is None:
        batch = get_latest_batch()
        if not batch:
            return {}
        batch_id = batch.id

    df = get_df_by_batch(batch_id)
    if df.empty:
        return {}

    num_cols = ["umur","imt","sistol","diastol",
                "hb","kolesterol","gula_darah","asam_urat"]
    num_cols = [c for c in num_cols if c in df.columns]

    desc = {}
    for col in num_cols:
        s = df[col].dropna()
        if len(s) == 0:
            continue
        desc[col] = {
            "count":  int(len(s)),
            "mean":   round(float(s.mean()),   2),
            "std":    round(float(s.std()),    2),
            "min":    round(float(s.min()),    2),
            "max":    round(float(s.max()),    2),
            "median": round(float(s.median()), 2),
        }

    return {
        "batch_id":     batch_id,
        "total_lansia": len(df),
        "total_desa":   int(df["desa"].nunique()),
        "desa_counts":  df["desa"].value_counts().to_dict(),
        "jk": {
            "laki_laki": int((df["jenis_kelamin"] == 1).sum()),
            "perempuan":  int((df["jenis_kelamin"] == 0).sum()),
        },
        "desc_stats": desc,
        "n_outlier":  0,
    }


def delete_batch(batch_id: int) -> bool:
    try:
        batch = db.session.get(UploadBatch, batch_id)
        if not batch:
            return False
        db.session.delete(batch)
        db.session.commit()
        return True
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception(f"Gagal hapus batch_id={batch_id}")
        return False
