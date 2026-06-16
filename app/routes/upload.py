"""
upload.py - Blueprint route for uploading Excel/CSV files.
Performs file validation, saves the file, and runs the initial pipeline (preprocessing + default clustering).
"""

# Standard Library
import os
from datetime import datetime
from pathlib import Path

# Third Party
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

# Local
from app.core.config import UPLOAD_DIR, ALLOWED_EXTENSIONS, N_CLUSTERS
from app.models.session_data import session_data
from app.services.preprocessing_service import process_upload
from app.services.clustering_service import run_clustering_pipeline

bp = Blueprint("upload", __name__)


def allowed_file(filename: str) -> bool:
    """Check if the uploaded file has a permitted extension."""
    suffix = Path(filename).suffix.lower()
    return suffix in ALLOWED_EXTENSIONS


@bp.route("/upload", methods=["GET", "POST"])
def index():
    """Render the upload form and process file uploads."""
    if request.method == "POST":
        # Check if file part exists
        if "file" not in request.files:
            flash("Tidak ada file yang dikirim.", "danger")
            return redirect(request.url)
            
        file = request.files["file"]
        
        if file.filename == "":
            flash("File belum dipilih.", "danger")
            return redirect(request.url)
            
        if not file or not allowed_file(file.filename):
            flash("Format file tidak valid. Gunakan format .xlsx atau .csv", "danger")
            return redirect(request.url)
            
        try:
            # Secure file saving
            filename = secure_filename(file.filename)
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            filepath = UPLOAD_DIR / filename
            file.save(filepath)
            
            # Reset session data for new analysis
            session_data.clear()
            
            # Step 1: Run Preprocessing
            pre_res = process_upload(filepath)
            if not pre_res.get("success"):
                flash(f"Error Preprocessing: {pre_res.get('error')}", "danger")
                return redirect(request.url)
                
            # Step 2: Run Clustering with default K
            clus_res = run_clustering_pipeline(n_clusters=N_CLUSTERS)
            if not clus_res.get("success"):
                flash(f"Error Clustering: {clus_res.get('error')}", "danger")
                return redirect(request.url)
                
            # Log to history list
            history_exists = any(item["filename"] == filename for item in session_data.history)
            if not history_exists:
                session_data.history.append({
                    "filename": filename,
                    "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M"),
                    "total_rows": pre_res.get("total_rows"),
                    "n_clusters": N_CLUSTERS,
                    "silhouette_score": clus_res.get("metrics", {}).get("silhouette_score", 0.0),
                    "davies_bouldin_index": clus_res.get("metrics", {}).get("davies_bouldin_index", 0.0)
                })
                
            flash(f"Berhasil mengunggah dan menganalisis '{filename}'! Data lansia siap divisualisasikan.", "success")
            return redirect(url_for("dashboard.index"))
            
        except Exception as e:
            flash(f"Terjadi kesalahan saat memproses file: {str(e)}", "danger")
            return redirect(request.url)
            
    # GET request
    # Provide a preview of session data if it already exists
    has_active_data = session_data.has_data()
    raw_preview_html = None
    
    if has_active_data and session_data.df_raw_preview is not None:
        # Convert preview to HTML table
        raw_preview_html = session_data.df_raw_preview.head(10).to_html(
            classes="table table-sm table-striped table-hover",
            index=False,
            border=0
        )

    # Access history
    history = session_data.history if hasattr(session_data, "history") else []

    return render_template(
        "upload.html",
        has_active_data=has_active_data,
        filename=session_data.filename,
        raw_preview_html=raw_preview_html,
        history=history
    )


@bp.route("/upload/clear", methods=["POST"])
def clear_data():
    """Clear all active session analysis data."""
    session_data.clear()
    flash("Semua data analisis aktif telah dibersihkan.", "info")
    return redirect(url_for("upload.index"))


@bp.route("/upload/reload/<filename>")
def reload_file(filename):
    """Reload an already uploaded file from the history list."""
    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        flash(f"Berkas '{filename}' tidak ditemukan di server.", "danger")
        return redirect(url_for("upload.index"))
        
    try:
        # Reset current session (preserving history)
        session_data.clear()
        
        # Step 1: Preprocess
        pre_res = process_upload(filepath)
        if not pre_res.get("success"):
            flash(f"Gagal memuat preprocessing berkas: {pre_res.get('error')}", "danger")
            return redirect(url_for("upload.index"))
            
        # Step 2: Cluster
        clus_res = run_clustering_pipeline(n_clusters=N_CLUSTERS)
        if not clus_res.get("success"):
            flash(f"Gagal memuat clustering berkas: {clus_res.get('error')}", "danger")
            return redirect(url_for("upload.index"))
            
        flash(f"Berkas '{filename}' berhasil dimuat kembali!", "success")
        return redirect(url_for("dashboard.index"))
        
    except Exception as e:
        flash(f"Terjadi kesalahan saat memuat berkas: {str(e)}", "danger")
        return redirect(url_for("upload.index"))
