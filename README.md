# Porta fontium Downloader

<p align="center">
  <img src="logo.png" alt="Porta fontium Logo" width="260"> <br>
</p>

Porta fontium Downloader is a desktop application for downloading scans from **portafontium.eu**.

The current source code is based on **PySide6** and is now organized as a modular package in `pfdownloader/`.

![Screenshot](https://github.com/Testatost/Porta-Fontium-Downloader/blob/main/Screenshot.png?raw=true)

## Overview

The application can:

- open URLs from `portafontium.eu`
- detect scan/image sources on the page
- generate direct JPEG download links
- download all pages or selected page ranges
- queue multiple entries in a waiting list
- save and load waiting lists as JSON
- export downloaded JPG folders to PDF
- show a live log and save the log manually to a text file
- switch between German, English, and Czech
- remember the selected language and theme

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

### Linux Mint / Ubuntu

```bash
sudo apt update
sudo apt install python3-pip
pip install requests beautifulsoup4 pillow reportlab PySide6 pip-system-certs
```

## Usage

1. Start the program.
2. Enter a Porta fontium URL.
3. Choose the target directory.
4. Optionally enter page ranges such as `1,5,8-10`.
5. Add one or more entries to the waiting list.
6. Start the download.

## Main features

### Download queue

- multiple books, maps, or documents can be added to a waiting list
- entries can be deleted again
- page ranges can be changed later
- double-click on a row opens the original URL in the browser

### Download logic

- the application searches the page for image/IIP links
- for Porta fontium pages it also tries to resolve detail pages for better metadata
- direct JPEG download URLs are generated automatically
- pages are downloaded one by one
- the overall progress is shown in a progress bar
- each queue item gets a status symbol: `⏳`, `✅`, `⚠️`, `❌`

### Folder naming

The current code uses a flat output structure:

```text
Target folder/
└── DocumentType_YearOrYearRange_RecordID/
    ├── DocumentType_0001.jpg
    ├── DocumentType_0002.jpg
    └── DocumentType_YearOrYearRange_RecordID.pdf
```

A record-specific suffix is added so that different Porta fontium items with similar titles do not overwrite each other.

### PDF export

Downloaded JPG files can be converted into a PDF per folder.

### Logging

- messages are shown in the log window inside the application
- the log can be shown or hidden
- the log can be saved manually to a chosen `.txt` file

### Interface

- available languages: German, English, Czech
- selected language is stored with `QSettings`
- dark mode / light mode is available
- selected theme is stored with `QSettings`

## Source code structure

The ZIP source is split into modules.

### Module summary

- `main.py` – application entry point
- `app_constants.py` – application name, version, author, settings keys
- `i18n.py` – UI texts for all supported languages
- `icons.py` – icon loading and Windows AppUserModelID handling
- `main_window.py` – full GUI and user interactions
- `metadata_parser.py` – metadata extraction from Porta fontium pages
- `metadata_patterns.py` – category and type patterns
- `models.py` – data models such as `BookEntry`
- `network.py` – HTTP requests and image download helpers
- `porta_logic.py` – Porta fontium specific logic and naming helpers
- `styles.py` – light and dark Qt stylesheets
- `text_utils.py` – text normalization and filename sanitizing
- `third_party.py` – optional imports such as ReportLab
- `worker.py` – threaded downloader logic

## Disclaimer

This project was created with support from ChatGPT 5.
