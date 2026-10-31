"""Porta Fontium scan discovery with strict per-page source verification."""
from __future__ import annotations

import html as html_lib
import re
from urllib.parse import quote, unquote, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

_PAGE = re.compile(r'^/iipimage/(\d+)/([^/?#]+)$', re.I)
_SERIAL = re.compile(r'^(.*_)(\d{4,6})([^/]*)$')


def _clean(url: str) -> str:
    p = urlparse(url)
    return urlunparse(p._replace(query='', fragment=''))


def _key(url: str):
    p = urlparse(url)
    m = _PAGE.match(unquote(p.path).rstrip('/'))
    return (m.group(1), m.group(2)) if m else None


def _serial(url: str):
    key = _key(url)
    return _SERIAL.match(key[1]) if key else None


def _source_id(url: str) -> str:
    """Normalize image identity, not the entire URL (including language or zoom)."""
    p = urlparse(url)
    from urllib.parse import parse_qs
    q = parse_qs(p.query)
    raw = q.get('DeepZoom', q.get('FIF', [url]))[0]
    return unquote(raw).split('.jp2')[0].lower().rstrip('/')


def find_porta_pages(document: str, base_url: str) -> list[str]:
    """Collect ordered links to scans of the SAME register.

    Never interpret duplicated thumbnail links or the current image as
    multiple pages. Link order comes from scan serials, not HTML placement.
    """
    original = _key(base_url)
    if not original:
        return []
    host = (urlparse(base_url).hostname or '').removeprefix('www.').lower()
    soup = BeautifulSoup(document, 'html.parser')
    candidates = [_clean(base_url)]
    for tag in soup.find_all(['a', 'link'], href=True):
        candidates.append(urljoin(base_url, html_lib.unescape(tag['href'])))
    text = html_lib.unescape(document).replace('\\/', '/')
    for path in re.findall(r'(?:https?://[^\s"\'<>\\]+)?/iipimage/\d+/[^\s"\'<>?&#\\]+', text, re.I):
        candidates.append(urljoin(base_url, path))
    base_serial = _serial(base_url)
    valid = {}
    for url in candidates:
        parsed = urlparse(url)
        if (parsed.hostname or '').removeprefix('www.').lower() != host:
            continue
        key = _key(url)
        if not key or key[0] != original[0]:
            continue
        if base_serial:
            candidate_serial = _serial(url)
            if not candidate_serial or (candidate_serial.group(1), candidate_serial.group(3)) != (base_serial.group(1), base_serial.group(3)):
                continue
        valid.setdefault(_clean(url), None)
    def sortkey(url):
        match = _serial(url)
        return (int(match.group(2)) if match else 0, url)
    return sorted(valid, key=sortkey)


def choose_page_image(images: list[str], page_url: str, used: set[str] | None = None) -> str:
    """Return only the source belonging to this page; refuse ambiguous matches."""
    used = used if used is not None else set()
    serial = _serial(page_url)
    if serial:
        slug = _key(page_url)[1]
        matches = []
        for image in images:
            # The JP2 filename and the detail URL usually share the same scan name.
            # Compare basename, allowing an optional -z or similar viewer suffix.
            source = _source_id(image).rsplit('/', 1)[-1]
            stem = serial.group(1) + serial.group(2)
            if source == slug or source == stem or source.startswith(stem + '-') or source.startswith(stem + '_'):
                matches.append(image)
        unique = list(dict.fromkeys(_source_id(m) for m in matches))
        if len(unique) == 1:
            selected = matches[0]
            if _source_id(selected) in used:
                raise ValueError('Dieselbe Bildquelle wurde bereits einer anderen Seite zugeordnet')
            return selected
        if len(unique) > 1:
            raise ValueError('Mehrere unterschiedliche JP2-Quellen für dieselbe Seite: Zuordnung unklar')
    # One source is safe only when it has not been attributed to another page.
    unique_images = list({ _source_id(i): i for i in images }.values())
    if len(unique_images) == 1 and _source_id(unique_images[0]) not in used:
        if serial:
            raise ValueError('Die Bildquelle stimmt nicht mit der gewünschten Seitennummer überein')
        return unique_images[0]
    raise ValueError('Keine eindeutig passende Bildquelle für die ausgewählte Seite')


def probe_numbered_pages(start_url: str, session, log=None, max_pages: int = 600, image_cache: dict | None = None) -> list[str]:
    """Fallback when the HTML omits the gallery: check adjacent numbered scan URLs.

    The server must respond with a distinct, matching scan source. Merely
    returning HTTP 200 is *not* proof that the requested scan exists.
    """
    serial = _serial(start_url)
    key = _key(start_url)
    if not serial or not key:
        return [start_url]
    from pfdownloader.network import fetch_html, find_iip_links
    parsed = urlparse(start_url)
    # Porta scans typically have 0010, 0020, ...; preserve the observed width.
    step = 10 if int(serial.group(2)) % 10 == 0 else 1
    first = step
    current = int(serial.group(2))
    start = first if current <= max_pages * step else current
    found = []
    seen_sources = set()
    misses = 0
    for number in range(start, start + max_pages * step, step):
        slug = f'{serial.group(1)}{number:0{len(serial.group(2))}d}{serial.group(3)}'
        candidate = urlunparse(parsed._replace(path=f'/iipimage/{key[0]}/{quote(slug)}', query='', fragment=''))
        try:
            page_html, resolved = fetch_html(candidate, session)
            sources = find_iip_links(page_html, resolved)
            # Ensure source actually matches requested scan number; guards
            # against a server that returns the first scan for any URL.
            chosen = choose_page_image(sources, candidate)
            source = _source_id(chosen)
            expected = f'{serial.group(1)}{number:0{len(serial.group(2))}d}'
            basename = source.rsplit('/', 1)[-1]
            if not (basename == expected or basename.startswith(expected + '-') or basename.startswith(expected + '_')):
                raise ValueError('Server gab eine andere Bildseite zurück')
            if source in seen_sources:
                raise ValueError('Wiederholte Bildquelle statt neuer Seite')
            seen_sources.add(source)
            found.append(candidate)
            if image_cache is not None:
                image_cache[candidate] = chosen
            misses = 0
        except Exception:
            misses += 1
            if misses >= 2 and number >= current:
                break
    if log:
        log(f'Seitensuche: {len(found)} unterschiedliche, geprüfte Buchseiten gefunden.')
    return found if found else [start_url]
