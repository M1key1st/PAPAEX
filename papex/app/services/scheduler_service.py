"""APScheduler — avtomatik vazifalar: TMDB Import, Sitemap, Trending, Backup."""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _run_auto_import():
    """TMDB import ishga tushirish."""
    try:
        from app.services import auto_import_service
        results = auto_import_service.run_auto_import()
        logger.info(f"Auto import completed: {results}")
    except Exception as e:
        logger.error(f"Auto import error: {e}")


def _run_sitemap_update():
    """Sitemap yangilash."""
    try:
        from flask import current_app
        with current_app.app_context():
            from app.models.db import get_db
            db = get_db()
            # Sitemap avtomatik yangilanadi — faqat log yozish
            logger.info("Sitemap updated")
    except Exception as e:
        logger.error(f"Sitemap update error: {e}")


def _run_trending_calc():
    """Trending va popularity hisoblash."""
    try:
        from app.services import title_service
        db = title_service.get_db() if hasattr(title_service, 'get_db') else None
        if db:
            # Views count asosida trending hisoblash
            db.execute(
                """UPDATE titles SET is_trending = CASE
                   WHEN views_count > (SELECT AVG(views_count) * 2 FROM titles WHERE status='published')
                   THEN 1 ELSE 0
                   END"""
            )
            # Popularity hisoblash
            db.execute(
                """UPDATE titles SET popularity = (
                   views_count * 0.5 + likes_count * 10 + dislikes_count * 5
               ) WHERE status = 'published'"""
            )
            db.commit()
            logger.info("Trending and popularity calculated")
    except Exception as e:
        logger.error(f"Trending calculation error: {e}")


def _run_db_cleanup():
    """Eski ma'lumotlarni tozalash."""
    try:
        from app.models.db import get_db
        db = get_db()
        # 90 kundan eski view larni tozalash
        cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        db.execute("DELETE FROM views WHERE viewed_on < ?", (cutoff,))
        # 30 kundan eski import_queue larni tozalash
        db.execute(
            "DELETE FROM import_queue WHERE status = 'completed' AND processed_at < datetime('now', '-30 days')"
        )
        db.commit()
        logger.info("Database cleanup completed")
    except Exception as e:
        logger.error(f"DB cleanup error: {e}")


def _run_backup():
    """Avtomatik backup yaratish."""
    try:
        from app.services import backup_service
        result = backup_service.create_backup()
        logger.info(f"Backup created: {result}")
    except Exception as e:
        logger.error(f"Backup error: {e}")


def _run_article_generation():
    """Maqola generatsiya qilish."""
    try:
        from app.services import article_service
        results = article_service.generate_missing_articles()
        logger.info(f"Article generation: {results}")
    except Exception as e:
        logger.error(f"Article generation error: {e}")


def init_scheduler(app):
    """Scheduler ni ishga tushirish."""
    if not app.config.get("SCHEDULER_ENABLED", True):
        return

    scheduler.start()

    interval_hours = app.config.get("AUTO_IMPORT_INTERVAL_HOURS", 6)

    # Har 6 soatda TMDB Import
    scheduler.add_job(
        _run_auto_import,
        trigger=IntervalTrigger(hours=interval_hours),
        id="auto_import",
        name="TMDB Auto Import",
        replace_existing=True,
    )

    # Har 12 soatda Sitemap yangilash
    scheduler.add_job(
        _run_sitemap_update,
        trigger=IntervalTrigger(hours=12),
        id="sitemap_update",
        name="Sitemap Update",
        replace_existing=True,
    )

    # Har 24 soatda Trending hisoblash (tungi 2:00 da)
    scheduler.add_job(
        _run_trending_calc,
        trigger=CronTrigger(hour=2, minute=0),
        id="trending_calc",
        name="Trending Calculation",
        replace_existing=True,
    )

    # Har 24 soatda Database tozalash (tungi 3:00 da)
    scheduler.add_job(
        _run_db_cleanup,
        trigger=CronTrigger(hour=3, minute=0),
        id="db_cleanup",
        name="Database Cleanup",
        replace_existing=True,
    )

    # Har 24 soatda Backup (tungi 4:00 da)
    scheduler.add_job(
        _run_backup,
        trigger=CronTrigger(hour=4, minute=0),
        id="auto_backup",
        name="Auto Backup",
        replace_existing=True,
    )

    # Har 6 soatda Maqola generatsiya (import dan keyin)
    scheduler.add_job(
        _run_article_generation,
        trigger=IntervalTrigger(hours=interval_hours),
        id="article_generation",
        name="Article Generation",
        replace_existing=True,
    )

    logger.info("Scheduler started with all jobs")


def get_scheduler_status():
    """Scheduler holatini qaytarish."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
        })
    return {
        "running": scheduler.running,
        "jobs": jobs,
    }


def trigger_job(job_id):
    """Bir martalik ishga tushirish."""
    job = scheduler.get_job(job_id)
    if job:
        job.func()
        return True
    return False
