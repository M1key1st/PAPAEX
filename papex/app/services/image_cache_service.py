"""TMDB posterlarini/backdrop'larini lokal static/cache papkasiga yuklab, keshlaydi.

Agar tarmoq mavjud bo'lmasa yoki yuklab olish muvaffaqiyatsiz tugasa, funksiya
None qaytaradi va chaqiruvchi kod TMDB'ning masofaviy URL'idan (yoki eski
emoji-fallback dizaynidan) foydalanishda davom etadi — sayt hech qachon
rasm sababli buzilmaydi.
"""

from pathlib import Path

import requests
from flask import current_app

from app.services import tmdb_service

TIMEOUT = 10


def _cache_dir(kind):
    sub = "posters" if kind == "poster" else "backdrops"
    path = Path(current_app.static_folder) / "cache" / sub
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_image(tmdb_path, tmdb_id, kind="poster", size="w500"):
    """Muvaffaqiyatli bo'lsa 'cache/posters/123.jpg' kabi static-relative yo'l qaytaradi."""
    if not tmdb_path or not current_app.config.get("IMAGE_CACHE_ENABLED"):
        return None

    ext = Path(tmdb_path).suffix or ".jpg"
    filename = f"{tmdb_id}{ext}"
    dest_dir = _cache_dir(kind)
    dest_path = dest_dir / filename

    if dest_path.exists():
        sub = "posters" if kind == "poster" else "backdrops"
        return f"cache/{sub}/{filename}"

    url = tmdb_service.image_url(tmdb_path, size=size)
    if not url:
        return None

    try:
        resp = requests.get(url, timeout=TIMEOUT, stream=True)
        if resp.status_code != 200:
            return None
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    except requests.RequestException:
        return None

    sub = "posters" if kind == "poster" else "backdrops"
    return f"cache/{sub}/{filename}"
