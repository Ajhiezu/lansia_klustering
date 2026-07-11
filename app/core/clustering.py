"""
clustering.py - K-Means clustering, evaluasi, dan interpretasi otomatis
(Preserved from original project - NO logic changes, only import paths adjusted)
"""

# Standard Library
import logging

# Third Party
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score
)
from sklearn.preprocessing import MinMaxScaler

# Local
from app.core.config import CLUSTER_FEATURES, N_CLUSTERS, RANDOM_STATE, ELBOW_MAX_K

logger = logging.getLogger("lansia.clustering")


# ══════════════════════════════════════════════════════════════════════════════
# 1. Feature scaling
# ══════════════════════════════════════════════════════════════════════════════

def scale_features(df: pd.DataFrame, features=None) -> tuple:
    """
    MinMax scale fitur clustering ke range [0, 1].

    Kembalikan:
        (df_scaled, scaler, feature_cols_used)
    """
    if features is None:
        features = CLUSTER_FEATURES

    # Gunakan hanya fitur yang tersedia di DataFrame
    available = [f for f in features if f in df.columns]
    missing   = [f for f in features if f not in df.columns]

    if missing:
        logger.warning(f"Fitur tidak tersedia (diisi 0): {missing}")
        for f in missing:
            df[f] = 0.0

    available = features  # sekarang semua ada

    X = df[available].copy()

    # Pastikan semua numerik
    X = X.apply(pd.to_numeric, errors="coerce")

    # Isi NaN per kolom dengan median; jika semua NaN, isi dengan 0
    for col in X.columns:
        med = X[col].median()
        if np.isnan(med):
            med = 0.0
        X[col] = X[col].fillna(med)

    # Final check: pastikan tidak ada NaN tersisa
    X = X.fillna(0.0)

    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    df_scaled = pd.DataFrame(X_scaled, columns=available, index=df.index)

    logger.info(f"Fitur di-scale: {len(available)} kolom")
    return df_scaled, scaler, available


# ══════════════════════════════════════════════════════════════════════════════
# 2. Elbow Method
# ══════════════════════════════════════════════════════════════════════════════

def compute_elbow(X_scaled: np.ndarray, max_k=None) -> list:
    """
    Hitung inertia untuk k=1..max_k.
    Kembalikan list inertia.
    """
    if max_k is None:
        max_k = ELBOW_MAX_K
    inertias = []
    for k in range(1, max_k + 1):
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        km.fit(X_scaled)
        inertias.append(km.inertia_)
    logger.info(f"Elbow method selesai (k=1..{max_k})")
    return inertias


# ══════════════════════════════════════════════════════════════════════════════
# 3. K-Means Clustering
# ══════════════════════════════════════════════════════════════════════════════

def run_kmeans(X_scaled: np.ndarray, n_clusters=None) -> tuple:
    """
    Jalankan K-Means dengan n_clusters.

    Kembalikan:
        (labels, centroids, kmeans_model)
    """
    if n_clusters is None:
        n_clusters = N_CLUSTERS
    km = KMeans(n_clusters=n_clusters, random_state=RANDOM_STATE, n_init=10)
    labels = km.fit_predict(X_scaled)
    logger.info(f"K-Means selesai: {n_clusters} cluster")
    return labels, km.cluster_centers_, km


# ══════════════════════════════════════════════════════════════════════════════
# 4. Evaluasi Clustering
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_clustering(X_scaled: np.ndarray, labels: np.ndarray,
                        km_model: KMeans) -> dict:
    """
    Hitung metrik evaluasi clustering.
    """
    sil   = silhouette_score(X_scaled, labels)
    dbi   = davies_bouldin_score(X_scaled, labels)
    inert = km_model.inertia_
    ch_score = calinski_harabasz_score(X_scaled, labels)

    unique, counts = np.unique(labels, return_counts=True)
    dist = dict(zip([int(u) for u in unique], [int(c) for c in counts]))

    metrics = {
        "silhouette_score":      round(sil, 4),
        "davies_bouldin_index":  round(dbi, 4),
        "inertia":               round(inert, 2),
        "jumlah_data_per_cluster": dist,
        "calinski_harabasz_score": round(ch_score, 4),
    }

    logger.info(f"Silhouette Score     : {sil:.4f}")
    logger.info(f"Davies-Bouldin Index : {dbi:.4f}")
    logger.info(f"Inertia              : {inert:.2f}")
    logger.info(f"Distribusi cluster   : {dist}")
    return metrics


# ══════════════════════════════════════════════════════════════════════════════
# 5. Interpretasi Otomatis Cluster
# ══════════════════════════════════════════════════════════════════════════════

