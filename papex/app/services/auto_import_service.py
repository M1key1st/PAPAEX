"""Avtomatik TMDB Import — har 6 soatda trending, popular, top rated, upcoming, TV, anime import."""

import logging
from datetime import datetime

from flask import current_app

from app.models.db import get_db
from app.services import genre_service, image_cache_service, tmdb_service
from app.utils.slugify import unique_slug

logger = logging.getLogger(__name__)

TMDB_SOURCES = {
    "trending": {"path": "/trending/movie/week", "category": "kino"},
    "popular": {"path": "/movie/popular", "category": "kino"},
    "top_rated": {"path": "/movie/top_rated", "category": "kino"},
    "upcoming": {"path": "/movie/upcoming", "category": "kino"},
    "tv": {"path": "/tv/popular", "category": "kino"},
    "anime": {"path": "/discover/tv", "category": "anime", "params": {"with_genres": "16"}},
}

TMDB_TV_CATEGORY_MAP = {
    16: "anime",
    35: "kino",
    18: "kino",
}


def _get_db():
    return get_db()


def _tmdb_get(path, params=None):
    """TMDB API'ga so'rov yuborish."""
    if not tmdb_service.is_enabled():
        return None
    params = dict(params or {})
    params["api_key"] = current_app.config["TMDB_API_KEY"]
    params.setdefault("language", current_app.config.get("TMDB_LANGUAGE", "en-US"))
    url = f"{current_app.config['TMDB_API_BASE']}{path}"
    import requests
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException as e:
        logger.error(f"TMDB request failed: {e}")
    return None


def _detect_category(genre_ids):
    """TMDB genre ID lariga qarab kategoriyani aniqlash."""
    if not genre_ids:
        return "kino"
    if 16 in genre_ids:
        return "anime"
    return "kino"


def _get_tmdb_movie_details(tmdb_id):
    """To'liq film ma'lumotlarini olish."""
    data = _tmdb_get(f"/movie/{tmdb_id}", {"append_to_response": "credits,videos,external_ids"})
    if not data:
        return None

    credits = data.get("credits") or {}
    cast = [
        {
            "name": c.get("name"),
            "character": c.get("character"),
            "profile_path": c.get("profile_path"),
        }
        for c in (credits.get("cast") or [])[:12]
    ]
    director = next(
        (c.get("name") for c in (credits.get("crew") or []) if c.get("job") == "Director"),
        None,
    )
    trailer_url = None
    for v in (data.get("videos") or {}).get("results", []):
        if v.get("site") == "YouTube" and v.get("type") == "Trailer":
            trailer_url = f"https://www.youtube.com/watch?v={v.get('key')}"
            break

    countries = data.get("production_countries") or []
    country = countries[0]["name"] if countries else None
    genres = [g["name"] for g in (data.get("genres") or [])]
    genre_tmdb_ids = [(g["name"], g["id"]) for g in (data.get("genres") or [])]

    return {
        "tmdb_id": data.get("id"),
        "imdb_id": (data.get("external_ids") or {}).get("imdb_id"),
        "name": data.get("title") or data.get("name"),
        "original_name": data.get("original_title") or data.get("original_name"),
        "summary": data.get("overview") or "",
        "tagline": data.get("tagline") or "",
        "year": int(data["release_date"][:4]) if data.get("release_date") else None,
        "release_date": data.get("release_date"),
        "runtime": data.get("runtime"),
        "country": country,
        "director": director,
        "poster_path": data.get("poster_path"),
        "backdrop_path": data.get("backdrop_path"),
        "trailer_url": trailer_url,
        "genres": genres,
        "genre_tmdb_ids": genre_tmdb_ids,
        "cast": cast,
        "vote_average": data.get("vote_average"),
    }


def _get_tmdb_tv_details(tmdb_id):
    """To'liq TV show ma'lumotlarini olish."""
    data = _tmdb_get(f"/tv/{tmdb_id}", {"append_to_response": "credits,videos,external_ids"})
    if not data:
        return None

    credits = data.get("credits") or {}
    cast = [
        {
            "name": c.get("name"),
            "character": c.get("character"),
            "profile_path": c.get("profile_path"),
        }
        for c in (credits.get("cast") or [])[:12]
    ]
    director = next(
        (c.get("name") for c in (credits.get("crew") or []) if c.get("job") == "Director"),
        None,
    )
    trailer_url = None
    for v in (data.get("videos") or {}).get("results", []):
        if v.get("site") == "YouTube" and v.get("type") == "Trailer":
            trailer_url = f"https://www.youtube.com/watch?v={v.get('key')}"
            break

    countries = data.get("production_countries") or []
    country = countries[0]["name"] if countries else None
    genres = [g["name"] for g in (data.get("genres") or [])]
    genre_tmdb_ids = [(g["name"], g["id"]) for g in (data.get("genres") or [])]
    genre_ids_raw = [g["id"] for g in (data.get("genres") or [])]

    name = data.get("name") or data.get("original_name")
    release_date = data.get("first_air_date") or ""
    year = int(release_date[:4]) if release_date else None

    return {
        "tmdb_id": data.get("id"),
        "imdb_id": (data.get("external_ids") or {}).get("imdb_id"),
        "name": name,
        "original_name": data.get("original_name"),
        "summary": data.get("overview") or "",
        "tagline": data.get("tagline") or "",
        "year": year,
        "release_date": release_date,
        "runtime": (data.get("episode_run_time") or [None])[0],
        "country": country,
        "director": director,
        "poster_path": data.get("poster_path"),
        "backdrop_path": data.get("backdrop_path"),
        "trailer_url": trailer_url,
        "genres": genres,
        "genre_tmdb_ids": genre_tmdb_ids,
        "category": _detect_category(genre_ids_raw),
        "cast": cast,
        "vote_average": data.get("vote_average"),
    }


