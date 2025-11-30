# Porta fontium Downloader
File-Downloader for Porta fontium 🇩🇪 🇬🇧 🇨🇿

![alt text](https://github.com/Testatost/Porta-Fontium-Downloader/blob/main/Porta%20fontium%20Downloader.png?raw=true)

# 🚀 Installation

## Voraussetzungen
- **Python 3.10+**  
- Linux Mint, Ubuntu oder Windows  
- Abhängigkeiten:  
  - `requests`
  - `beautifulsoup4`
  - `pillow`
  - `reportlab` (optional, für PDF-Export)
  - `tkinter` (unter Linux extra installieren)

---

# 📦 Abhängigkeiten installieren

## 👉 Linux Mint / Ubuntu
```md
sudo apt update
```
```md
sudo apt install python3-tk python3-pip
```
## 👉 in Pycharm
```md
pip install requests beautifulsoup4 pillow reportlab
```


# 🇩🇪 Deutsch

## 🔑 Hauptaufgabe

•	  Du kannst URLs von Büchern, Karten oder Dokumenten von portafontium.eu eingeben.  
•	  Das Programm sucht in der Seite nach IIP-Bildserver-Links (das sind die hochauflösenden Scans).  
•	  Es baut daraus direkte Download-Links zu JPEG-Bildern.  
•	  Diese Bilder werden als Einzelseiten (page_0001.jpg, page_0002.jpg, …) in einen Zielordner heruntergeladen.  
•	  Mehrere Bücher können in eine Warteliste gelegt und nacheinander heruntergeladen werden.  

## 🛠️ Funktionen
### 1.	Sprachen
•	 Oberfläche in Deutsch 🇩🇪, Englisch 🇬🇧 und Tschechisch 🇨🇿 umschaltbar.
### 2.	Buchverwaltung
•	 URL + Zielordner + gewünschte Seiten angeben.
•	 Seiten können z. B. als 1,5,8-10 spezifiziert werden, leer = alle.
•	 Bücher können hinzugefügt, gelöscht oder die Seitenbereiche geändert werden.
•	 Wartelisten lassen sich als JSON speichern und wieder laden.
### 3.	Download
•	 Bilder werden seitenweise geladen.
•	 Fortschritt je Buch (✅, ⚠️, ❌) und Gesamtfortschritt in einer Fortschrittsleiste angezeigt.
•	 Abbruch (Stop-Button) jederzeit möglich.
•	 Wiederaufnahme über gespeicherte Warteliste.
### 4.	Logging
•	 Meldungen (z. B. „Buch hinzugefügt“, „Download gestartet“) werden im Logbereich angezeigt.
•	 Optional werden die Logs in einer Datei download_log.txt im Zielordner gespeichert.
•	 Logfenster kann ein-/ausgeblendet werden.
### 5.	GUI-Details (Tkinter)
•	 Tabellenansicht der Warteliste mit URL, Seiten, Status.
•	 Buttons für „Download starten“, „Stoppen“, „Reset“.
•	 Kontextfunktionen wie Doppelklick → Buch-URL im Browser öffnen.
•	 Fortschrittsbalken für alle Bücher.

# 🇬🇧 English
## 🔑 Main Purpose
•	You can enter URLs of books, maps, or documents from portafontium.eu.  
•	The program scans the page for IIP image server links (these point to the high-resolution scans).  
•	It then builds direct JPEG download links.  
•	These images are saved as individual pages (page_0001.jpg, page_0002.jpg, …) in a chosen folder.  
•	Multiple books can be added to a waiting list and downloaded one after another.  

## 🛠️ Features
### 1.	Languages
•	 Interface available in German 🇩🇪, English 🇬🇧, and Czech 🇨🇿.
### 2.	Book management
•	 Enter URL + target folder + desired pages.
•	 Pages can be specified like 1,5,8-10; empty = all pages.
•	 Books can be added, deleted, or edited (pages).
•	 Waiting lists can be saved as JSON and loaded later.
### 3.	Download
•	 Downloads images page by page.
•	 Shows per-book status (✅, ⚠️, ❌) and overall progress bar.
•	 Can be stopped anytime.
•	 Downloads can be resumed from saved waiting lists.
### 4.	Logging
•	 Messages (e.g., “Book added”, “Download started”) appear in the log window.
•	 Optionally saved to download_log.txt in the target folder.
•	 Log window can be shown/hidden.
### 5.	GUI details (Tkinter)
•	 Table view of waiting list with URL, pages, and status.
•	 Buttons for “Download”, “Stop”, “Reset”.
•	 Double-click opens the book’s URL in browser.
•	 Global progress bar for all books.

# 🇨🇿 Čeština
## 🔑 Hlavní účel
•	Můžete zadat URL knih, map nebo dokumentů z portafontium.eu.  
•	Program vyhledá na stránce odkazy na IIP image server (ty vedou na naskenované stránky ve vysokém rozlišení).  
•	Vytvoří z nich přímé odkazy pro stažení JPEG obrázků.  
•	Obrázky se uloží jako jednotlivé stránky (page_0001.jpg, page_0002.jpg, …) do zvolené složky.  
•	Do seznamu ke stažení lze přidat více knih a stáhnout je postupně.  

## 🛠️ Funkce
### 1.	Jazyky
•	 Rozhraní je dostupné v němčině 🇩🇪, angličtině 🇬🇧 a češtině 🇨🇿.
### 2.	Správa knih
•	 Zadání URL + cílové složky + požadovaných stránek.
•	 Stránky lze specifikovat např. 1,5,8-10; prázdné = všechny.
•	 Knihy lze přidávat, mazat nebo měnit (rozsah stránek).
•	 Seznamy lze ukládat do JSON a později znovu načíst.
### 3.	Stahování
•	 Stránky se stahují jednotlivě.
•	 Zobrazuje stav každé knihy (✅, ⚠️, ❌) i celkový průběh.
•	 Stahování lze kdykoliv zastavit.
•	 Pokračování je možné ze uloženého seznamu.
### 4.	Logování
•	 Zprávy (např. „Kniha přidána“, „Stažení spuštěno“) se zobrazují v logu.
•	 Volitelně se ukládají do souboru download_log.txt v cílové složce.
•	 Okno s logem lze zobrazit nebo skrýt.
### 5.	GUI (Tkinter)
•	 Tabulkový seznam se sloupci URL, stránky a stav.
•	 Tlačítka „Stáhnout“, „Zastavit“, „Reset“.
•	 Dvojklik otevře URL knihy v prohlížeči.
•	 Celkový průběh je v progress baru.

------------------------------------------------------------------------------------------------------------------------

Disclaimer: This code was made with ChatGPT 5.


------------------------------------------------------------------------------------------------------------------------

Update 1.1
-individuelle Dateinnamen (heruntergeladene Dateien haben nun einen individuellen Namen von dem Verzeichnis aus dem sie herstammen)

------------------------------------------------------------------------------------------------------------------------

Update 1.2
-changed the structure of the pathes for the downloaded files
```md
📂 Ort-Misto-Place/
└── 📂 Geburtsmatrik-Matrika_narozených-Birth_register_1780-1795/
    ├── 🖼️ Geburtsmatrik_Matrika_narozených_Birth_register_0001.jpg
    ├── 🖼️ Geburtsmatrik_Matrika_narozených_Birth_register_0002.jpg
    ├── 📄 metadata.txt
    └── 📄 Geburtsmatrik-Matrika_narozených-Birth_register_1780-1795.pdf
```
