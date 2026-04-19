from __future__ import annotations

import re
import unicodedata


def sanitize_name(name: str) -> str:
    name = str(name or "").strip()
    if len(name) > 120:
        name = name[:120]
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = re.sub(r"\s+", " ", name)
    name = name.replace(" ", "_")
    return name or "Unbenannt"


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()
