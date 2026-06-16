"""
visualization.py - Visualisasi hasil preprocessing dan clustering
"""

import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # non-interactive backend untuk server
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from pathlib import Path
from sklearn.metrics import silhouette_samples, silhouette_score

from app.core.config import N_CLUSTERS, ELBOW_MAX_K

logger = logging.getLogger("lansia.visualization")

# Palet warna konsisten untuk cluster
CLUSTER_COLORS = ["#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6"]
sns.set_style("whitegrid")
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.titlesize": 13,
    "axes.labelsize": 11,
})


def _save(fig, path: Path, title: str):
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Grafik disimpan: {path.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. Elbow Method
# ══════════════════════════════════════════════════════════════════════════════

def plot_elbow(inertias: list, out_dir: Path):
    fig, ax = plt.subplots(figsize=(8, 5))
    ks = range(1, ELBOW_MAX_K + 1)
    ax.plot(ks, inertias, "bo-", linewidth=2, markersize=8)
    ax.axvline(x=N_CLUSTERS, color="red", linestyle="--",
               label=f"K terpilih = {N_CLUSTERS}")
    ax.set_xlabel("Jumlah Cluster (k)")
    ax.set_ylabel("Inertia (WCSS)")
    ax.set_title("Elbow Method – Penentuan Jumlah Cluster Optimal")
    ax.legend()
    _save(fig, out_dir / "elbow_method.png", "elbow")


# ══════════════════════════════════════════════════════════════════════════════
# 2. Cluster Scatter (PCA 2D)
# ══════════════════════════════════════════════════════════════════════════════

def plot_cluster_pca(X_pca: np.ndarray, labels: np.ndarray, out_dir: Path):
    fig, ax = plt.subplots(figsize=(9, 6))
    for cl in sorted(np.unique(labels)):
        mask = labels == cl
        ax.scatter(X_pca[mask, 0], X_pca[mask, 1],
                   c=CLUSTER_COLORS[cl % len(CLUSTER_COLORS)],
                   label=f"Cluster {cl}",
                   alpha=0.7, s=60, edgecolors="white", linewidths=0.4)
    ax.set_xlabel("Komponen Utama 1 (PC1)")
    ax.set_ylabel("Komponen Utama 2 (PC2)")
    ax.set_title("Visualisasi Cluster K-Means (PCA 2D)")
    ax.legend(title="Cluster", loc="best")
    _save(fig, out_dir / "cluster_visualization.png", "cluster_pca")

# ══════════════════════════════════════════════════════════════════════════════
# Silhouette Plot
# ══════════════════════════════════════════════════════════════════════════════

def plot_silhouette(X_scaled, labels, out_dir: Path):
    from sklearn.metrics import silhouette_samples

    fig, ax = plt.subplots(figsize=(9, 6))

    y_lower = 10
    n_clusters = len(np.unique(labels))

    for i in range(n_clusters):
        ith_cluster_silhouette_values = silhouette_samples(
            X_scaled, labels
        )[labels == i]

        ith_cluster_silhouette_values.sort()

        size_cluster_i = ith_cluster_silhouette_values.shape[0]
        y_upper = y_lower + size_cluster_i

        color = CLUSTER_COLORS[i % len(CLUSTER_COLORS)]

        ax.fill_betweenx(
            np.arange(y_lower, y_upper),
            0,
            ith_cluster_silhouette_values,
            facecolor=color,
            edgecolor=color,
            alpha=0.7
        )

        ax.text(-0.05, y_lower + 0.5 * size_cluster_i,
                f"Cluster {i}")

        y_lower = y_upper + 10

    silhouette_avg = silhouette_score(X_scaled, labels)

    ax.axvline(x=silhouette_avg,
               color="red",
               linestyle="--",
               label=f"Average = {silhouette_avg:.3f}")

    ax.set_xlabel("Silhouette Coefficient")
    ax.set_ylabel("Cluster")
    ax.set_title("Silhouette Plot K-Means")
    ax.legend()

    _save(fig, out_dir / "silhouette_plot.png", "silhouette")


# ══════════════════════════════════════════════════════════════════════════════
# 3. Distribusi Tambahan
# ══════════════════════════════════════════════════════════════════════════════

def plot_distribusi_umur(df: pd.DataFrame, out_dir: Path):
    fig, ax = plt.subplots(figsize=(9, 5))
    if "cluster" in df.columns:
        for cl in sorted(df["cluster"].unique()):
            subset = df[df["cluster"] == cl]["umur"].dropna()
            ax.hist(subset, bins=20, alpha=0.6,
                    color=CLUSTER_COLORS[cl % len(CLUSTER_COLORS)],
                    label=f"Cluster {cl}")
        ax.legend(title="Cluster")
    else:
        ax.hist(df["umur"].dropna(), bins=20, color="#3498DB", alpha=0.8)
    ax.set_xlabel("Umur (tahun)")
    ax.set_ylabel("Frekuensi")
    ax.set_title("Distribusi Umur Lansia per Cluster")
    _save(fig, out_dir / "distribusi_umur.png", "umur")


def plot_distribusi_imt(df: pd.DataFrame, out_dir: Path):
    fig, ax = plt.subplots(figsize=(9, 5))
    valid = df["imt"].dropna()
    ax.hist(valid, bins=25, color="#2ECC71", alpha=0.8, edgecolor="white")
    # Garis batas IMT
    for v, lbl in [(18.5, "Kurus"), (25, "Normal|OW"), (30, "OW|Obesitas")]:
        ax.axvline(x=v, color="red", linestyle="--", linewidth=1)
        ax.text(v + 0.2, ax.get_ylim()[1] * 0.9, lbl, fontsize=8, color="red")
    ax.set_xlabel("Indeks Massa Tubuh (IMT)")
    ax.set_ylabel("Frekuensi")
    ax.set_title("Distribusi IMT Lansia")
    _save(fig, out_dir / "distribusi_imt.png", "imt")


def plot_distribusi_td(df: pd.DataFrame, out_dir: Path):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, col, label, color in [
        (axes[0], "sistol",  "Tekanan Darah Sistolik (mmHg)",  "#E74C3C"),
        (axes[1], "diastol", "Tekanan Darah Diastolik (mmHg)", "#9B59B6"),
    ]:
        valid = df[col].dropna()
        ax.hist(valid, bins=25, color=color, alpha=0.8, edgecolor="white")
        ax.set_xlabel(label)
        ax.set_ylabel("Frekuensi")
        ax.set_title(f"Distribusi {label}")
    _save(fig, out_dir / "distribusi_td.png", "td")


def plot_heatmap_korelasi(df: pd.DataFrame, out_dir: Path):
    num_cols = [c for c in [
        "umur", "imt", "sistol", "diastol",
        "hb", "kolesterol", "gula_darah", "asam_urat"
    ] if c in df.columns]

    if len(num_cols) < 3:
        return

    corr = df[num_cols].corr()
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdYlGn",
                center=0, square=True, ax=ax,
                linewidths=0.5, cbar_kws={"shrink": 0.8})
    ax.set_title("Heatmap Korelasi Fitur Utama")
    _save(fig, out_dir / "heatmap_korelasi.png", "heatmap")


