"""TMDB (The Movie Database) integratsiyasi.

Admin faqat kino/anime/multfilm nomini kiritadi — qolgan barcha maydonlar
(poster, backdrop, tavsif, janrlar, aktyorlar, rejissyor, treyler, davomiyligi,
mamlakat, chiqarilgan sana, TMDB ID, IMDb ID) shu servis orqali avtomatik olinadi.

TMDB_API_KEY o'rnatilmagan bo'lsa, barcha funksiyalar xatosiz bo'sh natija
qaytaradi — admin panel bu holatda oddiy qo'lda-kiritish rejimida ishlayveradi.
"""

import requests
from flask import current_app

TIMEOUT = 8


def is_enabled():
    return bool(current_app.config.get("TMDB_API_KEY"))


def _get(path, params=None):
    if not is_enabled():
        return None
    params = dict(params or {})
    params["api_key"] = current_app.config["TMDB_API_KEY"]
    params.setdefault("language", current_app.config.get("TMDB_LANGUAGE", "uz-UZ"))
    url = f"{current_app.config['TMDB_API_BASE']}{path}"
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            # uz-UZ tarjimasi bo'sh bo'lsa (TMDB'da ko'p unvonlar tarjima qilinmagan),
            # ingliz tilida qayta so'raymiz.
            if path.startswith("/movie/") and not data.get("overview"):
                params["language"] = current_app.config["TMDB_FALLBACK_LANGUAGE"]
                resp2 = requests.get(url, params=params, timeout=TIMEOUT)
                if resp2.status_code == 200:
                    return resp2.json()
            return data
        return None
    except requests.RequestException:
        return None


def search_movie(query, year=None):
    """Nom bo'yicha qidiradi, natijalar ro'yxatini qaytaradi (admin tanlashi uchun)."""
    if not is_enabled():
        return []
    params = {"query": query}
    if year:
        params["year"] = year
    data = _get("/search/movie", params)
    if not data:
        return []
    return data.get("results", [])[:10]


def get_movie_details(tmdb_id):
    """To'liq film ma'lumotlarini (credits, videos bilan birga) qaytaradi."""
    if not is_enabled():
        return None
    data = _get(f"/movie/{tmdb_id}", {"append_to_response": "credits,videos,external_ids"})
    if not data:
        return None
    return _normalize_movie(data)


def _normalize_movie(data):
    credits = data.get("credits", {}) or {}
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
    for v in (data.get("videos", {}) or {}).get("results", []):
        if v.get("site") == "YouTube" and v.get("type") == "Trailer":
            trailer_url = f"https://www.youtube.com/watch?v={v.get('key')}"
            break

    countries = data.get("production_countries") or []
    country = countries[0]["name"] if countries else None

    genres = [g["name"] for g in (data.get("genres") or [])]
    genre_tmdb_ids = [(g["name"], g["id"]) for g in (data.get("genres") or [])]

    return {
        "tmdb_id": data.get("id"),
        "imdb_id": (data.get("external_ids") or {}).get("imdb_id") or data.get("imdb_id"),
        "name": data.get("title"),
        "original_name": data.get("original_title"),
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


def image_url(path, size="w500"):
    if not path:
        return None
    base = current_app.config["TMDB_IMAGE_BASE"]
    return f"{base}/{size}{path}"
