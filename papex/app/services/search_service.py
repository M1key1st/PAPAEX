"""Kuchaytirilgan qidiruv — SQLite FTS5 full-text search."""

from app.models.db import get_db
from app.utils.pagination import paginate


def _has_fts():
    """FTS5 mavjudligini tekshirish."""
    try:
        db = get_db()
        db.execute("SELECT * FROM titles_fts LIMIT 1")
        return True
    except Exception:
        return False


def search(q="", genre=None, actor=None, director=None, country=None,
           year=None, category=None, page=1, per_page=24):
    db = get_db()

    # Agar FTS5 mavjud bo'lsa va qidiruv so'zi bo'lsa, FTS ishlat
    if q and _has_fts():
        return _search_fts(q, genre=genre, actor=actor, director=director,
                          country=country, year=year, category=category,
                          page=page, per_page=per_page)

    # Oddiy LIKE qidiruv (fallback)
    return _search_like(q, genre=genre, actor=actor, director=director,
                       country=country, year=year, category=category,
                       page=page, per_page=per_page)


def _search_fts(q, genre=None, actor=None, director=None, country=None,
                year=None, category=None, page=1, per_page=24):
    """FTS5 full-text search."""
    db = get_db()

    joins = ""
    where = ["titles.status = 'published'"]
    params = []

    # FTS qidiruv
    fts_query = _build_fts_query(q)
    where.append("titles.id IN (SELECT rowid FROM titles_fts WHERE titles_fts MATCH ?)")
    params.append(fts_query)

    if genre:
        joins += " JOIN title_genres ON title_genres.title_id = titles.id JOIN genres ON genres.id = title_genres.genre_id"
        where.append("genres.slug = ?")
        params.append(genre)

    if actor:
        joins += " JOIN title_cast ON title_cast.title_id = titles.id"
        where.append("title_cast.actor_name LIKE ?")
        params.append(f"%{actor}%")

    if director:
        where.append("titles.director LIKE ?")
        params.append(f"%{director}%")

    if country:
        where.append("titles.country LIKE ?")
        params.append(f"%{country}%")

    if year:
        where.append("titles.year = ?")
        params.append(year)

    if category:
        where.append("titles.category = ?")
        params.append(category)

    where_sql = " AND ".join(where)
    base = f"SELECT DISTINCT titles.* FROM titles{joins} WHERE {where_sql} ORDER BY titles.published_at DESC"
    count = f"SELECT COUNT(DISTINCT titles.id) FROM titles{joins} WHERE {where_sql}"
    return paginate(db, base, count, params, page, per_page)


def _build_fts_query(q):
    """FTS5 query qurish — bir nechta so'z bo'lsa OR bilan bog'lash."""
    words = q.strip().split()
    if len(words) == 1:
        return f'"{words[0]}"'
    return " OR ".join(f'"{w}"' for w in words)


def _search_like(q, genre=None, actor=None, director=None, country=None,
                  year=None, category=None, page=1, per_page=24):
    """Oddiy LIKE qidiruv (FTS5 mavjud bo'lmasa)."""
    db = get_db()

    joins = ""
    where = ["titles.status = 'published'"]
    params = []

    if q:
        like = f"%{q}%"
        where.append(
            "(titles.name LIKE ? OR titles.original_name LIKE ? OR titles.summary LIKE ?)"
        )
        params.extend([like, like, like])

    if genre:
        joins += " JOIN title_genres ON title_genres.title_id = titles.id JOIN genres ON genres.id = title_genres.genre_id"
        where.append("genres.slug = ?")
        params.append(genre)

    if actor:
        joins += " JOIN title_cast ON title_cast.title_id = titles.id"
        where.append("title_cast.actor_name LIKE ?")
        params.append(f"%{actor}%")

    if director:
        where.append("titles.director LIKE ?")
        params.append(f"%{director}%")

    if country:
        where.append("titles.country LIKE ?")
        params.append(f"%{country}%")

    if year:
        where.append("titles.year = ?")
        params.append(year)

    if category:
        where.append("titles.category = ?")
        params.append(category)

    where_sql = " AND ".join(where)
    base = f"SELECT DISTINCT titles.* FROM titles{joins} WHERE {where_sql} ORDER BY titles.published_at DESC"
    count = f"SELECT COUNT(DISTINCT titles.id) FROM titles{joins} WHERE {where_sql}"
    return paginate(db, base, count, params, page, per_page)


def available_countries():
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT country FROM titles WHERE country IS NOT NULL AND country != '' ORDER BY country"
    ).fetchall()
    return [r["country"] for r in rows]


def available_years():
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT year FROM titles WHERE year IS NOT NULL ORDER BY year DESC"
    ).fetchall()
    return [r["year"] for r in rows]
