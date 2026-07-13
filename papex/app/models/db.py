"""Database qatlami — SQLite va PostgreSQL support.

Config orqali DB_TYPE tanlanadi:
- sqlite (default)
- postgresql
"""

import os
import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

DEFAULT_ROLES = [
    ("admin", "Administrator", "all"),
    ("editor", "Kontent muharriri", "titles.manage,genres.manage,tmdb.use"),
    ("moderator", "Moderator", "votes.moderate,logs.view,dashboard.view"),
]

DEFAULT_GENRES = [
    "Aksiya", "Sarguzasht", "Animatsiya", "Komediya", "Jinoyat", "Hujjatli",
    "Drama", "Oilaviy", "Fantastika", "Tarixiy", "Dahshat", "Musiqiy",
    "Detektiv", "Romantik", "Ilmiy-fantastika", "Triller", "Urush", "Vestern",
]


def _get_db_type():
    """Database turini aniqlash."""
    return current_app.config.get("DB_TYPE", "sqlite").lower()


def _get_pg_connection():
    """PostgreSQL ulanish olish."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=current_app.config.get("PG_HOST", "localhost"),
            port=current_app.config.get("PG_PORT", 5432),
            database=current_app.config.get("PG_DATABASE", "papex"),
            user=current_app.config.get("PG_USER", "postgres"),
            password=current_app.config.get("PG_PASSWORD", ""),
        )
        conn.autocommit = False
        return conn
    except ImportError:
        logger.error("psycopg2 not installed. Run: pip install psycopg2-binary")
        return None
    except Exception as e:
        logger.error(f"PostgreSQL connection error: {e}")
        return None


def get_db():
    """Database ulanish olish."""
    if "db" not in g:
        db_type = _get_db_type()

        if db_type == "postgresql":
            conn = _get_pg_connection()
            if conn:
                g.db = conn
            else:
                # Fallback to SQLite
                g.db = sqlite3.connect(
                    current_app.config["DB_PATH"],
                    detect_types=sqlite3.PARSE_DECLTYPES,
                )
                g.db.row_factory = sqlite3.Row
                g.db.execute("PRAGMA foreign_keys = ON")
        else:
            g.db = sqlite3.connect(
                current_app.config["DB_PATH"],
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


def close_db(exception=None):
    """Database ulanishini yopish."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _slugify(text):
    import re
    import unicodedata

    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "genre"


