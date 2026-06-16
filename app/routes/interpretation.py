"""
interpretation.py - Blueprint route for showing qualitative cluster interpretation.
Shows cluster health profiles, automatic recommendations, and radar charts.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, jsonify
from app.models.session_data import session_data
from app.services.clustering_service import get_clustering_summary
from app.core.clustering import _compute_cluster_risk_score, _rank_clusters_by_risk

bp = Blueprint("interpretation", __name__)


@bp.route("/interpretation")
def index():
    """Render the cluster interpretation and recommendations page."""
    if not session_data.has_data():
        flash("Silakan unggah data terlebih dahulu untuk melihat interpretasi hasil.", "warning")
        return redirect(url_for("upload.index"))

    summary = get_clustering_summary()

    # Parse the interpretasi text from core if it is a string
    interpretasi_raw = session_data.interpretasi

    # ── Build cluster means DataFrame for relative ranking ──────────────────
    import pandas as pd
    cluster_means_dict = summary["cluster_means"]
    cluster_means_df = pd.DataFrame(cluster_means_dict).T  # shape: (n_clusters, n_features)

    # Rank clusters relatively: highest score = Risiko Tinggi, lowest = Sehat
    rank_labels, rank_scores = _rank_clusters_by_risk(cluster_means_df)

    _LABEL_META = {
        "RISIKO TINGGI": {
            "level": "Risiko Tinggi",
            "color": "danger",
            "desc": (
                "Cluster ini memiliki kombinasi indikator kesehatan paling buruk dibanding "
                "cluster lain: IMT overweight, tekanan darah paling tinggi, dan gula darah "
                "paling tinggi. Memerlukan intervensi medis aktif, kunjungan rumah (home care), "
                "dan pemantauan ketat oleh tenaga kesehatan."
            ),
        },
        "RISIKO SEDANG": {
            "level": "Risiko Sedang",
            "color": "warning",
            "desc": (
                "Cluster dengan tingkat risiko menengah. Beberapa indikator (tekanan darah, "
                "IMT, atau gula darah) berada di atas nilai ideal meski tidak sekritis cluster "
                "risiko tinggi. Memerlukan edukasi gizi, modifikasi gaya hidup, dan senam lansia "
                "rutin agar tidak berkembang menjadi penyakit kronis."
            ),
        },
        "RELATIF SEHAT": {
            "level": "Relatif Sehat",
            "color": "success",
            "desc": (
                "Cluster dengan profil kesehatan terbaik dibanding cluster lain. Meskipun "
                "beberapa indikator masih di atas ambang ideal (misalnya pra-hipertensi), "
                "cluster ini memiliki beban risiko paling ringan. Memerlukan edukasi preventif "
                "dan pemantauan rutin untuk mempertahankan kondisi."
            ),
        },
    }

    recommendations = {}

    for c_id, means in cluster_means_dict.items():
        rel_label = rank_labels.get(c_id, "RISIKO SEDANG")
        meta = _LABEL_META[rel_label]

        recs = []

        # --- Rekomendasi berbasis nilai klinis aktual ---
        if "umur" in means and means["umur"] >= 70:
            recs.append("Skrining kesehatan geriatri berkala (sebulan sekali) dan pendampingan mobilitas.")
        elif "umur" in means and means["umur"] >= 60:
            recs.append("Skrining kesehatan lansia teratur (3 bulan sekali).")

        if "imt" in means:
            if means["imt"] >= 30:
                recs.append("Konseling gizi klinis untuk mengatasi obesitas dan pembatasan asupan kalori.")
            elif means["imt"] >= 25:
                recs.append("Program olahraga rutin dan edukasi porsi makan sehat untuk mengatasi overweight.")
            elif means["imt"] < 18.5:
                recs.append("Program PMT (Pemberian Makanan Tambahan) lansia untuk mengatasi malnutrisi.")

        if "sistol" in means:
            if means["sistol"] >= 140:
                recs.append("Terapi kepatuhan minum obat hipertensi, pembatasan garam, dan senam lansia.")
            elif means["sistol"] >= 120:
                recs.append("Pantau tekanan darah rutin; anjurkan diet DASH (rendah garam, tinggi kalium).")

        if "gula_darah" in means:
            if means["gula_darah"] >= 200:
                recs.append("Rujukan ke poli penyakit dalam untuk penanganan DM tipe 2 dan monitoring gula rutin.")
            elif means["gula_darah"] >= 140:
                recs.append("Edukasi diet rendah karbohidrat sederhana dan cek gula darah puasa berkala.")
            elif means["gula_darah"] >= 100:
                recs.append("Waspada pra-diabetes; anjurkan aktivitas fisik aerobik minimal 30 menit/hari.")

        if "kolesterol" in means and means["kolesterol"] >= 200:
            recs.append("Terapi statin sesuai resep dokter dan anjuran mengurangi konsumsi lemak jenuh/gorengan.")

        if "asam_urat" in means and means["asam_urat"] >= 7.0:
            recs.append("Hindari makanan tinggi purin (jeroan, kangkung) dan pastikan hidrasi cukup (≥8 gelas/hari).")

        # Tambahkan rekomendasi umum sesuai level
        if rel_label == "RISIKO TINGGI":
            recs.append("Prioritaskan kunjungan Prolanis/Posyandu lansia dan koordinasi dengan dokter layanan primer.")
        elif rel_label == "RISIKO SEDANG":
            recs.append("Ikuti program senam lansia dan konseling kesehatan minimal sebulan sekali di Posyandu.")
        else:
            recs.append("Pertahankan pola hidup sehat (PHBS); lakukan tes kesehatan rutin 3 bulan sekali.")

        recommendations[c_id] = {
            "level": meta["level"],
            "color": meta["color"],
            "desc": meta["desc"],
            "recs": recs,
            "risk_score": round(rank_scores.get(c_id, 0), 2),
        }

    return render_template(
        "interpretation.html",
        summary=summary,
        interpretasi_raw=interpretasi_raw,
        recommendations=recommendations,
    )


@bp.route("/api/interpretation/radar")
def radar_data_api():
    """API endpoint providing cluster mean comparison data for radar charts."""
    if not session_data.has_data():
        return jsonify({"success": False, "error": "No data available."}), 400
        
    summary = get_clustering_summary()
    
    # Selected features for radar chart display (standard key health metrics)
    radar_features = ["umur", "imt", "sistol", "diastol", "hb", "kolesterol", "gula_darah", "asam_urat"]
    radar_features = [f for f in radar_features if f in summary["features"]]
    
    # We should return both actual means and scaled means (0-1) so the radar looks balanced
    # Let's compute scaled cluster means from the scaled session data
    df_scaled = session_data.df_scaled.copy()
    df_scaled["cluster"] = session_data.labels
    scaled_means = df_scaled.groupby("cluster")[radar_features].mean().round(4).to_dict(orient="index")
    
    return jsonify({
        "success": True,
        "features": radar_features,
        "actual_means": summary["cluster_means"],
        "scaled_means": scaled_means,
        "n_clusters": session_data.n_clusters
    })
