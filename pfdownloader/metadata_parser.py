from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from pfdownloader.metadata_patterns import CATEGORY_LABELS, TYPE_PATTERNS
from pfdownloader.porta_logic import (
    detect_porta_fontium_category,
    get_localized_label,
    infer_display_type,
)
from pfdownloader.text_utils import normalize_text


def find_iipimage_detail_url(html: str, base_url: str) -> str | None:
    parsed = urlparse(base_url)
    path = parsed.path.rstrip("/")

    if re.search(r"/iipimage/\d+/[^/]+$", path, re.IGNORECASE):
        return base_url

    match = re.search(r"/iipimage/(\d+)$", path)
    if not match:
        return None

    image_id = re.escape(match.group(1))
    pattern = re.compile(rf"/iipimage/{image_id}/[^\"'#?\s]+", re.IGNORECASE)

    candidates: list[str] = []
    soup = BeautifulSoup(html, "html.parser")

    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        href = str(canonical.get("href", "")).strip()
        if pattern.search(href):
            candidates.append(urljoin(base_url, href))

    og_url = soup.find("meta", property="og:url")
    if og_url and og_url.get("content"):
        href = str(og_url.get("content", "")).strip()
        if pattern.search(href):
            candidates.append(urljoin(base_url, href))

    for tag in soup.find_all("a", href=True):
        href = str(tag.get("href", "")).strip()
        if pattern.search(href):
            candidates.append(urljoin(base_url, href))

    for found in pattern.findall(html):
        candidates.append(urljoin(base_url, found))

    unique: list[str] = []
    seen = set()
    for candidate in candidates:
        candidate = candidate.strip()
        if candidate and candidate not in seen:
            unique.append(candidate)
            seen.add(candidate)

    return unique[0] if unique else None


