from __future__ import annotations

import os

import requests
from PySide6.QtCore import QThread, Signal

from pfdownloader.app_constants import DEFAULT_HEADERS
from pfdownloader.metadata_parser import find_iipimage_detail_url, parse_generic_metadata, parse_pf_metadata
from pfdownloader.models import BookEntry
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
                self.log("[*] Abgebrochen.")
                self.book_status.emit(idx, "❌")
                break

            url = book.url
            metadata_url = localize_porta_fontium_url(url, self.ui_lang)

            try:
                html, resolved_url = fetch_html(metadata_url, self.session)
                if resolved_url != metadata_url:
                    self.log(f"[ℹ️] Weitergeleitet nach: {resolved_url}")

                links = find_iip_links(html, resolved_url)

                if is_porta_fontium(resolved_url):
                    base_meta = parse_pf_metadata(html, resolved_url, self.ui_lang)
                    meta = dict(base_meta)

                    detail_url = find_iipimage_detail_url(html, resolved_url)
                    if detail_url:
                        detail_url = localize_porta_fontium_url(detail_url, self.ui_lang)
                        try:
                            detail_html, resolved_detail_url = fetch_html(detail_url, self.session)

                            if resolved_detail_url != detail_url:
                                self.log(f"[ℹ️] Detail weitergeleitet nach: {resolved_detail_url}")

                            detail_meta = parse_pf_metadata(detail_html, resolved_detail_url, self.ui_lang)

                            merged_meta = dict(base_meta)
                            for key, value in detail_meta.items():
                                if value not in ("", None, [], {}):
                                    merged_meta[key] = value

                            merged_meta["url"] = resolved_detail_url
                            meta = merged_meta
                            self.log(f"[ℹ️] Detail-Metadaten verwendet: {resolved_detail_url}")

                        except Exception as detail_exc:
                            self.log(f"[!] Detail-Metadaten konnten nicht geladen werden: {detail_exc}")
                else:
                    meta = parse_generic_metadata(html, resolved_url)

            except Exception as exc:
                self.log(f"[!] Fehler beim Laden von {url}: {exc}")
                links = []
                meta = {}

            if not links:
                self.log(f"[!] Keine Seiten für {url}")
                self.book_status.emit(idx, "⚠️")
                books_done += 1
                self.global_progress.emit((books_done / total_books) * 100 if total_books else 0)
                continue

            full_outdir, _place_raw, type_de, _type_cz, _type_en, is_map, is_photo = self._resolve_output_folder(book, meta)

            title_raw = sanitize_name(meta.get("title", ""))
            type_name = sanitize_name(get_ui_type_name(meta, self.ui_lang) or type_de)
            pages_to_download = self.parse_pages(book.pages, len(links))
            errors = 0

            for page_no in pages_to_download:
                if self._stop_requested:
                    errors += 1
                    break

                link = links[page_no - 1]

                if (is_map or is_photo) and title_raw:
                    fname_raw = f"{type_name}_{title_raw}_{page_no:04d}.jpg"
                else:
                    fname_raw = f"{type_name}_{page_no:04d}.jpg"

                fname = sanitize_name(fname_raw)
                outpath = os.path.join(full_outdir, fname)
                dl_url = build_download_url(link)

                self.log(f"Lade {fname} -> {outpath}")
                ok = download_image(dl_url, outpath, self.session)
                if not ok:
                    errors += 1

            if errors == 0:
                self.book_status.emit(idx, "✅")
            elif errors < len(pages_to_download):
                self.book_status.emit(idx, "⚠️")
            else:
                self.book_status.emit(idx, "❌")

            books_done += 1
            self.global_progress.emit((books_done / total_books) * 100 if total_books else 0)

        self.log("[*] Alle Bücher fertig.")
        self.finished_signal.emit()
