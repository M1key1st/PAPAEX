from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.services import (
    article_service, auto_import_service, backup_service, genre_service,
    health_service, image_cache_service, log_service, scheduler_service,
    settings_service, stats_service, title_service, tmdb_service, user_service,
)
from app.utils.decorators import roles_required
from app.utils.security import clean_text, get_client_ip

admin_bp = Blueprint("admin", __name__)


# ---------------- DASHBOARD ----------------

@admin_bp.route("/")
@login_required
def dashboard():
    stats = stats_service.overview()
    health = health_service.get_full_status()
    return render_template("admin/dashboard.html", stats=stats, health=health)


# ---------------- MOVIES ----------------

@admin_bp.route("/movies")
@login_required
def movies_list():
    page = request.args.get("page", 1, type=int)
    category = request.args.get("category") or None
    status = request.args.get("status") or None
    q = request.args.get("q") or None
    pagination = title_service.admin_list(page, 20, category=category, status=status, q=q)
    return render_template(
        "admin/movies.html", pagination=pagination, category=category, status=status, q=q or ""
    )


def _collect_form_data(form):
    def to_float(v, default=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def to_int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    return {
        "tmdb_id": to_int(form.get("tmdb_id")),
        "imdb_id": clean_text(form.get("imdb_id", ""), 32) or None,
        "name": clean_text(form.get("name", ""), 300),
        "original_name": clean_text(form.get("original_name", ""), 300) or None,
        "category": form.get("category"),
        "summary": clean_text(form.get("summary", ""), 5000),
        "tagline": clean_text(form.get("tagline", ""), 300) or None,
        "year": to_int(form.get("year")),
        "release_date": form.get("release_date") or None,
        "runtime": to_int(form.get("runtime")),
        "country": clean_text(form.get("country", ""), 120) or None,
        "director": clean_text(form.get("director", ""), 200) or None,
        "poster_path": form.get("poster_path") or None,
        "backdrop_path": form.get("backdrop_path") or None,
        "poster_local": form.get("poster_local") or None,
        "backdrop_local": form.get("backdrop_local") or None,
        "poster_note": clean_text(form.get("poster_note", ""), 8) or None,
        "trailer_url": clean_text(form.get("trailer_url", ""), 300) or None,
        "quality_score": to_float(form.get("quality_score"), 0.0),
        "quality_label": clean_text(form.get("quality_label", "HD"), 30) or "HD",
        "status": form.get("status", "published"),
    }


def _validate(data):
    errors = []
    if not data["name"]:
        errors.append("Nom kiritilishi shart.")
    if data["category"] not in title_service.CATEGORY_LABELS:
        errors.append("Turkum noto'g'ri tanlangan.")
    if not data["summary"]:
        errors.append("Tavsif kiritilishi shart.")
    if not (0 <= data["quality_score"] <= 10):
        errors.append("Sifat bahosi 0 dan 10 gacha bo'lishi kerak.")
    return errors


@admin_bp.route("/movies/new", methods=["GET", "POST"])
@login_required
@roles_required("editor")
def movie_create():
    if request.method == "POST":
        data = _collect_form_data(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e)
            return render_template(
                "admin/movie_form.html", mode="new", title=None, form=request.form,
                genres=genre_service.list_genres(), selected_genre_ids=[],
                cast_text="", links_text="",
            )

        genre_ids = [int(g) for g in request.form.getlist("genre_ids")]
        cast_list = _parse_cast_text(request.form.get("cast_text", ""))
        links = title_service.parse_links_text(request.form.get("links_text", ""))

        title_id = title_service.create_title(data, genre_ids, cast_list, links)
        log_service.add_log(current_user.username, "create", f"title:{title_id}", data["name"], get_client_ip())
        flash("Yangi kontent qo'shildi.")
        return redirect(url_for("admin.movies_list"))

    return render_template(
        "admin/movie_form.html", mode="new", title=None, form={},
        genres=genre_service.list_genres(), selected_genre_ids=[],
        cast_text="", links_text="",
    )


@admin_bp.route("/movies/<int:title_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("editor")
def movie_edit(title_id):
    title = title_service.get_by_id(title_id)
    if title is None:
        flash("Topilmadi.")
        return redirect(url_for("admin.movies_list"))

    if request.method == "POST":
        data = _collect_form_data(request.form)
        errors = _validate(data)
        if errors:
            for e in errors:
                flash(e)
            return render_template(
                "admin/movie_form.html", mode="edit", title=title, form=request.form,
                genres=genre_service.list_genres(),
                selected_genre_ids=[int(g) for g in request.form.getlist("genre_ids")],
                cast_text=request.form.get("cast_text", ""),
                links_text=request.form.get("links_text", ""),
            )

        genre_ids = [int(g) for g in request.form.getlist("genre_ids")]
        cast_list = _parse_cast_text(request.form.get("cast_text", ""))
        links = title_service.parse_links_text(request.form.get("links_text", ""))

        title_service.update_title(title_id, data, genre_ids, cast_list, links)
        log_service.add_log(current_user.username, "update", f"title:{title_id}", data["name"], get_client_ip())
        flash("O'zgarishlar saqlandi.")
        return redirect(url_for("admin.movies_list"))

    genres = genre_service.genres_for_title(title_id)
    cast = title_service.get_cast(title_id)
    links = title_service.get_watch_links(title_id)
    cast_text = "\n".join(
        f"{c['actor_name']} | {c['character_name'] or ''}" for c in cast
    )
    return render_template(
        "admin/movie_form.html", mode="edit", title=title, form=dict(title),
        genres=genre_service.list_genres(),
        selected_genre_ids=[g["id"] for g in genres],
        cast_text=cast_text,
        links_text=title_service.links_to_text(links),
    )


@admin_bp.route("/movies/<int:title_id>/delete", methods=["POST"])
@login_required
@roles_required("editor")
def movie_delete(title_id):
    title = title_service.get_by_id(title_id)
    if title:
        title_service.delete_title(title_id)
        log_service.add_log(current_user.username, "delete", f"title:{title_id}", title["name"], get_client_ip())
        flash("Kontent o'chirildi.")
    return redirect(url_for("admin.movies_list"))


def _parse_cast_text(raw):
    cast = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        actor = parts[0].strip()
        character = parts[1].strip() if len(parts) > 1 else ""
        cast.append((actor, character, None))
    return cast


# ---------------- TMDB SEARCH / IMPORT ----------------

@admin_bp.route("/tmdb/search")
@login_required
@roles_required("editor")
def tmdb_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"enabled": tmdb_service.is_enabled(), "results": []})
    results = tmdb_service.search_movie(q)
    return jsonify({
        "enabled": tmdb_service.is_enabled(),
        "results": [
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "year": (r.get("release_date") or "")[:4],
                "poster": tmdb_service.image_url(r.get("poster_path"), "w92"),
            }
            for r in results
        ],
    })


