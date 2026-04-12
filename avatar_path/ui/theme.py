"""Tema visual centralizado da interface grafica do trabalho."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


BG = "#1e1e2e"
BG_SURFACE = "#262637"
BG_CARD = "#2e2e42"
BG_CARD_HOVER = "#363650"
TEXT_PRIMARY = "#e0e0f0"
TEXT_SECONDARY = "#a0a0c0"
ACCENT = "#7c9ff5"
ACCENT_DIM = "#5a7ad4"
PATH_COLOR = "#f07070"
MARKER_COLOR = "#f5c842"
CHECKPOINT_COLOR = "#e06040"
SEPARATOR_COLOR = "#3a3a55"
BORDER_COLOR = "#3a3a55"
MAP_BACKGROUND = "#1a1a2a"
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


def configure_style(root: tk.Misc) -> None:
    """Aplica um tema unico para evitar cores e fontes espalhadas pela GUI."""

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure("App.TFrame", background=BG)
    style.configure("Card.TFrame", background=BG_CARD)
    style.configure(
        "Panel.TLabelframe",
        background=BG_CARD,
        foreground=TEXT_SECONDARY,
        bordercolor=BORDER_COLOR,
        darkcolor=BORDER_COLOR,
        lightcolor=BORDER_COLOR,
    )
    style.configure(
        "Panel.TLabelframe.Label",
        background=BG_CARD,
        foreground=ACCENT,
        font=("Segoe UI", 10, "bold"),
    )
    style.configure(
        "Header.TLabel",
        background=BG,
        foreground=TEXT_PRIMARY,
        font=("Segoe UI", 22, "bold"),
    )
    style.configure(
        "Subheader.TLabel",
        background=BG,
        foreground=TEXT_SECONDARY,
        font=("Segoe UI", 10),
    )
    style.configure(
        "MapTitle.TLabel",
        background=BG_CARD,
        foreground=ACCENT,
        font=("Segoe UI", 11, "bold"),
    )
    style.configure(
        "Body.TLabel",
        background=BG_CARD,
        foreground=TEXT_SECONDARY,
        font=("Segoe UI", 10),
    )
    style.configure(
        "Value.TLabel",
        background=BG_CARD,
        foreground=TEXT_PRIMARY,
        font=("Segoe UI", 10),
    )
    style.configure(
        "SectionTitle.TLabel",
        background=BG_CARD,
        foreground=ACCENT,
        font=("Segoe UI", 9, "bold"),
    )
    style.configure(
        "Legend.TLabel",
        background=BG_CARD,
        foreground=TEXT_SECONDARY,
        font=("Segoe UI", 9),
    )
    style.configure(
        "Accent.TButton",
        background=ACCENT,
        foreground="white",
        font=("Segoe UI", 10, "bold"),
        borderwidth=0,
        focuscolor=ACCENT,
    )
    style.map(
        "Accent.TButton",
        background=[("active", ACCENT_DIM), ("pressed", ACCENT_DIM)],
    )
    style.configure(
        "Secondary.TButton",
        background=BG_CARD_HOVER,
        foreground=TEXT_PRIMARY,
        font=("Segoe UI", 10),
        borderwidth=0,
        focuscolor=BG_CARD_HOVER,
    )
    style.map(
        "Secondary.TButton",
        background=[("active", SEPARATOR_COLOR), ("pressed", SEPARATOR_COLOR)],
    )
    style.configure(
        "Treeview",
        background=BG_SURFACE,
        fieldbackground=BG_SURFACE,
        foreground=TEXT_PRIMARY,
        rowheight=26,
        borderwidth=0,
        font=("Segoe UI", 9),
    )
    style.configure(
        "Treeview.Heading",
        background=BG_CARD,
        foreground=ACCENT,
        font=("Segoe UI", 9, "bold"),
        borderwidth=0,
    )
    style.map(
        "Treeview",
        background=[("selected", ACCENT_DIM)],
        foreground=[("selected", "white")],
    )
    style.configure(
        "Horizontal.TScale",
        background=BG_CARD,
        troughcolor=BG_SURFACE,
        borderwidth=0,
    )
