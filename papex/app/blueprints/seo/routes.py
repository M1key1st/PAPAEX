from flask import Blueprint, Response, current_app, render_template, request, url_for

from app.models.db import get_db
from app.services import sitemap_service

seo_bp = Blueprint("seo", __name__)


@seo_bp.route("/robots.txt")
def robots():
    site_url = current_app.config["SITE_URL"]
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /auth/",
        "Disallow: /api/",
        f"Sitemap: {site_url}{url_for('seo.sitemap')}",
    ]
    return Response("\n".join(lines), mimetype="text/plain")


@seo_bp.route("/sitemap.xml")
def sitemap():
    """Sitemap — avtomatik sitemap index yoki oddiy sitemap."""
    db = get_db()
    site_url = current_app.config["SITE_URL"]

    # Agar sitemap split kerak bo'lsa
    index_xml = sitemap_service.generate_sitemap_index()
    if index_xml:
        return Response(index_xml, mimetype="application/xml")

    # Oddiy sitemap
    titles = db.execute(
        "SELECT slug, updated_at FROM titles WHERE status = 'published' ORDER BY updated_at DESC"
    ).fetchall()

    static_urls = [
        {"loc": f"{site_url}{url_for('public.home')}", "changefreq": "hourly", "priority": "1.0"},
        {"loc": f"{site_url}{url_for('public.by_category', category='kino')}", "changefreq": "daily", "priority": "0.8"},
        {"loc": f"{site_url}{url_for('public.by_category', category='anime')}", "changefreq": "daily", "priority": "0.8"},
        {"loc": f"{site_url}{url_for('public.by_category', category='multfilm')}", "changefreq": "daily", "priority": "0.8"},
        {"loc": f"{site_url}{url_for('public.articles')}", "changefreq": "daily", "priority": "0.7"},
    ]
    title_urls = [
        {
            "loc": f"{site_url}{url_for('public.title_detail', slug=t['slug'])}",
            "lastmod": (t["updated_at"] or "")[:10],
            "changefreq": "weekly",
            "priority": "0.6",
        }
        for t in titles
    ]

    xml = render_template("sitemap.xml", static_urls=static_urls, title_urls=title_urls)
    return Response(xml, mimetype="application/xml")


@seo_bp.route("/sitemap-<int:part>.xml")
def sitemap_part(part):
    """Sitemap qismi (50000+ URL uchun)."""
    xml = sitemap_service.generate_split_sitemap(part)
    return Response(xml, mimetype="application/xml")


@seo_bp.route("/rss.xml")
def rss():
    db = get_db()
    titles = db.execute(
        "SELECT * FROM titles WHERE status = 'published' ORDER BY published_at DESC LIMIT 30"
    ).fetchall()
    site_url = current_app.config["SITE_URL"]
    xml = render_template("rss.xml", titles=titles, site_url=site_url)
    return Response(xml, mimetype="application/rss+xml")
