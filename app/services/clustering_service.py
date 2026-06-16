"""
clustering_service.py - Wrapper service untuk clustering pipeline.
Support custom K dari web UI.
"""

import logging
import numpy as np
import pandas as pd

from app.core.clustering import run_clustering
from app.models.session_data import session_data

logger = logging.getLogger("lansia.service.clustering")


def run_clustering_pipeline(n_clusters: int = 3) -> dict:
    """
    Jalankan clustering dan simpan hasilnya ke session_data.

    Args:
        n_clusters: Jumlah cluster yang diinginkan user

    Returns:
        dict dengan info status dan hasil
    """
    if session_data.df_clean is None:
        return {"success": False, "error": "Data belum di-upload. Silakan upload data terlebih dahulu."}

    try:
        df_clean = session_data.df_clean.copy()

        # Jalankan pipeline clustering (PRESERVED logic)
        (df_result, df_scaled, df_centroids, elbow_inertias,
         df_k_evaluation, metrics, interpretasi,
         X_pca, pca_variance, features) = run_clustering(df_clean, n_clusters)

        # Simpan ke session
        session_data.df_result = df_result
        session_data.df_scaled = df_scaled
        session_data.df_centroids = df_centroids
        session_data.n_clusters = n_clusters
        session_data.features = features
        session_data.labels = df_result["cluster"].values
        session_data.metrics = metrics
        session_data.elbow_inertias = elbow_inertias
        session_data.df_k_evaluation = df_k_evaluation
        session_data.interpretasi = interpretasi
        session_data.X_pca = X_pca
        session_data.pca_variance = pca_variance
        session_data.is_processed = True

        logger.info(f"Clustering selesai: K={n_clusters}, "
                     f"Silhouette={metrics['silhouette_score']:.4f}")

        return {
            "success": True,
            "n_clusters": n_clusters,
            "metrics": metrics,
            "total_data": len(df_result),
        }

    except Exception as e:
        logger.error(f"Error clustering: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


def get_clustering_summary() -> dict:
    """Ambil ringkasan hasil clustering untuk ditampilkan."""
    if not session_data.has_data():
        return None

    df = session_data.df_result
    metrics = session_data.metrics

    # Cluster distribution
    cluster_dist = df["cluster"].value_counts().sort_index().to_dict()

    # Centroid data
    centroids_data = session_data.df_centroids.round(4).to_dict(orient="index")

    # Rata-rata fitur per cluster (unscaled)
    key_feats = ["umur", "imt", "sistol", "diastol",
                 "hb", "kolesterol", "gula_darah", "asam_urat"]
    key_feats = [f for f in key_feats if f in df.columns]
    cluster_means = df.groupby("cluster")[key_feats].mean().round(2).to_dict(orient="index")

    return {
        "n_clusters": session_data.n_clusters,
        "metrics": metrics,
        "cluster_dist": cluster_dist,
        "centroids": centroids_data,
        "cluster_means": cluster_means,
        "total_data": len(df),
        "features": session_data.features,
    }


def get_scatter_data() -> dict:
    """Data untuk scatter plot PCA interaktif."""
    if not session_data.has_data():
        return None

    X_pca = session_data.X_pca
    labels = session_data.labels
    df = session_data.df_result

    scatter = []
    for i in range(len(X_pca)):
        point = {
            "x": round(float(X_pca[i, 0]), 4),
            "y": round(float(X_pca[i, 1]), 4),
            "cluster": int(labels[i]),
            "nama": str(df.iloc[i].get("nama", "")),
            "desa": str(df.iloc[i].get("desa", "")),
        }
        scatter.append(point)

    return {
        "points": scatter,
        "variance": [round(float(v), 4) for v in session_data.pca_variance],
        "n_clusters": session_data.n_clusters,
    }
