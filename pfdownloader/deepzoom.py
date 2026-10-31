"""DeepZoom support for Porta Fontium's IIPImage server."""
from __future__ import annotations

import html as html_module
import math
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from io import BytesIO
from urllib.parse import quote, unquote, urlparse
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import requests
from PIL import Image


_DEEPZOOM_PATTERN = re.compile(r"DeepZoom=([^\s\"'<>]+?\.jp2)(?=\.dzi|_files|[&\"'<>\s]|$)", re.I)
_JP2_PATTERN = re.compile(r"(?:register|chronicle|amtsbuch|map|photo|periodical|deed|census)/[^\s\"'<>\\?&]+?\.jp2", re.I)


class ArchiveTemporarilyUnavailable(RuntimeError):
    """Archive is rejecting requests; pause rather than skipping further pages."""


def _retry_delay(response, attempt: int) -> float:
    """Honor Retry-After with a bounded fallback, without hammering the server."""
    value = response.headers.get('Retry-After', '')
    try:
        delay = float(value)
    except (ValueError, TypeError):
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            delay = (date - datetime.now(timezone.utc)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            delay = 2.0 * (2 ** attempt)
    return max(1.0, min(45.0, delay))


def extract_deepzoom_links(document: str, base_url: str) -> list[str]:
    """Recognize embedded IIPImage paths, including legacy viewer JavaScript."""
    document = html_module.unescape(document).replace('\\/', '/')
    base = urlparse(base_url)
    origin = f"{base.scheme}://{base.netloc}"
    results = []
    paths = [m.group(1) for m in _DEEPZOOM_PATTERN.finditer(document)]
    # Some viewers expose only the JP2 path, not a literal DeepZoom= URL.
    paths += [m.group(0) for m in _JP2_PATTERN.finditer(document)]
    for raw in paths:
        path = unquote(raw).split('?', 1)[0].lstrip('/')
        if not path or '..' in path.split('/'):
            continue
        url = f"{origin}/fcgi-bin/iipsrv.fcgi?DeepZoom={quote(path, safe='/:-_.')}"
        if url not in results:
            results.append(url)
    return results


def is_deepzoom(url: str) -> bool:
    return 'DeepZoom=' in url and '.jp2' in url.lower()


def download_deepzoom(url: str, output_path: str, session: requests.Session,
                      stop_requested=None, log=None, progress=None, workers: int = 10) -> None:
    """Fetch descriptor and all full-resolution tiles; never save partial output."""
    verify = "portafontium.eu" not in urlparse(url).hostname.lower() if urlparse(url).hostname else True
    root = url.split('DeepZoom=', 1)[0] + 'DeepZoom=' + url.split('DeepZoom=', 1)[1].split('.jp2', 1)[0] + '.jp2'
    desc_url = root + '.dzi'
    response = session.get(desc_url, timeout=35, verify=verify)
    if getattr(response, "status_code", 200) in (429, 503):
        raise ArchiveTemporarilyUnavailable(f'Bildserver meldet HTTP {response.status_code} für die Bildbeschreibung')
    response.raise_for_status()
    descriptor = ET.fromstring(response.content)
    if descriptor.tag.rsplit('}', 1)[-1] != 'Image':
        raise ValueError('Ungültige DeepZoom-Beschreibung (kein Image-Element)')
    tile_size = int(descriptor.attrib['TileSize'])
    overlap = int(descriptor.attrib.get('Overlap', '0'))
    ext = descriptor.attrib.get('Format', 'jpg')
    size = next((node for node in descriptor if node.tag.rsplit('}', 1)[-1] == 'Size'), None)
    if size is None:
        raise ValueError('DeepZoom-Beschreibung enthält keine Bildmaße')
    width, height = int(size.attrib['Width']), int(size.attrib['Height'])
    if tile_size <= 0 or width <= 0 or height <= 0 or width * height > 350_000_000:
        raise ValueError(f'Ungültige oder zu große Bildmaße: {width}×{height}')
    level = math.ceil(math.log2(max(width, height)))
    cols = math.ceil(width / tile_size)
    rows = math.ceil(height / tile_size)
    if log:
        log(f'DeepZoom: {width} × {height} Pixel, {cols * rows} Kacheln')
    # Moderate concurrency improves throughput on high-latency servers.
    # Keep it bounded to avoid overwhelming the archive or consuming too much RAM.
    workers = max(1, min(12, int(workers)))
    # Each thread owns its own Session: requests.Session is not thread-safe.
    thread_state = threading.local()
    headers = dict(session.headers)
    cooldown_lock = threading.Lock()
    cooldown_until = [0.0]
    # One image may contain hundreds of tiles. Keep rate-limit logs concise.
    rate_notice_lock = threading.Lock()
    rate_notice_count = [0]
    rate_notice_codes = set()

    def note_server_limit(status_code: int, delay: float) -> None:
        with rate_notice_lock:
            rate_notice_count[0] += 1
            first = rate_notice_count[0] == 1
            rate_notice_codes.add(status_code)
        if first and log:
            log(
                f'Bildserver meldet HTTP {status_code}; '
                f'Anfragen werden vorübergehend pausiert '
                f'(mindestens {delay:g} Sekunden). '
                'Weitere gleichartige Meldungen werden zusammengefasst.'
            )

    def summarize_server_limits() -> None:
        with rate_notice_lock:
            count = rate_notice_count[0]
            codes = ', '.join(f'HTTP {code}' for code in sorted(rate_notice_codes))
        if count > 1 and log:
            log(f'Bildserver-Begrenzung: {count} Serverantworten ({codes}) '
                'während dieser Bildseite zusammengefasst.')


    def wait_for_cooldown():
        while True:
            if stop_requested and stop_requested():
                raise RuntimeError('Download abgebrochen')
            with cooldown_lock:
                delay = cooldown_until[0] - time.monotonic()
            if delay <= 0:
                return
            time.sleep(min(0.25, delay))

    def apply_cooldown(delay):
        with cooldown_lock:
            cooldown_until[0] = max(cooldown_until[0], time.monotonic() + delay)

    def load_tile(x: int, y: int):
        if stop_requested and stop_requested():
            raise RuntimeError('Download abgebrochen')
        if not hasattr(thread_state, 'session'):
            thread_state.session = requests.Session()
            thread_state.session.headers.update(headers)
        local_session = thread_state.session
        tile_url = f'{root}_files/{level}/{x}_{y}.{ext}'
        last_error = None
        for attempt in range(4):
            wait_for_cooldown()
            try:
                with local_session.get(tile_url, timeout=35, verify=verify) as tile_response:
                    if getattr(tile_response, "status_code", 200) in (429, 503):
                        delay = _retry_delay(tile_response, attempt)
                        apply_cooldown(delay)
                        last_error = f'HTTP {tile_response.status_code}'
                        note_server_limit(tile_response.status_code, delay)
                        continue
                    tile_response.raise_for_status()
                    blob = tile_response.content
                    if not tile_response.headers.get('Content-Type', '').lower().startswith('image/') and not blob.startswith((b'\xff\xd8', b'\x89PNG')):
                        raise ValueError('Server liefert keine Bildkachel')
                with Image.open(BytesIO(blob)) as tile:
                    tile.load()
                    left = overlap if x > 0 else 0
                    top = overlap if y > 0 else 0
                    cropped = tile.crop((left, top, tile.width, tile.height)).convert('RGB')
                return x, y, cropped
            except (requests.RequestException, OSError, ValueError) as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(min(2.0 * (attempt + 1), 5.0))
        if isinstance(last_error, str) and last_error.startswith('HTTP '):
            raise ArchiveTemporarilyUnavailable(f'Bildkachel {x},{y}: {last_error} trotz Wartezeit. Bitte später fortsetzen.')
        raise RuntimeError(f'Bildkachel {x},{y} konnte nicht geladen werden: {last_error}')

    output = Image.new('RGB', (width, height))
    total_tiles = cols * rows
    completed = 0
    coordinates = ((x, y) for y in range(rows) for x in range(cols))
    try:
        # Keep only a small number of in-flight tiles in memory.
        pool = ThreadPoolExecutor(max_workers=workers)
        try:
            pending = {}
            def enqueue():
                try:
                    x, y = next(coordinates)
                except StopIteration:
                    return False
                future = pool.submit(load_tile, x, y)
                pending[future] = (x, y)
                return True

            for _ in range(min(total_tiles, workers)):
                enqueue()
            while pending:
                if stop_requested and stop_requested():
                    raise RuntimeError('Download abgebrochen')
                done, _ = wait(pending, timeout=0.25, return_when=FIRST_COMPLETED)
                for future in done:
                    pending.pop(future)
                    x, y, cropped = future.result()
                    try:
                        output.paste(cropped, (x * tile_size, y * tile_size))
                    finally:
                        cropped.close()
                    completed += 1
                    if progress:
                        progress(completed / total_tiles)
                    enqueue()
        finally:
            pool.shutdown(wait=True, cancel_futures=True)
        if stop_requested and stop_requested():
            raise RuntimeError('Download abgebrochen')
        tmp = output_path + '.part.jpg'
        try:
            output.save(tmp, format='JPEG', quality=92)
            os.replace(tmp, output_path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    finally:
        output.close()
        summarize_server_limits()
