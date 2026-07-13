from flask import session

from app.models.db import get_db

RECENTLY_VIEWED_KEY = "papex_recent"
RECENTLY_VIEWED_MAX = 20


def cast_vote(title_id, voter_key, ip_hash, value):
    """value: 1 (like) yoki -1 (dislike). Bir voter_key bitta title'ga bitta ovoz beradi;
    qayta bosilsa ovoz yangilanadi yoki bekor qilinadi (toggle)."""
    db = get_db()
    existing = db.execute(
        "SELECT * FROM votes WHERE title_id = ? AND voter_key = ?", (title_id, voter_key)
    ).fetchone()

    if existing and existing["value"] == value:
        # xuddi shu tugma qayta bosildi -> ovozni bekor qilish
        db.execute("DELETE FROM votes WHERE id = ?", (existing["id"],))
        db.commit()
        _recalculate_counts(title_id)
        return None

    if existing:
        db.execute(
            "UPDATE votes SET value = ?, ip_hash = ?, created_at = datetime('now') WHERE id = ?",
            (value, ip_hash, existing["id"]),
        )
    else:
        db.execute(
            "INSERT INTO votes (title_id, voter_key, ip_hash, value) VALUES (?, ?, ?, ?)",
            (title_id, voter_key, ip_hash, value),
        )
    db.commit()
    _recalculate_counts(title_id)
    return value


def _recalculate_counts(title_id):
    db = get_db()
    likes = db.execute(
        "SELECT COUNT(*) FROM votes WHERE title_id = ? AND value = 1", (title_id,)
    ).fetchone()[0]
    dislikes = db.execute(
        "SELECT COUNT(*) FROM votes WHERE title_id = ? AND value = -1", (title_id,)
    ).fetchone()[0]
    db.execute(
        "UPDATE titles SET likes_count = ?, dislikes_count = ? WHERE id = ?",
        (likes, dislikes, title_id),
    )
    db.commit()
    return likes, dislikes


def get_user_vote(title_id, voter_key):
    db = get_db()
    row = db.execute(
        "SELECT value FROM votes WHERE title_id = ? AND voter_key = ?", (title_id, voter_key)
    ).fetchone()
    return row["value"] if row else 0


def toggle_bookmark(title_id, voter_key, user_id=None):
    db = get_db()
    existing = db.execute(
        "SELECT id FROM bookmarks WHERE title_id = ? AND voter_key = ?", (title_id, voter_key)
    ).fetchone()
    if existing:
        db.execute("DELETE FROM bookmarks WHERE id = ?", (existing["id"],))
        db.commit()
        return False
    db.execute(
        "INSERT INTO bookmarks (title_id, voter_key, user_id) VALUES (?, ?, ?)",
        (title_id, voter_key, user_id),
    )
    db.commit()
    return True


def is_bookmarked(title_id, voter_key):
    db = get_db()
    return db.execute(
        "SELECT 1 FROM bookmarks WHERE title_id = ? AND voter_key = ?", (title_id, voter_key)
    ).fetchone() is not None


def list_bookmarks(voter_key, limit=50):
    db = get_db()
    return db.execute(
        """SELECT titles.* FROM bookmarks
           JOIN titles ON titles.id = bookmarks.title_id
           WHERE bookmarks.voter_key = ? AND titles.status = 'published'
           ORDER BY bookmarks.created_at DESC LIMIT ?""",
        (voter_key, limit),
    ).fetchall()


def push_recently_viewed(title_id):
    recent = session.get(RECENTLY_VIEWED_KEY, [])
    recent = [tid for tid in recent if tid != title_id]
    recent.insert(0, title_id)
    session[RECENTLY_VIEWED_KEY] = recent[:RECENTLY_VIEWED_MAX]
    session.permanent = True


def get_recently_viewed(exclude_id=None, limit=8):
    ids = session.get(RECENTLY_VIEWED_KEY, [])
    if exclude_id in ids:
        ids = [i for i in ids if i != exclude_id]
    ids = ids[:limit]
    if not ids:
        return []
    db = get_db()
    placeholders = ",".join("?" for _ in ids)
    rows = db.execute(
        f"SELECT * FROM titles WHERE id IN ({placeholders}) AND status = 'published'", ids
    ).fetchall()
    # session tartibini saqlab qolish
    rows_by_id = {r["id"]: r for r in rows}
    return [rows_by_id[i] for i in ids if i in rows_by_id]


def popular_titles(limit=10):
    db = get_db()
    return db.execute(
        "SELECT * FROM titles WHERE status = 'published' ORDER BY views_count DESC LIMIT ?",
        (limit,),
    ).fetchall()