def _compute_cluster_risk_score(row: pd.Series) -> float:
    """
    Hitung skor risiko komposit untuk satu baris rata-rata cluster.
    Menggunakan bobot klinis berdasarkan ambang batas kesehatan lansia.

    Skor kontinu (bukan biner) agar antar-cluster bisa dibedakan walau
    semua nilai masih di bawah ambang batas kritis.
    """
    score = 0.0

    # Umur (kontribusi linier di atas 60)
    if "umur" in row:
        if row["umur"] >= 75:
            score += 2.0
        elif row["umur"] >= 70:
            score += 1.5
        elif row["umur"] >= 65:
            score += 1.0
        elif row["umur"] >= 60:
            score += 0.5

    # IMT: overweight atau underweight
    if "imt" in row:
        if row["imt"] >= 30 or row["imt"] < 18.5:
            score += 2.0
        elif row["imt"] >= 27 or row["imt"] < 20:
            score += 1.0
        elif row["imt"] >= 25:
            score += 0.5

    # Tekanan Darah Sistolik
    if "sistolik" in row:
        if row["sistolik"] >= 160:
            score += 3.0
        elif row["sistolik"] >= 140:
            score += 2.0
        elif row["sistolik"] >= 130:
            score += 1.0
        elif row["sistolik"] >= 120:
            score += 0.5

    # Tekanan Darah Diastolik
    if "diastolik" in row:
        if row["diastolik"] >= 100:
            score += 2.0
        elif row["diastolik"] >= 90:
            score += 1.5
        elif row["diastolik"] >= 80:
            score += 0.5

    # Gula Darah Sewaktu (GDS 1)
    if "gds_1" in row:
        if row["gds_1"] >= 200:
            score += 3.0
        elif row["gds_1"] >= 140:
            score += 2.0
        elif row["gds_1"] >= 126:
            score += 1.0
        elif row["gds_1"] >= 100:
            score += 0.5

    # Kolesterol
    if "kolesterol" in row:
        if row["kolesterol"] >= 240:
            score += 2.0
        elif row["kolesterol"] >= 200:
            score += 1.0
        elif row["kolesterol"] >= 180:
            score += 0.3

    return round(score, 3)


def _rank_clusters_by_risk(cluster_means: pd.DataFrame) -> dict:
    """
    Tetapkan label risiko RELATIF antar cluster:
    - Cluster dengan skor tertinggi → RISIKO TINGGI
    - Cluster dengan skor terendah  → RELATIF SEHAT
    - Cluster di tengah             → RISIKO SEDANG

    Jika hanya 2 cluster, tidak ada 'SEDANG'.
    """
    scores = {cl: _compute_cluster_risk_score(cluster_means.loc[cl])
              for cl in cluster_means.index}

    sorted_cls = sorted(scores.items(), key=lambda x: x[1])  # ascending
    n = len(sorted_cls)

    labels = {}
    for rank, (cl, _) in enumerate(sorted_cls):
        if rank == n - 1:
            labels[cl] = "RISIKO TINGGI"
        elif rank == 0:
            labels[cl] = "RELATIF SEHAT"
        else:
            labels[cl] = "RISIKO SEDANG"

    return labels, scores