def _get_pg_schema():
    """PostgreSQL uchun schema (SQLite dan farqli)."""
    return """
-- ROLES & USERS
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    permissions TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role_id INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles (id)
);

-- GENRES
CREATE TABLE IF NOT EXISTS genres (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    tmdb_genre_id INTEGER
);

-- TITLES
CREATE TABLE IF NOT EXISTS titles (
    id SERIAL PRIMARY KEY,
    tmdb_id INTEGER UNIQUE,
    imdb_id TEXT,
    name TEXT NOT NULL,
    original_name TEXT,
    slug TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    tagline TEXT,
    year INTEGER,
    release_date TEXT,
    runtime INTEGER,
    country TEXT,
    director TEXT,
    poster_path TEXT,
    backdrop_path TEXT,
    poster_local TEXT,
    backdrop_local TEXT,
    poster_note TEXT,
    trailer_url TEXT,
    quality_score REAL NOT NULL DEFAULT 0,
    quality_label TEXT NOT NULL DEFAULT 'HD',
    status TEXT NOT NULL DEFAULT 'published',
    is_trending INTEGER NOT NULL DEFAULT 0,
    views_count INTEGER NOT NULL DEFAULT 0,
    likes_count INTEGER NOT NULL DEFAULT 0,
    dislikes_count INTEGER NOT NULL DEFAULT 0,
    popularity REAL NOT NULL DEFAULT 0,
    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_titles_category ON titles (category);
CREATE INDEX IF NOT EXISTS idx_titles_published_at ON titles (published_at);
CREATE INDEX IF NOT EXISTS idx_titles_quality_score ON titles (quality_score);
CREATE INDEX IF NOT EXISTS idx_titles_views_count ON titles (views_count);
CREATE INDEX IF NOT EXISTS idx_titles_slug ON titles (slug);
CREATE INDEX IF NOT EXISTS idx_titles_status ON titles (status);
CREATE INDEX IF NOT EXISTS idx_titles_tmdb_id ON titles (tmdb_id);

-- TITLE_GENRES
CREATE TABLE IF NOT EXISTS title_genres (
    title_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,
    PRIMARY KEY (title_id, genre_id),
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres (id) ON DELETE CASCADE
);

-- TITLE_CAST
CREATE TABLE IF NOT EXISTS title_cast (
    id SERIAL PRIMARY KEY,
    title_id INTEGER NOT NULL,
    actor_name TEXT NOT NULL,
    character_name TEXT,
    profile_path TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE
);

-- WATCH_LINKS
CREATE TABLE IF NOT EXISTS watch_links (
    id SERIAL PRIMARY KEY,
    title_id INTEGER NOT NULL,
    platform TEXT NOT NULL,
    url TEXT NOT NULL,
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE
);

-- VOTES
CREATE TABLE IF NOT EXISTS votes (
    id SERIAL PRIMARY KEY,
    title_id INTEGER NOT NULL,
    voter_key TEXT NOT NULL,
    ip_hash TEXT NOT NULL,
    value INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE,
    UNIQUE (title_id, voter_key)
);

-- BOOKMARKS
CREATE TABLE IF NOT EXISTS bookmarks (
    id SERIAL PRIMARY KEY,
    title_id INTEGER NOT NULL,
    voter_key TEXT NOT NULL,
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL,
    UNIQUE (title_id, voter_key)
);

-- VIEWS
CREATE TABLE IF NOT EXISTS views (
    id SERIAL PRIMARY KEY,
    title_id INTEGER NOT NULL,
    voter_key TEXT NOT NULL,
    ip_hash TEXT NOT NULL,
    viewed_on TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE,
    UNIQUE (title_id, voter_key, viewed_on)
);

-- SETTINGS
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

-- LOGS
CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT,
    details TEXT,
    ip TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- TELEGRAM_QUEUE
CREATE TABLE IF NOT EXISTS telegram_queue (
    id SERIAL PRIMARY KEY,
    title_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    message TEXT,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE
);

-- ARTICLES
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    title_id INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    seo_description TEXT NOT NULL DEFAULT '',
    telegram_text TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE
);

-- IMPORT_QUEUE
CREATE TABLE IF NOT EXISTS import_queue (
    id SERIAL PRIMARY KEY,
    tmdb_id INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    status TEXT NOT NULL DEFAULT 'pending',
    title_id INTEGER,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE SET NULL
);

-- AUTO_IMPORT_LOG
CREATE TABLE IF NOT EXISTS auto_import_log (
    id SERIAL PRIMARY KEY,
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT NOT NULL,
    items_found INTEGER NOT NULL DEFAULT 0,
    items_added INTEGER NOT NULL DEFAULT 0,
    items_skipped INTEGER NOT NULL DEFAULT 0,
    errors INTEGER NOT NULL DEFAULT 0,
    details TEXT
);

-- DAILY_STATS
CREATE TABLE IF NOT EXISTS daily_stats (
    id SERIAL PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    page_views INTEGER NOT NULL DEFAULT 0,
    unique_visitors INTEGER NOT NULL DEFAULT 0,
    new_titles INTEGER NOT NULL DEFAULT 0,
    new_articles INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- BACKUPS
CREATE TABLE IF NOT EXISTS backups (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(app):
    """Bazani/jadvallarni yaratadi."""
    db_type = app.config.get("DB_TYPE", "sqlite").lower()

    if db_type == "postgresql":
        _init_postgresql(app)
    else:
        _init_sqlite(app)


def _init_sqlite(app):
    """SQLite ni ishga tushirish."""
    db_path = Path(app.config["DB_PATH"])
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)

    # FTS triggerlar xatolik bersa ham davom etish uchun
    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [s.strip() for s in schema_text.split(";") if s.strip()]

    for stmt in statements:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass

    conn.commit()
    _seed_data(conn, app)
    conn.close()


def _init_postgresql(app):
    """PostgreSQL ni ishga tushirish."""
    conn = _get_pg_connection()
    if not conn:
        logger.error("PostgreSQL connection failed")
        return

    try:
        cursor = conn.cursor()
        schema = _get_pg_schema()
        cursor.execute(schema)
        conn.commit()
        _seed_data_pg(conn, app)
    except Exception as e:
        logger.error(f"PostgreSQL init error: {e}")
    finally:
        conn.close()


def _seed_data(conn, app):
    """Boshlang'ich ma'lumotlarni to'ldirish (SQLite)."""
    # Roles
    existing_roles = {row[0] for row in conn.execute("SELECT name FROM roles")}
    for name, label, perms in DEFAULT_ROLES:
        if name not in existing_roles:
            conn.execute(
                "INSERT INTO roles (name, label, permissions) VALUES (?, ?, ?)",
                (name, label, perms),
            )
    conn.commit()

    # Superadmin
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        from werkzeug.security import generate_password_hash
        admin_role_id = conn.execute(
            "SELECT id FROM roles WHERE name = 'admin'"
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO users (username, email, password_hash, role_id, is_active)
               VALUES (?, ?, ?, ?, 1)""",
            (
                app.config["ADMIN_USERNAME"],
                app.config["ADMIN_EMAIL"],
                generate_password_hash(app.config["ADMIN_PASSWORD"]),
                admin_role_id,
            ),
        )
        conn.commit()

    # Genres
    genre_count = conn.execute("SELECT COUNT(*) FROM genres").fetchone()[0]
    if genre_count == 0:
        for name in DEFAULT_GENRES:
            conn.execute(
                "INSERT OR IGNORE INTO genres (name, slug) VALUES (?, ?)",
                (name, _slugify(name)),
            )
        conn.commit()

    # Settings
    default_settings = {
        "site_name": app.config["SITE_NAME"],
        "site_description": app.config["SITE_DESCRIPTION"],
        "footer_text": "Barcha kontent uchinchi tomon rasmiy platformalarida joylashgan.",
    }
    existing_settings = {row[0] for row in conn.execute("SELECT key FROM settings")}
    for key, value in default_settings.items():
        if key not in existing_settings:
            conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()


def _seed_data_pg(conn, app):
    """Boshlang'ich ma'lumotlarni to'ldirish (PostgreSQL)."""
    cursor = conn.cursor()

    # Roles
    cursor.execute("SELECT name FROM roles")
    existing_roles = {row[0] for row in cursor.fetchall()}
    for name, label, perms in DEFAULT_ROLES:
        if name not in existing_roles:
            cursor.execute(
                "INSERT INTO roles (name, label, permissions) VALUES (%s, %s, %s)",
                (name, label, perms),
            )
    conn.commit()

    # Superadmin
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    if user_count == 0:
        from werkzeug.security import generate_password_hash
        cursor.execute("SELECT id FROM roles WHERE name = 'admin'")
        admin_role_id = cursor.fetchone()[0]
        cursor.execute(
            """INSERT INTO users (username, email, password_hash, role_id, is_active)
               VALUES (%s, %s, %s, %s, 1)""",
            (
                app.config["ADMIN_USERNAME"],
                app.config["ADMIN_EMAIL"],
                generate_password_hash(app.config["ADMIN_PASSWORD"]),
                admin_role_id,
            ),
        )
        conn.commit()

    # Genres
    cursor.execute("SELECT COUNT(*) FROM genres")
    genre_count = cursor.fetchone()[0]
    if genre_count == 0:
        for name in DEFAULT_GENRES:
            cursor.execute(
                "INSERT INTO genres (name, slug) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (name, _slugify(name)),
            )
        conn.commit()


def register_db(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db(app)
