import re
import unicodedata


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "nom"


def unique_slug(db, name: str, year=None, exclude_id=None) -> str:
    """titles.slug jadvalida takrorlanmaydigan slug generatsiya qiladi."""
    base = slugify(f"{name}-{year}" if year else name)
    slug = base
    counter = 2
    while True:
        query = "SELECT id FROM titles WHERE slug = ?"
        params = [slug]
        if exclude_id:
            query += " AND id != ?"
            params.append(exclude_id)
        row = db.execute(query, params).fetchone()
        if not row:
            return slug
        slug = f"{base}-{counter}"
        counter += 1
