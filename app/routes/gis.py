"""
gis.py - Blueprint route for GIS map visualization.
Supports filtering by risk level via query parameter.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, Response, request
from app.models.session_data import session_data
from app.services.gis_service import generate_map
from app.core.utils import calculate_individual_risk

bp = Blueprint("gis", __name__)


@bp.route("/gis")
def index():
    """Render the GIS dashboard template with KPI cards and filter controls."""
    if not session_data.has_data():
        flash("Silakan unggah data terlebih dahulu untuk melihat peta GIS.", "warning")
        return redirect(url_for("upload.index"))

    df = session_data.df_result.copy()

    # Calculate risk for each individual
    risks = df.apply(calculate_individual_risk, axis=1)
    total = len(df)
    sehat = sum(1 for r in risks if r["level"] == "Sehat")
    sedang = sum(1 for r in risks if r["level"] == "Sedang")
    tinggi = sum(1 for r in risks if r["level"] == "Tinggi")

    # Aggregate per desa
    df["risk_level"] = [r["level"] for r in risks]
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
