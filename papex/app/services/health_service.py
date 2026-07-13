"""Server holatini tekshirish — /health va /status endpointlari."""

import sqlite3
from datetime import datetime
from pathlib import Path

from flask import current_app

from app.models.db import get_db


def check_database():
    """Database ishlashini tekshirish."""
    try:
        db = get_db()
        db.execute("SELECT 1")
        return {"status": "ok", "message": "Database is running"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_scheduler():
    """Scheduler ishlashini tekshirish."""
    try:
        from app.services.scheduler_service import get_scheduler_status
        status = get_scheduler_status()
        return {
            "status": "ok" if status["running"] else "warning",
            "message": f"Scheduler is {'running' if status['running'] else 'stopped'}",
            "jobs": len(status.get("jobs", [])),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_tmdb():
    """TMDB API ishlashini tekshirish."""
    try:
        from app.services import tmdb_service
        enabled = tmdb_service.is_enabled()
        if not enabled:
            return {"status": "disabled", "message": "TMDB API not configured"}
        return {"status": "ok", "message": "TMDB API configured"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_cache():
    """Image cache holatini tekshirish."""
    try:
        cache_dir = Path(current_app.static_folder) / "cache"
        posters = list((cache_dir / "posters").glob("*.jpg")) if (cache_dir / "posters").exists() else []
        backdrops = list((cache_dir / "backdrops").glob("*.jpg")) if (cache_dir / "backdrops").exists() else []
        return {
            "status": "ok",
            "message": f"Cache: {len(posters)} posters, {len(backdrops)} backdrops",
            "posters": len(posters),
            "backdrops": len(backdrops),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_full_status():
    """To'liq server holati."""
    db = get_db()
    total_titles = db.execute("SELECT COUNT(*) FROM titles").fetchone()[0]
    total_articles = db.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    return {
        "timestamp": datetime.now().isoformat(),
        "database": check_database(),
        "scheduler": check_scheduler(),
        "tmdb": check_tmdb(),
        "cache": check_cache(),
        "stats": {
            "total_titles": total_titles,
            "total_articles": total_articles,
            "total_users": total_users,
        },
    }


def get_health():
    """Oddiy health check."""
    try:
        db = get_db()
        db.execute("SELECT 1")
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "timestamp": datetime.now().isoformat()}
