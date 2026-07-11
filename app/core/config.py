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

INPUT_FILE   = BASE_DIR / "ind_pkg_elderly.xlsx"
UPLOAD_DIR   = BASE_DIR / "uploads"
OUTPUT_DIR   = BASE_DIR / "outputs"
VIS_DIR      = BASE_DIR / "visualisasi"
LOG_DIR      = BASE_DIR / "logs"
CSV_DIR      = BASE_DIR / "csv"
DATA_DIR     = BASE_DIR / "data"

# ─── Kolom yang dibaca dari Excel (usecols) ────────────────────────────────
# Nama kolom harus PERSIS sesuai header di file Excel
USECOLS_EXCEL = [
    "Kecamatan Domisili",
    "Desa Kelurahan Domisili",
    "NIK",
    "Nama Lengkap",
    "Jenis Kelamin",
    "Berat Badan Kg",
    "Pengukuran Tinggi Badan cm",
    "Riwayat Tekanan Darah",
    "Tekanan Darah Sistolik",
    "Tekanan Darah Diastolik",
    "Gula Darah Sewaktu mg Atau dL",
    "Gula Darah Sewaktu Ke 2 GDS Ke 2 mg Atau dL",
    "Gula Darah Puasa mg Atau dL",
    "Gula Darah 2 Jam PP GD2PP mg Atau dL",
    "Interpretasi SKILAS Penurunan Kognitif",
    "Interpretasi SKILAS Malnutrisi",
    "SKILAS Intepretasi Gejala Depresi",
    "Nilai Kolesterol Total",
    "Tanggal Lahir",
]

# ─── Mapping rename kolom → snake_case ─────────────────────────────────────
COLUMN_RENAME_MAP = {
    "Kecamatan Domisili":                              "kecamatan",
    "Desa Kelurahan Domisili":                         "desa",
    "NIK":                                             "nik",
    "Nama Lengkap":                                    "nama",
    "Jenis Kelamin":                                   "jenis_kelamin",
    "Berat Badan Kg":                                  "berat_badan",
    "Pengukuran Tinggi Badan cm":                      "tinggi_badan",
    "Riwayat Tekanan Darah":                           "riwayat_hipertensi",
    "Tekanan Darah Sistolik":                          "sistolik",
    "Tekanan Darah Diastolik":                         "diastolik",
    "Gula Darah Sewaktu mg Atau dL":                   "gds_1",
    "Gula Darah Sewaktu Ke 2 GDS Ke 2 mg Atau dL":    "gds_2",
    "Gula Darah Puasa mg Atau dL":                     "gdp",
    "Gula Darah 2 Jam PP GD2PP mg Atau dL":            "gd2pp",
    "Interpretasi SKILAS Penurunan Kognitif":           "gangguan_kognitif",
    "Interpretasi SKILAS Malnutrisi":                   "malnutrisi",
    "SKILAS Intepretasi Gejala Depresi":                "depresi",
    "Nilai Kolesterol Total":                           "kolesterol",
    "Tanggal Lahir":                                   "tanggal_lahir",
}

# ─── Threshold penanganan missing value ────────────────────────────────────
# Kolom dihapus jika proporsi null MELEBIHI nilai ini
COL_MISSING_THRESHOLD = 0.70  # 70%

# Baris dihapus jika proporsi null MELEBIHI nilai ini
ROW_MISSING_THRESHOLD = 0.50  # 50%

# ─── K-Means ────────────────────────────────────────────────────────────────
N_CLUSTERS   = 3
RANDOM_STATE = 42
ELBOW_MAX_K  = 10

# ─── Fitur untuk clustering ─────────────────────────────────────────────────
CLUSTER_FEATURES = [
    "umur",
    "jenis_kelamin",
    "imt",
    "sistolik",
    "diastolik",
    "gds_1",
    "gds_2",
    "gdp",
    "gd2pp",
    "kolesterol",
    "riwayat_hipertensi",
    "gangguan_kognitif",
    "malnutrisi",
    "depresi",
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
    "mysql+pymysql://root:@localhost:3306/puskesmas_maesan?charset=utf8mb4"
)
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,      # otomatis reconnect jika koneksi putus
    "pool_recycle":  1800,      # recycle koneksi tiap 30 menit
}
SQLALCHEMY_TRACK_MODIFICATIONS = False
