"""
clustering.py - Blueprint route for displaying clustering results.
Supports re-running K-Means with custom K and provides JSON endpoints for charts.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models.session_data import session_data
from app.services.clustering_service import (
    run_clustering_pipeline, get_clustering_summary, get_scatter_data
)

bp = Blueprint("clustering", __name__)


@bp.route("/clustering")
def index():
    """Render the clustering results page."""
    if not session_data.has_data():
        flash("Silakan unggah data terlebih dahulu untuk menjalankan clustering.", "warning")
        return redirect(url_for("upload.index"))

    summary = get_clustering_summary()
    
    # Format cluster result table
    df_res_preview = session_data.df_result.copy()
    float_cols = df_res_preview.select_dtypes(include=["float"]).columns
    for col in float_cols:
        df_res_preview[col] = df_res_preview[col].round(2)
        
    table_html = df_res_preview.to_html(
        classes="table table-hover table-striped table-bordered align-middle",
        index=False,
        border=0
    )

    return render_template(
        "clustering.html",
        summary=summary,
        table_html=table_html
    )


@bp.route("/clustering/rerun", methods=["POST"])
def rerun():
    """Re-run K-Means clustering with a user-specified K."""
    if not session_data.has_data():
        return jsonify({"success": False, "error": "No active data session found."}), 400
        
    try:
        n_clusters = int(request.form.get("n_clusters", 3))
        if n_clusters < 2 or n_clusters > 10:
            flash("Jumlah cluster harus antara 2 hingga 10.", "danger")
            return redirect(url_for("clustering.index"))
            
        res = run_clustering_pipeline(n_clusters=n_clusters)
        if res.get("success"):
            flash(f"Clustering berhasil dijalankan ulang dengan K = {n_clusters}!", "success")
        else:
            flash(f"Gagal menjalankan clustering: {res.get('error')}", "danger")
            
        return redirect(url_for("clustering.index"))
        
    except ValueError:
        flash("Input jumlah cluster tidak valid.", "danger")
        return redirect(url_for("clustering.index"))


@bp.route("/api/clustering/scatter")
def scatter_api():
    """API endpoint providing 2D PCA coordinate data for scatter plot rendering."""
    if not session_data.has_data():
        return jsonify({"success": False, "error": "No data available."}), 400
    return jsonify(get_scatter_data())
