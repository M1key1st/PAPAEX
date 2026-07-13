"""Sitemap Auto Split — 50000+ URL uchun sitemap index yaratish."""

from flask import current_app, url_for

from app.models.db import get_db


SITEMAP_LIMIT = 50000


def generate_sitemap_index():
    """Agar URL soni 50000+ bo'lsa, sitemap index yaratish."""
    db = get_db()
    total_urls = db.execute(
        "SELECT COUNT(*) FROM titles WHERE status = 'published'"
    ).fetchone()[0]

    # Static URLs qo'shish
    total_urls += 10  # home, categories, etc.

    if total_urls <= SITEMAP_LIMIT:
        return None  # Oddiy sitemap yetarli

    # Sitemap index yaratish
    return _build_sitemap_index(total_urls)


def _build_sitemap_index(total_urls):
    """Sitemap index XML yaratish."""
    import math
    from datetime import datetime

    num_sitemaps = math.ceil(total_urls / SITEMAP_LIMIT)
    site_url = current_app.config["SITE_URL"]

    sitemaps = []
    for i in range(1, num_sitemaps + 1):
        sitemaps.append({
            "loc": f"{site_url}/sitemap-{i}.xml",
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
        })

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for sitemap in sitemaps:
        xml += f'  <sitemap>\n'
        xml += f'    <loc>{sitemap["loc"]}</loc>\n'
        xml += f'    <lastmod>{sitemap["lastmod"]}</lastmod>\n'
        xml += f'  </sitemap>\n'
    xml += '</sitemapindex>'

    return xml


def generate_split_sitemap(part_number):
    """Bir qism sitemap yaratish."""
    db = get_db()
    site_url = current_app.config["SITE_URL"]
    offset = (part_number - 1) * SITEMAP_LIMIT

    # Titles
    titles = db.execute(
        """SELECT slug, updated_at FROM titles
           WHERE status = 'published'
           ORDER BY updated_at DESC
           LIMIT ? OFFSET ?""",
        (SITEMAP_LIMIT, offset),
    ).fetchall()

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    # Static URLs (faqat birinchi qismda)
    if part_number == 1:
        static_urls = [
            {"loc": f"{site_url}/", "changefreq": "hourly", "priority": "1.0"},
            {"loc": f"{site_url}/turkum/kino", "changefreq": "daily", "priority": "0.8"},
            {"loc": f"{site_url}/turkum/anime", "changefreq": "daily", "priority": "0.8"},
            {"loc": f"{site_url}/turkum/multfilm", "changefreq": "daily", "priority": "0.8"},
            {"loc": f"{site_url}/qidiruv", "changefreq": "weekly", "priority": "0.5"},
            {"loc": f"{site_url}/maqolalar", "changefreq": "daily", "priority": "0.7"},
        ]
        for url in static_urls:
            xml += f'  <url>\n'
            xml += f'    <loc>{url["loc"]}</loc>\n'
            xml += f'    <changefreq>{url["changefreq"]}</changefreq>\n'
            xml += f'    <priority>{url["priority"]}</priority>\n'
            xml += f'  </url>\n'

    # Title URLs
    for title in titles:
        lastmod = (title["updated_at"] or "")[:10]
        xml += f'  <url>\n'
        xml += f'    <loc>{site_url}/movie/{title["slug"]}</loc>\n'
        if lastmod:
            xml += f'    <lastmod>{lastmod}</lastmod>\n'
        xml += f'    <changefreq>weekly</changefreq>\n'
        xml += f'    <priority>0.6</priority>\n'
        xml += f'  </url>\n'

    xml += '</urlset>'
    return xml


def get_sitemap_info():
    """Sitemap haqida ma'lumot."""
    db = get_db()
    total_titles = db.execute(
        "SELECT COUNT(*) FROM titles WHERE status = 'published'"
    ).fetchone()[0]

    total_urls = total_titles + 10
    needs_split = total_urls > SITEMAP_LIMIT
    num_parts = (total_urls // SITEMAP_LIMIT) + 1 if needs_split else 1

    return {
        "total_titles": total_titles,
        "total_urls": total_urls,
        "needs_split": needs_split,
        "num_parts": num_parts,
    }
