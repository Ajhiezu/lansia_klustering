"""
session_data.py - In-memory session data management for clustering results.
Stores preprocessing, clustering, and evaluation results per session.
"""

import threading


class SessionData:
    """
    Thread-safe singleton untuk menyimpan data analisis aktif.
    Dalam versi sederhana ini, hanya satu dataset yang aktif (single-user).
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_data()
        return cls._instance

    def _init_data(self):
        """Inisialisasi semua slot data."""
        self.filename = None

        # Preprocessing
        self.current_batch_id = None       # ID batch aktif di MySQL
        self.df_raw_preview = None         # DataFrame mentah (preview)
        self.df_clean = None               # DataFrame setelah preprocessing
        self.preprocessing_stats = None    # dict statistik preprocessing
        self.missing_before = None         # dict missing values sebelum imputasi
        self.missing_after = None          # dict missing values setelah imputasi

        # Clustering
        self.df_result = None              # DataFrame hasil clustering
        self.df_scaled = None              # DataFrame fitur ter-scale
        self.df_centroids = None           # DataFrame centroid
        self.n_clusters = None             # Jumlah cluster aktif
        self.features = None               # List fitur yang digunakan
        self.labels = None                 # Array label cluster

        # Evaluation
        self.metrics = None                # dict metrik evaluasi
        self.elbow_inertias = None         # list inertia elbow method
        self.df_k_evaluation = None        # DataFrame evaluasi semua K
        self.interpretasi = None           # String interpretasi cluster

        # PCA
        self.X_pca = None                  # Array PCA 2D
        self.pca_variance = None           # PCA variance explained

        # GIS
        self.gis_map_html = None           # HTML string peta GIS

        # Status
        self.is_processed = False          # Apakah data sudah diproses
        
        # History list
        if not hasattr(self, "history"):
            self.history = []

    def clear(self, clear_history=False):
        """Reset semua data aktif."""
        hist = self.history if hasattr(self, "history") else []
        self._init_data()
        if not clear_history:
            self.history = hist

    def has_data(self):
        """Cek apakah ada data yang sudah diproses."""
        return self.is_processed and self.df_result is not None


# Global instance
session_data = SessionData()
