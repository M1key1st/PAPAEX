PRAGMA foreign_keys = ON;

-- ================= ROLES & USERS (admin panel autentifikatsiyasi) =================

CREATE TABLE IF NOT EXISTS roles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,          -- admin / editor / moderator
    label       TEXT NOT NULL,
    permissions TEXT NOT NULL DEFAULT ''        -- vergul bilan ajratilgan ruxsatlar ro'yxati
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role_id       INTEGER NOT NULL,
    is_active     INTEGER NOT NULL DEFAULT 1,
    last_login_at TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (role_id) REFERENCES roles (id)
);

-- ================= GENRES =================

CREATE TABLE IF NOT EXISTS genres (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    slug          TEXT NOT NULL UNIQUE,
    tmdb_genre_id INTEGER
);

-- ================= TITLES (kino / anime / multfilm) =================

CREATE TABLE IF NOT EXISTS titles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tmdb_id         INTEGER,
    imdb_id         TEXT,
    name            TEXT NOT NULL,
    original_name   TEXT,
    slug            TEXT NOT NULL UNIQUE,
    category        TEXT NOT NULL,              -- kino / anime / multfilm
    summary         TEXT NOT NULL DEFAULT '',
    tagline         TEXT,
    year            INTEGER,
    release_date    TEXT,
    runtime         INTEGER,                    -- daqiqalarda
    country         TEXT,
    director        TEXT,
    poster_path     TEXT,                        -- TMDB masofaviy yo'l (masalan /abc.jpg)
    backdrop_path   TEXT,
    poster_local    TEXT,                        -- static/cache/posters/<file> (keshlangan)
    backdrop_local  TEXT,
    poster_note     TEXT,                        -- rasm bo'lmaganda emoji fallback (eski dizayn)
    trailer_url     TEXT,
    quality_score   REAL NOT NULL DEFAULT 0,      -- 0-10
    quality_label   TEXT NOT NULL DEFAULT 'HD',
    status          TEXT NOT NULL DEFAULT 'published',   -- published / draft
    is_trending     INTEGER NOT NULL DEFAULT 0,
    views_count     INTEGER NOT NULL DEFAULT 0,
    likes_count     INTEGER NOT NULL DEFAULT 0,
    dislikes_count  INTEGER NOT NULL DEFAULT 0,
    popularity      REAL NOT NULL DEFAULT 0,
    published_at    TEXT NOT NULL DEFAULT (datetime('now')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_titles_category ON titles (category);
CREATE INDEX IF NOT EXISTS idx_titles_published_at ON titles (published_at);
CREATE INDEX IF NOT EXISTS idx_titles_quality_score ON titles (quality_score);
CREATE INDEX IF NOT EXISTS idx_titles_views_count ON titles (views_count);
CREATE INDEX IF NOT EXISTS idx_titles_slug ON titles (slug);
CREATE INDEX IF NOT EXISTS idx_titles_status ON titles (status);
CREATE INDEX IF NOT EXISTS idx_titles_tmdb_id ON titles (tmdb_id);

CREATE TABLE IF NOT EXISTS title_genres (
    title_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,
    PRIMARY KEY (title_id, genre_id),
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_title_genres_genre ON title_genres (genre_id);

CREATE TABLE IF NOT EXISTS title_cast (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id       INTEGER NOT NULL,
    actor_name     TEXT NOT NULL,
    character_name TEXT,
    profile_path   TEXT,
    sort_order     INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_title_cast_title ON title_cast (title_id);
CREATE INDEX IF NOT EXISTS idx_title_cast_actor ON title_cast (actor_name);

-- Rasmiy tomosha platformalariga havolalar (eski loyihadan saqlanadi)
CREATE TABLE IF NOT EXISTS watch_links (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id INTEGER NOT NULL,
    platform TEXT NOT NULL,
    url      TEXT NOT NULL,
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_watch_links_title ON watch_links (title_id);

-- ================= VOTES (like/dislike) =================

CREATE TABLE IF NOT EXISTS votes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id   INTEGER NOT NULL,
    voter_key  TEXT NOT NULL,           -- cookie/session identifikatori
    ip_hash    TEXT NOT NULL,
    value      INTEGER NOT NULL,        -- 1 = like, -1 = dislike
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE,
    UNIQUE (title_id, voter_key)
);
CREATE INDEX IF NOT EXISTS idx_votes_title ON votes (title_id);

-- ================= BOOKMARKS =================

CREATE TABLE IF NOT EXISTS bookmarks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id   INTEGER NOT NULL,
    voter_key  TEXT NOT NULL,           -- foydalanuvchi login bo'lmasa ham cookie orqali ishlaydi
    user_id    INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL,
    UNIQUE (title_id, voter_key)
);
CREATE INDEX IF NOT EXISTS idx_bookmarks_voter ON bookmarks (voter_key);

-- ================= VIEWS (ko'rishlar, dedup uchun) =================

CREATE TABLE IF NOT EXISTS views (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id   INTEGER NOT NULL,
    voter_key  TEXT NOT NULL,
    ip_hash    TEXT NOT NULL,
    viewed_on  TEXT NOT NULL,           -- YYYY-MM-DD, kunlik dedup uchun
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE,
    UNIQUE (title_id, voter_key, viewed_on)
);
CREATE INDEX IF NOT EXISTS idx_views_title ON views (title_id);

-- ================= SETTINGS =================

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

-- ================= LOGS (admin harakatlari) =================

CREATE TABLE IF NOT EXISTS logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    actor      TEXT NOT NULL,           -- username yoki 'system'
    action     TEXT NOT NULL,           -- create/update/delete/login/...
    target     TEXT,                    -- masalan 'title:42'
    details    TEXT,
    ip         TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs (created_at);

-- ================= TELEGRAM QUEUE (keyingi faza uchun tayyor) =================

CREATE TABLE IF NOT EXISTS telegram_queue (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id   INTEGER NOT NULL,
    status     TEXT NOT NULL DEFAULT 'pending',   -- pending / sent / failed
    message    TEXT,
    error      TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    sent_at    TEXT,
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE
);

-- ================= ARTICLES (AI maqolalar) =================

CREATE TABLE IF NOT EXISTS articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id        INTEGER NOT NULL,
    title           TEXT NOT NULL DEFAULT '',
    summary         TEXT NOT NULL DEFAULT '',
    content         TEXT NOT NULL DEFAULT '',
    seo_description TEXT NOT NULL DEFAULT '',
    telegram_text   TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'draft',    -- draft / published
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_articles_title_id ON articles (title_id);
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles (status);

-- ================= AUTO IMPORT QUEUE =================

CREATE TABLE IF NOT EXISTS import_queue (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tmdb_id     INTEGER NOT NULL,
    source      TEXT NOT NULL DEFAULT 'manual',  -- manual / trending / popular / top_rated / upcoming / tv / anime
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending / processing / completed / failed
    title_id    INTEGER,
    error       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    processed_at TEXT,
    FOREIGN KEY (title_id) REFERENCES titles (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_import_queue_status ON import_queue (status);

-- ================= AUTO IMPORT LOG =================

CREATE TABLE IF NOT EXISTS auto_import_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at      TEXT NOT NULL DEFAULT (datetime('now')),
    source      TEXT NOT NULL,
    items_found INTEGER NOT NULL DEFAULT 0,
    items_added INTEGER NOT NULL DEFAULT 0,
    items_skipped INTEGER NOT NULL DEFAULT 0,
    errors      INTEGER NOT NULL DEFAULT 0,
    details     TEXT
);

-- ================= ANALYTICS (kunlik trafik) =================

CREATE TABLE IF NOT EXISTS daily_stats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL UNIQUE,
    page_views  INTEGER NOT NULL DEFAULT 0,
    unique_visitors INTEGER NOT NULL DEFAULT 0,
    new_titles  INTEGER NOT NULL DEFAULT 0,
    new_articles INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats (date);

-- ================= BACKUPS =================

CREATE TABLE IF NOT EXISTS backups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT NOT NULL,
    size_bytes  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ================= FTS5 FULL-TEXT SEARCH =================

CREATE VIRTUAL TABLE IF NOT EXISTS titles_fts USING fts5(
    name,
    original_name,
    summary,
    director,
    content=titles,
    content_rowid=id,
    tokenize='unicode61 remove_diacritics 2'
);

-- FTS triggers: titles ga o'zgarish bo'lganda FTS ni yangilash
CREATE TRIGGER IF NOT EXISTS titles_ai AFTER INSERT ON titles BEGIN
    INSERT INTO titles_fts(rowid, name, original_name, summary, director)
    VALUES (new.id, new.name, new.original_name, new.summary, new.director);
END;

CREATE TRIGGER IF NOT EXISTS titles_ad AFTER DELETE ON titles BEGIN
    INSERT INTO titles_fts(titles_fts, rowid, name, original_name, summary, director)
    VALUES('delete', old.id, old.name, old.original_name, old.summary, old.director);
END;

CREATE TRIGGER IF NOT EXISTS titles_au AFTER UPDATE ON titles BEGIN
    INSERT INTO titles_fts(titles_fts, rowid, name, original_name, summary, director)
    VALUES('delete', old.id, old.name, old.original_name, old.summary, old.director);
    INSERT INTO titles_fts(rowid, name, original_name, summary, director)
    VALUES (new.id, new.name, new.original_name, new.summary, new.director);
END;
