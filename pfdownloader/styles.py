from __future__ import annotations


def light_stylesheet() -> str:
    return """
    QMainWindow, QWidget {
        background: #f5f7fb;
        color: #1f2937;
    }
    QGroupBox {
        background: #ffffff;
        border: 1px solid #dbe2ea;
        border-radius: 14px;
        margin-top: 8px;
        font-weight: 600;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }
    QLabel {
        color: #334155;
        background: transparent;
    }
    QLabel#hintLabel {
        color: #64748b;
        font-style: italic;
    }
    QLineEdit, QTextEdit, QTableWidget {
        background: #ffffff;
        color: #1f2937;
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        padding: 8px;
    }
    QTableWidget {
        gridline-color: #e2e8f0;
        alternate-background-color: #f8fafc;
    }
    QHeaderView::section {
        background: #eef2f7;
        color: #334155;
        border: none;
        border-bottom: 1px solid #dbe2ea;
        padding: 10px;
        font-weight: 600;
    }
    QPushButton {
        background: #e9eef6;
        color: #1f2937;
        border: 1px solid #d4dce7;
        border-radius: 12px;
        padding: 10px 14px;
        font-weight: 600;
        text-align: center;
    }
    QPushButton:hover {
        background: #dde6f3;
    }
    QPushButton:pressed {
        background: #d5dfef;
    }
    QPushButton:disabled {
        color: #94a3b8;
        background: #eef2f7;
    }
    QPushButton#addBookButton {
        background: #facc15;
        color: #1f2937;
        border: 1px solid #eab308;
    }
    QPushButton#addBookButton:hover {
        background: #eab308;
    }
    QPushButton#addBookButton:pressed {
        background: #ca8a04;
        color: white;
    }
    QPushButton#deleteBookButton {
        background: #f97316;
        color: white;
        border: 1px solid #ea580c;
    }
    QPushButton#deleteBookButton:hover {
        background: #ea580c;
    }
    QPushButton#deleteBookButton:pressed {
        background: #c2410c;
    }
    QPushButton#changePagesButton {
        background: #a855f7;
        color: white;
        border: 1px solid #9333ea;
    }
    QPushButton#changePagesButton:hover {
        background: #9333ea;
    }
    QPushButton#changePagesButton:pressed {
        background: #7e22ce;
    }
    QPushButton#downloadButton {
        background: #22c55e;
        color: white;
        border: 1px solid #16a34a;
    }
    QPushButton#downloadButton:hover {
        background: #16a34a;
    }
    QPushButton#downloadButton:pressed {
        background: #15803d;
    }
    QPushButton#downloadButton:disabled {
        background: #86efac;
        color: white;
        border: 1px solid #4ade80;
    }
    QPushButton#stopButton {
        background: #ef4444;
        color: white;
        border: 1px solid #dc2626;
    }
    QPushButton#stopButton:hover {
        background: #dc2626;
    }
    QPushButton#stopButton:pressed {
        background: #b91c1c;
    }
    QPushButton#stopButton:disabled {
        background: #fca5a5;
        color: white;
        border: 1px solid #f87171;
    }
    QPushButton#resetButton {
        background: #3b82f6;
        color: white;
        border: 1px solid #2563eb;
    }
    QPushButton#resetButton:hover {
        background: #2563eb;
    }
    QPushButton#resetButton:pressed {
        background: #1d4ed8;
    }
    QPushButton#resetButton:disabled {
        background: #93c5fd;
        color: white;
        border: 1px solid #60a5fa;
    }
    QProgressBar {
        border: 1px solid #d4dce7;
        border-radius: 10px;
        background: #ffffff;
        text-align: center;
        min-height: 24px;
    }
    QProgressBar::chunk {
        background: #3b82f6;
        border-radius: 9px;
    }
    QRadioButton {
        spacing: 1px;
        background: transparent;
    }
    QStatusBar {
        background: #ffffff;
        color: #475569;
        border-top: 1px solid #dbe2ea;
    }
    """


