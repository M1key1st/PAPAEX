"""
Eski loyihadagi sayt.db (titles + watch_links, eski schema) ma'lumotlarini
yangi PAPEX schema'siga ko'chiradi.

Ishlatish:
    python migrations/migrate_legacy.py /yo'l/eski_sayt.db

Skript:
- eski 'titles' jadvalidagi har bir yozuvni yangi 'titles' jadvaliga ko'chiradi
  (slug avtomatik generatsiya qilinadi, TMDB maydonlari bo'sh qoldiriladi —
  keyinchalik admin panelda "TMDB'dan olish" tugmasi bilan to'ldirish mumkin)
- eski 'watch_links'ni yangi 'watch_links'ga ko'chiradi
- takroriy ishga tushirishda mavjud slug'larni qayta yozmaydi (idempotent)
"""

import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import get_config  # noqa: E402


def slugify(text, suffix=""):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    if suffix:
        text = f"{text}-{suffix}"
    return text or "nom"


def unique_slug(cur, base_name, year):
    base = slugify(base_name, str(year) if year else "")
    slug = base
    i = 2
    while cur.execute("SELECT 1 FROM titles WHERE slug = ?", (slug,)).fetchone():
        slug = f"{base}-{i}"
        i += 1
    return slug


def main():
    if len(sys.argv) != 2:
        print("Ishlatish: python migrations/migrate_legacy.py /yo'l/eski_sayt.db")
        sys.exit(1)

    legacy_path = Path(sys.argv[1])
    if not legacy_path.exists():
        print(f"Fayl topilmadi: {legacy_path}")
        sys.exit(1)

    config = get_config()
    new_db_path = Path(config.DB_PATH)
    if not new_db_path.exists():
        print(f"Yangi baza topilmadi: {new_db_path}. Avval 'python run.py' ni bir marta ishga tushiring.")
        sys.exit(1)

    old = sqlite3.connect(legacy_path)
    old.row_factory = sqlite3.Row
    new = sqlite3.connect(new_db_path)
    new.row_factory = sqlite3.Row
    new.execute("PRAGMA foreign_keys = ON")

    old_titles = old.execute("SELECT * FROM titles").fetchall()
    migrated, skipped = 0, 0

    for t in old_titles:
        exists = new.execute(
            "SELECT id FROM titles WHERE name = ? AND year IS ?", (t["name"], t["year"])
        ).fetchone()
        if exists:
            skipped += 1
            continue

        slug = unique_slug(new, t["name"], t["year"])
        cur = new.execute(
            """INSERT INTO titles
               (name, slug, category, summary, year, quality_score, quality_label,
                poster_note, published_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'published')""",
            (
                t["name"],
                slug,
                t["category"],
                t["summary"],
                t["year"],
                t["quality_score"],
                t["quality_label"],
                t["poster_note"],
                t["published"] if "published" in t.keys() else None,
            ),
        )
        new_title_id = cur.lastrowid

        links = old.execute(
            "SELECT * FROM watch_links WHERE title_id = ?", (t["id"],)
        ).fetchall()
        for link in links:
            new.execute(
                "INSERT INTO watch_links (title_id, platform, url) VALUES (?, ?, ?)",
                (new_title_id, link["platform"], link["url"]),
            )
        migrated += 1

    new.commit()
    old.close()
    new.close()

    print(f"Ko'chirildi: {migrated} ta yozuv. O'tkazib yuborildi (allaqachon mavjud): {skipped} ta.")


if __name__ == "__main__":
    main()
