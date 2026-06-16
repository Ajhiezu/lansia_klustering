"""
evaluation.py - Blueprint route for displaying cluster evaluation metrics.
Shows Silhouette, Davies-Bouldin, Calinski-Harabasz scores, and provides JSON chart data.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, jsonify
from app.models.session_data import session_data
from app.services.evaluation_service import get_evaluation_summary

bp = Blueprint("evaluation", __name__)


@bp.route("/evaluation")
def index():
    """Render the cluster evaluation page."""
    if not session_data.has_data():
        flash("Silakan unggah data terlebih dahulu untuk melihat hasil evaluasi.", "warning")
        return redirect(url_for("upload.index"))

    summary = get_evaluation_summary()
    return render_template("evaluation.html", summary=summary)


@bp.route("/api/evaluation/chart")
def chart_data_api():
    """API endpoint providing data for Elbow and validation metric charts."""
    if not session_data.has_data():
        return jsonify({"success": False, "error": "No data available."}), 400
        
    summary = get_evaluation_summary()
    return jsonify({
        "success": True,
        "k_eval_data": summary["k_eval_data"],
        "elbow_inertias": summary["elbow_inertias"],
        "current_k": summary["current_k"]
    })
