"""
config.py - Konfigurasi default untuk core ML modules
Dapat di-override melalui web interface
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ─── Path ──────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent.parent.parent  # project_lansia/
load_dotenv(BASE_DIR / ".env")

INPUT_FILE   = BASE_DIR / "input" / "data_januari.xlsx"
UPLOAD_DIR   = BASE_DIR / "uploads"
OUTPUT_DIR   = BASE_DIR / "outputs"
VIS_DIR      = BASE_DIR / "visualisasi"
LOG_DIR      = BASE_DIR / "logs"
CSV_DIR      = BASE_DIR / "csv"
DATA_DIR     = BASE_DIR / "data"

# ─── Sheet yang diabaikan ───────────────────────────────────────────────────
SKIP_SHEETS  = {"Rekap", "Sheet3", "REKAP", "rekap"}

# ─── K-Means ────────────────────────────────────────────────────────────────
N_CLUSTERS   = 3
RANDOM_STATE = 42
ELBOW_MAX_K  = 10
MIN_FILL_RATIO = 0.5  # minimal 50% data terisi per desa baru dilakukan imputasi


# ─── Fitur untuk clustering ─────────────────────────────────────────────────
CLUSTER_FEATURES = [
    "umur",
    "jenis_kelamin",
    "imt",
    "sistol",
    "diastol",
    "kemandirian_A",
    "kemandirian_B",
    "skilas_penurunan_kognitif",
    "skilas_keterbatasan_mobilitas",
    "skilas_malnutrisi",
    "skilas_ggn_penglihatan",
    "skilas_ggn_pendengaran",
    "skilas_gejala_depresi",
    "hb",
    "kolesterol",
    "gula_darah",
    "asam_urat",
    "gangguan_paru",
    "gangguan_ginjal",
    "kunjungan_baru",
    "kunjungan_lama",
    "diobati",
    "dirujuk",
]

# ─── Label cluster ──────────────────────────────────────────────────────────
CLUSTER_LABELS = {0: "Cluster 0", 1: "Cluster 1", 2: "Cluster 2"}

# ─── Flask ───────────────────────────────────────────────────────────────────
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "lansia-clustering-secret-key-2026")
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max upload
ALLOWED_EXTENSIONS = {".xlsx", ".csv"}

# ── MySQL Laragon ──
SQLALCHEMY_DATABASE_URI = os.getenv(
    "SQLALCHEMY_DATABASE_URI",
    "mysql+pymysql://root:@localhost:3306/puskesmas_tempeh?charset=utf8mb4"
)
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,      # otomatis reconnect jika koneksi putus
    "pool_recycle":  1800,      # recycle koneksi tiap 30 menit
}
SQLALCHEMY_TRACK_MODIFICATIONS = False
