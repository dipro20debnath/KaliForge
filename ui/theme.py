"""Theme — colour tokens and a global QSS stylesheet.

Three schemes are offered (matching the project brief): the default Kali dark
with neon green, a cyberpunk cyan variant and a muted professional SOC dark.
All three share one widget stylesheet driven by the colour tokens below.
"""
from __future__ import annotations

THEMES = {
    "kali_neon": {
        "name": "Kali Dark · Neon Green",
        "bg": "#080b0d", "bg_alt": "#0f1518", "panel": "#111a1d", "panel_alt": "#162226",
        "panel_hi": "#19282c", "border": "#1f2e32", "border_bright": "#27e0a1",
        "text": "#d6e4e6", "text_dim": "#7f9499", "text_mut": "#56696d",
        "accent": "#27e0a1", "accent_2": "#13c2c2", "accent_soft": "#0e3b32",
        "sel": "#123a33", "glow": "rgba(39, 224, 161, 0.35)",
        "crit": "#ff3860", "high": "#ff8c1a", "med": "#ffd23f", "low": "#2ecc71", "info": "#3fa9ff",
    },
    "cyber_cyan": {
        "name": "Black · Cyan Cyberpunk",
        "bg": "#04060c", "bg_alt": "#0a0f1a", "panel": "#0c1322", "panel_alt": "#121c30",
        "panel_hi": "#152138", "border": "#1b2740", "border_bright": "#00e5ff",
        "text": "#d4e6ff", "text_dim": "#7a90b5", "text_mut": "#536484",
        "accent": "#00e5ff", "accent_2": "#8a5cff", "accent_soft": "#07283a",
        "sel": "#0d2f45", "glow": "rgba(0, 229, 255, 0.35)",
        "crit": "#ff2d6f", "high": "#ff9f1c", "med": "#ffe14d", "low": "#3ddc97", "info": "#4dc3ff",
    },
    "soc_pro": {
        "name": "Professional SOC Dark",
        "bg": "#10131a", "bg_alt": "#171b24", "panel": "#1b202b", "panel_alt": "#222836",
        "panel_hi": "#283044", "border": "#2a3140", "border_bright": "#4c8bf5",
        "text": "#e2e6ee", "text_dim": "#9aa3b5", "text_mut": "#6b7488",
        "accent": "#4c8bf5", "accent_2": "#35c6c0", "accent_soft": "#1d2d4a",
        "sel": "#223250", "glow": "rgba(76, 139, 245, 0.35)",
        "crit": "#f04e6e", "high": "#f0984e", "med": "#f0d24e", "low": "#4ecf8a", "info": "#4c8bf5",
    },
    "light": {
        "name": "Light · Daybreak",
        "bg": "#f4f6f8", "bg_alt": "#eaeef2", "panel": "#ffffff", "panel_alt": "#f2f5f8",
        "panel_hi": "#eaf2ee", "border": "#d6dde5", "border_bright": "#0c9f76",
        "text": "#16202a", "text_dim": "#4f5e6c", "text_mut": "#7c8a97",
        "accent": "#0c9f76", "accent_2": "#0e9fae", "accent_soft": "#dcf3eb",
        "sel": "#d2efe5", "glow": "rgba(12, 159, 118, 0.25)",
        "crit": "#e11d48", "high": "#e07400", "med": "#b7900a", "low": "#16a34a", "info": "#2563eb",
        "light": True,
    },
}


def is_light(theme_id: str) -> bool:
    return bool(palette(theme_id).get("light"))

SEVERITY_KEYS = {"critical": "crit", "high": "high", "medium": "med", "low": "low", "info": "info"}


def palette(theme_id: str) -> dict:
    return THEMES.get(theme_id, THEMES["kali_neon"])


def severity_color(theme_id: str, severity: str) -> str:
    pal = palette(theme_id)
    return pal.get(SEVERITY_KEYS.get(severity, "info"), pal["info"])


