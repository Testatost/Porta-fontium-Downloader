from __future__ import annotations

import html
import json
import os
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from PySide6.QtCore import QSettings, QSize, QStringListModel, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QDesktopServices,
    QFont,
    QFontDatabase,
    QIcon,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QStyle,
    QStyleFactory,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from pfdownloader.browser_open import open_external_url
from pfdownloader.app_constants import (
    APP_AUTHOR,
    APP_DISPLAY_NAME,
    APP_FONT,
    APP_GITHUB_URL,
    APP_VERSION,
    SETTINGS_APP,
    SETTINGS_ORG,
)
from pfdownloader.icons import get_app_icon, get_banner_pixmap
from pfdownloader.i18n import LANG, LANGUAGE_LABELS, SUPPORTED_LANGS
from pfdownloader.models import BookEntry
from pfdownloader.styles import dark_stylesheet, light_stylesheet
from pfdownloader.third_party import A4, HAVE_REPORTLAB, canvas
from pfdownloader.worker import DownloaderWorker


class ShortcutLineEdit(QLineEdit):
    ctrlReturnPressed = Signal()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and event.modifiers() & Qt.ControlModifier:
            self.ctrlReturnPressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class DownwardComboBox(QComboBox):
    def showPopup(self) -> None:
        super().showPopup()
        popup = self.view().window()
        if popup is not None:
            popup.move(self.mapToGlobal(self.rect().bottomLeft()))


