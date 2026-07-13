"""AI News Engine — har bir import qilingan kino uchun avtomatik maqola generatsiya qilish.

AI Cost Protection:
- Bir kontent qayta generatsiya qilinmasin
- Cache ishlatilsin
- Limitlar bo'lsin
"""

import hashlib
import json
import logging

from flask import current_app

from app.models.db import get_db
from app.services import ai_service
from app.utils.pagination import paginate

logger = logging.getLogger(__name__)


def _cache_key(title_id):
    """Cache uchun kalit yaratish."""
    return f"article_{title_id}"


def _check_cache(title_id):
    """Cache dan tekshirish — allaqachon generatsiya qilinganmi?"""
    db = get_db()
    cached = db.execute(
        "SELECT value FROM settings WHERE key = ?", (_cache_key(title_id),)
    ).fetchone()
    return cached is not None


def _set_cache(title_id, article_id):
    """Cache ga saqlash."""
    from app.services.settings_service import set_many
    set_many({_cache_key(title_id): str(article_id)})


def _check_daily_limit():
    """Kunlik AI generatsiya limitini tekshirish."""
    from datetime import datetime
    db = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    today_count = db.execute(
        """SELECT COUNT(*) FROM articles
           WHERE date(created_at) = ?""",
        (today,),
    ).fetchone()[0]
    max_daily = current_app.config.get("AI_DAILY_LIMIT", 50)
    return today_count < max_daily


def generate_article_for_title(title_id):
    """Bir title uchun AI maqola generatsiya qilish.

    AI Cost Protection:
    1. Cache tekshirish — allaqachon bo'lsa, qaytarish
    2. Kunlik limit tekshirish
    3. AI ishlamasa fallback maqola
    """
    db = get_db()
    title = db.execute("SELECT * FROM titles WHERE id = ?", (title_id,)).fetchone()
    if not title:
        return None, "Title not found"

    # Cache tekshirish
    if _check_cache(title_id):
        return None, "Article already exists (cached)"

    # Kunlik limit tekshirish
    if not _check_daily_limit():
        return None, "Daily AI limit reached"

    # AI generatsiya
    genres = db.execute(
        """SELECT genres.name FROM genres
           JOIN title_genres ON title_genres.genre_id = genres.id
           WHERE title_genres.title_id = ?""",
        (title_id,),
    ).fetchall()
    genre_names = ", ".join(g["name"] for g in genres)

    cast = db.execute(
        "SELECT actor_name, character_name FROM title_cast WHERE title_id = ? ORDER BY sort_order",
        (title_id,),
    ).fetchall()
    cast_text = ", ".join(f"{c['actor_name']} ({c['character_name']})" for c in cast if c["actor_name"])

    # AI ga so'rov
    if ai_service.is_enabled():
        system_prompt = """Sen professional kino yangiliklari muharririsan. O'zbek tilida kino maqolalar yozasan.
Maqola qiziqarli, professional va kino yangiliklari saytiga mos bo'lishi kerak.
TMDB tavsifini nusxalamasliging kerak — o'zing qayta yoz.
Matn kino yangiliklari saytiga mos bo'lsin."""

        _or = "yoki"
        _yoq = "Yo'q"
        _nomalum = "Noma'lum"
        _orig_name = title['original_name'] or _yoq
        _year = title['year'] or _nomalum
        _country = title['country'] or _nomalum
        _director = title['director'] or _nomalum
        _cast = cast_text or _nomalum

        prompt = f"""Quyidagi kino/serial haqida professional maqola yoz:

Nomi: {title['name']}
Asl nomi: {_orig_name}
Janr: {genre_names}
Yil: {_year}
Davlat: {_country}
Rejissyor: {_director}
Aktyorlar: {_cast}
Tavsif: {title['summary']}

Quyidagi formatda yoz:
1. TITLE: Maqola sarlavhasi (kino nomi + qo'shimcha)
2. SUMMARY: Qisqa tavsif (1-2 jumlа)
3. CONTENT: To'liq maqola (300-500 so'z)
4. SEO: SEO tavsif (160 belgi)
5. TELEGRAM: Telegram post matni (qisqa va jozibali)

Har bir bo'limni "---" bilan ajrating."""

        result = ai_service.generate_text(prompt, system_prompt)
    else:
        result = None

    # AI ishlamasa — fallback maqola
    if not result:
        result = _generate_fallback_article(title, genre_names, cast_text)

    # Natijani parse qilish
    sections = result.split("---")
    title_text = sections[0].strip() if len(sections) > 0 else title["name"]
    summary = sections[1].strip() if len(sections) > 1 else title["summary"][:200]
    content = sections[2].strip() if len(sections) > 2 else ""
    seo_desc = sections[3].strip() if len(sections) > 3 else ""
    telegram_text = sections[4].strip() if len(sections) > 4 else ""

    # Title prefix ni tozalash
    for prefix in ["TITLE:", "Sarlavha:", "Sarlavha"]:
        if title_text.startswith(prefix):
            title_text = title_text[len(prefix):].strip()

    db.execute(
        """INSERT INTO articles (title_id, title, summary, content, seo_description, telegram_text, status)
           VALUES (?, ?, ?, ?, ?, ?, 'draft')""",
        (title_id, title_text, summary, content, seo_desc, telegram_text),
    )
    db.commit()

    article_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Cache ga saqlash
    _set_cache(title_id, article_id)

    return article_id, "created"


