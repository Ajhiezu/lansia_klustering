"""
app/__init__.py - Flask Application Factory.
Configures error handlers, registers blueprints, and ensures folder structure exists.
"""

import os
import logging
from flask import Flask, render_template
from app.extensions import db, migrate
from app.core.config import (
    FLASK_SECRET_KEY, MAX_CONTENT_LENGTH, UPLOAD_DIR, LOG_DIR, OUTPUT_DIR, DATA_DIR,
    SQLALCHEMY_DATABASE_URI, SQLALCHEMY_ENGINE_OPTIONS, SQLALCHEMY_TRACK_MODIFICATIONS
)
from app.core.utils import setup_logger


def create_app() -> Flask:
    """Create and configure the Flask application instance."""
    app = Flask(__name__)
    
    # Configure Flask settings
    app.config["SECRET_KEY"] = FLASK_SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
    app.config["SQLALCHEMY_DATABASE_URI"]        = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_ENGINE_OPTIONS"]      = SQLALCHEMY_ENGINE_OPTIONS
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from app.models import lansia  # noqa: F401
        db.create_all()


    # Ensure required directories exist
    for directory in [UPLOAD_DIR, LOG_DIR, OUTPUT_DIR, DATA_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    # Initialize logging
    logger = setup_logger("lansia", LOG_DIR)
    logger.info("Initializing Lansia Clustering Web Application...")

    # Register blueprints
    from app.routes import dashboard, upload, preprocessing, clustering, evaluation, manual_calc, gis, interpretation, reports
    
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(upload.bp)
    app.register_blueprint(preprocessing.bp)
    app.register_blueprint(clustering.bp)
    app.register_blueprint(evaluation.bp)
    app.register_blueprint(manual_calc.bp)
    app.register_blueprint(gis.bp)
    app.register_blueprint(interpretation.bp)
    app.register_blueprint(reports.bp)

    # Context processors and custom filters for Jinja2
    @app.context_processor
    def inject_globals():
        from app.models.session_data import session_data
        return {
            "has_session_data": session_data.has_data(),
            "session_filename": session_data.filename,
            "session_n_clusters": session_data.n_clusters
        }

    @app.template_filter("format_value")
    def format_value(value):
        import math
        if value is None:
            return "-"
        if isinstance(value, float):
            if math.isnan(value):
                return "-"
            return f"{value:.2f}"
        return str(value)

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("errors/500.html"), 500

    logger.info("Flask application factory initialization complete.")
    return app
