from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pfdownloader.metadata_patterns import CATEGORY_LABELS, REGISTER_CODE_PATTERNS, TYPE_PATTERNS
from pfdownloader.text_utils import normalize_text, sanitize_name


def get_localized_label(item: dict, lang: str) -> str:
    return str(item.get(lang) or item.get("de") or "").strip()


def is_porta_fontium(url: str) -> bool:
    return "portafontium.eu" in str(url or "")


def localize_porta_fontium_url(url: str, lang: str) -> str:
    if not is_porta_fontium(url):
        return url

    preferred_lang = lang if lang in {"de", "cs"} else "de"
    parsed = urlparse(url)
    params = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key != "language"]
    params.append(("language", preferred_lang))
    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))


def detect_porta_fontium_category(url: str) -> str | None:
    lowered = str(url or "").lower()
    for category in CATEGORY_LABELS:
        if f"/{category}/" in lowered or f"/searching/{category}" in lowered or f"/contents/{category}" in lowered:
            return category
    if "/searching/register" in lowered or "/contents/register" in lowered:
        return "register"
    return None


def looks_generic_type(value: str) -> bool:
    normalized = normalize_text(value)
    return normalized in {
        "matrik",
        "register",
        "chronik",
        "chronicle",
        "kronika",
        "dokument",
        "document",
        "map",
        "mapa",
        "karte",
        "photo",
        "foto",
        "fotografie",
        "urkunde",
        "deed",
        "listina",
        "amtsbuch",
        "official book",
        "uredni kniha",
        "periodikum",
        "periodical",
    }


def translate_known_type(text: str, lang: str) -> str | None:
    normalized = normalize_text(text)
    if not normalized:
        return None

    for pattern in TYPE_PATTERNS:
        aliases = [normalize_text(alias) for alias in pattern["aliases"]]
        if any(alias and alias in normalized for alias in aliases):
            return get_localized_label(pattern, lang)
    return None


def extract_register_types_from_codes(text: str, lang: str) -> list[str]:
    found: list[str] = []
    for key, pattern in REGISTER_CODE_PATTERNS:
        if pattern.search(text):
            label = next((get_localized_label(item, lang) for item in TYPE_PATTERNS if item["key"] == key), "")
            if label and label not in found:
                found.append(label)
    return found


def infer_display_type(meta: dict, url: str, ui_lang: str) -> str:
    title = str(meta.get("title", "")).strip()
    book_type = str(meta.get("book_type", "")).strip()
    detail_text = str(meta.get("detail_text", "")).strip()
    combined = "\n".join(part for part in [book_type, title, detail_text, str(meta.get("date_raw", ""))] if part)

    translated_book_type = translate_known_type(book_type, ui_lang)
    if translated_book_type:
        return translated_book_type

    register_labels = extract_register_types_from_codes(combined, ui_lang)
    if register_labels:
        return " + ".join(register_labels)

    translated_title = translate_known_type(title, ui_lang)
    if translated_title:
        return translated_title

    category = detect_porta_fontium_category(url)
    if category == "register" and book_type and not looks_generic_type(book_type):
        return book_type

    if category in {"chronicle", "amtsbuch", "map", "photo", "periodical", "deed", "census"} and title:
        return title

    if book_type and not looks_generic_type(book_type):
        return book_type

    if category and category in CATEGORY_LABELS:
        return get_localized_label(CATEGORY_LABELS[category], ui_lang)

    return title or book_type or "Dokument"


def get_ui_type_name(meta: dict, ui_lang: str) -> str:
    lang_key = {"de": "type_de", "en": "type_en", "cs": "type_cz"}.get(ui_lang, "type_de")
    localized = str(meta.get(lang_key) or "").strip()
    if localized:
        return localized

    for candidate in (meta.get("display_type"), meta.get("book_type"), meta.get("title")):
        translated = translate_known_type(str(candidate or ""), ui_lang)
        if translated:
            return translated

    category = detect_porta_fontium_category(str(meta.get("url", "")))
    if category and category in CATEGORY_LABELS:
        return get_localized_label(CATEGORY_LABELS[category], ui_lang)

    fallback = str(meta.get("display_type") or meta.get("book_type") or meta.get("title") or "").strip()
    if fallback:
        return fallback

    return {"de": "Dokument", "en": "Document", "cs": "Dokument"}.get(ui_lang, "Dokument")


def looks_like_porta_navigation_text(text: str) -> bool:
    value = normalize_text(text)
    if not value:
        return True

    bad_parts = [
        "direkt zum inhalt",
        "porta fontium",
        "hauptmenu",
        "hauptmenü",
        "obsah",
        "recherche",
        "uber das projekt",
        "über das projekt",
        "hilfe",
        "cesky",
        "čeština",
        "deutsch",
        "nr.",
        "←",
        "→",
    ]

    hits = sum(1 for part in bad_parts if part in value)
    if hits >= 2:
        return True
    if len(value) > 120 and hits >= 1:
        return True
    return False


def get_unique_record_suffix(url: str) -> str:
    path = urlparse(str(url or "")).path.rstrip("/")

    match = re.search(r"/iipimage/(\d+)(?:/([^/]+))?$", path, re.IGNORECASE)
    if match:
        return match.group(1)

    parts = [part for part in path.split("/") if part]
    for part in reversed(parts):
        part = part.strip()
        if part and not part.isdigit() and not looks_like_porta_navigation_text(part):
            return sanitize_name(part)

    return ""
