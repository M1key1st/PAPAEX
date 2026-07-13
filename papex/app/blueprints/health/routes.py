from flask import Blueprint, jsonify

from app.services import health_service

health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health():
    """Oddiy health check endpoint."""
    result = health_service.get_health()
    status_code = 200 if result["status"] == "healthy" else 503
    return jsonify(result), status_code


@health_bp.route("/status")
def status():
    """To'liq server holati (admin uchun)."""
    result = health_service.get_full_status()
    return jsonify(result)
