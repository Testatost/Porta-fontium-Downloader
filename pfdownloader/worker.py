from __future__ import annotations

import os

import requests
from PySide6.QtCore import QThread, Signal

from pfdownloader.app_constants import DEFAULT_HEADERS
from pfdownloader.i18n import LANG
from pfdownloader.metadata_parser import find_iipimage_detail_url, parse_generic_metadata, parse_pf_metadata
from pfdownloader.models import BookEntry
from pfdownloader.page_discovery import find_porta_pages, choose_page_image, probe_numbered_pages, _source_id
from pfdownloader.deepzoom import is_deepzoom, download_deepzoom, ArchiveTemporarilyUnavailable
from pfdownloader.dfg_mets import discover_mets_url, resolve_mets_images, image_download_url, has_external_viewer_marker
from pfdownloader.network import build_download_url, download_image, fetch_html, find_iip_links
from pfdownloader.porta_logic import (
    detect_porta_fontium_category,
    get_ui_type_name,
    get_unique_record_suffix,
    is_porta_fontium,
    localize_porta_fontium_url,
)
from pfdownloader.text_utils import sanitize_name


class DownloaderWorker(QThread):
    log_message = Signal(str)
    book_status = Signal(int, str)
    global_progress = Signal(float)
    finished_signal = Signal()

    def __init__(
        self,
        books: list[BookEntry],
        ui_lang: str = "de",
        parent=None,
    ):
        super().__init__(parent)
        self.books = books
        self.ui_lang = ui_lang
        self._stop_requested = False
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def _t(self, key: str) -> str:
        lang = self.ui_lang if self.ui_lang in LANG else "de"
        return LANG[lang].get(key, LANG["en"].get(key, LANG["de"].get(key, key)))

    def stop(self) -> None:
        self._stop_requested = True

    def parse_pages(self, pages_str: str, total: int) -> list[int]:
        if not str(pages_str).strip():
            return list(range(1, total + 1))

        pages: list[int] = []
        for part in str(pages_str).split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                try:
                    start_page, end_page = map(int, part.split("-", 1))
                    pages.extend(i for i in range(start_page, end_page + 1) if 1 <= i <= total)
                except Exception:
                    pass
            else:
                try:
                    page_number = int(part)
                    if 1 <= page_number <= total:
                        pages.append(page_number)
                except Exception:
                    pass

        return sorted(set(pages))

    def log(self, message: str) -> None:
        self.log_message.emit(message)

    def _resolve_output_folder(self, book: BookEntry, meta: dict) -> tuple[str, str, str, str, str, bool, bool]:
        place_raw = str(meta.get("place", "")).strip() or str(meta.get("title", "")).strip() or "Unknown"

        ui_type_name = get_ui_type_name(meta, self.ui_lang)
        type_name = sanitize_name(ui_type_name)
        category = detect_porta_fontium_category(str(meta.get("url", book.url)))
        is_map = category == "map"
        is_photo = category == "photo"

        year_from = meta.get("year_from")
        year_to = meta.get("year_to")
        if year_from and year_to and year_from != year_to:
            year_span = f"{year_from}-{year_to}"
        elif year_from:
            year_span = year_from
        else:
            year_span = ""

        record_suffix = get_unique_record_suffix(str(meta.get("url", "")) or book.url)

        folder_parts = [type_name]
        if year_span:
            folder_parts.append(year_span)
        if record_suffix:
            folder_parts.append(record_suffix)

        sub_folder_raw = "_".join(folder_parts)
        sub_folder = sanitize_name(sub_folder_raw)
        base_outdir = book.outdir or os.getcwd()
        full_outdir = os.path.join(base_outdir, sub_folder)
        os.makedirs(full_outdir, exist_ok=True)

        type_de = str(meta.get("type_de") or get_ui_type_name(meta, "de") or ui_type_name)
        type_cz = str(meta.get("type_cz") or get_ui_type_name(meta, "cs") or ui_type_name)
        type_en = str(meta.get("type_en") or get_ui_type_name(meta, "en") or ui_type_name)

        return full_outdir, place_raw, type_de, type_cz, type_en, is_map, is_photo

    def run(self) -> None:
        total_books = len(self.books)
        books_done = 0

        for idx, book in enumerate(self.books):
            if self._stop_requested:
                self.log(self._t("worker_cancelled"))
                self.book_status.emit(idx, "❌")
                break

            page_image_cache: dict[str, str] = {}
            mets_url = None
            url = book.url
            metadata_url = localize_porta_fontium_url(url, self.ui_lang)

            try:
                html, resolved_url = fetch_html(metadata_url, self.session)
                if resolved_url != metadata_url:
                    self.log(self._t("worker_redirected").format(url=resolved_url))

                mets_url = discover_mets_url(html, resolved_url)
                if mets_url:
                    self.log(f'DFG-Viewer erkannt: Lade hochauflösende Bilder aus METS: {mets_url}')
                    links = resolve_mets_images(mets_url, self.session)
                    self.log(f'DFG-METS: {len(links)} Bildseite(n) gefunden.')
                else:
                    if has_external_viewer_marker(html):
                        raise ValueError('DFG-Viewer-Verweis erkannt, aber METS-Adresse nicht gefunden. Vorschaubild wird nicht geladen.')
                    links = find_iip_links(html, resolved_url)
                scan_pages = find_porta_pages(html, resolved_url)
                if scan_pages and not mets_url:
                    # Detail URLs represent scans even when their image URLs
                    # are produced dynamically by JavaScript.
                    links = scan_pages
                    self.log(f"Porta Fontium: {len(links)} Bildseite(n) in der Navigation erkannt.")

                if is_porta_fontium(resolved_url) and len(scan_pages) <= 1 and '/iipimage/' in resolved_url:
                    self.log('Keine vollständige Seitennavigation vorhanden; prüfe nummerierte Buchseiten ...')
                    links = probe_numbered_pages(resolved_url, self.session, self.log, image_cache=page_image_cache)

                if is_porta_fontium(resolved_url):
                    base_meta = parse_pf_metadata(html, resolved_url, self.ui_lang)
                    meta = dict(base_meta)

                    detail_url = find_iipimage_detail_url(html, resolved_url)
                    if detail_url:
                        detail_url = localize_porta_fontium_url(detail_url, self.ui_lang)
                        try:
                            detail_html, resolved_detail_url = fetch_html(detail_url, self.session)

                            if resolved_detail_url != detail_url:
                                self.log(self._t("worker_detail_redirected").format(url=resolved_detail_url))

                            detail_meta = parse_pf_metadata(detail_html, resolved_detail_url, self.ui_lang)

                            merged_meta = dict(base_meta)
                            for key, value in detail_meta.items():
                                if value not in ("", None, [], {}):
                                    merged_meta[key] = value

                            merged_meta["url"] = resolved_detail_url
                            meta = merged_meta
                            self.log(self._t("worker_detail_used").format(url=resolved_detail_url))
                            if not mets_url:
                                detail_mets = discover_mets_url(detail_html, resolved_detail_url)
                                if detail_mets:
                                    mets_url = detail_mets
                                    self.log(f'DFG-Viewer im Detail erkannt: {mets_url}')
                                    links = resolve_mets_images(mets_url, self.session)
                                    self.log(f'DFG-METS: {len(links)} Bildseite(n) gefunden.')
                                elif not links:
                                    if has_external_viewer_marker(detail_html):
                                        raise ValueError('DFG-METS konnte nicht ausgewertet werden; kein Vorschaubild als Ersatz')
                                    detail_links = find_porta_pages(detail_html, resolved_detail_url)
                                    links = detail_links or find_iip_links(detail_html, resolved_detail_url)

                        except Exception as detail_exc:
                            self.log(self._t("worker_detail_failed").format(error=detail_exc))
                else:
                    meta = parse_generic_metadata(html, resolved_url)

            except Exception as exc:
                self.log(self._t("worker_load_error").format(url=url, error=exc))
                links = []
                meta = {}

            if not links:
                self.log(self._t("worker_no_pages").format(url=url))
                self.book_status.emit(idx, "⚠️")
                books_done += 1
                self.global_progress.emit((books_done / total_books) * 100 if total_books else 0)
                continue

            full_outdir, _place_raw, type_de, _type_cz, _type_en, is_map, is_photo = self._resolve_output_folder(book, meta)

            title_raw = sanitize_name(meta.get("title", ""))
            type_name = sanitize_name(get_ui_type_name(meta, self.ui_lang) or type_de)
            pages_to_download = self.parse_pages(book.pages, len(links))
            errors = 0
            server_paused = False
            seen_sources: set[str] = set()
            self.log(f'Seiten im Buch: {len(links)}; ausgewählt: {", ".join(map(str, pages_to_download)) or "keine"}')
            if not pages_to_download:
                self.log('Der angegebene Seitenbereich liegt außerhalb der erkannten Seiten.')
                self.book_status.emit(idx, '⚠️')
                books_done += 1
                self.global_progress.emit((books_done / total_books) * 100 if total_books else 0)
                continue

            # Overall progress is book-weighted, with updates within each book.
            # Discovery time is not measurable, but each finished page advances it.
            def report_page_progress(page_index: int, fraction: float = 0.0) -> None:
                fraction = max(0.0, min(1.0, fraction))
                value = 100.0 * (idx + (page_index + fraction) / len(pages_to_download)) / total_books
                self.global_progress.emit(value)

            report_page_progress(0)
            for page_index, page_no in enumerate(pages_to_download):
                if self._stop_requested:
                    errors += 1
                    break

                link = links[page_no - 1]
                if "/iipimage/" in link and "portafontium.eu" in link:
                    try:
                        if link in page_image_cache:
                            link = page_image_cache[link]
                        else:
                            page_html, page_url = fetch_html(localize_porta_fontium_url(link, self.ui_lang), self.session)
                            page_images = find_iip_links(page_html, page_url)
                            if not page_images:
                                raise ValueError("Keine JP2-/DeepZoom-Bildadresse im HTML der Bildseite gefunden")
                            # Never choose a generic first image shared by all pages.
                            link = choose_page_image(page_images, page_url, seen_sources)
                    except Exception as exc:
                        self.log(f"Bildseite {page_no}: {exc} (URL: {link})")
                        errors += 1
                        report_page_progress(page_index, 1.0)
                        continue

                source_id = _source_id(link)
                if source_id in seen_sources:
                    self.log(f'Bildseite {page_no}: identische Bildquelle erkannt; kein doppeltes Bild gespeichert.')
                    errors += 1
                    report_page_progress(page_index, 1.0)
                    continue
                seen_sources.add(source_id)
                self.log(f'Bildseite {page_no}: eindeutige Quelle {source_id}')

                if (is_map or is_photo) and title_raw:
                    fname_raw = f"{type_name}_{title_raw}_{page_no:04d}.jpg"
                else:
                    fname_raw = f"{type_name}_{page_no:04d}.jpg"

                fname = sanitize_name(fname_raw)
                outpath = os.path.join(full_outdir, fname)
                dl_url = image_download_url(link) if mets_url else build_download_url(link)

                self.log(self._t("worker_downloading").format(name=fname, path=outpath))
                # Avoid re-downloading complete images after an interrupted run.
                if os.path.isfile(outpath) and os.path.getsize(outpath) > 0:
                    self.log(f"Bildseite {page_no}: bereits vorhanden, übersprungen.")
                    report_page_progress(page_index, 1.0)
                    continue
                if is_deepzoom(dl_url):
                    try:
                        download_deepzoom(dl_url, outpath, self.session,
                                          stop_requested=lambda: self._stop_requested, log=self.log,
                                          progress=lambda fraction, i=page_index: report_page_progress(i, fraction * 0.98),
                                          workers=7)
                        ok = True
                    except ArchiveTemporarilyUnavailable as exc:
                        self.log(f"[!] Bild {page_no}: {exc}")
                        self.log("[!] Server momentan überlastet oder begrenzt Anfragen. "
                                 "Download angehalten; bereits gespeicherte Seiten bleiben erhalten. "
                                 "Später erneut starten, um vorhandene Bilder zu überspringen.")
                        errors += 1
                        server_paused = True
                        break
                    except Exception as exc:
                        self.log(f"Bild {page_no}: {exc}")
                        ok = False
                else:
                    ok = download_image(dl_url, outpath, self.session)
                if not ok:
                    errors += 1
                report_page_progress(page_index, 1.0)

            if self._stop_requested:
                self.book_status.emit(idx, "❌")
                break

            if server_paused:
                self.book_status.emit(idx, "⚠️")
                break
            if errors == 0:
                self.book_status.emit(idx, "✅")
            elif errors < len(pages_to_download):
                self.book_status.emit(idx, "⚠️")
            else:
                self.book_status.emit(idx, "❌")

            books_done += 1
            self.global_progress.emit((books_done / total_books) * 100 if total_books else 0)

        if 'server_paused' in locals() and server_paused:
            self.log('[!] Download wegen vorübergehender Serverbegrenzung nicht vollständig.')
        else:
            self.log(self._t("worker_all_done"))
        self.finished_signal.emit()
