# Porta fontium Downloader

A file downloader for Porta fontium in German, English, and Czech.

![Porta fontium Downloader](https://github.com/Testatost/Porta-Fontium-Downloader/blob/main/Screenshot.png?raw=true)

## Overview

Porta fontium Downloader lets you download books, maps, and documents from `portafontium.eu` as individual JPEG pages.

The application:

- scans a Porta fontium page for IIP image server links,
- builds direct JPEG download links,
- downloads the pages into a selected folder,
- supports multiple entries in a waiting list,
- and can export downloaded images to PDF.

The interface is available in:

- German
- English
- Czech

## Requirements

- Python 3.10 or newer
- Windows, Linux Mint, or Ubuntu

Required packages:

- `requests`
- `beautifulsoup4`
- `pillow`
- `reportlab` (optional, for PDF export)
- `tkinter` or the corresponding GUI dependencies on Linux, if needed

## Installation

### Linux Mint / Ubuntu

```bash
sudo apt update
sudo apt install python3-tk python3-pip
```

### Install Python dependencies

```bash
pip install requests beautifulsoup4 pillow reportlab certifi pip-system-certs
```

## Features

### Language support

The user interface can be switched between:

- German
- English
- Czech

### Book management

- Add entries using URL, target folder, and page selection
- Select pages like `1,5,8-10`
- Leave the page field empty to download all pages
- Delete entries from the waiting list
- Change page ranges later
- Save and reload waiting lists as JSON files

### Download workflow

- Downloads pages one by one
- Shows per-book status with symbols such as `✅`, `⚠️`, and `❌`
- Shows overall progress with a progress bar
- Can be stopped at any time
- Can continue work from a previously saved waiting list

### Logging

- Log messages are shown inside the application
- The log can be saved manually to a text file
- The log window can be shown or hidden

### PDF export

- Export downloaded JPG files as a PDF
- One PDF is created per folder containing downloaded images

## Usage

1. Start the application.
2. Enter a Porta fontium URL.
3. Choose a target directory.
4. Optionally enter specific pages, for example `1,5,8-10`.
5. Add the entry to the waiting list.
6. Start the download.
7. Optionally export the downloaded images to PDF.

## Output structure

Example:

```text
Folder/
├── Birth_register_1780-1795_32001020/
│   ├── Birth_register_0001.jpg
│   ├── Birth_register_0002.jpg
│   └── Birth_register_1780-1795_32001020.pdf
```

Depending on the source and detected metadata, folder and file names may vary.


## Notes

This project was created with assistance from ChatGPT 5.

## Disclaimer

Use this tool responsibly and make sure your downloads comply with the terms of use of the source website.
