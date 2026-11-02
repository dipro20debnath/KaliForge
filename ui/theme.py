"""Theme — colour tokens and a global QSS stylesheet.

Three schemes are offered (matching the project brief): the default Kali dark
with neon green, a cyberpunk cyan variant and a muted professional SOC dark.
All three share one widget stylesheet driven by the colour tokens below.
"""
from __future__ import annotations

THEMES = {
    "kali_neon": {
        "name": "Kali Dark · Neon Green",
        "bg": "#0a0e10", "bg_alt": "#0f1518", "panel": "#111a1d", "panel_alt": "#162226",
        "border": "#1f2e32", "border_bright": "#27e0a1",
        "text": "#d6e4e6", "text_dim": "#7f9499", "text_mut": "#56696d",
        "accent": "#27e0a1", "accent_2": "#13c2c2", "accent_soft": "#0e3b32",
        "sel": "#123a33",
        "crit": "#ff3860", "high": "#ff8c1a", "med": "#ffd23f", "low": "#2ecc71", "info": "#3fa9ff",
    },
    "cyber_cyan": {
        "name": "Black · Cyan Cyberpunk",
        "bg": "#05070d", "bg_alt": "#0a0f1a", "panel": "#0c1322", "panel_alt": "#121c30",
        "border": "#1b2740", "border_bright": "#00e5ff",
        "text": "#d4e6ff", "text_dim": "#7a90b5", "text_mut": "#536484",
        "accent": "#00e5ff", "accent_2": "#8a5cff", "accent_soft": "#07283a",
        "sel": "#0d2f45",
        "crit": "#ff2d6f", "high": "#ff9f1c", "med": "#ffe14d", "low": "#3ddc97", "info": "#4dc3ff",
    },
    "soc_pro": {
        "name": "Professional SOC Dark",
        "bg": "#12151c", "bg_alt": "#171b24", "panel": "#1b202b", "panel_alt": "#222836",
        "border": "#2a3140", "border_bright": "#4c8bf5",
        "text": "#e2e6ee", "text_dim": "#9aa3b5", "text_mut": "#6b7488",
        "accent": "#4c8bf5", "accent_2": "#35c6c0", "accent_soft": "#1d2d4a",
        "sel": "#223250",
        "crit": "#f04e6e", "high": "#f0984e", "med": "#f0d24e", "low": "#4ecf8a", "info": "#4c8bf5",
    },
}

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
QMainWindow, QDialog {{ background: {c['bg']}; }}

QToolTip {{
    background: {c['panel_alt']}; color: {c['text']};
    border: 1px solid {c['border_bright']}; padding: 5px 8px; border-radius: 4px;
}}

/* ---- Sidebar ---- */
#Sidebar {{ background: {c['bg_alt']}; border-right: 1px solid {c['border']}; }}
#Brand {{ color: {c['accent']}; font-size: {ui_font_size + 7}pt; font-weight: 800; letter-spacing: 1px; }}
#BrandSub {{ color: {c['text_mut']}; font-size: {ui_font_size - 2}pt; }}
#StatusPill {{
    color: {c['accent']}; background: {c['accent_soft']};
    border: 1px solid {c['accent']}; border-radius: 9px; padding: 2px 10px;
    font-size: {ui_font_size - 2}pt; font-weight: 700;
}}
QPushButton#NavItem {{
    text-align: left; padding: 9px 14px; border: none; border-radius: 8px;
    background: transparent; color: {c['text_dim']}; font-weight: 600;
}}
QPushButton#NavItem:hover {{ background: {c['panel']}; color: {c['text']}; }}
QPushButton#NavItem:checked {{
    background: {c['accent_soft']}; color: {c['accent']};
    border-left: 3px solid {c['accent']};
}}
#NavSection {{ color: {c['text_mut']}; font-size: {ui_font_size - 2}pt;
               font-weight: 700; letter-spacing: 1px; padding: 12px 14px 4px; }}

