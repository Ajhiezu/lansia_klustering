"""
report_service.py - Service to export analysis results to Excel and PDF formats.
Uses reportlab for PDF generation and pandas/xlsxwriter for Excel generation.
"""

import io
import logging
from datetime import datetime
import pandas as pd
import numpy as np

# Excel writing
import xlsxwriter

# PDF writing (ReportLab)
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.models.session_data import session_data

logger = logging.getLogger("lansia.service.report")


class NumberedCanvas(canvas.Canvas):
    """Custom canvas to draw page numbers and footer on each page."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (on pages after the first page)
        if self._pageNumber > 1:
            self.drawString(54, 750, "Laporan Analisis Risiko Kesehatan Lansia — Puskesmas Maesan")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)
            
        # Footer
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 50, 558, 50)
        
        page_text = f"Halaman {self._pageNumber} dari {page_count}"
        self.drawRightString(558, 38, page_text)
        
        date_str = datetime.now().strftime("%d-%m-%Y %H:%M")
        self.drawString(54, 38, f"Dicetak otomatis oleh Sistem Clustering Lansia • {date_str}")
        self.restoreState()


def export_excel() -> io.BytesIO:
    """
    Export clustering results to Excel.
    Creates a spreadsheet with 3 sheets: Data Hasil Cluster, Centroid, Evaluasi.
    """
    if not session_data.has_data():
        return None

    output = io.BytesIO()
    
    # 1. Read data
    df_result = session_data.df_result.copy()
    df_centroids = session_data.df_centroids.copy()
    metrics = session_data.metrics
    df_k_eval = session_data.df_k_evaluation
    
    # Re-order columns for output readability
    first_cols = ["nama", "nik", "desa", "umur", "jenis_kelamin", "imt", "sistol", "diastol", "cluster", "cluster_label"]
    remaining_cols = [c for c in df_result.columns if c not in first_cols]
    df_result_export = df_result[first_cols + remaining_cols]
    
    # Map jenis kelamin for excel
    if "jenis_kelamin" in df_result_export.columns:
        df_result_export["jenis_kelamin"] = df_result_export["jenis_kelamin"].map({1.0: "Laki-laki", 0.0: "Perempuan"})

    # 2. Write to buffer using xlsxwriter
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Sheet 1: Hasil Clustering
        df_result_export.to_excel(writer, sheet_name="Hasil Clustering", index=False)
        workbook = writer.book
        worksheet1 = writer.sheets["Hasil Clustering"]
        
        # Sheet 2: Centroids
        df_centroids.to_excel(writer, sheet_name="Centroid Cluster")
        worksheet2 = writer.sheets["Centroid Cluster"]
        
        # Sheet 3: Evaluasi Metrik
        # Format evaluation summary
        eval_summary = [
            {"Parameter": "Jumlah Cluster (K)", "Nilai": session_data.n_clusters},
            {"Parameter": "Silhouette Score", "Nilai": metrics.get("silhouette_score")},
            {"Parameter": "Davies-Bouldin Index", "Nilai": metrics.get("davies_bouldin_index")},
            {"Parameter": "Calinski-Harabasz Score", "Nilai": metrics.get("calinski_harabasz_score")},
            {"Parameter": "Inertia (SSE)", "Nilai": metrics.get("inertia")},
        ]
        df_eval_summary = pd.DataFrame(eval_summary)
        df_eval_summary.to_excel(writer, sheet_name="Evaluasi Metrik", index=False, startrow=0, startcol=0)
        
        # Append elbow and K evaluation
        df_k_eval.to_excel(writer, sheet_name="Evaluasi Metrik", index=False, startrow=8, startcol=0)
        worksheet3 = writer.sheets["Evaluasi Metrik"]
        
        # 3. Formatting Excel sheets
        header_format = workbook.add_format({
            "bold": True,
            "text_wrap": True,
            "valign": "top",
            "fg_color": "#1e293b",
            "font_color": "#ffffff",
            "border": 1
        })
        
        # Apply header formatting
        for ws in [worksheet1, worksheet2, worksheet3]:
            ws.set_row(0, 24)
            
        # Adjust column widths
        for col_num, col_name in enumerate(df_result_export.columns):
            worksheet1.set_column(col_num, col_num, max(len(col_name) + 3, 12))
            
    output.seek(0)
    return output


def export_pdf() -> io.BytesIO:
    """
    Export analysis summary to PDF.
    Generates a formal, beautiful document.
    """
    if not session_data.has_data():
        return None

    buffer = io.BytesIO()
    
    # Page setup
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=54, # 0.75 in
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles matching theme
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=25
    )
    
    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=10
    )
    
    table_text_style = ParagraphStyle(
        "TableText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b")
    )
    
    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.white
    )

    story = []
    
    # ─── HEADER / COVER ───
    story.append(Paragraph("LAPORAN HASIL CLUSTERING K-MEANS", title_style))
    story.append(Paragraph(
        f"Analisis Risiko Kesehatan Lansia Berbasis Wilayah • Puskesmas Maesan<br/>"
        f"Tanggal Analisis: {datetime.now().strftime('%d %B %Y')} | Dataset: {session_data.filename}",
        subtitle_style
    ))
    story.append(Spacer(1, 10))
    
    # ─── SECTION 1: RINGKASAN METODE & EVALUASI ───
    story.append(Paragraph("1. Evaluasi & Parameter K-Means", h1_style))
    story.append(Paragraph(
        "Clustering K-Means dijalankan menggunakan fitur kesehatan terstandarisasi untuk mengidentifikasi tingkat risiko lansia. "
        "Kualitas clustering diuji menggunakan Silhouette Score (pemisahan cluster), Davies-Bouldin Index (kompaksi cluster), "
        "dan Calinski-Harabasz Score (rasio dispersi).",
        body_style
    ))
    
    # Table of metrics
    metrics = session_data.metrics
    eval_data = [
        [Paragraph("Parameter Evaluasi", table_header_style), Paragraph("Nilai Hasil Uji", table_header_style), Paragraph("Interpretasi", table_header_style)],
        [Paragraph("Jumlah Cluster (K)", table_text_style), Paragraph(str(session_data.n_clusters), table_text_style), Paragraph("Ditentukan pengguna / rekomendasi sistem", table_text_style)],
        [Paragraph("Silhouette Score", table_text_style), Paragraph(f"{metrics.get('silhouette_score')}", table_text_style), Paragraph(_get_sil_desc(metrics.get('silhouette_score')), table_text_style)],
        [Paragraph("Davies-Bouldin Index", table_text_style), Paragraph(f"{metrics.get('davies_bouldin_index')}", table_text_style), Paragraph(_get_dbi_desc(metrics.get('davies_bouldin_index')), table_text_style)],
        [Paragraph("Calinski-Harabasz Score", table_text_style), Paragraph(f"{metrics.get('calinski_harabasz_score')}", table_text_style), Paragraph("Semakin tinggi menunjukkan pemisahan yang semakin solid", table_text_style)],
        [Paragraph("Inertia (SSE)", table_text_style), Paragraph(f"{metrics.get('inertia')}", table_text_style), Paragraph("Total kuadrat jarak data ke centroid masing-masing", table_text_style)],
    ]
    
    t_eval = Table(eval_data, colWidths=[150, 100, 250])
    t_eval.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t_eval)
    story.append(Spacer(1, 20))
    
    # ─── SECTION 2: KARAKTERISTIK CLUSTER ───
    story.append(Paragraph("2. Karakteristik & Karakter Cluster", h1_style))
    story.append(Paragraph(
        "Berikut adalah profil rata-rata untuk setiap cluster (nilai fisik asli sebelum scaling). "
        "Ini digunakan untuk menarik kesimpulan status kesehatan lansia di masing-masing cluster.",
        body_style
    ))
    
    df_res = session_data.df_result
    key_feats = ["umur", "imt", "sistol", "diastol", "hb", "kolesterol", "gula_darah", "asam_urat"]
    key_feats = [f for f in key_feats if f in df_res.columns]
    
    # Calculate group means
    cluster_means = df_res.groupby("cluster")[key_feats].mean().round(2)
    cluster_counts = df_res["cluster"].value_counts().to_dict()
    
    char_headers = [Paragraph("Variabel Kesehatan", table_header_style)]
    for c_id in sorted(cluster_counts.keys()):
        char_headers.append(Paragraph(f"Cluster {c_id}<br/>(N = {cluster_counts[c_id]})", table_header_style))
        
    char_table_data = [char_headers]
    
    var_labels = {
        "umur": "Rata-rata Umur (tahun)",
        "imt": "Indeks Massa Tubuh (IMT)",
        "sistol": "TD Sistolik (mmHg)",
        "diastol": "TD Diastolik (mmHg)",
        "hb": "Hemoglobin / Hb (g/dL)",
        "kolesterol": "Kolesterol Total (mg/dL)",
        "gula_darah": "Gula Darah Sewaktu (mg/dL)",
        "asam_urat": "Asam Urat (mg/dL)",
    }
    
    for f in key_feats:
        row = [Paragraph(var_labels.get(f, f), table_text_style)]
        for c_id in sorted(cluster_counts.keys()):
            val = cluster_means.loc[c_id, f]
            row.append(Paragraph(str(val), table_text_style))
        char_table_data.append(row)
        
    # Append risk conclusion row
    conclusion_row = [Paragraph("<b>Kesimpulan Risiko</b>", table_text_style)]
    for c_id in sorted(cluster_counts.keys()):
        c_mean = cluster_means.loc[c_id]
        risk_score = 0
        if "umur" in c_mean and c_mean["umur"] >= 70: risk_score += 1
        if "imt" in c_mean and (c_mean["imt"] >= 30 or c_mean["imt"] < 18.5): risk_score += 1
        if "sistol" in c_mean and c_mean["sistol"] >= 140: risk_score += 1
        if "kolesterol" in c_mean and c_mean["kolesterol"] >= 200: risk_score += 1
        if "gula_darah" in c_mean and c_mean["gula_darah"] >= 140: risk_score += 1
        
        risk_label = "<b>Tinggi</b>" if risk_score >= 3 else "<b>Sedang</b>" if risk_score >= 1 else "<b>Rendah (Sehat)</b>"
        conclusion_row.append(Paragraph(risk_label, table_text_style))
    char_table_data.append(conclusion_row)
    
    num_cols = len(cluster_counts) + 1
    col_widths = [200] + [300 / (num_cols - 1)] * (num_cols - 1)
    
    t_char = Table(char_table_data, colWidths=col_widths)
    t_char.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#06b6d4")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e2e8f0")), # grey background for conclusion row
    ]))
    story.append(t_char)
    story.append(Spacer(1, 20))
    
    # ─── SECTION 3: SEBARAN DESA ───
    story.append(Paragraph("3. Distribusi Lansia per Wilayah Desa", h1_style))
    story.append(Paragraph(
        "Tabel berikut merangkum jumlah lansia di setiap desa berdasarkan cluster yang terbentuk.",
        body_style
    ))
    
    desa_counts = df_res.groupby(["desa", "cluster"]).size().unstack(fill_value=0)
    
    desa_headers = [Paragraph("Desa Wilayah", table_header_style)]
    for c_id in sorted(cluster_counts.keys()):
        desa_headers.append(Paragraph(f"Cluster {c_id}", table_header_style))
    desa_headers.append(Paragraph("Total Lansia", table_header_style))
    
    desa_table_data = [desa_headers]
    for d_name, row in desa_counts.iterrows():
        r_data = [Paragraph(str(d_name), table_text_style)]
        tot = 0
        for c_id in sorted(cluster_counts.keys()):
            val = int(row.get(c_id, 0))
            tot += val
            r_data.append(Paragraph(str(val), table_text_style))
        r_data.append(Paragraph(f"<b>{tot}</b>", table_text_style))
        desa_table_data.append(r_data)
        
    # Append total row
    tot_row = [Paragraph("<b>Total</b>", table_text_style)]
    grand_total = 0
    for c_id in sorted(cluster_counts.keys()):
        c_sum = int(desa_counts[c_id].sum())
        grand_total += c_sum
        tot_row.append(Paragraph(f"<b>{c_sum}</b>", table_text_style))
    tot_row.append(Paragraph(f"<b>{grand_total}</b>", table_text_style))
    desa_table_data.append(tot_row)
    
    d_col_widths = [160] + [260 / (num_cols - 1)] * (num_cols - 1) + [80]
    t_desa = Table(desa_table_data, colWidths=d_col_widths)
    t_desa.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor("#f8fafc")]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#f1f5f9")),
    ]))
    story.append(t_desa)
    
    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer


def _get_sil_desc(val: float) -> str:
    if val >= 0.7: return "Sangat Baik (Struktur Kuat)"
    if val >= 0.5: return "Baik (Struktur Cukup)"
    if val >= 0.25: return "Cukup (Cluster Tumpang Tindih)"
    return "Kurang Baik (Struktur Lemah)"


def _get_dbi_desc(val: float) -> str:
    if val <= 0.5: return "Sangat Baik (Sangat Kompak)"
    if val <= 1.0: return "Baik (Kompak)"
    if val <= 2.0: return "Cukup Baik"
    return "Kurang Baik (Menyebar)"
