"""
reports.py - Blueprint route for exporting reports.
Serves file downloads for Excel and PDF formats.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, send_file
from app.models.session_data import session_data
from app.services.report_service import export_excel, export_pdf

bp = Blueprint("reports", __name__)


@bp.route("/reports")
def index():
    """Render the reports page."""
    if not session_data.has_data():
        flash("Silakan unggah data terlebih dahulu untuk mengekspor laporan.", "warning")
        return redirect(url_for("upload.index"))

    return render_template(
        "reports.html",
        filename=session_data.filename,
        n_clusters=session_data.n_clusters
    )


@bp.route("/reports/download/<file_type>")
def download(file_type: str):
    """Download the analysis report in PDF or Excel format."""
    if not session_data.has_data():
        flash("Tidak ada data aktif untuk diunduh.", "danger")
        return redirect(url_for("upload.index"))

    if file_type == "excel":
        buffer = export_excel()
        if not buffer:
            flash("Gagal mengekspor file Excel.", "danger")
            return redirect(url_for("reports.index"))
            
        # Format filename with date
        filename = f"Laporan_Clustering_Lansia_{session_data.filename.split('.')[0]}.xlsx"
        return send_file(
            buffer,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )
        
    elif file_type == "pdf":
        buffer = export_pdf()
        if not buffer:
            flash("Gagal mengekspor laporan PDF.", "danger")
            return redirect(url_for("reports.index"))
            
        filename = f"Laporan_Clustering_Lansia_{session_data.filename.split('.')[0]}.pdf"
        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )
        
    else:
        flash("Tipe file ekspor tidak dikenal.", "danger")
        return redirect(url_for("reports.index"))
