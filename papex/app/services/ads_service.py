"""Ads System — Google AdSense joylashuvlari.

Joylashuvlar:
- Header
- Sidebar
- Article Top
- Article Bottom
"""

from flask import current_app


def is_enabled():
    """Reklama yoqilganmi."""
    return current_app.config.get("ADS_ENABLED", False)


def get_adsense_id():
    """Google AdSense ID."""
    return current_app.config.get("ADSENSE_ID", "")


def get_ad(code_key):
    """Config'dan reklama kodini olish."""
    return current_app.config.get(code_key, "")


def get_header_ad():
    """Header reklama."""
    return get_ad("AD_HEADER")


def get_sidebar_ad():
    """Sidebar reklama."""
    return get_ad("AD_SIDEBAR")


def get_article_top_ad():
    """Maqola yuqorisidagi reklama."""
    return get_ad("AD_ARTICLE_TOP")


def get_article_bottom_ad():
    """Maqola pastidagi reklama."""
    return get_ad("AD_ARTICLE_BOTTOM")


def get_adsense_script():
    """Google AdSense JavaScript."""
    adsense_id = get_adsense_id()
    if not adsense_id:
        return ""
    return f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={adsense_id}" crossorigin="anonymous"></script>'


def get_adsense_tag(ad_slot, ad_format="auto", ad_style=None):
    """AdSense reklama tegi."""
    adsense_id = get_adsense_id()
    if not adsense_id:
        return ""

    style = ad_style or 'display:block'
    return f'''<ins class="adsbygoogle"
     style="{style}"
     data-ad-client="{adsense_id}"
     data-ad-slot="{ad_slot}"
     data-ad-format="{ad_format}"
     data-full-width-responsive="true"></ins>
<script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>'''


def inject_ads_context():
    """Template context ga reklama ma'lumotlarini qo'shish."""
    if not is_enabled():
        return {}

    return {
        "ads_enabled": True,
        "adsense_id": get_adsense_id(),
        "ad_header": get_header_ad(),
        "ad_sidebar": get_sidebar_ad(),
        "ad_article_top": get_article_top_ad(),
        "ad_article_bottom": get_article_bottom_ad(),
        "adsense_script": get_adsense_script(),
    }