class HelpDialog(QDialog):
    def __init__(self, parent: QWidget | None, title: str, html_text: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(get_app_icon())
        self.resize(720, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        banner_label = QLabel()
        banner_pixmap = get_banner_pixmap(680, 120)
        if not banner_pixmap.isNull():
            banner_label.setPixmap(banner_pixmap)
            banner_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(banner_label)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(html_text)
        layout.addWidget(browser, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class HistoryDialog(QDialog):
    def __init__(self, parent: QWidget | None, title: str, entries: list[str]):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(get_app_icon())
        self.resize(760, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setReadOnly(True)
        lines = []
        for index, entry in enumerate(entries, 1):
            safe_entry = html.escape(str(entry or ""))
            lines.append(f"<p style='margin:0 0 8px 0;'><b>{index}.</b> <a href='{safe_entry}'>{safe_entry}</a></p>")
        browser.setHtml("".join(lines))
        layout.addWidget(browser, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class MainWindow(QMainWindow):
    def __init__(self, *, windows_safe_mode: bool = False):
        super().__init__()
        self._windows_safe_mode = windows_safe_mode
        self._windows_style_mode = os.environ.get("PF_DOWNLOADER_UI_MODE", "full")
        if not windows_safe_mode:
            self.setWindowIcon(get_app_icon())
        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self.lang = self._load_language_setting()
        self.is_dark = self._load_theme_setting()
        self._emoji_family = self._find_emoji_font_family()
        self.last_outdir = self._load_outdir_setting()
        self.history_limit = self._load_history_limit_setting()
        self.book_history = self._load_history_setting()
        self.books: list[BookEntry] = []
        self.worker: DownloaderWorker | None = None
        self._syncing_table = False
        self._last_search_text = ""

        self.setWindowTitle(self._t("title"))
        self.resize(1000, 900)
        self.setMinimumSize(880, 580)
        self.setFont(APP_FONT)

        qapp = QStyleFactory.create("Fusion")
        if qapp:
            self.setStyle(qapp)

        self._building_initial_ui = True
        self._build_ui()
        self.retranslate_ui()
        self._building_initial_ui = False
        self.apply_theme()
        self.statusBar().showMessage(self._t("status_ready"))

    def _t(self, key: str) -> str:
        lang_map = LANG.get(self.lang) or LANG.get("en") or LANG["de"]
        if key in lang_map:
            return lang_map[key]
        if key in LANG.get("en", {}):
            return LANG["en"][key]
        return LANG["de"].get(key, key)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.btn_home = QPushButton()
        self.btn_home.clicked.connect(self.open_home)
        top_bar.addWidget(self.btn_home)

        self.btn_theme = QPushButton()
        self.btn_theme.setFixedSize(46, 40)
        self.btn_theme.clicked.connect(self.toggle_theme)
        top_bar.addWidget(self.btn_theme)

        self.btn_help = QPushButton("?")
        self.btn_help.setFixedSize(46, 40)
        self.btn_help.clicked.connect(self.show_help_dialog)
        top_bar.addWidget(self.btn_help)

        top_bar.addStretch(1)

        self.lbl_language = QLabel()
        top_bar.addWidget(self.lbl_language)

        self.language_combo = DownwardComboBox()
        self.language_combo.setMinimumHeight(40)
        self.language_combo.setMinimumWidth(145)
        self.language_combo.setMaximumWidth(175)
        self.language_combo.setMaxVisibleItems(len(SUPPORTED_LANGS))
        self._build_language_menu()
        top_bar.addWidget(self.language_combo)

        main_layout.addLayout(top_bar)

        input_group = QGroupBox()
        input_layout = QGridLayout(input_group)
        input_layout.setHorizontalSpacing(12)
        input_layout.setVerticalSpacing(10)

        self.lbl_url = QLabel()
        self.url_entry = ShortcutLineEdit()
        self.url_entry.setPlaceholderText("https://www.portafontium.eu/…")
        self.url_entry.setClearButtonEnabled(True)
        self.history_model = QStringListModel(self.book_history, self)
        self.url_completer = QCompleter(self.history_model, self)
        self.url_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.url_completer.setFilterMode(Qt.MatchContains)
        self.url_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.url_completer.setMaxVisibleItems(12)
        self.url_entry.setCompleter(self.url_completer)
        self.url_entry.returnPressed.connect(self.add_book)
        self.url_entry.ctrlReturnPressed.connect(self.on_url_ctrl_return)

        self.btn_history = QPushButton()
        self.btn_history.setFixedHeight(40)
        self.btn_history.setMinimumWidth(0)
        self.btn_history.setMaximumWidth(16777215)
        self.btn_history.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.history_menu = QMenu(self)
        self.btn_history.setMenu(self.history_menu)

        input_layout.addWidget(self.lbl_url, 0, 0)
        input_layout.addWidget(self.url_entry, 0, 1, 1, 2)
        input_layout.addWidget(self.btn_history, 0, 3)

        self.lbl_outdir = QLabel()
        self.outdir_entry = QLineEdit()
        self.outdir_entry.setText(self.last_outdir)
        self.outdir_entry.setClearButtonEnabled(True)
        self.outdir_entry.editingFinished.connect(self.on_outdir_changed)
        input_layout.addWidget(self.lbl_outdir, 1, 0)
        input_layout.addWidget(self.outdir_entry, 1, 1, 1, 2)

        self.btn_choose = QPushButton()
        self.btn_choose.setFixedHeight(40)
        self.btn_choose.clicked.connect(self.choose_dir)
        input_layout.addWidget(self.btn_choose, 1, 3)

        self.lbl_pages = QLabel()
        self.pages_entry = QLineEdit()
        self.pages_entry.setClearButtonEnabled(True)
        input_layout.addWidget(self.lbl_pages, 2, 0)
        input_layout.addWidget(self.pages_entry, 2, 1)

        self.lbl_pages_hint = QLabel()
        self.lbl_pages_hint.setObjectName("hintLabel")
        input_layout.addWidget(self.lbl_pages_hint, 2, 2, 1, 2)

        input_layout.setColumnStretch(1, 2)
        input_layout.setColumnStretch(2, 2)
        input_layout.setColumnStretch(3, 1)

        main_layout.addWidget(input_group)

        self.btn_add_book = QPushButton()
        self.btn_add_book.setObjectName("addBookButton")
        self.btn_add_book.clicked.connect(self.add_book)

        self.btn_delete_book = QPushButton()
        self.btn_delete_book.setObjectName("deleteBookButton")
        self.btn_delete_book.clicked.connect(self.delete_book)

        self.btn_change_pages = QPushButton()
        self.btn_change_pages.setObjectName("changePagesButton")
        self.btn_change_pages.clicked.connect(self.change_pages)

        self.btn_download = QPushButton()
        self.btn_download.setObjectName("downloadButton")
        self.btn_download.clicked.connect(self.start_books)

        self.btn_stop = QPushButton()
        self.btn_stop.setObjectName("stopButton")
        self.btn_stop.clicked.connect(self.stop_download)

        self.btn_reset = QPushButton()
        self.btn_reset.setObjectName("resetButton")
        self.btn_reset.clicked.connect(self.reset_books)

        self.btn_save_list = QPushButton()
        self.btn_save_list.clicked.connect(self.save_list)

        self.btn_load_list = QPushButton()
        self.btn_load_list.clicked.connect(self.load_list)

        self.btn_export_pdf = QPushButton()
        self.btn_export_pdf.clicked.connect(self.export_pdf)

        self.btn_log_toggle = QPushButton()
        self.btn_log_toggle.clicked.connect(self.toggle_log)

        self.btn_save_log = QPushButton()
        self.btn_save_log.clicked.connect(self.save_log_to_file)

        action_rows = []
        for _ in range(3):
            row = QHBoxLayout()
            row.setSpacing(10)
            action_rows.append(row)
            main_layout.addLayout(row)

        action_rows[0].addStretch(1)
        for btn in (self.btn_add_book, self.btn_delete_book, self.btn_change_pages):
            btn.setMinimumHeight(42)
            btn.setMinimumWidth(185)
            action_rows[0].addWidget(btn)
        action_rows[0].addStretch(1)

        action_rows[1].addStretch(1)
        for btn in (self.btn_download, self.btn_stop, self.btn_reset):
            btn.setMinimumHeight(42)
            btn.setMinimumWidth(185)
            action_rows[1].addWidget(btn)
        action_rows[1].addStretch(1)

        action_rows[2].addStretch(1)
        for btn in (self.btn_save_list, self.btn_load_list, self.btn_export_pdf, self.btn_save_log, self.btn_log_toggle):
            btn.setMinimumHeight(40)
            btn.setMinimumWidth(155)
            action_rows[2].addWidget(btn)
        action_rows[2].addStretch(1)

        self.lbl_waiting = QLabel()
        main_layout.addWidget(self.lbl_waiting)

        self.table = QTableWidget(0, 3)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        self.table.cellClicked.connect(self.on_table_cell_clicked)
        self.table.itemChanged.connect(self.on_table_item_changed)
        self.table.setMinimumHeight(320)
        main_layout.addWidget(self.table, 1)

        progress_row = QHBoxLayout()
        self.lbl_progress = QLabel()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_label = QLabel("0%")
        self.progress_label.setMinimumWidth(48)
        progress_row.addWidget(self.lbl_progress)
        progress_row.addWidget(self.progress_bar, 1)
        progress_row.addWidget(self.progress_label)
        main_layout.addLayout(progress_row)

        self.log_container = QGroupBox()
        self.log_container_layout = QVBoxLayout(self.log_container)
        self.log_container_layout.setContentsMargins(8, 8, 8, 8)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(160)
        self.log_container_layout.addWidget(self.log_text)
        main_layout.addWidget(self.log_container)
        self.log_container.hide()

        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        self._build_history_menu()
        self._init_shortcuts()

    def _build_language_menu(self) -> None:
        self.language_combo.blockSignals(True)
        self.language_combo.clear()
        for code in SUPPORTED_LANGS:
            self.language_combo.addItem(LANGUAGE_LABELS.get(code, code.upper()), code)
        self.language_combo.currentIndexChanged.connect(self.on_language_combo_changed)
        self._refresh_language_button_text()
        self.language_combo.blockSignals(False)

    def _refresh_language_button_text(self) -> None:
        index = self.language_combo.findData(self.lang)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)

    @Slot(int)
    def on_language_combo_changed(self, index: int) -> None:
        if index < 0:
            return
        code = str(self.language_combo.itemData(index) or '').strip().lower()
        if code:
            self.set_language(code)

    def _find_emoji_font_family(self) -> str | None:
        database = QFontDatabase()
        try:
            families = {str(name) for name in database.families()}
        except Exception:
            families = set()

        for candidate in (
            "Noto Color Emoji",
            "emoji",
            "Noto Emoji",
            "Twitter Color Emoji",
            "Twemoji Mozilla",
            "Apple Color Emoji",
            "Segoe UI Emoji",
        ):
            if candidate in families:
                return candidate
        return None

    def _make_ui_font(self, *, prefer_emoji: bool = False) -> QFont:
        font = QFont(self.font())
        if prefer_emoji and self._emoji_family:
            try:
                base_family = self.font().family()
                families = [self._emoji_family]
                if base_family and base_family not in families:
                    families.append(base_family)
                font.setFamilies(families)
            except Exception:
                try:
                    font.setFamily(self._emoji_family)
                except Exception:
                    pass
        return font

    def _icon_from_theme_or_style(self, names: tuple[str, ...], fallback_style_icon) -> QIcon:
        for name in names:
            icon = QIcon.fromTheme(name)
            if not icon.isNull():
                return icon
        return self.style().standardIcon(fallback_style_icon)

    def _recolor_icon(self, icon: QIcon, color: str, size: QSize | None = None) -> QIcon:
        size = size or QSize(18, 18)
        base = icon.pixmap(size)
        if base.isNull():
            return icon

        tinted = QPixmap(base.size())
        tinted.fill(Qt.transparent)

        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, base)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), QColor(color))
        painter.end()

        return QIcon(tinted)

    def _set_button_icon_color(self, button: QPushButton, color: str) -> None:
        icon = button.icon()
        if icon.isNull():
            return
        button.setIcon(self._recolor_icon(icon, color, button.iconSize()))

    def _apply_icon_color_scheme(self, buttons: list[QPushButton], *, color: str) -> None:
        for button in buttons:
            self._set_button_icon_color(button, color)

    def _theme_button_icon(self) -> QIcon:
        """Draw the theme icon ourselves to avoid missing/filled system icons.

        While the application is in light mode, display a crescent moon as
        the action that switches to dark mode. In dark mode, show a sun.
        """
        scale = 3
        logical_size = 24
        pixmap = QPixmap(logical_size * scale, logical_size * scale)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.scale(scale, scale)
        color = QColor("#ffffff" if self.is_dark else "#000000")
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)

        if self.is_dark:
            # Clear sun disk and eight rays, all drawn in white.
            from math import cos, pi, sin
            painter.drawEllipse(8, 8, 8, 8)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(color, 1.8, Qt.SolidLine, Qt.RoundCap))
            for i in range(8):
                angle = i * pi / 4
                painter.drawLine(
                    round(12 + 7.1 * cos(angle)),
                    round(12 + 7.1 * sin(angle)),
                    round(12 + 9.7 * cos(angle)),
                    round(12 + 9.7 * sin(angle)),
                )
        else:
            # Subtract an offset circle from the moon to form a crescent.
            # Unlike a theme-dependent glyph this cannot become a black dot.
            moon = QPainterPath()
            moon.addEllipse(4, 3, 17, 17)
            cutout = QPainterPath()
            cutout.addEllipse(10, 0, 15, 15)
            painter.drawPath(moon.subtracted(cutout))

        painter.end()
        pixmap.setDevicePixelRatio(scale)
        return QIcon(pixmap)

    def _set_button_symbol(
        self,
        button: QPushButton,
        names: tuple[str, ...],
        fallback_style_icon,
        *,
        icon_only: bool = False,
        icon_size: QSize | None = None,
    ) -> None:
        button.setIcon(self._icon_from_theme_or_style(names, fallback_style_icon))
        button.setIconSize(icon_size or (QSize(20, 20) if icon_only else QSize(18, 18)))
        if icon_only:
            button.setText("")

    def _apply_topbar_button_visuals(self) -> None:
        self.btn_home.setFont(self._make_ui_font())
        self.btn_help.setFont(self._make_ui_font())
        self.btn_theme.setFont(self._make_ui_font())

        self.btn_home.setText(self._t("home"))
        self.btn_help.setText("")
        self.btn_theme.setText("")

        self._set_button_symbol(self.btn_home, ("go-home", "user-home", "home"), QStyle.SP_DirHomeIcon)
        self._set_button_symbol(
            self.btn_help,
            ("help-about", "dialog-question", "system-help"),
            QStyle.SP_MessageBoxQuestion,
            icon_only=True,
        )
        self.btn_theme.setIcon(self._theme_button_icon())
        self.btn_theme.setIconSize(QSize(20, 20))

        # Icons are recolored from fresh theme/style sources on every theme change.
        # Never inherit icon colors from the operating system's icon theme.
        self._apply_icon_color_scheme(
            [self.btn_home, self.btn_help],
            color="#ffffff" if self.is_dark else "#000000",
        )

        self.btn_home.setToolTip(self._t("home"))
        self.btn_help.setToolTip(self._t("help_button_tooltip"))
        self.btn_theme.setToolTip(self._t("theme_light") if self.is_dark else self._t("theme_dark"))

    def _apply_action_button_visuals(self) -> None:
        button_specs = (
            (self.btn_history, ("document-open-recent", "view-history", "folder-recent"), QStyle.SP_DialogOpenButton),
            (self.btn_choose, ("folder-open", "document-open", "inode-directory"), QStyle.SP_DialogOpenButton),
            (self.btn_add_book, ("list-add", "document-new", "add"), QStyle.SP_DialogOpenButton),
            (self.btn_delete_book, ("edit-delete", "user-trash", "trash-empty"), QStyle.SP_TrashIcon),
            (self.btn_change_pages, ("document-edit", "edit-rename", "accessories-text-editor"), QStyle.SP_FileIcon),
            (self.btn_download, ("download", "folder-download", "go-down"), QStyle.SP_DialogSaveButton),
            (self.btn_stop, ("process-stop", "media-playback-stop", "dialog-cancel"), QStyle.SP_BrowserStop),
            (self.btn_reset, ("edit-clear", "view-refresh", "document-revert"), QStyle.SP_BrowserReload),
            (self.btn_save_list, ("document-save", "document-save-as"), QStyle.SP_DialogSaveButton),
            (self.btn_load_list, ("document-open", "folder-open"), QStyle.SP_DialogOpenButton),
            (self.btn_export_pdf, ("application-pdf", "document-export", "x-office-document"), QStyle.SP_FileIcon),
            (self.btn_save_log, ("document-save", "text-x-log", "document-save-as"), QStyle.SP_DialogSaveButton),
        )

        for button, names, fallback in button_specs:
            self._set_button_symbol(button, names, fallback)

        log_toggle_names = ("dialog-close", "window-close") if self.log_container.isVisible() else ("text-x-log", "view-list-text", "utilities-terminal")
        log_toggle_fallback = QStyle.SP_DockWidgetCloseButton if self.log_container.isVisible() else QStyle.SP_FileIcon
        self._set_button_symbol(self.btn_log_toggle, log_toggle_names, log_toggle_fallback)

        # Apply the same contrasting icon color to every action button,
        # including colored action buttons and the log toggle.
        self._apply_icon_color_scheme(
            [button for button, _, _ in button_specs] + [self.btn_log_toggle],
            color="#ffffff" if self.is_dark else "#000000",
        )

    def _load_theme_setting(self) -> bool:
        value = self.settings.value("ui/is_dark", False)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "on")

    def _save_theme_setting(self) -> None:
        self.settings.setValue("ui/is_dark", self.is_dark)

    def _load_language_setting(self) -> str:
        value = str(self.settings.value("ui/lang", "de") or "de").strip().lower()
        if value == "cs":
            value = "cz"
        return value if value in LANG else "de"

    def _save_language_setting(self) -> None:
        self.settings.setValue("ui/lang", self.lang)

    def _load_outdir_setting(self) -> str:
        value = str(self.settings.value("ui/last_outdir", os.getcwd()) or os.getcwd()).strip()
        return value or os.getcwd()

    def _save_outdir_setting(self, outdir: str | None = None) -> None:
        selected_outdir = (outdir or self.outdir_entry.text().strip() or os.getcwd()).strip()
        self.last_outdir = selected_outdir
        self.settings.setValue("ui/last_outdir", selected_outdir)

    def _load_history_limit_setting(self) -> int:
        value = self.settings.value("history/max_entries", 200)
        try:
            limit = int(value)
        except (TypeError, ValueError):
            limit = 200
        return max(1, min(limit, 100000))

    def _save_history_limit_setting(self) -> None:
        self.settings.setValue("history/max_entries", int(self.history_limit))

    def _load_history_setting(self) -> list[str]:
        value = self.settings.value("history/book_urls", [])
        if isinstance(value, list):
            raw_values = value
        elif isinstance(value, tuple):
            raw_values = list(value)
        elif isinstance(value, str):
            text = value.strip()
            if not text:
                raw_values = []
            elif text.startswith("[") and text.endswith("]"):
                try:
                    raw_values = json.loads(text)
                except Exception:
                    raw_values = [text]
            else:
                raw_values = [text]
        else:
            raw_values = []

        history: list[str] = []
        seen: set[str] = set()
        for entry in raw_values:
            url = str(entry or "").strip()
            if not url:
                continue
            normalized = self._normalized_book_url(url)
            if normalized in seen:
                continue
            seen.add(normalized)
            history.append(url)
        return history[: self.history_limit]

    def _save_history_setting(self) -> None:
        self.settings.setValue("history/book_urls", self.book_history[: self.history_limit])

    def _add_history_url(self, url: str) -> None:
        url = str(url or "").strip()
        if not url:
            return

        normalized = self._normalized_book_url(url)
        updated = [url]
        for existing in self.book_history:
            if self._normalized_book_url(existing) != normalized:
                updated.append(existing)

        self.book_history = updated[: self.history_limit]
        self._refresh_history_model()
        self._save_history_setting()

    def _refresh_history_model(self) -> None:
        self.history_model.setStringList(self.book_history)
        self._build_history_menu()
        if hasattr(self, "btn_history"):
            self.btn_history.setToolTip(
                self._t("history_button_tooltip")
                + "\n"
                + self._t("history_count_tooltip").format(count=len(self.book_history), limit=self.history_limit)
            )

    def _build_history_menu(self) -> None:
        if not hasattr(self, "history_menu"):
            return

        self.history_menu.clear()

        info_action = self.history_menu.addAction(
            self._t("history_count_tooltip").format(count=len(self.book_history), limit=self.history_limit)
        )
        info_action.setEnabled(False)

        self.history_menu.addSeparator()

        limit_menu = self.history_menu.addMenu(self._t("history_limit_menu"))
        limit_group = QActionGroup(self)
        limit_group.setExclusive(True)

        for value in (50, 100, 200):
            action = limit_menu.addAction(str(value))
            action.setCheckable(True)
            action.setChecked(self.history_limit == value)
            action.triggered.connect(lambda checked=False, v=value: self.set_history_limit(v))
            limit_group.addAction(action)

        limit_menu.addSeparator()
        custom_label = self._t("history_limit_custom")
        if self.history_limit not in (50, 100, 200):
            custom_label = f"{custom_label} ({self.history_limit})"
        custom_action = limit_menu.addAction(custom_label)
        custom_action.triggered.connect(self.prompt_custom_history_limit)

        show_action = self.history_menu.addAction(self._t("history_show"))
        show_action.setEnabled(bool(self.book_history))
        show_action.triggered.connect(self.show_history_dialog)

        self.history_menu.addSeparator()
        clear_action = self.history_menu.addAction(self._t("history_clear"))
        clear_action.setEnabled(bool(self.book_history))
        clear_action.triggered.connect(self.clear_history)

    @Slot()
    def show_history_dialog(self) -> None:
        if not self.book_history:
            QMessageBox.information(self, self._t("title"), self._t("history_empty"))
            return

        dialog = HistoryDialog(self, self._t("history_dialog_title"), self.book_history)
        dialog.exec()

    @Slot()
    def clear_history(self) -> None:
        self.book_history = []
        self._refresh_history_model()
        self._save_history_setting()
        self.log(f"[*] {self._t('history_cleared')}")
        self.statusBar().showMessage(self._t("history_cleared"), 3000)

    def set_history_limit(self, limit: int) -> None:
        limit = max(1, min(int(limit), 100000))
        if limit == self.history_limit:
            self._build_history_menu()
            return

        self.history_limit = limit
        self.book_history = self.book_history[: self.history_limit]
        self._save_history_limit_setting()
        self._refresh_history_model()
        self._save_history_setting()
        msg = self._t("history_limit_set").format(limit=self.history_limit)
        self.log(f"[⚙️] {msg}")
        self.statusBar().showMessage(msg, 3000)

    @Slot()
    def prompt_custom_history_limit(self) -> None:
        value, ok = QInputDialog.getInt(
            self,
            self._t("history_limit_prompt_title"),
            self._t("history_limit_prompt_label"),
            value=self.history_limit,
            minValue=1,
            maxValue=100000,
            step=1,
        )
        if ok:
            self.set_history_limit(value)

    def _apply_windows_safe_visuals(self) -> None:
        self.apply_theme()

    def _apply_windows_safe_topbar_button_visuals(self) -> None:
        self.btn_home.setFont(self._make_ui_font())
        self.btn_help.setFont(self._make_ui_font())
        self.btn_theme.setFont(self._make_ui_font())

        self.btn_home.setText(self._t("home"))
        self.btn_help.setText("")
        self.btn_theme.setText("☀" if self.is_dark else "☾")

        self._set_button_symbol(self.btn_home, ("go-home", "user-home", "home"), QStyle.SP_DirHomeIcon)
        self._set_button_symbol(
            self.btn_help,
            ("help-about", "dialog-question", "system-help"),
            QStyle.SP_MessageBoxQuestion,
            icon_only=True,
        )

        self.btn_home.setToolTip(self._t("home"))
        self.btn_help.setToolTip(self._t("help_button_tooltip"))
        self.btn_theme.setToolTip(self._t("theme_light") if self.is_dark else self._t("theme_dark"))

    def _apply_windows_safe_action_button_visuals(self) -> None:
        button_specs = (
            (self.btn_history, ("document-open-recent", "view-history", "folder-recent"), QStyle.SP_DialogOpenButton),
            (self.btn_choose, ("folder-open", "document-open", "inode-directory"), QStyle.SP_DialogOpenButton),
            (self.btn_add_book, ("list-add", "document-new", "add"), QStyle.SP_DialogOpenButton),
            (self.btn_delete_book, ("edit-delete", "user-trash", "trash-empty"), QStyle.SP_TrashIcon),
            (self.btn_change_pages, ("document-edit", "edit-rename", "accessories-text-editor"), QStyle.SP_FileIcon),
            (self.btn_download, ("download", "folder-download", "go-down"), QStyle.SP_DialogSaveButton),
            (self.btn_stop, ("process-stop", "media-playback-stop", "dialog-cancel"), QStyle.SP_BrowserStop),
            (self.btn_reset, ("edit-clear", "view-refresh", "document-revert"), QStyle.SP_BrowserReload),
            (self.btn_save_list, ("document-save", "document-save-as"), QStyle.SP_DialogSaveButton),
            (self.btn_load_list, ("document-open", "folder-open"), QStyle.SP_DialogOpenButton),
            (self.btn_export_pdf, ("application-pdf", "document-export", "x-office-document"), QStyle.SP_FileIcon),
            (self.btn_save_log, ("document-save", "text-x-log", "document-save-as"), QStyle.SP_DialogSaveButton),
        )

        for button, names, fallback in button_specs:
            self._set_button_symbol(button, names, fallback)

        log_toggle_names = ("dialog-close", "window-close") if self.log_container.isVisible() else ("text-x-log", "view-list-text", "utilities-terminal")
        log_toggle_fallback = QStyle.SP_DockWidgetCloseButton if self.log_container.isVisible() else QStyle.SP_FileIcon
        self._set_button_symbol(self.btn_log_toggle, log_toggle_names, log_toggle_fallback)

    def _apply_windows_button_labels(self) -> None:
        """Set each Windows button label once, using its translation.

        Most translated labels already begin with an emoji. Adding a second
        symbol caused the duplicate icons seen in Windows 11.
        """
        # These two translations contain no icon; use a single text symbol.
        self.btn_home.setIcon(QIcon())
        self.btn_home.setText(f"🏠 {self._t('home')}")
        self.btn_history.setIcon(QIcon())
        self.btn_history.setText(f"◷ {self._t('history_button')}")

        # All other labels already contain their own emoji in i18n.py.
        buttons = (
            (self.btn_choose, "choose_dir"),
            (self.btn_add_book, "add_book"),
            (self.btn_delete_book, "delete_book"),
            (self.btn_change_pages, "change_pages"),
            (self.btn_download, "download"),
            (self.btn_stop, "stop"),
            (self.btn_reset, "reset"),
            (self.btn_save_list, "save_list"),
            (self.btn_load_list, "load_list"),
            (self.btn_export_pdf, "export_pdf"),
            (self.btn_save_log, "log_save"),
        )
        for button, key in buttons:
            button.setIcon(QIcon())
            button.setText(self._t(key))

        self._update_windows_log_button_label()
        self.btn_home.setToolTip(self._t("home"))
        self.btn_help.setIcon(QIcon())
        self.btn_help.setText("ⓘ")
        self.btn_help.setToolTip(self._t("help_button_tooltip"))
        self.btn_theme.setIcon(QIcon())
        self.btn_theme.setText("☀" if self.is_dark else "☾")
        self.btn_theme.setToolTip(self._t("theme_light") if self.is_dark else self._t("theme_dark"))

    def _update_windows_log_button_label(self) -> None:
        self.btn_log_toggle.setIcon(QIcon())
        key = "log_close" if self.log_container.isVisible() else "log_open"
        # Translated string already includes the scroll icon.
        self.btn_log_toggle.setText(self._t(key))

    def apply_theme(self) -> None:
        # Preserve the original 1.6 colour palette and action-button styling.
        # Windows falls back to the 1.6-style text/emoji glyphs rather than
        # constructing and recolouring QIcons with QPainter on every update.
        self.setStyleSheet(dark_stylesheet() if self.is_dark else light_stylesheet())
        if self._windows_safe_mode:
            # Windows: use the old v1.6 approach (text glyphs, no QPainter /
            # QIcon.fromTheme). Always rebuild labels from translations rather
            # than prefixing their *current* text (which duplicated symbols).
            self._apply_windows_button_labels()
            return
        self._apply_topbar_button_visuals()
        self._apply_action_button_visuals()

    def _windows_simple_stylesheet(self) -> str:
        dark = self.is_dark
        bg = "#111827" if dark else "#f5f7fb"
        surface = "#1f2937" if dark else "#ffffff"
        fg = "#e5e7eb" if dark else "#1f2937"
        soft = "#273549" if dark else "#e9eef6"
        border = "#374151" if dark else "#d4dce7"
        header = "#243041" if dark else "#eef2f7"
        return f"""
            QMainWindow {{ background: {bg}; color: {fg}; }}
            QMainWindow > QWidget {{ background: {bg}; color: {fg}; }}
            QLabel {{ color: {fg}; }}
            QGroupBox {{ background: {surface}; border: 1px solid {border}; border-radius: 12px; }}
            QLineEdit, QTextEdit, QTableWidget {{ background: {surface}; color: {fg}; border: 1px solid {border}; border-radius: 8px; padding: 6px; }}
            QHeaderView::section {{ background: {header}; color: {fg}; border: none; padding: 8px; }}
            QPushButton {{ background: {soft}; color: {fg}; border: 1px solid {border}; border-radius: 10px; padding: 9px 12px; }}
            QPushButton#addBookButton {{ background: #facc15; color: #1f2937; }}
            QPushButton#deleteBookButton {{ background: #f97316; color: white; }}
            QPushButton#changePagesButton {{ background: #a855f7; color: white; }}
            QPushButton#downloadButton {{ background: #22c55e; color: white; }}
            QPushButton#stopButton {{ background: #ef4444; color: white; }}
            QPushButton#resetButton {{ background: #3b82f6; color: white; }}
            QProgressBar {{ background: {surface}; color: {fg}; border: 1px solid {border}; border-radius: 8px; }}
            QProgressBar::chunk {{ background: #3b82f6; border-radius: 7px; }}
        """

    def set_language(self, lang: str) -> None:
        lang = str(lang or "de").strip().lower()
        if not lang or lang == self.lang:
            return
        self.lang = lang
        self._save_language_setting()
        self.retranslate_ui()

    @Slot()
    def toggle_theme(self) -> None:
        self.is_dark = not self.is_dark
        self._save_theme_setting()
        self.apply_theme()

    @Slot()
    def open_home(self) -> None:
        url = "https://www.portafontium.eu/searching"
        if not open_external_url(url):
            QMessageBox.warning(
                self,
                "Porta fontium",
                f"Der Standardbrowser konnte nicht geöffnet werden.\nBitte öffne die Webseite manuell:\n{url}",
            )

    @Slot()
    def on_outdir_changed(self) -> None:
        self._save_outdir_setting()

    @Slot()
    def on_url_ctrl_return(self) -> None:
        if self.url_entry.text().strip():
            self.add_book()
        self.start_books()

    def retranslate_ui(self) -> None:
        self.setWindowTitle(self._t("title"))
        self.btn_help.setToolTip(self._t("help_button_tooltip"))
        self.btn_history.setText(self._t("history_button"))
        self.btn_add_book.setText(self._t("add_book"))
        self.btn_delete_book.setText(self._t("delete_book"))
        self.btn_change_pages.setText(self._t("change_pages"))
        self.btn_download.setText(self._t("download"))
        self.btn_stop.setText(self._t("stop"))
        self.btn_reset.setText(self._t("reset"))
        self.btn_save_list.setText(self._t("save_list"))
        self.btn_load_list.setText(self._t("load_list"))
        self.btn_export_pdf.setText(self._t("export_pdf"))
        self.btn_save_log.setText(self._t("log_save"))
        self.btn_choose.setText(self._t("choose_dir"))
        self.lbl_url.setText(self._t("book_url"))
        self.lbl_outdir.setText(self._t("target_dir"))
        self.lbl_pages.setText(self._t("pages"))
        self.lbl_pages_hint.setText(self._t("pages_hint"))
        self.lbl_pages_hint.setToolTip(self._t("hint_pages_editable"))
        self.lbl_waiting.setText(self._t("waiting_list"))
        self.lbl_language.setText(self._t("language"))
        self.lbl_progress.setText(self._t("global_progress"))
        self.table.setHorizontalHeaderLabels([self._t("col_book"), self._t("col_pages"), self._t("col_status")])
        self.log_container.setTitle(self._t("log_title"))
        self.btn_log_toggle.setText(self._t("log_close") if self.log_container.isVisible() else self._t("log_open"))
        self._refresh_language_button_text()
        self._refresh_history_model()
        if not getattr(self, "_building_initial_ui", False):
            self.apply_theme()

    def _status_message(self, key: str) -> None:
        self.statusBar().showMessage(self._t(key))

    def log(self, msg: str) -> None:
        line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
        self.log_text.append(line)

    def _normalized_book_url(self, url: str) -> str:
        parsed = urlparse(str(url or "").strip())
        query_items = [
            (key.lower(), value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() != "language"
        ]
        query = urlencode(sorted(query_items), doseq=True)
        path = parsed.path.rstrip("/") or "/"
        return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.params, query, ""))

    def _book_already_exists(self, url: str) -> bool:
        normalized = self._normalized_book_url(url)
        return any(self._normalized_book_url(book.url) == normalized for book in self.books)

    def _help_html(self) -> str:
        def esc(value: str) -> str:
            return html.escape(str(value or ""))

        version_display = str(APP_VERSION).split()[0]
        ctrl = self._t("shortcut_ctrl")
        book_url_label = self._t("book_url").rstrip(":")

        github_link = (
            f'<a href="{esc(APP_GITHUB_URL)}">{esc(APP_GITHUB_URL)}</a>'
            if str(APP_GITHUB_URL).strip()
            else "-"
        )

        shortcuts = [
            ("F1", self._t("help_sc_f1")),
            (f"{ctrl} + S", self._t("help_sc_save_list")),
            (f"{ctrl} + D", self._t("help_sc_load_list")),
            (f"{ctrl} + X", self._t("help_sc_clear_queue")),
            (f"{ctrl} + F", self._t("help_sc_search_queue")),
            (f"{ctrl} + Q", self._t("help_sc_quit")),
            (f"{ctrl} + H", self._t("help_sc_toggle_theme")),
            (self._t("shortcut_delete"), self._t("help_sc_delete_selected")),
            (f"{ctrl} + L", self._t("help_sc_save_log")),
            (f"Enter ({book_url_label})", self._t("help_sc_add_book")),
            (f"{ctrl} + Enter", self._t("help_sc_start_download")),
        ]

        shortcuts_html = "".join(
            f"<tr><td style='padding:4px 10px 4px 0;'><b>{esc(key)}</b></td><td style='padding:4px 0;'>{esc(text)}</td></tr>"
            for key, text in shortcuts
        )

        return f"""
        <h3>{esc(self._t('help_about'))}</h3>
        <p style='margin-top:0;'>{esc(self._t('help_description'))}</p>
        <p>
            <b>{esc(self._t('help_author'))}:</b> {esc(APP_AUTHOR)}<br>
            <b>{esc(self._t('help_source'))}:</b> {github_link}<br>
            <b>{esc(self._t('help_version'))}:</b> {esc(version_display)}
        </p>
        <h3>{esc(self._t('help_shortcuts'))}</h3>
        <table cellspacing='0' cellpadding='0'>{shortcuts_html}</table>
        """

    def _selected_rows(self) -> list[int]:
        selection_model = self.table.selectionModel()
        if not selection_model:
            return []
        return sorted({index.row() for index in selection_model.selectedRows()})

    def _init_shortcuts(self) -> None:
        self._shortcut_actions: list[QAction] = []

        def add_shortcut(shortcut: str | QKeySequence, callback) -> None:
            action = QAction(self)
            action.setShortcut(shortcut)
            action.setShortcutContext(Qt.WindowShortcut)
            action.triggered.connect(callback)
            self.addAction(action)
            self._shortcut_actions.append(action)

        add_shortcut("F1", self.show_help_dialog)
        add_shortcut("Ctrl+S", self.save_list)
        add_shortcut("Ctrl+D", self.load_list)
        add_shortcut("Ctrl+X", self.reset_books)
        add_shortcut("Ctrl+F", self.find_in_waiting_list)
        add_shortcut("Ctrl+Q", self.close)
        add_shortcut("Ctrl+H", self.toggle_theme)
        add_shortcut("Delete", self.delete_book)
        add_shortcut("Ctrl+L", self.save_log_to_file)
        add_shortcut("Ctrl+Return", self.start_books)
        add_shortcut("Ctrl+Enter", self.start_books)

    @Slot()
    def show_help_dialog(self) -> None:
        dialog = HelpDialog(self, self._t("help_title"), self._help_html())
        dialog.exec()

    @Slot()
    def find_in_waiting_list(self) -> None:
        if not self.books:
            QMessageBox.warning(self, self._t("title"), self._t("error_no_book"))
            return

        text, ok = QInputDialog.getText(
            self,
            self._t("search_title"),
            self._t("search_label"),
            text=self._last_search_text,
        )
        if not ok:
            return

        needle = text.strip().lower()
        if not needle:
            return

        self._last_search_text = text.strip()
        start_row = self.table.currentRow() + 1 if self.table.currentRow() >= 0 else 0
        row_count = self.table.rowCount()
        matches = list(range(start_row, row_count)) + list(range(0, start_row))

        for row in matches:
            item = self.table.item(row, 0)
            if item and needle in item.text().lower():
                self.table.setCurrentCell(row, 0)
                self.table.selectRow(row)
                self.table.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                self.statusBar().showMessage(self._t("search_found"), 3000)
                return

        QMessageBox.information(self, self._t("title"), self._t("search_not_found"))

    @Slot()
    def save_log_to_file(self) -> None:
        content = self.log_text.toPlainText().strip()
        if not content:
            QMessageBox.information(self, self._t("title"), self._t("log_empty"))
            return

        default_name = os.path.join(os.getcwd(), self._t("save_log_default"))
        path, _ = QFileDialog.getSaveFileName(self, self._t("log_save"), default_name, self._t("filter_text"))
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content + "\n")
            QMessageBox.information(self, self._t("title"), self._t("log_saved"))
        except Exception as exc:
            QMessageBox.critical(self, self._t("title"), str(exc))

    @Slot()
    def toggle_log(self) -> None:
        visible = not self.log_container.isVisible()
        self.log_container.setVisible(visible)
        if self._windows_safe_mode:
            # Avoid QIcon recoloring during an active worker download. The
            # previous code crashed here on Windows in the native Qt renderer.
            self._update_windows_log_button_label()
        else:
            self.btn_log_toggle.setText(self._t("log_close") if visible else self._t("log_open"))
            self._apply_action_button_visuals()

    @Slot()
    def choose_dir(self) -> None:
        start_dir = self.outdir_entry.text().strip() or self.last_outdir or os.getcwd()
        selected = QFileDialog.getExistingDirectory(self, self._t("choose_dir"), start_dir)
        if selected:
            self.outdir_entry.setText(selected)
            self._save_outdir_setting(selected)
            self.log(f"[📂] {self._t('target_dir_saved')}: {selected}")

    @Slot()
    def add_book(self) -> None:
        url = self.url_entry.text().strip()
        outdir = self.outdir_entry.text().strip() or self.last_outdir or os.getcwd()
        pages = self.pages_entry.text().strip()

        if not url:
            QMessageBox.warning(self, self._t("title"), self._t("error_no_url"))
            return

        if self._book_already_exists(url):
            QMessageBox.information(self, self._t("title"), self._t("error_duplicate_book"))
            self.log(f"[=] {self._t('error_duplicate_book')} {url}")
            return

        self._save_outdir_setting(outdir)
        self.outdir_entry.setText(outdir)
        self._add_history_url(url)

        book = BookEntry(url=url, outdir=outdir, pages=pages)
        self.books.append(book)
        self._append_table_row(book)
        self.log(f"[+] {self._t('log_book_added')}: {url}")

        self.url_entry.clear()
        self.pages_entry.clear()
        self.url_entry.setFocus()

    def _append_table_row(self, book: BookEntry) -> None:
        row = self.table.rowCount()
        self._syncing_table = True
        self.table.insertRow(row)

        url_item = QTableWidgetItem(book.url)
        pages_item = QTableWidgetItem(book.pages)
        status_item = QTableWidgetItem("⏳")

        pages_item.setTextAlignment(Qt.AlignCenter)
        status_item.setTextAlignment(Qt.AlignCenter)

        self.table.setItem(row, 0, url_item)
        self.table.setItem(row, 1, pages_item)
        self.table.setItem(row, 2, status_item)
        self._syncing_table = False

    @Slot()
    def delete_book(self) -> None:
        selected = sorted(self._selected_rows(), reverse=True)
        if not selected:
            QMessageBox.warning(self, self._t("title"), self._t("error_no_selection"))
            return

        self._syncing_table = True
        for row in selected:
            del self.books[row]
            self.table.removeRow(row)
        self._syncing_table = False

        self.log(f"[-] {self._t('log_book_deleted')}")

    @Slot()
    def change_pages(self) -> None:
        selected = self._selected_rows()
        if not selected:
            QMessageBox.warning(self, self._t("title"), self._t("error_no_selection"))
            return

        row = selected[0]
        current_pages = self.books[row].pages
        pages, ok = QInputDialog.getText(
            self,
            self._t("pages_dialog_title"),
            self._t("pages_hint"),
            text=current_pages,
        )
        if ok:
            pages = pages.strip()
            self.books[row].pages = pages
            self._syncing_table = True
            self.table.item(row, 1).setText(pages)
            self._syncing_table = False
            self.log(f"[~] {self._t('pages_updated')} {self.books[row].url} -> {pages}")

    @Slot(int, int)
    def on_table_double_clicked(self, row: int, column: int) -> None:
        if column == 0:
            item = self.table.item(row, 0)
            if item and item.text():
                QDesktopServices.openUrl(QUrl(item.text()))
        elif column == 1 and not (self.worker and self.worker.isRunning()):
            item = self.table.item(row, 1)
            if item:
                self.table.editItem(item)

    @Slot(int, int)
    def on_table_cell_clicked(self, row: int, column: int) -> None:
        if column == 1 and not (self.worker and self.worker.isRunning()):
            item = self.table.item(row, 1)
            if item:
                self.table.editItem(item)

    @Slot(QTableWidgetItem)
    def on_table_item_changed(self, item: QTableWidgetItem) -> None:
        if self._syncing_table or item.column() != 1:
            return

        row = item.row()
        if row < 0 or row >= len(self.books):
            return

        pages = item.text().strip()
        if item.text() != pages:
            self._syncing_table = True
            item.setText(pages)
            self._syncing_table = False

        self.books[row].pages = pages
        self.log(f"[~] {self._t('pages_updated')} {self.books[row].url} -> {pages}")

    @Slot()
    def reset_books(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, self._t("title"), self._t("error_running_reset"))
            return

        self.books.clear()
        self._syncing_table = True
        self.table.setRowCount(0)
        self._syncing_table = False
        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")
        self.log(f"[*] {self._t('log_queue_cleared')}")

    @Slot()
    def save_list(self) -> None:
        if not self.books:
            return

        default_name = os.path.join(os.getcwd(), self._t("save_list_default"))
        path, _ = QFileDialog.getSaveFileName(self, self._t("save_list"), default_name, self._t("filter_json"))
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump([book.to_dict() for book in self.books], handle, indent=2, ensure_ascii=False)
        except Exception as exc:
            QMessageBox.critical(self, self._t("title"), str(exc))
            return

        self.log(f"[💾] {self._t('log_list_saved')}: {path}")

    @Slot()
    def load_list(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self._t("load_list"), os.getcwd(), self._t("filter_json"))
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as handle:
                raw_books = json.load(handle)
        except Exception as exc:
            QMessageBox.critical(self, self._t("title"), str(exc))
            return

        self.books = [BookEntry.from_dict(book) for book in raw_books]
        self._syncing_table = True
        self.table.setRowCount(0)
        for book in self.books:
            self._append_table_row(book)
            self._add_history_url(book.url)
        self._syncing_table = False

        if self.books:
            self.outdir_entry.setText(self.books[-1].outdir)
            self._save_outdir_setting(self.books[-1].outdir)

        self.log(f"[📂] {self._t('log_list_loaded')}: {path}")

    @Slot()
    def export_pdf(self) -> None:
        if not self.books:
            QMessageBox.warning(self, self._t("title"), self._t("pdf_error_no_books"))
            return

        if not HAVE_REPORTLAB or A4 is None or canvas is None:
            QMessageBox.critical(self, self._t("title"), self._t("pdf_error_lib"))
            return

        try:
            from PIL import Image
        except Exception:
            QMessageBox.critical(self, self._t("title"), self._t("pdf_error_pillow"))
            return

        for book in self.books:
            outdir = book.outdir
            if not outdir or not os.path.isdir(outdir):
                continue

            for root, _dirs, files in os.walk(outdir):
                images = sorted([f for f in files if f.lower().endswith(".jpg")])
                if not images:
                    continue

                pdf_path = os.path.join(root, os.path.basename(root) + ".pdf")
                pdf_canvas = canvas.Canvas(pdf_path, pagesize=A4)
                pdf_w, pdf_h = A4

                for image_name in images:
                    img_path = os.path.join(root, image_name)
                    try:
                        with Image.open(img_path) as im:
                            img_w, img_h = im.size
                            scale = min(pdf_w / img_w, pdf_h / img_h)
                            new_w = img_w * scale
                            new_h = img_h * scale
                            x = (pdf_w - new_w) / 2
                            y = (pdf_h - new_h) / 2
                            pdf_canvas.drawImage(img_path, x, y, width=new_w, height=new_h, preserveAspectRatio=True)
                            pdf_canvas.showPage()
                    except Exception as exc:
                        self.log(f"[!] {self._t('log_pdf_error')} {image_name}: {exc}")

                pdf_canvas.save()
                self.log(f"[📄] {self._t('log_pdf_exported')}: {pdf_path}")

        QMessageBox.information(self, self._t("title"), self._t("pdf_saved"))

    def _set_running_state(self, running: bool) -> None:
        self.btn_add_book.setEnabled(not running)
        self.btn_delete_book.setEnabled(not running)
        self.btn_change_pages.setEnabled(not running)
        self.btn_download.setEnabled(not running)
        self.btn_reset.setEnabled(not running)
        self.btn_save_list.setEnabled(not running)
        self.btn_load_list.setEnabled(not running)
        self.btn_export_pdf.setEnabled(not running)
        self.btn_save_log.setEnabled(not running)
        self.btn_choose.setEnabled(not running)
        self.btn_history.setEnabled(not running)
        self.url_entry.setEnabled(not running)
        self.outdir_entry.setEnabled(not running)
        self.pages_entry.setEnabled(not running)
        self.language_combo.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    @Slot()
    def start_books(self) -> None:
        if not self.books:
            QMessageBox.warning(self, self._t("title"), self._t("error_no_book"))
            return

        if self.worker and self.worker.isRunning():
            return

        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")
        self._set_running_state(True)

        self._syncing_table = True
        for row in range(self.table.rowCount()):
            self.table.item(row, 2).setText("⏳")
        self._syncing_table = False

        self.worker = DownloaderWorker(
            books=[BookEntry(url=book.url, outdir=book.outdir, pages=book.pages) for book in self.books],
            ui_lang=self.lang,
            parent=self,
        )
        self.worker.log_message.connect(self.log)
        self.worker.book_status.connect(self.update_book_status)
        self.worker.global_progress.connect(self.update_global_progress)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.worker.start()

        self._status_message("status_running")

    @Slot()
    def stop_download(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self._status_message("status_stopped")

    @Slot(int, str)
    def update_book_status(self, row: int, value: str) -> None:
        item = self.table.item(row, 2)
        if item:
            self._syncing_table = True
            item.setText(value)
            self._syncing_table = False

    @Slot(float)
    def update_global_progress(self, value: float) -> None:
        int_value = max(0, min(100, int(round(value))))
        self.progress_bar.setValue(int_value)
        self.progress_label.setText(f"{int_value}%")

    @Slot()
    def on_worker_finished(self) -> None:
        self._set_running_state(False)
        self._status_message("status_finished")
        self.worker = None

    def closeEvent(self, event) -> None:
        self._save_theme_setting()
        self._save_language_setting()
        self._save_outdir_setting()
        self._save_history_limit_setting()
        self._save_history_setting()
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        event.accept()
