"""AI Provider Service — OpenAI, Gemini, OpenRouter orqali matn generatsiya.

Config orqali AI_PROVIDER tanlanadi:
- openai
- gemini
- openrouter

Agar AI ishlamasa, fallback maqola yaratadi.
"""

import json
import logging

import requests
from flask import current_app

logger = logging.getLogger(__name__)


def _get_provider():
    """Config'dan AI provayderni olish."""
    return current_app.config.get("AI_PROVIDER", "openai").lower()


def _get_api_config():
    """AI provayder uchun API config."""
    provider = _get_provider()
    api_url = current_app.config.get("AI_API_URL", "")
    api_key = current_app.config.get("AI_API_KEY", "")
    model = current_app.config.get("AI_MODEL", "")

    if provider == "openai":
        return {
            "url": api_url or "https://api.openai.com/v1/chat/completions",
            "key": api_key,
            "model": model or "gpt-3.5-turbo",
            "headers": {"Authorization": f"Bearer {api_key}"},
        }
    elif provider == "gemini":
        return {
            "url": api_url or f"https://generativelanguage.googleapis.com/v1beta/models/{model or 'gemini-pro'}:generateContent?key={api_key}",
            "key": api_key,
            "model": model or "gemini-pro",
            "headers": {"Content-Type": "application/json"},
        }
    elif provider == "openrouter":
        return {
            "url": api_url or "https://openrouter.ai/api/v1/chat/completions",
            "key": api_key,
            "model": model or "openai/gpt-3.5-turbo",
            "headers": {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": current_app.config.get("SITE_URL", "https://papex.uz"),
            },
        }
    else:
        return None


def generate_text(prompt, system_prompt=None, max_tokens=1500):
    """AI orqali matn generatsiya qilish."""
    config = _get_api_config()
    if not config or not config["key"]:
        logger.warning("AI API not configured")
        return None

    provider = _get_provider()

    try:
        if provider == "gemini":
            return _call_gemini(config, prompt, system_prompt, max_tokens)
        else:
            return _call_openai_compatible(config, prompt, system_prompt, max_tokens)
    except Exception as e:
        logger.error(f"AI API error ({provider}): {e}")
        return None


def _call_openai_compatible(config, prompt, system_prompt, max_tokens):
    """OpenAI va OpenRouter uchun umumiy so'rov."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        config["url"],
        headers={**config["headers"], "Content-Type": "application/json"},
        json={
            "model": config["model"],
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        },
        timeout=30,
    )

    if resp.status_code == 200:
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    else:
        logger.error(f"AI API returned {resp.status_code}: {resp.text[:200]}")
        return None


def _call_gemini(config, prompt, system_prompt, max_tokens):
    """Google Gemini uchun so'rov."""
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n{prompt}"

    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.7,
        },
    }

    resp = requests.post(
        config["url"],
        headers=config["headers"],
        json=payload,
        timeout=30,
    )

    if resp.status_code == 200:
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            return candidates[0]["content"]["parts"][0]["text"].strip()
    else:
        logger.error(f"Gemini API returned {resp.status_code}: {resp.text[:200]}")
    return None


def is_enabled():
    """AI ishlayaptimi tekshirish."""
    config = _get_api_config()
    return config is not None and bool(config.get("key"))


def get_provider_name():
    """Joriy AI provayder nomi."""
    return _get_provider()