def _create_title_from_tmdb(details):
    """TMDB ma'lumotlaridan yangi title yaratish."""
    db = _get_db()

    # Duplicate tekshirish
    existing = db.execute(
        "SELECT id FROM titles WHERE tmdb_id = ?", (details["tmdb_id"],)
    ).fetchone()
    if existing:
        return None, "duplicate"

    category = details.get("category", "kino")
    slug = unique_slug(db, details["name"], details.get("year"))

    db.execute(
        """INSERT INTO titles (tmdb_id, imdb_id, name, original_name, slug, category,
           summary, tagline, year, release_date, runtime, country, director,
           poster_path, backdrop_path, trailer_url, quality_score, quality_label, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'published')""",
        (
            details["tmdb_id"], details.get("imdb_id"), details["name"],
            details.get("original_name"), slug, category,
            details["summary"], details.get("tagline"), details.get("year"),
            details.get("release_date"), details.get("runtime"),
            details.get("country"), details.get("director"),
            details.get("poster_path"), details.get("backdrop_path"),
            details.get("trailer_url"),
            details.get("vote_average", 0) or 0,
            _quality_label(details.get("vote_average", 0)),
        ),
    )
    title_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.commit()

    # Poster va backdrop ni cache qilish
    poster_local = image_cache_service.cache_image(
        details.get("poster_path"), details["tmdb_id"], "poster"
    )
    backdrop_local = image_cache_service.cache_image(
        details.get("backdrop_path"), details["tmdb_id"], "backdrop", size="w1280"
    )
    if poster_local or backdrop_local:
        db.execute(
            "UPDATE titles SET poster_local=?, backdrop_local=? WHERE id=?",
            (poster_local, backdrop_local, title_id),
        )
        db.commit()

    # Genre larni qo'shish
    genre_ids = []
    for genre_name, tmdb_genre_id in details.get("genre_tmdb_ids", []):
        gid = genre_service.get_or_create_by_name(genre_name, tmdb_genre_id)
        genre_ids.append(gid)
    if genre_ids:
        genre_service.set_title_genres(title_id, genre_ids)

    # Cast ni qo'shish
    cast_list = [
        (c["name"], c.get("character"), c.get("profile_path"))
        for c in details.get("cast", []) if c.get("name")
    ]
    if cast_list:
        from app.services.title_service import set_cast
        set_cast(title_id, cast_list)

    return title_id, "created"


def _quality_label(score):
    if score >= 8:
        return "HD"
    elif score >= 6:
        return "SD"
    return "CAM"


def run_auto_import(source_key=None):
    """Asosiy import funksiyasi. source_key berilsa faqat shu source, aks holda hammasi."""
    if not tmdb_service.is_enabled():
        return {"error": "TMDB API key not configured"}

    db = _get_db()
    results = {}

    sources_to_run = {source_key: TMDB_SOURCES[source_key]} if source_key else TMDB_SOURCES

    for key, source in sources_to_run.items():
        params = source.get("params", {})
        data = _tmdb_get(source["path"], params)
        if not data:
            results[key] = {"found": 0, "added": 0, "skipped": 0, "errors": 0}
            continue

        items = data.get("results", [])
        found = len(items)
        added = 0
        skipped = 0
        errors = 0

        for item in items:
            tmdb_id = item.get("id")
            if not tmdb_id:
                continue

            try:
                # TV show uchun alohida detal olish
                if key == "tv" or (key == "anime" and item.get("media_type") == "tv"):
                    details = _get_tmdb_tv_details(tmdb_id)
                    if details and "category" not in details:
                        details["category"] = source.get("category", "kino")
                else:
                    details = _get_tmdb_movie_details(tmdb_id)

                if not details:
                    skipped += 1
                    continue

                title_id, status = _create_title_from_tmdb(details)
                if status == "created":
                    added += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"Import error for TMDB {tmdb_id}: {e}")
                errors += 1

        # Log yozish
        db.execute(
            """INSERT INTO auto_import_log (source, items_found, items_added, items_skipped, errors)
               VALUES (?, ?, ?, ?, ?)""",
            (key, found, added, skipped, errors),
        )
        db.commit()

        results[key] = {"found": found, "added": added, "skipped": skipped, "errors": errors}

    return results


def get_import_stats():
    """Oxirgi import statiskasini qaytarish."""
    db = _get_db()
    last_run = db.execute(
        "SELECT * FROM auto_import_log ORDER BY id DESC LIMIT 1"
    ).fetchone()

    today = datetime.now().strftime("%Y-%m-%d")
    today_stats = db.execute(
        """SELECT source, SUM(items_added) as total_added
           FROM auto_import_log WHERE date(run_at) = ?
           GROUP BY source""",
        (today,),
    ).fetchall()

    queue_pending = db.execute(
        "SELECT COUNT(*) FROM import_queue WHERE status = 'pending'"
    ).fetchone()[0]

    return {
        "last_run": dict(last_run) if last_run else None,
        "today_stats": [dict(r) for r in today_stats],
        "queue_pending": queue_pending,
    }


def get_import_log(page=1, per_page=20):
    """Import loglarini sahifalangan holda qaytarish."""
    from app.utils.pagination import paginate
    db = _get_db()
    base = "SELECT * FROM auto_import_log ORDER BY id DESC"
    count = "SELECT COUNT(*) FROM auto_import_log"
    return paginate(db, base, count, [], page, per_page)
