<p align="center">
  
  ![Screenshot](banner.png)
</p>

Porta fontium Downloader is a desktop application for downloading scans from **portafontium.eu** and supported **DFG-Viewer / METS** sources.

The application is written in **Python** with **PySide6** and organized as a modular package in `pfdownloader/`.

## Version 1.6 overview

Version **1.6** adds a larger multilingual UI, a more flexible queue workflow, persistent user settings, URL history management, platform-specific UI adjustments, and improved source handling for non-Porta scan viewers.

## Main features

- open supported scan URLs from **portafontium.eu**
- support **DFG-Viewer / METS** links in addition to Porta fontium links
- detect image sources automatically and generate direct JPEG download links
- download all pages or only selected page ranges such as `1,5,8-10`
- queue multiple entries in a waiting list
- prevent duplicate queue entries and warn when the same book is already queued
- edit page ranges later, including directly in the waiting list
- save and load waiting lists as JSON
- export downloaded JPG folders to PDF
- show a live log and save the log manually as a text file
- open a compact help dialog with program info and keyboard shortcuts
- switch between light and dark mode
- remember the selected language, theme, target directory, and history settings

## User interface languages

The UI supports the following languages:

- German
- English
- Polish
- Czech
- Italian
- French
- Spanish
- Dutch
- Hungarian
- Slovak
- Slovenian
- Croatian
- Romanian
- Latin
- Danish
- Swedish
- Norwegian
- Finnish
- Icelandic
- Estonian
- Latvian
- Lithuanian

Note: if a target website does not provide the same language, the downloader uses a safe fallback internally for the source request while keeping the UI in the selected language.

## Queue, history, and workflow

### Waiting list

- add one or more books, maps, or documents to the queue
- delete selected entries again
- change page ranges later
- double-click a row to open the original source URL in the browser
- click the page-range cell to edit pages directly in the table

### URL history / “Chronic”

- recently used book URLs are stored in a persistent history
- the history can be shown from the **Chronic** button
- the history size can be limited to `50`, `100`, `200`, or a custom value
- when the history limit is reached, older entries are automatically replaced by newer ones
- the history can be cleared manually

### Persistent settings

The application stores its settings with `QSettings`, including:

- selected UI language
- light/dark mode
- last selected target directory
- URL history
- history limit

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `F1` | Open the help dialog |
| `Ctrl + S` | Save waiting list |
| `Ctrl + D` | Load waiting list |
| `Ctrl + X` | Clear waiting list |
| `Ctrl + F` | Search in waiting list |
| `Ctrl + Q` | Quit the program |
| `Ctrl + H` | Toggle light/dark mode |
| `Delete` | Delete the selected queue entry |
| `Ctrl + L` | Save the log |
| `Enter` in the URL field | Add the current book to the queue |
| `Ctrl + Enter` in the URL field | Add the current book and start the download |

## Folder structure

The downloader uses a flat folder structure per record:

```text
Target folder/
└── DocumentType_YearOrYearRange_RecordID/
    ├── DocumentType_0001.jpg
    ├── DocumentType_0002.jpg
    └── DocumentType_YearOrYearRange_RecordID.pdf
```

A record-specific suffix is added so that different items with similar titles do not overwrite each other.

## Tech stack

- Python 3.10+
- PySide6
- requests
- BeautifulSoup4
- Pillow
- reportlab (optional, for PDF export)
- pip-system-certs

## Installation

### Windows / PyCharm / virtual environment

```bash
pip install requests beautifulsoup4 pillow reportlab PySide6 pip-system-certs
```

### Linux / virtual environment

```bash
pip install requests beautifulsoup4 pillow reportlab PySide6 pip-system-certs
```

## Usage

1. Start the program.
2. Enter a Porta fontium or supported DFG-Viewer/METS URL.
3. Choose the target directory.
4. Optionally enter page ranges such as `1,5,8-10`.
5. Press `Enter` in the URL field or use the add button.
6. Start the download manually or use `Ctrl + Enter` in the URL field.

## Source code structure

The project is split into modules inside `pfdownloader/`.

- `main.py` – application entry point
- `app_constants.py` – application name, version, author, settings keys
- `i18n.py` – translations and language configuration
- `icons.py` – icon loading and platform-specific icon helpers
- `main_window.py` – full GUI, dialogs, queue, history, shortcuts, and user interactions
- `metadata_parser.py` – metadata extraction from Porta fontium pages
- `metadata_patterns.py` – category and type patterns
- `models.py` – data models such as `BookEntry`
- `network.py` – HTTP requests, source parsing, and image download helpers
- `porta_logic.py` – Porta fontium specific logic and naming helpers
- `styles.py` – light and dark Qt stylesheets
- `text_utils.py` – text normalization and filename sanitizing
- `third_party.py` – optional imports such as ReportLab
- `worker.py` – threaded downloader logic

## Build notes

### Windows

A Windows one-file build can be created with a PyInstaller spec such as `main_windows_onefile.spec`.

### Linux

Linux builds may use a separate PyInstaller spec adjusted for the target desktop environment.

## Disclaimer

This project was created with support from ChatGPT.
