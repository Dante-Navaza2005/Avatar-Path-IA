"""Desenho do mapa e do marcador animado na interface grafica."""

from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk

from avatar_path.domain import AnimationFrame, Coordinate, JourneyResult
from avatar_path.ui.theme import (
    BG_CARD,
    CHECKPOINT_COLOR,
    MAP_BACKGROUND,
    MARKER_COLOR,
    PATH_COLOR,
    TERRAIN_COLORS,
)


@dataclass
class MapCanvasState:
    """Guarda os elementos do canvas que precisam ser atualizados ao longo da animacao."""

    base_map_photo: tk.PhotoImage
    scaled_map_photo: tk.PhotoImage
    path_line_id: int
    marker_id: int


def coord_bounds(
    coord: Coordinate,
    cell_size: int,
    padding: int,
) -> tuple[float, float, float, float]:
    """Converte uma coordenada da matriz no retangulo correspondente no canvas."""

    row, col = coord
    x1 = padding + col * cell_size
    y1 = padding + row * cell_size
    x2 = x1 + cell_size
    y2 = y1 + cell_size
    return x1, y1, x2, y2


def coord_center(coord: Coordinate, cell_size: int, padding: int) -> tuple[float, float]:
    """Retorna o centro visual de uma coordenada do mapa no canvas."""

    x1, y1, x2, y2 = coord_bounds(coord, cell_size, padding)
    return (x1 + x2) / 2, (y1 + y2) / 2


def draw_static_map(
    canvas: tk.Canvas,
    result: JourneyResult,
    frames: tuple[AnimationFrame, ...],
    cell_size: int,
    padding: int,
) -> MapCanvasState:
    """Desenha o mapa fixo do trabalho, com terrenos e checkpoints."""

    map_data = result.map_data
    width = map_data.width * cell_size + padding * 2
    height = map_data.height * cell_size + padding * 2
    canvas.configure(scrollregion=(0, 0, width, height))
    canvas.create_rectangle(0, 0, width, height, fill=MAP_BACKGROUND, outline="")

    base_map_photo = tk.PhotoImage(width=map_data.width, height=map_data.height)
    terrain_colors = TERRAIN_COLORS.copy()
    for symbol in result.config.checkpoint_order:
        terrain_colors.setdefault(symbol, CHECKPOINT_COLOR)

    for row, line in enumerate(map_data.grid):
        row_colors = "{" + " ".join(terrain_colors.get(symbol, BG_CARD) for symbol in line) + "}"
        base_map_photo.put(row_colors, to=(0, row))

    scaled_map_photo = base_map_photo.zoom(cell_size, cell_size)
    canvas.create_image(padding, padding, image=scaled_map_photo, anchor="nw")

    for checkpoint, coord in map_data.checkpoints.items():
        x1, y1, x2, y2 = coord_bounds(coord, cell_size, padding)
        inset = max(1, cell_size // 3)
        canvas.create_oval(
            x1 + inset,
            y1 + inset,
            x2 - inset,
            y2 - inset,
            fill=CHECKPOINT_COLOR,
            outline="#a03020",
            width=1,
        )
        canvas.create_text(
            (x1 + x2) / 2,
            (y1 + y2) / 2,
            text=checkpoint,
            fill="white",
            font=("Segoe UI", 7, "bold"),
        )

    start_x, start_y = coord_center(frames[0].coordinate, cell_size, padding)
    path_line_id = canvas.create_line(
        start_x,
        start_y,
        start_x,
        start_y,
        fill=PATH_COLOR,
        width=max(2, cell_size - 1),
        capstyle=tk.ROUND,
        joinstyle=tk.ROUND,
    )
    marker_id = canvas.create_oval(0, 0, 0, 0, fill=MARKER_COLOR, outline="white", width=2)

    return MapCanvasState(
        base_map_photo=base_map_photo,
        scaled_map_photo=scaled_map_photo,
        path_line_id=path_line_id,
        marker_id=marker_id,
    )


def build_path_points(
    frames: tuple[AnimationFrame, ...],
    frame_index: int,
    cell_size: int,
    padding: int,
) -> list[float]:
    """Converte o caminho percorrido ate um frame na lista de pontos da linha."""

    points: list[float] = []
    for frame in frames[: frame_index + 1]:
        x, y = coord_center(frame.coordinate, cell_size, padding)
        points.extend((x, y))

    if len(points) == 2:
        points.extend(points)
    return points


def update_marker_position(
    canvas: tk.Canvas,
    marker_id: int,
    coord: Coordinate,
    cell_size: int,
    padding: int,
) -> None:
    """Move o marcador amarelo para a posicao atual do agente."""

    marker_radius = max(5, cell_size + 2)
    center_x, center_y = coord_center(coord, cell_size, padding)
    canvas.coords(
        marker_id,
        center_x - marker_radius,
        center_y - marker_radius,
        center_x + marker_radius,
        center_y + marker_radius,
    )
    canvas.tag_raise(marker_id)


def center_on_coordinate(
    canvas: tk.Canvas,
    coord: Coordinate,
    cell_size: int,
    padding: int,
) -> None:
    """Centraliza o scroll da interface na coordenada atual da animacao."""

    canvas.update_idletasks()
    center_x, center_y = coord_center(coord, cell_size, padding)
    scroll_region = canvas.cget("scrollregion").split()
    if len(scroll_region) != 4:
        return

    _, _, max_x, max_y = (float(value) for value in scroll_region)
    canvas_width = max(1, canvas.winfo_width())
    canvas_height = max(1, canvas.winfo_height())
    x_fraction = max(0.0, min((center_x - canvas_width / 2) / max(1.0, max_x - canvas_width), 1.0))
    y_fraction = max(0.0, min((center_y - canvas_height / 2) / max(1.0, max_y - canvas_height), 1.0))
    canvas.xview_moveto(x_fraction)
    canvas.yview_moveto(y_fraction)
