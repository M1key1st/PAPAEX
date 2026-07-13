import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _env_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Config:
    # --- Core ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    if not SECRET_KEY:
        import secrets as _secrets
        SECRET_KEY = _secrets.token_hex(32)

    # --- Database ---
    DB_TYPE = os.environ.get("DB_TYPE", "sqlite").lower()  # sqlite / postgresql
    DB_PATH = os.environ.get("DB_PATH", str(BASE_DIR / "instance" / "papex.db"))

    # PostgreSQL
    PG_HOST = os.environ.get("PG_HOST", "localhost")
    PG_PORT = int(os.environ.get("PG_PORT", 5432))
    PG_DATABASE = os.environ.get("PG_DATABASE", "papex")
    PG_USER = os.environ.get("PG_USER", "postgres")
    PG_PASSWORD = os.environ.get("PG_PASSWORD", "")

    # --- Admin bootstrap ---
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@papex.local")

    # --- TMDB ---
    TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "").strip()
    TMDB_API_BASE = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
    TMDB_LANGUAGE = os.environ.get("TMDB_LANGUAGE", "uz-UZ")
    TMDB_FALLBACK_LANGUAGE = "en-US"
    TMDB_ENABLED = bool(TMDB_API_KEY)
    IMAGE_CACHE_ENABLED = _env_bool("IMAGE_CACHE_ENABLED", True)

    # --- Telegram ---
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "").strip()
    TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID)

    # --- Site meta / SEO ---
    SITE_NAME = os.environ.get("SITE_NAME", "PAPEX")
    SITE_URL = os.environ.get("SITE_URL", "http://localhost:5000").rstrip("/")
    SITE_DESCRIPTION = os.environ.get(
        "SITE_DESCRIPTION",
        "PAPEX — Movies, Anime & Entertainment Reimagined.",
    )

    # --- Pagination ---
    PAGE_SIZE = int(os.environ.get("PAGE_SIZE", 24))
    HOME_SECTION_SIZE = int(os.environ.get("HOME_SECTION_SIZE", 10))

    # --- Security ---
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    WTF_CSRF_TIME_LIMIT = None
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "200 per hour")

    # --- Auto Import ---
    AUTO_IMPORT_ENABLED = _env_bool("AUTO_IMPORT_ENABLED", True)
    AUTO_IMPORT_INTERVAL_HOURS = int(os.environ.get("AUTO_IMPORT_INTERVAL_HOURS", 6))

    # --- AI / Maqola Generatsiya ---
    # Provider: openai / gemini / openrouter
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "openai").strip().lower()
    AI_ENABLED = _env_bool("AI_ENABLED", False)
    AI_API_URL = os.environ.get("AI_API_URL", "").strip()
    AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
    AI_MODEL = os.environ.get("AI_MODEL", "").strip()
    AI_DAILY_LIMIT = int(os.environ.get("AI_DAILY_LIMIT", 50))

    # --- Backup ---
    BACKUP_ENABLED = _env_bool("BACKUP_ENABLED", True)
    BACKUP_DIR = os.environ.get("BACKUP_DIR", str(BASE_DIR / "backups"))

    # --- Scheduler ---
    SCHEDULER_ENABLED = _env_bool("SCHEDULER_ENABLED", True)

    # --- Ads ---
    ADS_ENABLED = _env_bool("ADS_ENABLED", False)
    ADSENSE_ID = os.environ.get("ADSENSE_ID", "").strip()
    AD_HEADER = os.environ.get("AD_HEADER", "").strip()
    AD_SIDEBAR = os.environ.get("AD_SIDEBAR", "").strip()
    AD_ARTICLE_TOP = os.environ.get("AD_ARTICLE_TOP", "").strip()
    AD_ARTICLE_BOTTOM = os.environ.get("AD_ARTICLE_BOTTOM", "").strip()

    # --- Cloudflare ---
    TRUSTED_PROXIES = _env_bool("TRUSTED_PROXIES", False)

    DEBUG = _env_bool("FLASK_DEBUG", False)


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


def get_config():
    env = os.environ.get("FLASK_ENV", "production").lower()
    return DevelopmentConfig if env == "development" else ProductionConfig
