"""Analitika — dashboard statistikasi, kunlik/haftalik/oylik trafik."""

from datetime import datetime, timedelta

from app.models.db import get_db


def overview():
    db = get_db()
    total_titles = db.execute("SELECT COUNT(*) FROM titles").fetchone()[0]
    total_views = db.execute("SELECT COALESCE(SUM(views_count), 0) FROM titles").fetchone()[0]
    total_likes = db.execute("SELECT COALESCE(SUM(likes_count), 0) FROM titles").fetchone()[0]
    total_bookmarks = db.execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0]
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_articles = db.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    by_category = db.execute(
        "SELECT category, COUNT(*) AS c FROM titles GROUP BY category"
    ).fetchall()
    top_viewed = db.execute(
        "SELECT id, name, slug, views_count FROM titles ORDER BY views_count DESC LIMIT 5"
    ).fetchall()
    recent_titles = db.execute(
        "SELECT id, name, slug, category, published_at FROM titles ORDER BY id DESC LIMIT 5"
    ).fetchall()

    # Oxirgi import
    last_import = db.execute(
        "SELECT * FROM auto_import_log ORDER BY id DESC LIMIT 1"
    ).fetchone()

    return {
        "total_titles": total_titles,
        "total_views": total_views,
        "total_likes": total_likes,
        "total_bookmarks": total_bookmarks,
        "total_users": total_users,
        "total_articles": total_articles,
        "by_category": {r["category"]: r["c"] for r in by_category},
        "top_viewed": top_viewed,
        "recent_titles": recent_titles,
        "last_import": dict(last_import) if last_import else None,
    }


def get_daily_stats(days=30):
    """Kunlik trafik statistikasi."""
    db = get_db()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = db.execute(
        "SELECT * FROM daily_stats WHERE date >= ? ORDER BY date",
        (cutoff,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_weekly_stats():
    """Haftalik trafik statistikasi."""
    db = get_db()
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    rows = db.execute(
        """SELECT date, SUM(page_views) as page_views, SUM(unique_visitors) as unique_visitors
           FROM daily_stats WHERE date >= ?
           GROUP BY date ORDER BY date""",
        (cutoff,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_monthly_stats():
    """Oylik trafik statistikasi."""
    db = get_db()
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    rows = db.execute(
        """SELECT substr(date, 1, 7) as month,
                  SUM(page_views) as page_views,
                  SUM(unique_visitors) as unique_visitors,
                  SUM(new_titles) as new_titles,
                  SUM(new_articles) as new_articles
           FROM daily_stats WHERE date >= ?
           GROUP BY month ORDER BY month""",
        (cutoff,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_top_viewed_titles(limit=10):
    """Eng ko'p ko'rilgan kinolar."""
    db = get_db()
    return db.execute(
        """SELECT id, name, slug, category, views_count, likes_count
           FROM titles WHERE status = 'published'
           ORDER BY views_count DESC LIMIT ?""",
        (limit,),
    ).fetchall()


def get_top_articles(limit=10):
    """Eng ko'p o'qilgan maqolalar."""
    db = get_db()
    return db.execute(
        """SELECT articles.id, articles.title, articles.created_at,
                  titles.name as movie_name, titles.views_count
           FROM articles
           JOIN titles ON titles.id = articles.title_id
           WHERE articles.status = 'published'
           ORDER BY titles.views_count DESC LIMIT ?""",
        (limit,),
    ).fetchall()


def get_popular_genres(limit=10):
    """Eng mashhur janrlar."""
    db = get_db()
    return db.execute(
        """SELECT genres.name, genres.slug, COUNT(title_genres.title_id) as count
           FROM genres
           JOIN title_genres ON title_genres.genre_id = genres.id
           JOIN titles ON titles.id = title_genres.title_id
           WHERE titles.status = 'published'
           GROUP BY genres.id
           ORDER BY count DESC LIMIT ?""",
        (limit,),
    ).fetchall()


def record_daily_visit():
    """Kunlik tashrifni qayd qilish."""
    db = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        db.execute(
            """INSERT INTO daily_stats (date, page_views, unique_visitors)
               VALUES (?, 1, 1)
               ON CONFLICT(date) DO UPDATE SET
               page_views = page_views + 1,
               unique_visitors = unique_visitors + 1""",
            (today,),
        )
        db.commit()
    except Exception:
        pass