/* ---- Cards / panels ---- */
#Card, #Panel {{
    background: {c['panel']}; border: 1px solid {c['border']}; border-radius: 12px;
}}
#Card:hover {{ border: 1px solid {c['border_bright']}; }}
#CardTitle {{ font-weight: 700; font-size: {ui_font_size + 1}pt; color: {c['text']}; }}
#StatValue {{ font-size: {ui_font_size + 14}pt; font-weight: 800; color: {c['accent']}; }}
#StatLabel {{ color: {c['text_mut']}; font-size: {ui_font_size - 1}pt;
              font-weight: 700; letter-spacing: 1px; }}
#PageTitle {{ font-size: {ui_font_size + 9}pt; font-weight: 800; color: {c['text']}; }}
#PageSub {{ color: {c['text_dim']}; }}
#Hint {{ color: {c['text_mut']}; font-size: {ui_font_size - 1}pt; }}

/* ---- Buttons ---- */
QPushButton {{
    background: {c['panel_alt']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 8px; padding: 7px 14px; font-weight: 600;
}}
QPushButton:hover {{ border: 1px solid {c['border_bright']}; color: {c['text']}; }}
QPushButton:disabled {{ color: {c['text_mut']}; border-color: {c['border']}; }}
QPushButton#Primary {{
    background: {c['accent']}; color: {c['bg']}; border: none; font-weight: 800;
}}
QPushButton#Primary:hover {{ background: {c['accent_2']}; }}
QPushButton#Danger {{ background: {c['crit']}; color: #fff; border: none; }}
QPushButton#Ghost {{ background: transparent; }}

/* ---- Inputs ---- */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {c['bg_alt']}; border: 1px solid {c['border']}; border-radius: 8px;
    padding: 7px 10px; selection-background-color: {c['sel']};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
    border: 1px solid {c['accent']};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {c['panel_alt']}; border: 1px solid {c['border_bright']};
    selection-background-color: {c['sel']};
}}

/* ---- Tabs ---- */
QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: 8px; top: -1px; }}
QTabBar::tab {{
    background: transparent; color: {c['text_dim']}; padding: 8px 16px;
    border-bottom: 2px solid transparent; font-weight: 600;
}}
QTabBar::tab:selected {{ color: {c['accent']}; border-bottom: 2px solid {c['accent']}; }}

/* ---- Tables / lists ---- */
QTableWidget, QTreeWidget, QListWidget {{
    background: {c['panel']}; border: 1px solid {c['border']}; border-radius: 8px;
    gridline-color: {c['border']}; alternate-background-color: {c['bg_alt']};
}}
QHeaderView::section {{
    background: {c['panel_alt']}; color: {c['text_dim']}; padding: 6px 8px;
    border: none; border-bottom: 1px solid {c['border']}; font-weight: 700;
}}
QTableWidget::item:selected, QListWidget::item:selected, QTreeWidget::item:selected {{
    background: {c['sel']}; color: {c['text']};
}}

/* ---- Filter chips ---- */
QPushButton#Chip {{
    background: {c['bg_alt']}; color: {c['text_dim']}; border: 1px solid {c['border']};
    border-radius: 14px; padding: 5px 13px; font-weight: 600;
}}
QPushButton#Chip:checked {{
    background: {c['accent_soft']}; color: {c['accent']}; border: 1px solid {c['accent']};
}}

/* ---- Badges ---- */
#BadgeInstalled {{ color: {c['low']}; font-weight: 700; }}
#BadgeMissing {{ color: {c['high']}; font-weight: 700; }}
#BadgeBuiltin {{ color: {c['info']}; font-weight: 700; }}

/* ---- Progress / meters ---- */
QProgressBar {{
    background: {c['bg_alt']}; border: 1px solid {c['border']}; border-radius: 7px;
    height: 14px; text-align: center; color: {c['text']};
}}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 6px; }}

/* ---- Scrollbars ---- */
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 5px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {c['accent']}; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 5px; min-width: 28px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}

QSplitter::handle {{ background: {c['border']}; }}
#TermView {{ background: #05080a; border: 1px solid {c['border']}; border-radius: 8px; }}
QLabel#SevCrit {{ color: {c['crit']}; font-weight: 800; }}
QLabel#SevHigh {{ color: {c['high']}; font-weight: 800; }}
QLabel#SevMed {{ color: {c['med']}; font-weight: 800; }}
QLabel#SevLow {{ color: {c['low']}; font-weight: 800; }}
QLabel#SevInfo {{ color: {c['info']}; font-weight: 800; }}
"""
