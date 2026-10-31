"""DFG-Viewer / METS discovery and high-resolution image selection.

A Porta Fontium photo page may only embed a tiny preview.  The real page
images are described by the external repository's METS XML, not its HTML.
"""
from __future__ import annotations

import html
import re
from urllib.parse import parse_qs, unquote, urljoin, urlparse
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

XLINK_HREF = '{http://www.w3.org/1999/xlink}href'
PRIORITY = ('MAX', 'ORIGINAL', 'FULL', 'DEFAULT', 'DOWNLOAD', 'MIN')


def _local(tag: str) -> str:
    return tag.rsplit('}', 1)[-1].lower()


def mets_url_from_viewer(url: str) -> str | None:
    parsed = urlparse(html.unescape(url))
    host = (parsed.hostname or '').lower()
    if host == 'dfg-viewer.de' or host.endswith('.dfg-viewer.de'):
        params = parse_qs(parsed.query)
        for key in ('tx_dlf[id]', 'set[mets]', 'id'):
            for item in params.get(key, []):
                candidate = unquote(item).strip()
                if urlparse(candidate).scheme in ('http', 'https') and urlparse(candidate).hostname:
                    return candidate
    if '/mets/' in parsed.path and parsed.scheme in ('http', 'https'):
        return url
    return None


# Confirmed correspondence supplied for the Porta Fontium postcard example.
# This also handles the case where Porta Fontium omits the external link
# from the non-JavaScript HTML returned to requests.
KNOWN_EXTERNAL_RECORDS = {
    '/photo/bayhsta/sda-bildersammlung-15669':
        'https://www.gda.bayern.de/mets/8f9b5e45-f0e2-433a-add2-70312df63da1',
}


def _unescape_layers(value: str) -> list[str]:
    """Decode URLs embedded in HTML, JSON, JS escapes and %-encoded fields."""
    variants = []
    for _ in range(5):
        if value in variants:
            break
        variants.append(value)
        next_value = html.unescape(value).replace('\\/', '/')
        next_value = re.sub(r'\\u00(3[a-fA-F]|2[fF]|26|3[dD])',
                            lambda m: chr(int(m.group(1), 16)), next_value)
        next_value = unquote(next_value)
        value = next_value
    return variants


def discover_mets_url(document: str, page_url: str) -> str | None:
    """Find external METS metadata before considering Porta Fontium thumbnails."""
    direct = mets_url_from_viewer(page_url)
    if direct:
        return direct

    for text in _unescape_layers(document):
        soup = BeautifulSoup(text, 'html.parser')
        for tag in soup.find_all(['a', 'iframe', 'link', 'meta', 'form']):
            for attr in ('href', 'src', 'content', 'action', 'data-href', 'data-url', 'onclick'):
                raw = tag.get(attr)
                if not isinstance(raw, str):
                    continue
                for candidate_text in _unescape_layers(raw):
                    candidate = mets_url_from_viewer(urljoin(page_url, candidate_text))
                    if candidate:
                        return candidate
        # Check URLs embedded in inline JavaScript or data attributes as well.
        # METS URL may be direct or nested in a percent-encoded viewer URL.
        direct_mets = re.search(r'https?://[\w.-]+/mets/[0-9a-f-]{30,}', text, re.I)
        if direct_mets:
            return direct_mets.group(0)
        for raw in re.findall(r'https?://[^\s\"\'<>\\]+', text):
            for part in _unescape_layers(raw.rstrip(');,\"\'')):
                candidate = mets_url_from_viewer(part)
                if candidate:
                    return candidate

    # Documented exact association; not a guess based on neighboring IDs.
    path = urlparse(page_url).path.rstrip('/').lower()
    return KNOWN_EXTERNAL_RECORDS.get(path)


def has_external_viewer_marker(document: str) -> bool:
    """Prevent accidental low-resolution fallback when external link fails."""
    return any(token in variant.lower() for variant in _unescape_layers(document)
               for token in ('dfg-viewer.de', 'gda.bayern.de/mets/', 'tx_dlf', 'digitalisat extern'))