def interpret_clusters(df: pd.DataFrame, features: list) -> str:
    """
    Buat teks interpretasi otomatis berdasarkan rata-rata tiap cluster.
    Menggunakan sistem ranking relatif antar cluster sehingga setiap cluster
    mendapatkan label risiko yang berbeda (Sehat / Sedang / Tinggi).
    """
    lines = ["\n" + "=" * 60]
    lines.append("INTERPRETASI CLUSTER")
    lines.append("=" * 60)

    key_feats = ["umur", "imt", "sistolik", "diastolik",
                 "kolesterol", "gds_1"]
    key_feats = [f for f in key_feats if f in features]

    cluster_means = df.groupby("cluster")[key_feats].mean()

    # Hitung label risiko relatif
    risk_labels, risk_scores = _rank_clusters_by_risk(cluster_means)

    for cl in sorted(df["cluster"].unique()):
        lines.append(f"\nCluster {cl}  (n={len(df[df['cluster']==cl])} lansia):")
        row = cluster_means.loc[cl]

        # Umur
        if "umur" in row:
            tag = "tua (≥70)" if row["umur"] >= 70 else \
                  "paruh baya (60-69)" if row["umur"] >= 60 else "pra-lansia (45-59)"
            lines.append(f"  • Rata-rata umur  : {row['umur']:.1f} th ({tag})")

        # IMT
        if "imt" in row:
            tag = "obesitas" if row["imt"] >= 30 else \
                  "overweight" if row["imt"] >= 25 else \
                  "normal" if row["imt"] >= 18.5 else "underweight"
            lines.append(f"  • Rata-rata IMT   : {row['imt']:.1f} ({tag})")

        # TD Sistolik
        if "sistolik" in row:
            tag = "hipertensi berat" if row["sistolik"] >= 180 else \
                  "hipertensi" if row["sistolik"] >= 140 else \
                  "pra-hipertensi" if row["sistolik"] >= 120 else "normal"
            lines.append(f"  • Rata-rata TD    : {row['sistolik']:.0f} mmHg ({tag})")

        # Kolesterol
        if "kolesterol" in row:
            tag = "tinggi (≥200)" if row["kolesterol"] >= 200 else \
                  "batas tinggi" if row["kolesterol"] >= 180 else "normal"
            lines.append(f"  • Kolesterol      : {row['kolesterol']:.0f} mg/dL ({tag})")

        # Gula Darah Sewaktu (GDS 1)
        if "gds_1" in row:
            tag = "diabetes (≥200)" if row["gds_1"] >= 200 else \
                  "pra-diabetes (≥140)" if row["gds_1"] >= 140 else \
                  "batas (≥100)" if row["gds_1"] >= 100 else "normal"
            lines.append(f"  • GDS 1           : {row['gds_1']:.0f} mg/dL ({tag})")

        risk_label = risk_labels[cl]
        risk_note = (
            "(skor risiko tertinggi di antara semua cluster)"
            if risk_label == "RISIKO TINGGI" else
            "(skor risiko menengah di antara semua cluster)"
            if risk_label == "RISIKO SEDANG" else
            "(skor risiko terendah di antara semua cluster)"
        )
        lines.append(f"  → Kesimpulan      : {risk_label} {risk_note}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 6. PCA untuk visualisasi 2D
# ══════════════════════════════════════════════════════════════════════════════

def compute_pca(X_scaled: np.ndarray, n_components=2) -> tuple:
    """Reduksi dimensi menggunakan PCA."""
    pca = PCA(n_components=n_components, random_state=RANDOM_STATE)
    X_pca = pca.fit_transform(X_scaled)
    var = pca.explained_variance_ratio_
    logger.info(f"PCA variance explained: {', '.join([f'PC{i+1}={v:.2%}' for i,v in enumerate(var)])}")
    return X_pca, var


# ══════════════════════════════════════════════════════════════════════════════
# 7. Evaluasi semua nilai K
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_all_k(X_scaled: np.ndarray, max_k=None) -> pd.DataFrame:
    """
    Evaluasi clustering untuk berbagai nilai K.
    """
    if max_k is None:
        max_k = ELBOW_MAX_K

    results = []

    for k in range(2, max_k + 1):
        km = KMeans(
            n_clusters=k,
            random_state=RANDOM_STATE,
            n_init=10
        )
        labels = km.fit_predict(X_scaled)

        sil = silhouette_score(X_scaled, labels)
        dbi = davies_bouldin_score(X_scaled, labels)
        ch  = calinski_harabasz_score(X_scaled, labels)

        results.append({
            "k": k,
            "inertia": km.inertia_,
            "silhouette_score": round(sil, 4),
            "davies_bouldin_index": round(dbi, 4),
            "calinski_harabasz_score": round(ch, 4)
        })

        logger.info(
            f"K={k} | "
            f"Silhouette={sil:.4f} | "
            f"DBI={dbi:.4f} | "
            f"CH={ch:.2f}"
        )

    return pd.DataFrame(results)


# ══════════════════════════════════════════════════════════════════════════════
# 8. Pipeline clustering lengkap
# ══════════════════════════════════════════════════════════════════════════════

def run_clustering(df: pd.DataFrame, n_clusters=None) -> tuple:
    """
    Pipeline lengkap: scale → elbow → kmeans → evaluate → PCA.

    Kembalikan:
        (df_result, df_scaled, df_centroids, elbow_inertias,
         df_k_evaluation, metrics, interpretasi, X_pca, pca_variance, features)
    """
    if n_clusters is None:
        n_clusters = N_CLUSTERS

    df = df.copy().reset_index(drop=True)

    # Scale
    df_scaled, scaler, features = scale_features(df)
    X_scaled = df_scaled.values

    # Elbow
    elbow_inertias = compute_elbow(X_scaled)

    # Evaluasi semua K
    df_k_evaluation = evaluate_all_k(X_scaled)

    # K-Means
    labels, centroids, km = run_kmeans(X_scaled, n_clusters)

    # Tambahkan ke DataFrame
    df["cluster"] = labels
    df["cluster_label"] = df["cluster"].map(lambda x: f"Cluster {x}")

    # Evaluasi
    metrics = evaluate_clustering(X_scaled, labels, km)

    # Centroid DataFrame
    df_centroids = pd.DataFrame(centroids, columns=features)
    df_centroids.index = [f"Cluster {i}" for i in range(n_clusters)]

    # Interpretasi
    interpretasi = interpret_clusters(df, features)

    # PCA
    X_pca, pca_variance = compute_pca(X_scaled)

    return (df, df_scaled, df_centroids, elbow_inertias,
            df_k_evaluation, metrics, interpretasi, X_pca, pca_variance, features)