def stylesheet(theme_id: str, ui_font_size: int = 10) -> str:
    c = palette(theme_id)
    return f"""
* {{
    font-family: "Inter", "Segoe UI", "DejaVu Sans", sans-serif;
    font-size: {ui_font_size}pt;
    color: {c['text']};
    outline: none;
}}
QWidget {{ background: {c['bg']}; }}
QMainWindow, QDialog {{
    background: qlineargradient(x1:0, y1:0, x2:0.6, y2:1,
                stop:0 {c['bg']}, stop:1 {c['bg_alt']});
}}

QToolTip {{
    background: {c['panel_alt']}; color: {c['text']};
    border: 1px solid {c['border_bright']}; padding: 5px 9px; border-radius: 5px;
}}

/* ---- Sidebar ---- */
#Sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {c['bg_alt']}, stop:1 {c['bg']});
    border-right: 1px solid {c['border']};
}}
#Brand {{ color: {c['accent']}; font-size: {ui_font_size + 7}pt; font-weight: 800; letter-spacing: 1px; }}
#BrandSub {{ color: {c['text_mut']}; font-size: {ui_font_size - 2}pt; }}
#StatusPill {{
    color: {c['accent']};
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {c['accent_soft']}, stop:1 transparent);
    border: 1px solid {c['accent']}; border-radius: 9px; padding: 2px 10px;
    font-size: {ui_font_size - 2}pt; font-weight: 700;
}}
QPushButton#NavItem {{
    text-align: left; padding: 9px 14px; border: none; border-radius: 9px;
    background: transparent; color: {c['text_dim']}; font-weight: 600;
    border-left: 3px solid transparent;
}}
QPushButton#NavItem:hover {{ background: {c['panel']}; color: {c['text']}; border-left: 3px solid {c['border_bright']}; }}
QPushButton#NavItem:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {c['accent_soft']}, stop:1 transparent);
    color: {c['accent']}; border-left: 3px solid {c['accent']};
}}
#NavSection {{ color: {c['text_mut']}; font-size: {ui_font_size - 2}pt;
               font-weight: 700; letter-spacing: 1px; padding: 12px 14px 4px; }}

/* ---- Top header bar ---- */
#TopBar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {c['bg_alt']}, stop:1 {c['bg']});
    border-bottom: 1px solid {c['border']};
}}
#TopTitle {{ font-size: {ui_font_size + 4}pt; font-weight: 800; color: {c['text']}; }}
#TopIcon {{ font-size: {ui_font_size + 5}pt; }}
#WsChip {{
    color: {c['accent']}; background: {c['accent_soft']};
    border: 1px solid {c['border']}; border-radius: 12px; padding: 4px 12px;
    font-weight: 700; font-size: {ui_font_size - 1}pt;
}}
QPushButton#SearchBtn {{
    background: {c['bg']}; color: {c['text_dim']}; border: 1px solid {c['border']};
    border-radius: 9px; padding: 6px 14px; text-align: left; font-weight: 600;
}}
QPushButton#SearchBtn:hover {{ border: 1px solid {c['border_bright']}; color: {c['text']}; }}

/* ---- Cards / panels ---- */
#Card, #Panel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {c['panel_alt']}, stop:1 {c['panel']});
    border: 1px solid {c['border']}; border-radius: 13px;
}}
#Card:hover {{ border: 1px solid {c['border_bright']}; background: {c['panel_hi']}; }}
#CardTitle {{ font-weight: 700; font-size: {ui_font_size + 1}pt; color: {c['text']}; }}
#StatValue {{ font-size: {ui_font_size + 15}pt; font-weight: 800; color: {c['accent']}; }}
#StatLabel {{ color: {c['text_mut']}; font-size: {ui_font_size - 1}pt;
              font-weight: 700; letter-spacing: 1px; }}
#PageTitle {{ font-size: {ui_font_size + 9}pt; font-weight: 800; color: {c['text']}; }}
#PageSub {{ color: {c['text_dim']}; }}
#Hint {{ color: {c['text_mut']}; font-size: {ui_font_size - 1}pt; }}

/* ---- Buttons ---- */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {c['panel_hi']}, stop:1 {c['panel_alt']});
    color: {c['text']}; border: 1px solid {c['border']}; border-radius: 9px;
    padding: 7px 15px; font-weight: 600;
}}
QPushButton:hover {{ border: 1px solid {c['border_bright']}; color: {c['text']}; }}
QPushButton:pressed {{ background: {c['panel']}; padding-top: 8px; padding-bottom: 6px; }}
QPushButton:disabled {{ color: {c['text_mut']}; border-color: {c['border']}; background: {c['panel']}; }}
QPushButton#Primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {c['accent']}, stop:1 {c['accent_2']});
    color: {c['bg']}; border: none; font-weight: 800;
}}
QPushButton#Primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {c['accent_2']}, stop:1 {c['accent']});
}}
QPushButton#Danger {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {c['crit']}, stop:1 #c22847);
    color: #fff; border: none; font-weight: 700;
}}
QPushButton#Danger:hover {{ background: {c['crit']}; }}
QPushButton#Ghost {{ background: transparent; border: 1px solid {c['border']}; }}
QPushButton#Ghost:hover {{ border: 1px solid {c['border_bright']}; background: {c['panel']}; }}
QToolButton {{
    background: {c['panel_alt']}; color: {c['text_dim']}; border: 1px solid {c['border']};
    border-radius: 9px; padding: 6px 12px; font-weight: 600;
}}
QToolButton:hover {{ border: 1px solid {c['border_bright']}; color: {c['text']}; }}
QToolButton:checked {{ background: {c['accent_soft']}; color: {c['accent']}; border: 1px solid {c['accent']}; }}

/* ---- Inputs ---- */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {c['bg_alt']}; border: 1px solid {c['border']}; border-radius: 9px;
    padding: 7px 11px; selection-background-color: {c['sel']};
}}
QLineEdit:hover, QComboBox:hover, QPlainTextEdit:hover, QTextEdit:hover {{ border: 1px solid {c['text_mut']}; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {c['accent']};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {c['panel_alt']}; border: 1px solid {c['border_bright']};
    selection-background-color: {c['sel']}; border-radius: 8px; padding: 4px;
}}

/* ---- Tabs ---- */
QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: 10px; top: -1px; }}
QTabBar::tab {{
    background: transparent; color: {c['text_dim']}; padding: 8px 18px;
    border-bottom: 2px solid transparent; font-weight: 600; margin-right: 2px;
}}
QTabBar::tab:hover {{ color: {c['text']}; }}
QTabBar::tab:selected {{ color: {c['accent']}; border-bottom: 2px solid {c['accent']}; }}

/* ---- Tables / lists / trees ---- */
QTableWidget, QTreeWidget, QListWidget {{
    background: {c['panel']}; border: 1px solid {c['border']}; border-radius: 10px;
    gridline-color: {c['border']}; alternate-background-color: {c['bg_alt']};
}}
QHeaderView::section {{
    background: {c['panel_alt']}; color: {c['text_dim']}; padding: 7px 9px;
    border: none; border-bottom: 1px solid {c['border']}; font-weight: 700;
}}
QTableWidget::item, QTreeWidget::item, QListWidget::item {{ padding: 3px; }}
QTableWidget::item:hover, QTreeWidget::item:hover, QListWidget::item:hover {{ background: {c['panel_alt']}; }}
QTableWidget::item:selected, QListWidget::item:selected, QTreeWidget::item:selected {{
    background: {c['sel']}; color: {c['text']};
}}

/* ---- Filter chips ---- */
QPushButton#Chip {{
    background: {c['bg_alt']}; color: {c['text_dim']}; border: 1px solid {c['border']};
    border-radius: 14px; padding: 5px 14px; font-weight: 600;
}}
QPushButton#Chip:hover {{ border: 1px solid {c['border_bright']}; color: {c['text']}; }}
QPushButton#Chip:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {c['accent_soft']}, stop:1 {c['panel_alt']});
    color: {c['accent']}; border: 1px solid {c['accent']};
}}

/* ---- Badges ---- */
#BadgeInstalled {{ color: {c['low']}; font-weight: 700; }}
#BadgeMissing {{ color: {c['high']}; font-weight: 700; }}
#BadgeBuiltin {{ color: {c['info']}; font-weight: 700; }}

/* ---- Progress / meters ---- */
QProgressBar {{
    background: {c['bg_alt']}; border: 1px solid {c['border']}; border-radius: 8px;
    height: 15px; text-align: center; color: {c['text']};
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {c['accent']}, stop:1 {c['accent_2']});
    border-radius: 7px;
}}

/* ---- Scrollbars ---- */
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {c['accent']}; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 5px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {c['accent']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QSplitter::handle {{ background: {c['border']}; }}
QSplitter::handle:hover {{ background: {c['accent']}; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid {c['border']};
    border-radius: 4px; background: {c['bg_alt']};
}}
QCheckBox::indicator:hover {{ border: 1px solid {c['border_bright']}; }}
QCheckBox::indicator:checked {{
    background: {c['accent']}; border: 1px solid {c['accent']};
}}
QStatusBar {{ background: {c['bg_alt']}; color: {c['text_dim']}; border-top: 1px solid {c['border']}; }}
#TermView {{ background: #05080a; border: 1px solid {c['border']}; border-radius: 10px; }}
QLabel#SevCrit {{ color: {c['crit']}; font-weight: 800; }}
QLabel#SevHigh {{ color: {c['high']}; font-weight: 800; }}
QLabel#SevMed {{ color: {c['med']}; font-weight: 800; }}
QLabel#SevLow {{ color: {c['low']}; font-weight: 800; }}
QLabel#SevInfo {{ color: {c['info']}; font-weight: 800; }}
"""
