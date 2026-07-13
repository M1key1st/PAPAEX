# PAPEX V2

Movies, Anime & Entertainment Reimagined.

## Xususiyatlari

- **Blueprint Architecture** — modular code structure
- **Service Layer** — business logic abstraction
- **Flask Login** — authentication system
- **Role System** — admin/editor/moderator permissions
- **Admin Panel** — full-featured dashboard
- **TMDB Integration** — auto movie import
- **AI News Engine** — automatic article generation
- **Search System** — SQLite FTS5 full-text search
- **Vote System** — like/dislike
- **Bookmark System** — save favorites
- **SEO** — JSON-LD, Open Graph, sitemap
- **Sitemap** — auto-split for 50000+ URLs
- **RSS Feed** — content syndication
- **Cache System** — local image caching
- **Scheduler** — APScheduler for background tasks
- **Auto Import** — trending/popular movies
- **Backup System** — automatic database backup
- **Health Check** — /health and /status endpoints
- **Ads System** — Google AdSense integration
- **Docker** — containerized deployment
- **PostgreSQL** — optional database support
- **Cloudflare** — proxy and security headers

## O'rnatish

### 1. Oddiy usul (SQLite)

```bash
# Repository ni clone qilish
git clone https://github.com/username/papex.git
cd papex

# Virtual environment yaratish
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Dependenciyalar o'rnatish
pip install -r requirements.txt

# .env faylini yaratish
cp .env.example .env
# .env faylini tahrirlang

# Serverni ishga tushirish
python run.py
```

### 2. Docker usuli

```bash
# Docker Compose bilan
docker-compose up -d

# PostgreSQL bilan
docker-compose --profile postgresql up -d

# Production (Nginx bilan)
docker-compose --profile production up -d
```

### 3. Production deployment

```bash
# Serverga ulanish
ssh user@your-server

# Kodni yuklab olish
git clone https://github.com/username/papex.git
cd papex

# Virtual environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# .env konfiguratsiya
cp .env.example .env
nano .env

# Systemd service
sudo cp papex.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable papex
sudo systemctl start papex

# Nginx konfiguratsiya
sudo cp nginx/nginx.conf /etc/nginx/nginx.conf
sudo nginx -t
sudo systemctl restart nginx
```

## Konfiguratsiya

### AI Provider

```env
# OpenAI
AI_PROVIDER=openai
AI_API_KEY=sk-...

# Google Gemini
AI_PROVIDER=gemini
AI_API_KEY=...

# OpenRouter
AI_PROVIDER=openrouter
AI_API_KEY=sk-or-...
```

### Database

```env
# SQLite (default)
DB_TYPE=sqlite
DB_PATH=instance/papex.db

# PostgreSQL
DB_TYPE=postgresql
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=papex
PG_USER=postgres
PG_PASSWORD=your-password
```

### Ads

```env
ADS_ENABLED=true
ADSENSE_ID=ca-pub-...
AD_HEADER=<ins class="adsbygoogle" ...></ins>
AD_SIDEBAR=<ins class="adsbygoogle" ...></ins>
AD_ARTICLE_TOP=<ins class="adsbygoogle" ...></ins>
AD_ARTICLE_BOTTOM=<ins class="adsbygoogle" ...></ins>
```

## API Endpointlar

- `GET /` — Bosh sahifa
- `GET /turkum/<category>` — Kategoriya sahifasi
- `GET /qidiruv` — Qidiruv
- `GET /movie/<slug>` — Kino detail
- `GET /maqolalar` — Maqolalar ro'yxati
- `GET /maqola/<id>` — Maqola detail
- `GET /health` — Health check
- `GET /status` — Server holati
- `GET /sitemap.xml` — Sitemap
- `GET /rss.xml` — RSS feed
- `POST /api/vote/<id>` — Ovoz berish
- `POST /api/bookmark/<id>` — Bookmark

## Admin Panel

- `/admin` — Dashboard
- `/admin/movies` — Kontent boshqaruvi
- `/admin/auto-import` — Auto import
- `/admin/articles` — Maqolalar
- `/admin/backups` — Backup
- `/admin/scheduler` — Scheduler
- `/admin/stats` — Statistika
- `/admin/settings` — Sozlamalar

## License

MIT