@admin_bp.route("/tmdb/import/<int:tmdb_id>")
@login_required
@roles_required("editor")
def tmdb_import(tmdb_id):
    details = tmdb_service.get_movie_details(tmdb_id)
    if not details:
        return jsonify({"ok": False, "error": "TMDB'dan ma'lumot olinmadi."}), 400

    poster_local = image_cache_service.cache_image(details["poster_path"], tmdb_id, "poster")
    backdrop_local = image_cache_service.cache_image(details["backdrop_path"], tmdb_id, "backdrop", size="w1280")

    return jsonify({
        "ok": True,
        "data": {
            "tmdb_id": details["tmdb_id"],
            "imdb_id": details["imdb_id"],
            "name": details["name"],
            "original_name": details["original_name"],
            "summary": details["summary"],
            "tagline": details["tagline"],
            "year": details["year"],
            "release_date": details["release_date"],
            "runtime": details["runtime"],
            "country": details["country"],
            "director": details["director"],
            "poster_path": details["poster_path"],
            "backdrop_path": details["backdrop_path"],
            "poster_local": poster_local,
            "backdrop_local": backdrop_local,
            "trailer_url": details["trailer_url"],
            "genres": details["genres"],
            "cast": details["cast"],
        },
    })


# ---------------- AUTO IMPORT DASHBOARD ----------------

