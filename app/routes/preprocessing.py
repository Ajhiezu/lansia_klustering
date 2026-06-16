"""
preprocessing.py - Blueprint route for displaying preprocessing results.
Shows missing value resolutions, outlier identification, and clean dataset previews.
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from app.models.session_data import session_data
from app.services.preprocessing_service import get_preprocessing_summary

bp = Blueprint("preprocessing", __name__)


@bp.route("/preprocessing")
def index():
    """Render the preprocessing details page."""
    if not session_data.has_data():
        flash("Silakan unggah data terlebih dahulu untuk melihat hasil preprocessing.", "warning")
        return redirect(url_for("upload.index"))

    summary = get_preprocessing_summary()
    
    # Convert clean dataset to HTML for preview
    # Show all rows
    df_clean_preview = session_data.df_clean
    
    # Format floating columns to 2 decimals for cleaner rendering
    float_cols = df_clean_preview.select_dtypes(include=["float"]).columns
    df_clean_preview_formatted = df_clean_preview.copy()
    for col in float_cols:
        df_clean_preview_formatted[col] = df_clean_preview_formatted[col].round(2)
        
    table_html = df_clean_preview_formatted.to_html(
        classes="table table-hover table-striped table-bordered align-middle",
        index=False,
        border=0
    )

    return render_template(
        "preprocessing.html",
        summary=summary,
        table_html=table_html
    )