def _generate_fallback_article(title, genre_names, cast_text):
    """AI ishlamaganida fallback maqola yaratish."""
    name = title["name"]
    year = title["year"] or ""
    country = title["country"] or ""
    director = title["director"] or ""
    summary = title["summary"] or ""

    _nomalum = "Noma'lum"
    _dir_fallback = director or _nomalum
    _cast_fallback = cast_text or _nomalum

    title_text = f"{name} — {year} yilgi kino haqida"

    summary_text = f"{name} — {year} yili {country}da suratga olingan {genre_names} janridagi kino."

    content = f"""{name} — {year} yili {country}da suratga olingan {genre_names} janridagi kino.

Rejissyor: {_dir_fallback}
Aktyorlar: {_cast_fallback}

{summary}

Bu kino tomosha qilishga arziydigan {genre_names} janridagi yaxshi asardir."""

    seo_desc = f"{name} ({year}) — {genre_names} janridagi kino. Rejissyor: {_dir_fallback}. Batafsil ma'lumot PAPEX saytida."

    telegram_text = f"🎬 {name} ({year})\n\n{summary[:200]}...\n\nBatafsil: https://papex.uz/movie/{title['slug']}"

    return f"{title_text}---{summary_text}---{content}---{seo_desc}---{telegram_text}"


def generate_missing_articles():
    """Maqolasi yo'q barcha title lar uchun maqola generatsiya qilish."""
    db = get_db()
    titles_without_articles = db.execute(
        """SELECT titles.id FROM titles
           LEFT JOIN articles ON articles.title_id = titles.id
           WHERE articles.id IS NULL AND titles.status = 'published'
           LIMIT 10"""
    ).fetchall()

    results = {"generated": 0, "failed": 0, "skipped": 0}
    for row in titles_without_articles:
        article_id, status = generate_article_for_title(row["id"])
        if status == "created":
            results["generated"] += 1
        elif "already exists" in status or "limit" in status:
            results["skipped"] += 1
        else:
            results["failed"] += 1

    return results


def list_articles(page=1, per_page=20, status=None):
    """Maqolalar ro'yxatini sahifalangan holda qaytarish."""
    db = get_db()
    where = ["1=1"]
    params = []
    if status:
        where.append("articles.status = ?")
        params.append(status)
    where_sql = " AND ".join(where)

    base = f"""SELECT articles.*, titles.name as movie_name, titles.slug as movie_slug
               FROM articles
               JOIN titles ON titles.id = articles.title_id
               WHERE {where_sql}
               ORDER BY articles.created_at DESC"""
    count = f"SELECT COUNT(*) FROM articles WHERE {where_sql}"
    return paginate(db, base, count, params, page, per_page)


def get_article(article_id):
    db = get_db()
    return db.execute(
        """SELECT articles.*, titles.name as movie_name, titles.slug as movie_slug
           FROM articles
           JOIN titles ON titles.id = articles.title_id
           WHERE articles.id = ?""",
        (article_id,),
    ).fetchone()


def get_article_by_title_id(title_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM articles WHERE title_id = ?", (title_id,)
    ).fetchone()


def update_article(article_id, data):
    db = get_db()
    db.execute(
        """UPDATE articles SET title=?, summary=?, content=?, seo_description=?,
           telegram_text=?, status=?, updated_at=datetime('now')
           WHERE id=?""",
        (
            data.get("title", ""),
            data.get("summary", ""),
            data.get("content", ""),
            data.get("seo_description", ""),
            data.get("telegram_text", ""),
            data.get("status", "draft"),
            article_id,
        ),
    )
    db.commit()


def delete_article(article_id):
    db = get_db()
    db.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    db.commit()


def regenerate_article(article_id):
    """Mavjud maqolani qayta generatsiya qilish (cache ni ham yangilash)."""
    db = get_db()
    article = db.execute("SELECT title_id FROM articles WHERE id = ?", (article_id,)).fetchone()
    if not article:
        return None, "Article not found"

    # Cache ni tozalash
    from app.services.settings_service import set_many
    set_many({f"article_{article['title_id']}": ""})

    db.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    db.commit()

    return generate_article_for_title(article["title_id"])


def publish_article(article_id):
    db = get_db()
    db.execute(
        "UPDATE articles SET status='published', updated_at=datetime('now') WHERE id=?",
        (article_id,),
    )
    db.commit()


def get_published_articles(limit=20):
    db = get_db()
    return db.execute(
        """SELECT articles.*, titles.name as movie_name, titles.slug as movie_slug
           FROM articles
           JOIN titles ON titles.id = articles.title_id
           WHERE articles.status = 'published'
           ORDER BY articles.created_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()


def article_count():
    db = get_db()
    return db.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
