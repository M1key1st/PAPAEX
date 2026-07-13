from datetime import date

from flask import Blueprint, abort, redirect, render_template, request, url_for

from app.services import article_service, genre_service, interaction_service, search_service, seo_service, title_service
from app.utils.security import get_client_ip, get_voter_key, hash_ip

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def home():
    sections = {
        "trend": title_service.trending(limit=10),
        "yangi": title_service.newest(limit=10),
        "top": title_service.top_rated(limit=10),
        "kino": title_service.by_category_preview("kino", limit=10),
        "anime": title_service.by_category_preview("anime", limit=10),
        "multfilm": title_service.by_category_preview("multfilm", limit=10),
    }
    recent_articles = article_service.get_published_articles(limit=5)
    og = seo_service.generate_og_tags(None)
    return render_template("index.html", sections=sections, is_home=True,
                          recent_articles=recent_articles, og=og)


@public_bp.route("/turkum/<category>")
def by_category(category):
    if category not in title_service.CATEGORY_LABELS:
        abort(404)
    page = request.args.get("page", 1, type=int)
    from flask import current_app
    per_page = current_app.config["PAGE_SIZE"]
    pagination = title_service.by_category_page(category, page, per_page)
    return render_template(
        "category.html", pagination=pagination, active_category=category
    )


@public_bp.route("/qidiruv")
def search():
    q = request.args.get("q", "").strip()
    genre = request.args.get("genre", "").strip() or None
    actor = request.args.get("actor", "").strip() or None
    director = request.args.get("director", "").strip() or None
    country = request.args.get("country", "").strip() or None
    year = request.args.get("year", type=int)
    category = request.args.get("category", "").strip() or None
    page = request.args.get("page", 1, type=int)

    from flask import current_app
    per_page = current_app.config["PAGE_SIZE"]

    has_filters = any([q, genre, actor, director, country, year, category])
    pagination = None
    if has_filters:
        pagination = search_service.search(
            q=q, genre=genre, actor=actor, director=director, country=country,
            year=year, category=category, page=page, per_page=per_page,
        )

    return render_template(
        "search.html",
        pagination=pagination,
        search_query=q,
        filters={
            "genre": genre, "actor": actor, "director": director,
            "country": country, "year": year, "category": category,
        },
        all_genres=genre_service.list_genres(),
        all_countries=search_service.available_countries(),
        all_years=search_service.available_years(),
    )


@public_bp.route("/movie/<slug>")
def title_detail(slug):
    title = title_service.get_by_slug(slug)
    if title is None:
        abort(404)

    voter_key = get_voter_key()
    ip_hash = hash_ip(get_client_ip())
    title_service.record_daily_view(title["id"], voter_key, ip_hash, date.today().isoformat())
    interaction_service.push_recently_viewed(title["id"])

    genres = genre_service.genres_for_title(title["id"])
    cast = title_service.get_cast(title["id"])
    links = title_service.get_watch_links(title["id"])
    related = title_service.related_titles(title, limit=6)
    recently_viewed = interaction_service.get_recently_viewed(exclude_id=title["id"], limit=8)
    article = article_service.get_article_by_title_id(title["id"])

    og = seo_service.generate_og_tags(title, genres)

    return render_template(
        "detail.html",
        title=title,
        genres=genres,
        cast=cast,
        links=links,
        related=related,
        recently_viewed=recently_viewed,
        user_vote=interaction_service.get_user_vote(title["id"], voter_key),
        is_bookmarked=interaction_service.is_bookmarked(title["id"], voter_key),
        json_ld=seo_service.movie_json_ld(title, genres, cast),
        meta_description=seo_service.meta_description(title["summary"]),
        canonical=seo_service.canonical_url(url_for("public.title_detail", slug=title["slug"])),
        article=article,
        og=og,
    )


@public_bp.route("/nom/<int:title_id>")
def legacy_title_redirect(title_id):
    """Eski (/nom/<id>) havolalarni yangi SEO-slug URL'iga qayta yo'naltiradi."""
    title = title_service.get_by_id(title_id)
    if title is None:
        abort(404)
    return redirect(url_for("public.title_detail", slug=title["slug"]), code=301)


@public_bp.route("/bookmarklarim")
def my_bookmarks():
    voter_key = get_voter_key()
    titles = interaction_service.list_bookmarks(voter_key)
    return render_template("bookmarks.html", titles=titles)


# --- Maqolalar ---

@public_bp.route("/maqolalar")
def articles():
    page = request.args.get("page", 1, type=int)
    from flask import current_app
    per_page = current_app.config["PAGE_SIZE"]
    pagination = article_service.list_articles(page, per_page, status="published")
    return render_template("articles.html", pagination=pagination)


@public_bp.route("/maqola/<int:article_id>")
def article_detail(article_id):
    article = article_service.get_article(article_id)
    if not article or article["status"] != "published":
        abort(404)

    title = title_service.get_by_id(article["title_id"])
    og = seo_service.generate_og_tags(article=article)

    return render_template(
        "article_detail.html",
        article=article,
        title=title,
        og=og,
        meta_description=seo_service.meta_description(article["seo_description"] or article["summary"]),
    )
