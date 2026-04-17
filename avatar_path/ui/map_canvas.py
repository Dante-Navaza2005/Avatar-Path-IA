"""Desenho do mapa e do marcador animado na interface grafica.

Este modulo cuida apenas da traducao visual do mapa, sem misturar logica de
planejamento com detalhes de pintura na tela.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QImage, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsScene, QGraphicsView

from avatar_path.domain import AnimationFrame, Coordinate, JourneyResult
from avatar_path.ui.theme import (
    BG_CARD,
    CHECKPOINT_COLOR,
    MAP_BACKGROUND,
    MARKER_COLOR,
    PATH_COLOR,
    TERRAIN_COLORS,
)


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


def build_path_points(
    frames: tuple[AnimationFrame, ...],
    frame_index: int,
    cell_size: int,
    padding: int,
) -> list[tuple[float, float]]:
    """Converte o caminho percorrido ate um frame na lista de pontos da linha."""

    return [
        coord_center(frame.coordinate, cell_size, padding)
        for frame in frames[: frame_index + 1]
    ]


class MapWidget(QGraphicsView):
    """Exibe o mapa com terrenos, checkpoints, caminho e marcador animado."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setBackgroundBrush(QBrush(QColor(MAP_BACKGROUND)))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        self._path_item: QGraphicsPathItem | None = None
        self._marker_item: QGraphicsEllipseItem | None = None
        self._cell_size = 5
        self._padding = 18

    def draw_static_map(
        self,
        result: JourneyResult,
        frames: tuple[AnimationFrame, ...],
        cell_size: int,
        padding: int,
    ) -> None:
        """Desenha a versao estatica do mapa antes da animacao comecar.

        Esta etapa pinta os terrenos uma unica vez e deixa separados os itens
        dinamicos que serao atualizados durante a animacao.
        """

        self._cell_size = cell_size
        self._padding = padding
        map_data = result.map_data

        img = QImage(map_data.width, map_data.height, QImage.Format.Format_RGB32)
        terrain_colors = TERRAIN_COLORS.copy()
        for symbol in result.config.checkpoint_order:
            terrain_colors.setdefault(symbol, CHECKPOINT_COLOR)

        for row, line in enumerate(map_data.grid):
            for col, symbol in enumerate(line):
                color = QColor(terrain_colors.get(symbol, BG_CARD))
                img.setPixelColor(col, row, color)

        scaled = img.scaled(
            map_data.width * cell_size,
            map_data.height * cell_size,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        pixmap_item = self._scene.addPixmap(QPixmap.fromImage(scaled))
        pixmap_item.setPos(padding, padding)

        for checkpoint, coord in map_data.checkpoints.items():
            x1, y1, x2, y2 = coord_bounds(coord, cell_size, padding)
            inset = max(1, cell_size // 3)
            ellipse = self._scene.addEllipse(
                x1 + inset,
                y1 + inset,
                (x2 - x1) - 2 * inset,
                (y2 - y1) - 2 * inset,
                QPen(QColor("#a03020"), 1),
                QBrush(QColor(CHECKPOINT_COLOR)),
            )
            ellipse.setZValue(1)

            text_item = self._scene.addText(checkpoint, QFont("Segoe UI", 7, QFont.Weight.Bold))
            text_item.setDefaultTextColor(QColor("white"))
            text_item.setPos(
                (x1 + x2) / 2 - text_item.boundingRect().width() / 2,
                (y1 + y2) / 2 - text_item.boundingRect().height() / 2,
            )
            text_item.setZValue(2)

        start_x, start_y = coord_center(frames[0].coordinate, cell_size, padding)
        path = QPainterPath()
        path.moveTo(start_x, start_y)
        pen = QPen(QColor(PATH_COLOR), max(2, cell_size - 1))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self._path_item = self._scene.addPath(path, pen)
        self._path_item.setZValue(3)

        marker_radius = max(5, cell_size + 2)
        self._marker_item = self._scene.addEllipse(
            -marker_radius,
            -marker_radius,
            marker_radius * 2,
            marker_radius * 2,
            QPen(QColor("white"), 2),
            QBrush(QColor(MARKER_COLOR)),
        )
        self._marker_item.setZValue(4)
        self._marker_item.setPos(start_x, start_y)

        width = map_data.width * cell_size + padding * 2
        height = map_data.height * cell_size + padding * 2
        self._scene.setSceneRect(0, 0, width, height)

    def update_path(self, points: list[tuple[float, float]]) -> None:
        """Atualiza a linha do caminho percorrido no mapa."""

        if self._path_item is None or len(points) < 2:
            return
        path = QPainterPath()
        path.moveTo(points[0][0], points[0][1])
        for x, y in points[1:]:
            path.lineTo(x, y)
        self._path_item.setPath(path)

    def update_marker(self, coord: Coordinate) -> None:
        """Move o marcador para a posicao atual do agente."""

        if self._marker_item is None:
            return
        cx, cy = coord_center(coord, self._cell_size, self._padding)
        self._marker_item.setPos(cx, cy)

    def center_on_coord(self, coord: Coordinate) -> None:
        """Centraliza a visualizacao na coordenada indicada."""

        cx, cy = coord_center(coord, self._cell_size, self._padding)
        self.centerOn(cx, cy)
