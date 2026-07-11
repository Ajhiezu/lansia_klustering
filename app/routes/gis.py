"""
gis.py - Blueprint route for GIS map visualization.
Supports filtering by risk level via query parameter.
Uses actual K-Means clustering results with relative risk ranking.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, Response, request
from app.models.session_data import session_data
from app.services.gis_service import generate_map
from app.core.clustering import _rank_clusters_by_risk

bp = Blueprint("gis", __name__)


def _get_cluster_risk_map(df, features):
    """
    Build a mapping from cluster_id -> risk_level using the relative
    ranking system (_rank_clusters_by_risk) so each of the 3 clusters
    gets a distinct label: Sehat, Sedang, or Tinggi.
    """
    key_feats = ["umur", "imt", "sistolik", "diastolik", "kolesterol", "gds_1"]
    key_feats = [f for f in key_feats if f in df.columns]

    cluster_means = df.groupby("cluster")[key_feats].mean()
    rank_labels, _ = _rank_clusters_by_risk(cluster_means)

    # Convert internal labels to display labels
    label_map = {
        "RELATIF SEHAT": "Sehat",
        "RISIKO SEDANG": "Sedang",
        "RISIKO TINGGI": "Tinggi",
    }
    return {cl: label_map.get(lbl, "Sedang") for cl, lbl in rank_labels.items()}


@bp.route("/gis")
def index():
    """Render the GIS dashboard template with KPI cards and filter controls."""
    if not session_data.has_data():
        flash("Silakan unggah data terlebih dahulu untuk melihat peta GIS.", "warning")
        return redirect(url_for("upload.index"))

    df = session_data.df_result.copy()
    features = session_data.features or []

    # Use actual K-Means cluster results with relative risk ranking
    cluster_risk_map = _get_cluster_risk_map(df, features)
    df["risk_level"] = df["cluster"].map(cluster_risk_map)

    total = len(df)
    sehat = int((df["risk_level"] == "Sehat").sum())
    sedang = int((df["risk_level"] == "Sedang").sum())
    tinggi = int((df["risk_level"] == "Tinggi").sum())

    # Aggregate per desa
    desa_table = []
    for desa_name in sorted(df["desa"].unique()):
        df_d = df[df["desa"] == desa_name]
        desa_table.append({
            "desa": desa_name,
            "total": len(df_d),
            "sehat": int((df_d["risk_level"] == "Sehat").sum()),
            "sedang": int((df_d["risk_level"] == "Sedang").sum()),
            "tinggi": int((df_d["risk_level"] == "Tinggi").sum()),
        })

    active_filter = request.args.get("risk_level", "all")

    return render_template(
        "gis.html",
        total=total,
        sehat=sehat,
        sedang=sedang,
        tinggi=tinggi,
        desa_table=desa_table,
        active_filter=active_filter,
    )


@bp.route("/gis/map")
def serve_map():
    """Serve the raw generated Folium map HTML, optionally filtered by risk_level."""
    if not session_data.has_data():
        return "No active session data found.", 404

    risk_filter = request.args.get("risk_level", "all")
    map_html = generate_map(risk_filter=risk_filter)
    return Response(map_html, mimetype="text/html")