def parse_pf_metadata(html: str, url: str, ui_lang: str = "de") -> dict:
    soup = BeautifulSoup(html, "html.parser")
    meta = {"source": "Porta fontium", "url": url}

    html_tag = soup.find("html")
    if html_tag:
        lang = html_tag.get("xml:lang") or html_tag.get("lang")
        if lang:
            meta["lang"] = lang

    title = None
    h1 = soup.find("h1", id="page-title") or soup.find("h1", class_="title")
    if h1:
        title = h1.get_text(" ", strip=True)

    if not title:
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            title = str(og["content"]).strip()

    if not title and soup.title and soup.title.string:
        candidate = soup.title.string.strip()
        if len(candidate) < 200:
            title = candidate

    meta["title"] = title or "Unbenannt"

    place = None
    place_selectors = [
        ".field-name-field-doc-place .field-items",
        ".field-name-field-place .field-items",
        ".field-name-field-register-place .field-items",
        ".field-name-field-origin-place .field-items",
    ]

    for selector in place_selectors:
        place_field = soup.select_one(selector)
        if place_field:
            strongs = [
                item.get_text(" ", strip=True)
                for item in place_field.select("strong")
                if item.get_text(strip=True)
            ]
            place = ", ".join(strongs) if strongs else place_field.get_text(" ", strip=True)
            if place:
                break

    if not place:
        for label_text in ("Místo:", "Místo", "Ort:", "Ort", "Place:", "Place"):
            label = soup.find(
                lambda tag: tag.name in ("div", "span", "th", "td")
                and label_text.lower() in tag.get_text(" ", strip=True).lower()
            )
            if label and label.parent:
                full = label.parent.get_text(" ", strip=True)
                rest = full.replace(label_text, "").strip(" : ")
                if rest:
                    place = rest
                    break

    if place:
        meta["place"] = place

    type_items: list[str] = []
    type_selectors = (
        ".field-name-field-register-type .field-item",
        ".field-name-field-book-type .field-item",
        ".field-name-field-doc-type .field-item",
        ".field-name-field-type .field-item",
    )
    for selector in type_selectors:
        for item in soup.select(selector):
            text_value = item.get_text(" ", strip=True)
            if text_value and text_value not in type_items:
                type_items.append(text_value)

    if not type_items:
        type_keywords = (
            "typ",
            "type",
            "book type",
            "buchtyp",
            "typ knihy",
            "druh matriky",
            "typ matriky",
        )
        for field in soup.select(".field, tr"):
            label = field.select_one(".field-label, th")
            if not label:
                continue
            label_text = label.get_text(" ", strip=True).lower()
            if any(keyword in label_text for keyword in type_keywords):
                values = field.select(".field-item, td")
                if values:
                    for item in values:
                        text_value = item.get_text(" ", strip=True)
                        if text_value and text_value != label.get_text(" ", strip=True) and text_value not in type_items:
                            type_items.append(text_value)
                else:
                    field_text = field.get_text(" ", strip=True)
                    rest = field_text.replace(label.get_text(" ", strip=True), "", 1).strip(" : ")
                    if rest and rest not in type_items:
                        type_items.append(rest)
                if type_items:
                    break

    if type_items:
        meta["book_type"] = " | ".join(type_items)
    else:
        category = detect_porta_fontium_category(url)
        if category and category in CATEGORY_LABELS:
            meta["book_type"] = get_localized_label(CATEGORY_LABELS[category], ui_lang)
        else:
            meta["book_type"] = "Dokument"

    detail_chunks: list[str] = []
    for selector in (
        ".field-name-field-register-content .field-item",
        ".field-name-field-doc-content .field-item",
        ".field-name-field-content .field-item",
        ".field-name-field-regest .field-item",
        ".field-name-field-original-title .field-item",
    ):
        for item in soup.select(selector):
            text_value = item.get_text(" ", strip=True)
            if text_value:
                detail_chunks.append(text_value)

    if not detail_chunks:
        body_text = soup.get_text("\n", strip=True)
        detail_chunks.append(body_text[:4000])

    meta["detail_text"] = "\n".join(detail_chunks)

    date_text = None
    date_field = soup.select_one(".field-name-field-doc-dates .field-item")
    if date_field:
        date_text = date_field.get_text(" ", strip=True)

    if not date_text:
        candidate = soup.find(string=lambda s: s and "-" in s and any(ch.isdigit() for ch in s))
        if candidate:
            date_text = str(candidate).strip()

    if date_text:
        meta["date_raw"] = date_text
        years = re.findall(r"(\d{3,4})", date_text)
        if len(years) >= 2:
            meta["year_from"], meta["year_to"] = years[0], years[1]
        elif len(years) == 1:
            meta["year_from"] = meta["year_to"] = years[0]

    material_section = None
    for legend_label in (
        "Materiál / forma",
        "Material / Form",
        "Materiál / form",
        "Materiál / Forma",
        "Material / forma",
    ):
        leg = soup.find("legend", string=lambda t: t and legend_label.lower() in t.lower())
        if leg:
            material_section = leg.find_parent("fieldset")
            if material_section:
                break

    if material_section:
        meta["material_section_text"] = material_section.get_text("\n", strip=True)

    display_type = infer_display_type(meta, url, ui_lang)
    meta["display_type"] = display_type
    matched_pattern = None
    normalized_display_type = normalize_text(display_type)
    for pattern in TYPE_PATTERNS:
        aliases = [normalize_text(alias) for alias in pattern["aliases"]]
        labels = [normalize_text(get_localized_label(pattern, language)) for language in ("de", "cs", "en")]
        if normalized_display_type in labels or any(alias and alias in normalized_display_type for alias in aliases):
            matched_pattern = pattern
            break

    if matched_pattern:
        meta["type_de"] = get_localized_label(matched_pattern, "de")
        meta["type_cz"] = get_localized_label(matched_pattern, "cs")
        meta["type_en"] = get_localized_label(matched_pattern, "en")
    else:
        meta["type_de"] = display_type
        meta["type_cz"] = display_type
        meta["type_en"] = display_type

    return meta


def parse_generic_metadata(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    meta = {"source": "generic", "url": url}

    title = soup.title.string.strip() if soup.title and soup.title.string else None
    if title:
        meta["title"] = title

    text = soup.get_text(" ", strip=True)
    years = re.findall(r"\b(1[5-9]\d{2}|20[0-2]\d)\b", text)
    if years:
        meta["year_from"] = years[0]
        meta["year_to"] = years[-1]

    meta["book_type"] = "Dokument"
    meta["type_de"] = "Dokument"
    meta["type_cz"] = "Dokument"
    meta["type_en"] = "Document"
    return meta
