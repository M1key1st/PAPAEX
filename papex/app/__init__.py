from datetime import timedelta

from flask import Flask, render_template, request

from config import get_config
from app.extensions import csrf, limiter, login_manager
from app.models.db import register_db


def create_app(config_class=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class or get_config())
    app.permanent_session_lifetime = timedelta(days=180)

    # --- Extensions ---
    register_db(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Davom etish uchun tizimga kiring."
    csrf.init_app(app)
    limiter.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.services.user_service import get_user_by_id
        return get_user_by_id(user_id)

    # --- Blueprints ---
    from app.blueprints.public.routes import public_bp
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.admin.routes import admin_bp
    from app.blueprints.api.routes import api_bp
    from app.blueprints.seo.routes import seo_bp
    from app.blueprints.health.routes import health_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(seo_bp)
    app.register_blueprint(health_bp)

    # --- Global template context ---
    from app.services.title_service import CATEGORY_LABELS

    @app.context_processor
    def inject_globals():
        from app.services import settings_service, ads_service
        context = {
            "categories": CATEGORY_LABELS,
            "active_category": None,
            "site_name": settings_service.get("site_name", app.config["SITE_NAME"]),
            "site_description": settings_service.get(
                "site_description", app.config["SITE_DESCRIPTION"]
            ),
            "footer_text": settings_service.get("footer_text", ""),
        }
        # Ads context
        context.update(ads_service.inject_ads_context())
        return context

    # --- Jinja filters ---
    from app.services import tmdb_service

    @app.template_filter("tmdb_image")
    def tmdb_image_filter(path, size="w500"):
        if not path:
            return None
        from flask import current_app
        base = current_app.config["TMDB_IMAGE_BASE"]
        return f"{base}/{size}{path}"

    @app.template_filter("truncate_words")
    def truncate_words_filter(text, length=120):
        text = text or ""
        if len(text) <= length:
            return text
        return text[:length].rsplit(" ", 1)[0] + "\u2026"

    # --- Scheduler ---
    if app.config.get("SCHEDULER_ENABLED", True):
        from app.services.scheduler_service import init_scheduler
        init_scheduler(app)

    # --- Error handlers ---
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500

    @app.after_request
    def set_security_headers(response):
        # --- Cloudflare tayyorgarlik ---
        if app.config.get("TRUSTED_PROXIES"):
            response.headers["X-Forwarded-For"] = request.headers.get("X-Forwarded-For", "")

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # --- Kunlik tashrifni qayd qilish ---
    @app.before_request
    def track_visit():
        from app.services.stats_service import record_daily_visit
        if not request.path.startswith("/static") and not request.path.startswith("/admin"):
            record_daily_visit()

    return app