def dark_stylesheet() -> str:
    return """
    QMainWindow, QWidget {
        background: #111827;
        color: #e5e7eb;
    }
    QGroupBox {
        background: #1f2937;
        border: 1px solid #374151;
        border-radius: 14px;
        margin-top: 8px;
        font-weight: 600;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }
    QLabel {
        color: #d1d5db;
        background: transparent;
    }
    QLabel#hintLabel {
        color: #9ca3af;
        font-style: italic;
    }
    QLineEdit, QTextEdit, QTableWidget {
        background: #0f172a;
        color: #e5e7eb;
        border: 1px solid #374151;
        border-radius: 10px;
        padding: 8px;
    }
    QTableWidget {
        gridline-color: #253041;
        alternate-background-color: #111827;
    }
    QHeaderView::section {
        background: #243041;
        color: #e5e7eb;
        border: none;
        border-bottom: 1px solid #374151;
        padding: 10px;
        font-weight: 600;
    }
    QPushButton {
        background: #273549;
        color: #f8fafc;
        border: 1px solid #3c4b60;
        border-radius: 12px;
        padding: 10px 14px;
        font-weight: 600;
        text-align: center;
    }
    QPushButton:hover {
        background: #32445d;
    }
    QPushButton:pressed {
        background: #40526b;
    }
    QPushButton:disabled {
        color: #94a3b8;
        background: #1f2937;
    }
    QPushButton#addBookButton {
        background: #eab308;
        color: #111827;
        border: 1px solid #ca8a04;
    }
    QPushButton#addBookButton:hover {
        background: #facc15;
    }
    QPushButton#addBookButton:pressed {
        background: #a16207;
        color: white;
    }
    QPushButton#deleteBookButton {
        background: #f97316;
        color: white;
        border: 1px solid #ea580c;
    }
    QPushButton#deleteBookButton:hover {
        background: #ea580c;
    }
    QPushButton#deleteBookButton:pressed {
        background: #c2410c;
    }
    QPushButton#changePagesButton {
        background: #9333ea;
        color: white;
        border: 1px solid #7e22ce;
    }
    QPushButton#changePagesButton:hover {
        background: #7e22ce;
    }
    QPushButton#changePagesButton:pressed {
        background: #6b21a8;
    }
    QPushButton#downloadButton {
        background: #16a34a;
        color: white;
        border: 1px solid #15803d;
    }
    QPushButton#downloadButton:hover {
        background: #15803d;
    }
    QPushButton#downloadButton:pressed {
        background: #166534;
    }
    QPushButton#downloadButton:disabled {
        background: #14532d;
        color: #d1fae5;
        border: 1px solid #166534;
    }
    QPushButton#stopButton {
        background: #dc2626;
        color: white;
        border: 1px solid #b91c1c;
    }
    QPushButton#stopButton:hover {
        background: #b91c1c;
    }
    QPushButton#stopButton:pressed {
        background: #991b1b;
    }
    QPushButton#stopButton:disabled {
        background: #7f1d1d;
        color: #fee2e2;
        border: 1px solid #991b1b;
    }
    QPushButton#resetButton {
        background: #2563eb;
        color: white;
        border: 1px solid #1d4ed8;
    }
    QPushButton#resetButton:hover {
        background: #1d4ed8;
    }
    QPushButton#resetButton:pressed {
        background: #1e40af;
    }
    QPushButton#resetButton:disabled {
        background: #1e3a8a;
        color: #dbeafe;
        border: 1px solid #2563eb;
    }
    QProgressBar {
        border: 1px solid #374151;
        border-radius: 10px;
        background: #0f172a;
        text-align: center;
        min-height: 24px;
    }
    QProgressBar::chunk {
        background: #60a5fa;
        border-radius: 9px;
    }
    QRadioButton {
        spacing: 1px;
        background: transparent;
    }
    QStatusBar {
        background: #1f2937;
        color: #cbd5e1;
        border-top: 1px solid #374151;
    }
    """
