"""
manual_calc.py - Blueprint route for showing step-by-step manual calculation details.
Passes calculated mathematical trace to Jinja2 template.
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from app.models.session_data import session_data
from app.services.manual_calc_service import get_manual_calculation_steps

bp = Blueprint("manual_calc", __name__)


@bp.route("/manual")
def index():
    """Render the manual calculation page."""
    if not session_data.has_data():
        flash("Silakan unggah data terlebih dahulu untuk melihat simulasi perhitungan manual.", "warning")
        return redirect(url_for("upload.index"))

    steps = get_manual_calculation_steps()
    return render_template("manual_calc.html", steps=steps)
