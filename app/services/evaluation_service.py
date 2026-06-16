"""
evaluation_service.py - Service evaluasi cluster dengan interpretasi lengkap.
"""

import logging
from app.models.session_data import session_data

logger = logging.getLogger("lansia.service.evaluation")


def get_evaluation_summary() -> dict:
    """
    Ambil ringkasan evaluasi lengkap termasuk interpretasi.
    """
    if not session_data.has_data():
        return None

    metrics = session_data.metrics
    df_k_eval = session_data.df_k_evaluation

    # Cari K optimal berdasarkan masing-masing metrik
    best_sil_k = int(df_k_eval.loc[df_k_eval["silhouette_score"].idxmax(), "k"])
    best_dbi_k = int(df_k_eval.loc[df_k_eval["davies_bouldin_index"].idxmin(), "k"])
    best_ch_k = int(df_k_eval.loc[df_k_eval["calinski_harabasz_score"].idxmax(), "k"])

    # Interpretasi kualitas clustering saat ini
    sil = metrics["silhouette_score"]
    dbi = metrics["davies_bouldin_index"]
    ch = metrics["calinski_harabasz_score"]

    sil_quality = _interpret_silhouette(sil)
    dbi_quality = _interpret_dbi(dbi)
    ch_quality = _interpret_ch(ch)

    # Data evaluasi semua K untuk grafik
    k_eval_data = df_k_eval.to_dict(orient="records")

    return {
        "current_k": session_data.n_clusters,
        "metrics": metrics,
        "best_k": {
            "silhouette": best_sil_k,
            "davies_bouldin": best_dbi_k,
            "calinski_harabasz": best_ch_k,
        },
        "interpretations": {
            "silhouette": sil_quality,
            "davies_bouldin": dbi_quality,
            "calinski_harabasz": ch_quality,
        },
        "k_eval_data": k_eval_data,
        "elbow_inertias": session_data.elbow_inertias,
    }


def _interpret_silhouette(score: float) -> dict:
    """Interpretasi Silhouette Score."""
    if score >= 0.7:
        quality = "Sangat Baik"
        color = "success"
        desc = "Cluster sangat terpisah dengan jelas. Struktur clustering sangat kuat."
    elif score >= 0.5:
        quality = "Baik"
        color = "success"
        desc = "Cluster terpisah dengan baik. Struktur clustering cukup kuat."
    elif score >= 0.25:
        quality = "Cukup"
        color = "warning"
        desc = "Cluster agak tumpang tindih. Struktur clustering masih bisa diterima."
    else:
        quality = "Kurang"
        color = "danger"
        desc = "Cluster saling tumpang tindih. Perlu evaluasi ulang jumlah cluster."

    return {
        "score": score,
        "quality": quality,
        "color": color,
        "description": desc,
        "explanation": (
            "Silhouette Score mengukur seberapa mirip sebuah data dengan cluster-nya sendiri "
            "dibandingkan dengan cluster tetangga terdekat. Nilai berkisar dari -1 hingga 1. "
            "Semakin mendekati 1, semakin baik pemisahan antar cluster."
        ),
        "formula": "S(i) = (b(i) - a(i)) / max(a(i), b(i))",
        "kelebihan": [
            "Mudah diinterpretasikan (range -1 hingga 1)",
            "Tidak memerlukan ground truth",
            "Memperhitungkan kohesi dan separasi cluster",
        ],
        "kekurangan": [
            "Kurang efektif untuk cluster dengan bentuk tidak konveks",
            "Sensitif terhadap outlier",
            "Komputasi bisa lambat untuk dataset besar",
        ],
    }


def _interpret_dbi(score: float) -> dict:
    """Interpretasi Davies-Bouldin Index."""
    if score <= 0.5:
        quality = "Sangat Baik"
        color = "success"
        desc = "Cluster sangat kompak dan terpisah jauh satu sama lain."
    elif score <= 1.0:
        quality = "Baik"
        color = "success"
        desc = "Cluster cukup kompak dan terpisah dengan baik."
    elif score <= 2.0:
        quality = "Cukup"
        color = "warning"
        desc = "Cluster masih bisa dibedakan namun ada area tumpang tindih."
    else:
        quality = "Kurang"
        color = "danger"
        desc = "Cluster terlalu menyebar atau terlalu berdekatan."

    return {
        "score": score,
        "quality": quality,
        "color": color,
        "description": desc,
        "explanation": (
            "Davies-Bouldin Index mengukur rata-rata 'similarity' antar cluster. "
            "Semakin kecil nilainya (mendekati 0), semakin baik pemisahan cluster. "
            "DBI memperhitungkan jarak intra-cluster dan jarak antar-centroid."
        ),
        "formula": "DBI = (1/K) × Σ max(j≠i) [(σᵢ + σⱼ) / d(cᵢ, cⱼ)]",
        "kelebihan": [
            "Nilai selalu ≥ 0, mudah dipahami (semakin kecil semakin baik)",
            "Memperhitungkan dispersi cluster dan jarak antar centroid",
            "Komputasi relatif efisien",
        ],
        "kekurangan": [
            "Cenderung bias terhadap cluster berbentuk konveks",
            "Menggunakan centroid sebagai representasi, tidak cocok untuk bentuk arbitrer",
            "Sensitif terhadap noise/outlier",
        ],
    }


def _interpret_ch(score: float) -> dict:
    """Interpretasi Calinski-Harabasz Score."""
    if score >= 500:
        quality = "Sangat Baik"
        color = "success"
        desc = "Cluster sangat dense dan terpisah jauh satu sama lain."
    elif score >= 200:
        quality = "Baik"
        color = "success"
        desc = "Cluster cukup dense dan terpisah dengan baik."
    elif score >= 100:
        quality = "Cukup"
        color = "warning"
        desc = "Cluster masih bisa dibedakan namun densitas kurang optimal."
    else:
        quality = "Kurang"
        color = "danger"
        desc = "Cluster kurang dense atau kurang terpisah. Perlu evaluasi ulang."

    return {
        "score": score,
        "quality": quality,
        "color": color,
        "description": desc,
        "explanation": (
            "Calinski-Harabasz Score (Variance Ratio Criterion) mengukur rasio antara "
            "dispersi antar-cluster dan dispersi intra-cluster. Semakin tinggi nilainya, "
            "semakin baik cluster terpisah dan semakin dense anggota dalam cluster."
        ),
        "formula": "CH = [tr(Bₖ)/(K-1)] / [tr(Wₖ)/(n-K)]",
        "kelebihan": [
            "Komputasi sangat cepat",
            "Nilai semakin tinggi semakin baik, intuitif",
            "Bagus untuk cluster berbentuk konveks dan dense",
        ],
        "kekurangan": [
            "Cenderung bias terhadap cluster konveks",
            "Tidak memiliki range tetap, sulit untuk threshold absolut",
            "Kurang efektif untuk cluster dengan kepadatan berbeda",
        ],
    }