def plot_jumlah_per_cluster(df: pd.DataFrame, out_dir: Path):
    if "cluster" not in df.columns:
        return
    counts = df["cluster"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(
        [f"Cluster {i}" for i in counts.index],
        counts.values,
        color=[CLUSTER_COLORS[i % len(CLUSTER_COLORS)] for i in counts.index],
        edgecolor="white", width=0.6
    )
    for bar, val in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                str(val), ha="center", va="bottom", fontweight="bold")
    ax.set_ylabel("Jumlah Lansia")
    ax.set_title("Distribusi Anggota per Cluster")
    _save(fig, out_dir / "jumlah_per_cluster.png", "cluster_count")


def plot_radar_cluster(df: pd.DataFrame, features: list, out_dir: Path):
    """Radar chart rata-rata fitur utama per cluster."""
    feats = [f for f in ["umur", "imt", "sistol", "hb",
                          "kolesterol", "gula_darah", "asam_urat"]
             if f in features and f in df.columns]
    if len(feats) < 3 or "cluster" not in df.columns:
        return

    means = df.groupby("cluster")[feats].mean()
    # Normalisasi 0-1 untuk radar
    means_norm = (means - means.min()) / (means.max() - means.min() + 1e-9)

    N = len(feats)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    for cl in means_norm.index:
        vals = means_norm.loc[cl].tolist()
        vals += vals[:1]
        ax.plot(angles, vals, linewidth=2,
                color=CLUSTER_COLORS[cl % len(CLUSTER_COLORS)],
                label=f"Cluster {cl}")
        ax.fill(angles, vals,
                color=CLUSTER_COLORS[cl % len(CLUSTER_COLORS)], alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([f.replace("_", " ").title() for f in feats], size=9)
    ax.set_title("Profil Rata-Rata Cluster (Radar Chart)", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    _save(fig, out_dir / "radar_cluster.png", "radar")

def plot_silhouette_scores(df_eval: pd.DataFrame, out_dir: Path):

    fig, ax = plt.subplots(figsize=(8,5))

    ax.plot(
        df_eval["k"],
        df_eval["silhouette_score"],
        marker="o",
        linewidth=2
    )

    best_k = df_eval.loc[
        df_eval["silhouette_score"].idxmax(),
        "k"
    ]

    ax.axvline(
        best_k,
        color="red",
        linestyle="--",
        label=f"K terbaik = {best_k}"
    )

    ax.set_xlabel("Jumlah Cluster (K)")
    ax.set_ylabel("Silhouette Score")
    ax.set_title("Evaluasi Silhouette Score")
    ax.legend()

    _save(fig,
          out_dir / "silhouette_scores.png",
          "silhouette_scores")    

def plot_davies_bouldin(df_eval: pd.DataFrame, out_dir: Path):

    fig, ax = plt.subplots(figsize=(8,5))

    ax.plot(
        df_eval["k"],
        df_eval["davies_bouldin_index"],
        marker="o",
        linewidth=2
    )

    best_k = df_eval.loc[
        df_eval["davies_bouldin_index"].idxmin(),
        "k"
    ]

    ax.axvline(
        best_k,
        color="red",
        linestyle="--",
        label=f"K terbaik = {best_k}"
    )

    ax.set_xlabel("Jumlah Cluster (K)")
    ax.set_ylabel("Davies-Bouldin Index")
    ax.set_title("Evaluasi Davies-Bouldin Index")
    ax.legend()

    _save(fig,
          out_dir / "davies_bouldin_scores.png",
          "davies_bouldin")

def plot_calinski_harabasz(df_eval: pd.DataFrame, out_dir: Path):

    fig, ax = plt.subplots(figsize=(8,5))

    ax.plot(
        df_eval["k"],
        df_eval["calinski_harabasz_score"],
        marker="o",
        linewidth=2
    )

    best_k = df_eval.loc[
        df_eval["calinski_harabasz_score"].idxmax(),
        "k"
    ]

    ax.axvline(
        best_k,
        color="red",
        linestyle="--",
        label=f"K terbaik = {best_k}"
    )

    ax.set_xlabel("Jumlah Cluster (K)")
    ax.set_ylabel("Calinski-Harabasz Score")
    ax.set_title("Evaluasi Calinski-Harabasz")
    ax.legend()

    _save(fig,
          out_dir / "calinski_harabasz_scores.png",
          "calinski_harabasz")                    


# ══════════════════════════════════════════════════════════════════════════════
# 4. Run semua visualisasi
# ══════════════════════════════════════════════════════════════════════════════

def run_all_visualizations(df: pd.DataFrame, X_scaled: np.ndarray, X_pca: np.ndarray,
                           elbow_inertias: list,df_k_evaluation, features: list,
                           out_dir: Path, vis_dir: Path):
    """Buat semua grafik dan simpan ke folder yang sesuai."""
    out_dir.mkdir(parents=True, exist_ok=True)
    vis_dir.mkdir(parents=True, exist_ok=True)

    labels = df["cluster"].values if "cluster" in df.columns else None

    # Elbow → outputs/
    plot_elbow(elbow_inertias, out_dir)

    # Cluster PCA → outputs/
    if labels is not None:
        plot_cluster_pca(X_pca, labels, out_dir)
        plot_silhouette(X_scaled, labels, out_dir)

    # Visualisasi tambahan → visualisasi/
    plot_distribusi_umur(df, vis_dir)
    plot_distribusi_imt(df, vis_dir)
    plot_distribusi_td(df, vis_dir)
    plot_heatmap_korelasi(df, vis_dir)
    plot_jumlah_per_cluster(df, vis_dir)
    plot_radar_cluster(df, features, vis_dir)
    plot_silhouette_scores(df_k_evaluation, out_dir)

    plot_davies_bouldin(df_k_evaluation, out_dir)

    plot_calinski_harabasz(df_k_evaluation, out_dir)

    logger.info("Semua visualisasi selesai dibuat")
