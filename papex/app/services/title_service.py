from app.models.db import get_db
from app.services import genre_service
from app.utils.pagination import paginate
from app.utils.slugify import unique_slug

CATEGORY_LABELS = {
    "kino": "Kino",
    "anime": "Anime",
    "multfilm": "Multfilm",
}

TITLE_FIELDS = (
    "tmdb_id", "imdb_id", "name", "original_name", "category", "summary", "tagline",
    "year", "release_date", "runtime", "country", "director", "poster_path",
    "backdrop_path", "poster_local", "backdrop_local", "poster_note", "trailer_url",
    "quality_score", "quality_label", "status",
)


def parse_links_text(raw_text):
    links = []
    for line in (raw_text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            platform, url = line.split("|", 1)
        else:
            platform, url = "Platforma", line
        platform, url = platform.strip(), url.strip()
        if platform and url:
            links.append((platform, url))
    return links


def links_to_text(links):
    return "\n".join(f"{link['platform']} | {link['url']}" for link in links)


def get_watch_links(title_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM watch_links WHERE title_id = ? ORDER BY id", (title_id,)
    ).fetchall()


def set_watch_links(title_id, links):
    db = get_db()
    db.execute("DELETE FROM watch_links WHERE title_id = ?", (title_id,))
    for platform, url in links:
        db.execute(
            "INSERT INTO watch_links (title_id, platform, url) VALUES (?, ?, ?)",
            (title_id, platform, url),
        )
    db.commit()


def get_cast(title_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM title_cast WHERE title_id = ? ORDER BY sort_order", (title_id,)
    ).fetchall()


def set_cast(title_id, cast_list):
    """cast_list: [(actor_name, character_name, profile_path), ...]"""
    db = get_db()
    db.execute("DELETE FROM title_cast WHERE title_id = ?", (title_id,))
    for i, (actor, character, profile_path) in enumerate(cast_list):
        if not actor:
            continue
        db.execute(
            """INSERT INTO title_cast (title_id, actor_name, character_name, profile_path, sort_order)
               VALUES (?, ?, ?, ?, ?)""",
            (title_id, actor.strip(), (character or "").strip(), profile_path, i),
        )
    db.commit()


def get_by_id(title_id):
    db = get_db()
    return db.execute("SELECT * FROM titles WHERE id = ?", (title_id,)).fetchone()


def get_by_slug(slug):
    db = get_db()
    return db.execute(
        "SELECT * FROM titles WHERE slug = ? AND status = 'published'", (slug,)
    ).fetchone()


def get_by_slug_any_status(slug):
    db = get_db()
    return db.execute("SELECT * FROM titles WHERE slug = ?", (slug,)).fetchone()


def get_by_tmdb_id(tmdb_id):
    db = get_db()
    return db.execute("SELECT * FROM titles WHERE tmdb_id = ?", (tmdb_id,)).fetchone()


def create_title(data, genre_ids=None, cast_list=None, links=None):
    db = get_db()
    slug = unique_slug(db, data["name"], data.get("year"))
    columns = ["slug"] + list(TITLE_FIELDS)
    values = [slug] + [data.get(f) for f in TITLE_FIELDS]
    placeholders = ", ".join("?" for _ in columns)
    cur = db.execute(
        f"INSERT INTO titles ({', '.join(columns)}) VALUES ({placeholders})", values
    )
    title_id = cur.lastrowid
    db.commit()

    if genre_ids:
        genre_service.set_title_genres(title_id, genre_ids)
    if cast_list:
        set_cast(title_id, cast_list)
    if links:
        set_watch_links(title_id, links)
    return title_id


def update_title(title_id, data, genre_ids=None, cast_list=None, links=None):
    db = get_db()
    current = get_by_id(title_id)
    if current is None:
        return False

    if data["name"] != current["name"] or data.get("year") != current["year"]:
        slug = unique_slug(db, data["name"], data.get("year"), exclude_id=title_id)
    else:
        slug = current["slug"]

    assignments = ", ".join(f"{f}=?" for f in TITLE_FIELDS)
    values = [data.get(f) for f in TITLE_FIELDS]
    db.execute(
        f"UPDATE titles SET slug=?, {assignments}, updated_at=datetime('now') WHERE id=?",
        [slug] + values + [title_id],
    )
    db.commit()

    if genre_ids is not None:
        genre_service.set_title_genres(title_id, genre_ids)
    if cast_list is not None:
        set_cast(title_id, cast_list)
    if links is not None:
        set_watch_links(title_id, links)
    return True


def delete_title(title_id):
    db = get_db()
    db.execute("DELETE FROM titles WHERE id = ?", (title_id,))
    db.commit()


def increment_view(title_id):
    db = get_db()
    db.execute(
        "UPDATE titles SET views_count = views_count + 1 WHERE id = ?", (title_id,)
    )
    db.commit()


def record_daily_view(title_id, voter_key, ip_hash, today_str):
    """Kunlik dedup bilan ko'rishni qayd qiladi; agar bugun bu voter_key ilgari
    ko'rmagan bo'lsa, views_count'ni oshiradi va True qaytaradi."""
    db = get_db()
    try:
        db.execute(
            "INSERT INTO views (title_id, voter_key, ip_hash, viewed_on) VALUES (?, ?, ?, ?)",
            (title_id, voter_key, ip_hash, today_str),
        )
        db.commit()
    except Exception:
        return False
    increment_view(title_id)
    return True


# ---------------- HOME SECTIONS ----------------

def trending(limit=10):
    db = get_db()
    return db.execute(
        """SELECT * FROM titles WHERE status = 'published'
           ORDER BY is_trending DESC, views_count DESC, published_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()


def newest(limit=10):
    db = get_db()
    return db.execute(
        "SELECT * FROM titles WHERE status = 'published' ORDER BY published_at DESC LIMIT ?",
        (limit,),
    ).fetchall()


def top_rated(limit=10):
    db = get_db()
    return db.execute(
        """SELECT * FROM titles WHERE status = 'published'
           ORDER BY quality_score DESC, views_count DESC LIMIT ?""",
        (limit,),
    ).fetchall()


def by_category_preview(category, limit=10):
    db = get_db()
    return db.execute(
        """SELECT * FROM titles WHERE status = 'published' AND category = ?
           ORDER BY published_at DESC LIMIT ?""",
        (category, limit),
    ).fetchall()


def by_category_page(category, page, per_page):
    db = get_db()
    base = "SELECT * FROM titles WHERE status = 'published' AND category = ? ORDER BY published_at DESC"
    count = "SELECT COUNT(*) FROM titles WHERE status = 'published' AND category = ?"
    return paginate(db, base, count, (category,), page, per_page)


def related_titles(title, limit=6):
    db = get_db()
    genre_ids = [g["id"] for g in genre_service.genres_for_title(title["id"])]
    if genre_ids:
        placeholders = ",".join("?" for _ in genre_ids)
        rows = db.execute(
            f"""SELECT DISTINCT titles.* FROM titles
                JOIN title_genres ON title_genres.title_id = titles.id
                WHERE title_genres.genre_id IN ({placeholders})
                  AND titles.id != ? AND titles.status = 'published'
                ORDER BY titles.quality_score DESC LIMIT ?""",
            genre_ids + [title["id"], limit],
        ).fetchall()
        if rows:
            return rows
    return db.execute(
        """SELECT * FROM titles WHERE category = ? AND id != ? AND status = 'published'
           ORDER BY published_at DESC LIMIT ?""",
        (title["category"], title["id"], limit),
    ).fetchall()


# ---------------- ADMIN LIST ----------------

def admin_list(page, per_page, category=None, status=None, q=None):
    db = get_db()
    where = ["1=1"]
    params = []
    if category:
        where.append("category = ?")
        params.append(category)
    if status:
        where.append("status = ?")
        params.append(status)
    if q:
        where.append("name LIKE ?")
        params.append(f"%{q}%")
    where_sql = " AND ".join(where)
    base = f"SELECT * FROM titles WHERE {where_sql} ORDER BY id DESC"
    count = f"SELECT COUNT(*) FROM titles WHERE {where_sql}"
    return paginate(db, base, count, params, page, per_page)


def count_by_category():
    db = get_db()
    rows = db.execute(
        "SELECT category, COUNT(*) AS c FROM titles GROUP BY category"
    ).fetchall()
    return {r["category"]: r["c"] for r in rows}


def total_count():
    db = get_db()
    return db.execute("SELECT COUNT(*) FROM titles").fetchone()[0]
