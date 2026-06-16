"""
dashboard.py - Route blueprint for dashboard page.
Displays summary stats and redirect links.
"""

from flask import Blueprint, render_template, redirect, url_for
from app.models.session_data import session_data
from app.services.clustering_service import get_clustering_summary
from app.services.preprocessing_service import get_preprocessing_summary

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    """Render the dashboard home page."""
    if not session_data.has_data():
        # Render a dashboard welcome screen prompting the user to upload data
        return render_template(
            "dashboard.html",
            has_data=False,
            total_rows=0,
            n_clusters=0,
            filename=None
        )

    # Get data summaries
    pre_summary = get_preprocessing_summary()
    clus_summary = get_clustering_summary()

    return render_template(
        "dashboard.html",
        has_data=True,
        total_rows=pre_summary["total_rows"] if pre_summary else 0,
        n_clusters=session_data.n_clusters,
        filename=session_data.filename,
        pre_summary=pre_summary,
        clus_summary=clus_summary,
        metrics=session_data.metrics
    )
