"""Atalho para abrir a interface grafica da jornada.

Este arquivo existe para manter a importacao da GUI simples no restante do
projeto.
"""

from avatar_path.ui.gui import JourneyGUI, launch_gui


__all__ = ["JourneyGUI", "launch_gui"]
