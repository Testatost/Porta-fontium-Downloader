from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from pfdownloader.porta_logic import is_porta_fontium


def fetch_html(url: str, session: requests.Session) -> tuple[str, str]:
    verify = not is_porta_fontium(url)
    response = session.get(url, timeout=20, verify=verify)
    response.raise_for_status()
    return response.text, response.url


def extract_dfg_images(url: str) -> list[str]:
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except Exception:
        return []

    match = re.search(r"https://www\.gda\.bayern\.de/digitalisat/iiif/[0-9a-f-]+/[0-9]+", response.text)
    return [match.group(0)] if match else []


def find_iip_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")

    manifest = re.search(r'https://[^"\']+/iiif/.+?/manifest', html)
    if manifest:
        return [manifest.group(0)]

    gda_image = re.search(r'https://www\.gda\.bayern\.de/digitalisat/(?:iiif|jpeg)/[^"\s]+', html)
    if gda_image:
        return [gda_image.group(0)]

    mets = re.search(r"https://www\.gda\.bayern\.de/mets/[0-9a-f-]+", html)
    if mets:
        return extract_dfg_images(mets.group(0))

    if "dfg-viewer.de" in base_url:
        return extract_dfg_images(base_url)

    links: list[str] = []
    for tag in soup.find_all(["a", "img"]):
        attr = tag.get("href") or tag.get("src")
        if not attr:
            continue
        if any(token in attr for token in ["iipsrv", "fcgi-bin", ".jp2"]):
            links.append(urljoin(base_url, attr))

    return list(dict.fromkeys(links))


def build_download_url(iip_url: str) -> str:
    if "/iiif/" in iip_url and "/manifest" not in iip_url:
        return iip_url.rstrip("/") + "/full/full/0/default.jpg"

    parsed = urlparse(iip_url)
    qs = parse_qs(parsed.query)
    fif = qs.get("FIF", [None])[0]
    if not fif:
        return iip_url

    base = parsed.scheme + "://" + parsed.netloc + parsed.path
    return f"{base}?FIF={fif}&cvt=jpeg&Q=90"


def download_image(url: str, path: str, session: requests.Session, retries: int = 3) -> bool:
    for attempt in range(retries):
        try:
            verify = not is_porta_fontium(url)
            response = session.get(url, stream=True, timeout=60, verify=verify)
            response.raise_for_status()
            with open(path, "wb") as handle:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        handle.write(chunk)
            return True
        except Exception:
            if attempt == retries - 1:
                return False
    return False