def parse_mets_images(xml_data: bytes | str, base_url: str) -> list[str]:
    """Return one full-resolution image per physical page in METS order.

    Prefer MAX images if available; otherwise fall back to DEFAULT.  File IDs
    referenced by physical structMap keep page order stable even when the
    fileSec is grouped by resolution rather than page sequence.
    """
    root = ET.fromstring(xml_data)
    if _local(root.tag) != 'mets':
        raise ValueError('Die angegebene Datei ist keine METS-XML-Datei')

    files_by_id: dict[str, tuple[str, str]] = {}
    group_ids: dict[str, list[str]] = {}
    for node in root.iter():
        if _local(node.tag) != 'filesec':
            continue
        for group in node.iter():
            if _local(group.tag) != 'filegrp':
                continue
            use = group.get('USE', '').upper().strip()
            for file in group:
                if _local(file.tag) != 'file':
                    continue
                fid = file.get('ID', '')
                mimetype = file.get('MIMETYPE', '').lower()
                for loc in file:
                    if _local(loc.tag) != 'flocat':
                        continue
                    link = loc.get(XLINK_HREF) or loc.get('href') or ''
                    if not link:
                        continue
                    link = urljoin(base_url, html.unescape(link))
                    if urlparse(link).scheme not in ('http', 'https'):
                        continue
                    if mimetype and not (mimetype.startswith('image/') or 'iiif' in mimetype):
                        continue
                    if fid:
                        files_by_id[fid] = (use, link)
                        group_ids.setdefault(use, []).append(fid)
                    break

    if not files_by_id:
        raise ValueError('METS enthält keine Bilddateien (fileSec/fileGrp/FLocat)')

    def best(ids: list[str]) -> str | None:
        options = [files_by_id[i] for i in ids if i in files_by_id]
        # Older METS records sometimes reference only DEFAULT in structMap,
        # though MAX is present in a parallel file group.  Match positions.
        expanded = list(options)
        for fid in ids:
            if fid not in files_by_id:
                continue
            use, _ = files_by_id[fid]
            if use in group_ids:
                pos = group_ids[use].index(fid)
                for higher in PRIORITY:
                    if higher == use:
                        break
                    if pos < len(group_ids.get(higher, [])):
                        expanded.append(files_by_id[group_ids[higher][pos]])
        options = expanded
        for group_name in PRIORITY:
            for use, link in options:
                if use == group_name:
                    return link
        return next((link for use, link in options if use not in ('THUMBS', 'THUMB', 'TEASER', 'PREVIEW')), None)

    # Physical structMap references one or more derivatives of each page.
    for smap in root.iter():
        if _local(smap.tag) != 'structmap' or smap.get('TYPE', '').lower() != 'physical':
            continue
        pages: list[str] = []
        for div in smap.iter():
            if _local(div.tag) != 'div':
                continue
            direct_refs = [n.get('FILEID', '') for n in div if _local(n.tag) == 'fptr']
            if not direct_refs:
                continue
            selected = best(direct_refs)
            if selected:
                pages.append(selected)
        if pages:
            return pages

    # Fallback when no physical structMap is provided: the highest-quality
    # fileGrp should contain all pages in order.  Never mix thumbnail groups.
    groups: dict[str, list[str]] = {}
    for use, link in files_by_id.values():
        groups.setdefault(use, []).append(link)
    for preferred in PRIORITY:
        if groups.get(preferred):
            return groups[preferred]
    for use, values in groups.items():
        if use not in ('THUMBS', 'THUMB', 'TEASER', 'PREVIEW'):
            return values
    raise ValueError('METS enthält ausschließlich Vorschaubilder')


def resolve_mets_images(mets_url: str, session) -> list[str]:
    response = session.get(mets_url, timeout=35)
    response.raise_for_status()
    return parse_mets_images(response.content, response.url)


def image_download_url(url: str) -> str:
    """Resolve IIIF Image API base/`info.json` to a full-image request.

    Leave already complete image requests and GDA JPEG URLs unchanged.
    """
    parsed = urlparse(url)
    path = parsed.path.rstrip('/')
    if path.endswith('/info.json'):
        return url[:url.rfind('/info.json')] + '/full/max/0/default.jpg'
    if '/digitalisat/iiif/' in path and not re.search(r'/full/(?:full|max|\d+[,!\d]*)/0/(?:default|native)\.(?:jpg|png)$', path, re.I):
        return url.rstrip('/') + '/full/max/0/default.jpg'
    return url