@admin_bp.route("/auto-import")
@login_required
@roles_required("editor")
def auto_import_dashboard():
    stats = auto_import_service.get_import_stats()
    return render_template("admin/auto_import.html", stats=stats)


@admin_bp.route("/auto-import/run", methods=["POST"])
@login_required
@roles_required("editor")
def auto_import_run():
    source = request.form.get("source") or None
    results = auto_import_service.run_auto_import(source)
    log_service.add_log(current_user.username, "auto_import", details=str(results), ip=get_client_ip())
    flash("Import muvaffaqiyatli tugadi.")
    return redirect(url_for("admin.auto_import_dashboard"))


@admin_bp.route("/auto-import/log")
@login_required
@roles_required("editor")
def auto_import_log():
    page = request.args.get("page", 1, type=int)
    pagination = auto_import_service.get_import_log(page, 20)
    return render_template("admin/auto_import_log.html", pagination=pagination)


# ---------------- ARTICLES ----------------

@admin_bp.route("/articles")
@login_required
@roles_required("editor")
def articles_list():
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status") or None
    pagination = article_service.list_articles(page, 20, status=status)
    return render_template("admin/articles.html", pagination=pagination, status=status)


@admin_bp.route("/articles/<int:article_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("editor")
def article_edit(article_id):
    article = article_service.get_article(article_id)
    if not article:
        flash("Maqola topilmadi.")
        return redirect(url_for("admin.articles_list"))

    if request.method == "POST":
        data = {
            "title": clean_text(request.form.get("title", ""), 300),
            "summary": clean_text(request.form.get("summary", ""), 1000),
            "content": request.form.get("content", ""),
            "seo_description": clean_text(request.form.get("seo_description", ""), 300),
            "telegram_text": clean_text(request.form.get("telegram_text", ""), 2000),
            "status": request.form.get("status", "draft"),
        }
        article_service.update_article(article_id, data)
        log_service.add_log(current_user.username, "update", f"article:{article_id}", ip=get_client_ip())
        flash("Maqola yangilandi.")
        return redirect(url_for("admin.articles_list"))

    return render_template("admin/article_form.html", article=article)


@admin_bp.route("/articles/<int:article_id>/delete", methods=["POST"])
@login_required
@roles_required("editor")
def article_delete(article_id):
    article_service.delete_article(article_id)
    log_service.add_log(current_user.username, "delete", f"article:{article_id}", ip=get_client_ip())
    flash("Maqola o'chirildi.")
    return redirect(url_for("admin.articles_list"))


@admin_bp.route("/articles/<int:article_id>/publish", methods=["POST"])
@login_required
@roles_required("editor")
def article_publish(article_id):
    article_service.publish_article(article_id)
    log_service.add_log(current_user.username, "publish", f"article:{article_id}", ip=get_client_ip())
    flash("Maqola nashr etildi.")
    return redirect(url_for("admin.articles_list"))


@admin_bp.route("/articles/<int:article_id>/regenerate", methods=["POST"])
@login_required
@roles_required("editor")
def article_regenerate(article_id):
    article, status = article_service.regenerate_article(article_id)
    if article:
        log_service.add_log(current_user.username, "regenerate", f"article:{article_id}", ip=get_client_ip())
        flash("Maqola qayta generatsiya qilindi.")
    else:
        flash(f"Xato: {status}")
    return redirect(url_for("admin.articles_list"))


@admin_bp.route("/articles/generate-missing", methods=["POST"])
@login_required
@roles_required("editor")
def articles_generate_missing():
    results = article_service.generate_missing_articles()
    log_service.add_log(current_user.username, "generate_articles", details=str(results), ip=get_client_ip())
    flash(f"Generatsiya: {results['generated']} ta maqola yaratildi, {results['failed']} ta xato.")
    return redirect(url_for("admin.articles_list"))


# ---------------- GENRES ----------------

@admin_bp.route("/genres", methods=["GET", "POST"])
@login_required
@roles_required("editor")
def genres():
    if request.method == "POST":
        name = clean_text(request.form.get("name", ""), 100)
        if name:
            genre_service.create_genre(name)
            log_service.add_log(current_user.username, "create", f"genre:{name}", ip=get_client_ip())
            flash("Janr qo'shildi.")
        return redirect(url_for("admin.genres"))
    return render_template("admin/genres.html", genres=genre_service.list_genres())


@admin_bp.route("/genres/<int:genre_id>/edit", methods=["POST"])
@login_required
@roles_required("editor")
def genre_edit(genre_id):
    name = clean_text(request.form.get("name", ""), 100)
    if name:
        genre_service.update_genre(genre_id, name)
        flash("Janr yangilandi.")
    return redirect(url_for("admin.genres"))


@admin_bp.route("/genres/<int:genre_id>/delete", methods=["POST"])
@login_required
@roles_required("editor")
def genre_delete(genre_id):
    genre_service.delete_genre(genre_id)
    log_service.add_log(current_user.username, "delete", f"genre:{genre_id}", ip=get_client_ip())
    flash("Janr o'chirildi.")
    return redirect(url_for("admin.genres"))


# ---------------- USERS & ROLES ----------------

@admin_bp.route("/users", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def users():
    if request.method == "POST":
        username = clean_text(request.form.get("username", ""), 50)
        email = clean_text(request.form.get("email", ""), 120)
        password = request.form.get("password", "")
        role_id = request.form.get("role_id", type=int)

        if not username or not email or len(password) < 6 or not role_id:
            flash("Barcha maydonlarni to'g'ri to'ldiring (parol kamida 6 belgi).")
        elif user_service.username_or_email_taken(username, email):
            flash("Bu login yoki email allaqachon band.")
        else:
            user_service.create_user(username, email, password, role_id)
            log_service.add_log(current_user.username, "create", f"user:{username}", ip=get_client_ip())
            flash("Foydalanuvchi qo'shildi.")
        return redirect(url_for("admin.users"))

    return render_template(
        "admin/users.html", users=user_service.list_users(), roles=user_service.list_roles()
    )


@admin_bp.route("/users/<int:user_id>/edit", methods=["POST"])
@login_required
@roles_required("admin")
def user_edit(user_id):
    username = clean_text(request.form.get("username", ""), 50)
    email = clean_text(request.form.get("email", ""), 120)
    role_id = request.form.get("role_id", type=int)
    is_active = request.form.get("is_active") == "on"
    password = request.form.get("password", "").strip()

    if user_service.username_or_email_taken(username, email, exclude_id=user_id):
        flash("Bu login yoki email band.")
    else:
        user_service.update_user(user_id, username, email, role_id, is_active, password or None)
        log_service.add_log(current_user.username, "update", f"user:{user_id}", ip=get_client_ip())
        flash("Foydalanuvchi yangilandi.")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def user_delete(user_id):
    if str(user_id) == current_user.id:
        flash("O'zingizni o'chira olmaysiz.")
    else:
        user_service.delete_user(user_id)
        log_service.add_log(current_user.username, "delete", f"user:{user_id}", ip=get_client_ip())
        flash("Foydalanuvchi o'chirildi.")
    return redirect(url_for("admin.users"))


@admin_bp.route("/roles")
@login_required
@roles_required("admin")
def roles():
    return render_template("admin/roles.html", roles=user_service.list_roles())


# ---------------- SETTINGS ----------------

@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def settings():
    if request.method == "POST":
        data = {
            "site_name": clean_text(request.form.get("site_name", ""), 100),
            "site_description": clean_text(request.form.get("site_description", ""), 300),
            "footer_text": clean_text(request.form.get("footer_text", ""), 500),
        }
        settings_service.set_many(data)
        log_service.add_log(current_user.username, "update", "settings", ip=get_client_ip())
        flash("Sozlamalar saqlandi.")
        return redirect(url_for("admin.settings"))

    return render_template(
        "admin/settings.html",
        settings=settings_service.get_all(),
        tmdb_enabled=bool(current_app.config.get("TMDB_API_KEY")),
    )


# ---------------- BACKUPS ----------------

@admin_bp.route("/backups")
@login_required
@roles_required("admin")
def backups_list():
    backups = backup_service.list_backups()
    stats = backup_service.get_backup_stats()
    return render_template("admin/backups.html", backups=backups, stats=stats)


@admin_bp.route("/backups/create", methods=["POST"])
@login_required
@roles_required("admin")
def backup_create():
    result = backup_service.create_backup()
    if "error" in result:
        flash(f"Xato: {result['error']}")
    else:
        log_service.add_log(current_user.username, "backup", details=result["filename"], ip=get_client_ip())
        flash("Backup yaratildi.")
    return redirect(url_for("admin.backups_list"))


@admin_bp.route("/backups/<int:backup_id>/download")
@login_required
@roles_required("admin")
def backup_download(backup_id):
    result = backup_service.download_backup(backup_id)
    if result:
        return result
    flash("Backup topilmadi.")
    return redirect(url_for("admin.backups_list"))


@admin_bp.route("/backups/<int:backup_id>/restore", methods=["POST"])
@login_required
@roles_required("admin")
def backup_restore(backup_id):
    result = backup_service.restore_backup(backup_id)
    if "error" in result:
        flash(f"Xato: {result['error']}")
    else:
        log_service.add_log(current_user.username, "restore_backup", ip=get_client_ip())
        flash("Database tiklandi.")
    return redirect(url_for("admin.backups_list"))


@admin_bp.route("/backups/<int:backup_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def backup_delete(backup_id):
    backup_service.delete_backup(backup_id)
    log_service.add_log(current_user.username, "delete", f"backup:{backup_id}", ip=get_client_ip())
    flash("Backup o'chirildi.")
    return redirect(url_for("admin.backups_list"))


# ---------------- LOGS ----------------

@admin_bp.route("/logs")
@login_required
@roles_required("moderator")
def logs():
    page = request.args.get("page", 1, type=int)
    pagination = log_service.list_logs(page, 50)
    return render_template("admin/logs.html", pagination=pagination)


# ---------------- STATISTICS ----------------

@admin_bp.route("/stats")
@login_required
def stats_page():
    stats = stats_service.overview()
    daily = stats_service.get_daily_stats(30)
    top_viewed = stats_service.get_top_viewed_titles(10)
    popular_genres = stats_service.get_popular_genres(10)
    return render_template(
        "admin/stats.html",
        stats=stats,
        daily_stats=daily,
        top_viewed=top_viewed,
        popular_genres=popular_genres,
    )


# ---------------- SCHEDULER ----------------

@admin_bp.route("/scheduler")
@login_required
@roles_required("admin")
def scheduler_page():
    status = scheduler_service.get_scheduler_status()
    return render_template("admin/scheduler.html", scheduler=status)


@admin_bp.route("/scheduler/trigger/<job_id>", methods=["POST"])
@login_required
@roles_required("admin")
def scheduler_trigger(job_id):
    success = scheduler_service.trigger_job(job_id)
    if success:
        flash("Vazifa ishga tushirildi.")
    else:
        flash("Vazifa topilmadi.")
    return redirect(url_for("admin.scheduler_page"))
