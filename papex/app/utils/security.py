import hashlib
import re
import uuid

from flask import current_app, request, session

VOTER_COOKIE_KEY = "papex_vid"


def hash_ip(ip: str) -> str:
    """IP manzilni qaytarib bo'lmaydigan tarzda xeshlaydi (loglarda xom IP saqlanmaydi)."""
    salt = current_app.config["SECRET_KEY"]
    return hashlib.sha256(f"{salt}:{ip}".encode("utf-8")).hexdigest()


def get_client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "0.0.0.0"


def get_voter_key() -> str:
    """Har bir brauzer uchun barqaror, imzolangan sessiya-cookie asosidagi identifikator.

    Login qilmagan foydalanuvchilar uchun ovoz berish/bookmark/ko'rishlarni
    IP + cookie orqali cheklash imkonini beradi (Cookie/IP himoyasi).
    """
    if VOTER_COOKIE_KEY not in session:
        session[VOTER_COOKIE_KEY] = uuid.uuid4().hex
        session.permanent = True
    return session[VOTER_COOKIE_KEY]


_SAFE_TEXT_RE = re.compile(r"^[\w\s\-\.,'\"!?():;/\u0400-\u04FF\u0100-\u017F&%+#@]*$", re.UNICODE)


def clean_text(value: str, max_length: int = 5000) -> str:
    """XSS/injection oldini olish uchun matnni qisqartiradi va kesuvchi bo'shliqlarni tozalaydi.

    Jinja2 avtomatik ravishda HTML-escape qiladi, shuning uchun bu funksiya
    asosan uzunlik va boshqaruv belgilaridan himoya qiladi.
    """
    if value is None:
        return ""
    value = str(value).strip()
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)  # boshqaruv belgilari
    return value[:max_length]


def is_safe_url(target: str) -> bool:
    """Open-redirect hujumlarining oldini olish uchun faqat ichki (nisbiy) URL'larga ruxsat beradi."""
    if not target:
        return False
    return target.startswith("/") and not target.startswith("//")
