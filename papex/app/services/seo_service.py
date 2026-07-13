"""SEO — JSON-LD, Meta Description, Canonical URL, Open Graph."""

import json

from flask import current_app, url_for

from app.services import tmdb_service


def movie_json_ld(title, genres, cast):
    site_url = current_app.config["SITE_URL"]
    data = {
        "@context": "https://schema.org",
        "@type": "Movie",
        "name": title["name"],
        "description": (title["summary"] or "")[:500],
        "url": f"{site_url}{url_for('public.title_detail', slug=title['slug'])}",
        "genre": [g["name"] for g in genres],
        "datePublished": title["release_date"] or "",
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": title["quality_score"],
            "bestRating": "10",
            "worstRating": "0",
            "ratingCount": max(title["likes_count"] + title["dislikes_count"], 1),
        },
    }
    if title["poster_local"]:
        data["image"] = f"{site_url}/static/{title['poster_local']}"
    elif title["poster_path"]:
        data["image"] = tmdb_service.image_url(title["poster_path"], size="w780")

    if title["director"]:
        data["director"] = {"@type": "Person", "name": title["director"]}
    if cast:
        data["actor"] = [{"@type": "Person", "name": c["actor_name"]} for c in cast[:8]]
    if title["runtime"]:
        data["duration"] = f"PT{title['runtime']}M"
    if title["imdb_id"]:
        data["sameAs"] = f"https://www.imdb.com/title/{title['imdb_id']}/"

    return json.dumps(data, ensure_ascii=False)


def meta_description(text, max_length=160):
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rsplit(" ", 1)[0] + "\u2026"


def canonical_url(path):
    site_url = current_app.config["SITE_URL"]
    return f"{site_url}{path}"


def generate_og_tags(title, genres=None, article=None):
    """Open Graph meta teglarini generatsiya qilish."""
    site_url = current_app.config["SITE_URL"]
    site_name = current_app.config.get("SITE_NAME", "PAPEX")

    og = {
        "og:site_name": site_name,
        "og:locale": "uz_UZ",
        "og:type": "website",
    }

    if title:
        og["og:title"] = title["name"]
        og["og:description"] = meta_description(title["summary"], 200)
        og["og:url"] = f"{site_url}{url_for('public.title_detail', slug=title['slug'])}"
        og["og:type"] = "article"

        if title["poster_local"]:
            og["og:image"] = f"{site_url}/static/{title['poster_local']}"
        elif title["poster_path"]:
            og["og:image"] = tmdb_service.image_url(title["poster_path"], size="w780")

        if title.get("backdrop_local"):
            og["og:image:width"] = "1280"
            og["og:image:height"] = "720"

        if genres:
            og["article:section"] = genres[0]["name"] if genres else ""

        if title.get("release_date"):
            og["article:published_time"] = title["release_date"]

        # Twitter Card
        og["twitter:card"] = "summary_large_image"
        og["twitter:title"] = title["name"]
        og["twitter:description"] = meta_description(title["summary"], 200)
        if og.get("og:image"):
            og["twitter:image"] = og["og:image"]

    elif article:
        og["og:title"] = article.get("title", "")
        og["og:description"] = meta_description(article.get("summary", ""), 200)
        og["og:type"] = "article"

        if article.get("content"):
            # Rasmlarni topish
            import re
            images = re.findall(r'!\[.*?\]\((.*?)\)', article["content"])
            if images:
                og["og:image"] = images[0]

    else:
        og["og:title"] = site_name
        og["og:description"] = current_app.config.get("SITE_DESCRIPTION", "")
        og["og:url"] = site_url

    return og


def generate_meta_tags(title=None, article=None, page_title=None, description=None):
    """To'liq meta teglarini generatsiya qilish."""
    site_name = current_app.config.get("SITE_NAME", "PAPEX")

    meta = {
        "title": page_title or (title["name"] if title else site_name),
        "description": description or (meta_description(title["summary"]) if title else current_app.config.get("SITE_DESCRIPTION", "")),
        "canonical": None,
        "og": {},
    }

    if title:
        meta["canonical"] = canonical_url(url_for("public.title_detail", slug=title["slug"]))
        meta["og"] = generate_og_tags(title)
    elif article:
        meta["og"] = generate_og_tags(article=article)
    else:
        meta["og"] = generate_og_tags(None)

    return meta
