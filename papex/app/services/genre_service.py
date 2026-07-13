from app.models.db import get_db
from app.utils.slugify import slugify


def list_genres():
    db = get_db()
    return db.execute("SELECT * FROM genres ORDER BY name").fetchall()


def get_genre(genre_id):
    db = get_db()
    return db.execute("SELECT * FROM genres WHERE id = ?", (genre_id,)).fetchone()


def get_or_create_by_name(name, tmdb_genre_id=None):
    db = get_db()
    name = name.strip()
    row = db.execute("SELECT * FROM genres WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    slug = slugify(name)
    base_slug, i = slug, 2
    while db.execute("SELECT 1 FROM genres WHERE slug = ?", (slug,)).fetchone():
        slug = f"{base_slug}-{i}"
        i += 1
    cur = db.execute(
        "INSERT INTO genres (name, slug, tmdb_genre_id) VALUES (?, ?, ?)",
        (name, slug, tmdb_genre_id),
    )
    db.commit()
    return cur.lastrowid


def create_genre(name):
    db = get_db()
    name = name.strip()
    slug = slugify(name)
    db.execute("INSERT INTO genres (name, slug) VALUES (?, ?)", (name, slug))
    db.commit()


def update_genre(genre_id, name):
    db = get_db()
    name = name.strip()
    slug = slugify(name)
    db.execute("UPDATE genres SET name=?, slug=? WHERE id=?", (name, slug, genre_id))
    db.commit()


def delete_genre(genre_id):
    db = get_db()
    db.execute("DELETE FROM genres WHERE id = ?", (genre_id,))
    db.commit()


def genres_for_title(title_id):
    db = get_db()
    return db.execute(
        """SELECT genres.* FROM genres
           JOIN title_genres ON title_genres.genre_id = genres.id
           WHERE title_genres.title_id = ? ORDER BY genres.name""",
        (title_id,),
    ).fetchall()


def set_title_genres(title_id, genre_ids):
    db = get_db()
    db.execute("DELETE FROM title_genres WHERE title_id = ?", (title_id,))
    for gid in genre_ids:
        db.execute(
            "INSERT OR IGNORE INTO title_genres (title_id, genre_id) VALUES (?, ?)",
            (title_id, gid),
        )
    db.commit()
