"""Tema visual centralizado da interface grafica do trabalho.

Concentrar cores e estilos aqui deixa a GUI mais facil de ajustar sem misturar
aparencia com a logica de exibicao.
"""

from __future__ import annotations


BG = "#1a1a1a"
BG_SURFACE = "#222222"
BG_CARD = "#252525"
BG_CARD_HOVER = "#2e2e2e"
TEXT_PRIMARY = "#d8d8d8"
TEXT_SECONDARY = "#808080"
ACCENT = "#5c9ece"
ACCENT_DIM = "#4a7fa8"
PATH_COLOR = "#e06050"
MARKER_COLOR = "#e8b830"
CHECKPOINT_COLOR = "#d05838"
SEPARATOR_COLOR = "#333333"
BORDER_COLOR = "#333333"
MAP_BACKGROUND = "#181818"
TERRAIN_LEGEND_ORDER = (".", "R", "F", "A", "M")

TERRAIN_COLORS = {
    ".": "#c8c4b8",
    "R": "#8d98a0",
    "F": "#4a8a50",
    "V": "#4a8a50",
    "A": "#4a90c8",
    "M": "#8a6542",
}

TERRAIN_LABELS = {
    ".": "Plano",
    "R": "Rochoso",
    "F": "Floresta",
    "V": "Floresta",
    "A": "Agua",
    "M": "Montanha",
}


def build_stylesheet() -> str:
    """Retorna o stylesheet Qt global usado pela interface do trabalho."""

    return f"""
        QMainWindow, QWidget {{
            background-color: {BG};
            color: {TEXT_PRIMARY};
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            font-size: 13px;
        }}
        QGroupBox {{
            background-color: {BG_CARD};
            border: 1px solid {BORDER_COLOR};
            border-radius: 6px;
            margin-top: 14px;
            padding: 14px 10px 10px 10px;
            font-size: 11px;
            font-weight: 600;
            color: {TEXT_SECONDARY};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 6px;
            color: {TEXT_SECONDARY};
        }}
        QPushButton {{
            background-color: {BG_CARD};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 6px 14px;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {BG_CARD_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {SEPARATOR_COLOR};
        }}
        QSlider::groove:horizontal {{
            height: 4px;
            background: {BG_SURFACE};
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: {TEXT_SECONDARY};
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {TEXT_PRIMARY};
        }}
        QTableWidget {{
            background-color: {BG_SURFACE};
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            gridline-color: {BORDER_COLOR};
            font-size: 11px;
        }}
        QTableWidget::item {{
            padding: 4px 8px;
            color: {TEXT_PRIMARY};
        }}
        QTableWidget::item:selected {{
            background-color: {ACCENT_DIM};
            color: white;
        }}
        QHeaderView::section {{
            background-color: {BG_CARD};
            color: {TEXT_SECONDARY};
            font-weight: 600;
            font-size: 11px;
            border: none;
            border-bottom: 1px solid {BORDER_COLOR};
            padding: 6px 8px;
        }}
        QScrollBar:vertical {{
            background: {BG};
            width: 8px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background: {SEPARATOR_COLOR};
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {TEXT_SECONDARY};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        QScrollBar:horizontal {{
            background: {BG};
            height: 8px;
            border: none;
        }}
        QScrollBar::handle:horizontal {{
            background: {SEPARATOR_COLOR};
            border-radius: 4px;
            min-width: 20px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {TEXT_SECONDARY};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}
    """
