"""Interface grafica para visualizar a jornada resolvida pelo programa."""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from avatar_path.domain import JourneyResult
from avatar_path.formatting import format_cost
from avatar_path.ui.animation import build_animation_frames
from avatar_path.ui.map_canvas import MapWidget, build_path_points, coord_center
from avatar_path.ui.presenters import (
    build_segment_index,
    energy_text,
    progress_text,
    segment_row_values,
    status_text,
    team_text,
)
from avatar_path.ui.theme import (
    ACCENT,
    BG_CARD,
    BORDER_COLOR,
    CHECKPOINT_COLOR,
    TEXT_SECONDARY,
    TERRAIN_COLORS,
    TERRAIN_LABELS,
    TERRAIN_LEGEND_ORDER,
    build_stylesheet,
)


class JourneyGUI(QMainWindow):
    """Mostra, em uma janela, o mapa, os custos e a execucao da jornada."""

    def __init__(self, result: JourneyResult) -> None:
        """Prepara os widgets que exibem a solucao do trabalho em tempo real."""

        super().__init__()
        self.result = result
        self.frames = build_animation_frames(result, step_stride=1)
        self.segment_last_frame_index = build_segment_index(self.frames)
        self.cell_size = 5
        self.padding = 18
        self.playing = False
        self.current_frame_index = 0
        self.current_path_points: list[tuple[float, float]] = []
        self._selected_segment_index: int | None = None

        self.setWindowTitle("Avatar Path")
        self.resize(1540, 920)
        self.setMinimumSize(1320, 760)
        self.setStyleSheet(build_stylesheet())

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._schedule_next)
        self.speed_value = 18

        self._build_layout()
        self.map_widget.draw_static_map(self.result, self.frames, self.cell_size, self.padding)
        self._populate_segments()
        self._update_frame(0, recenter=True)

    def _build_layout(self) -> None:
        """Organiza os grandes blocos da interface: cabecalho, mapa e painel lateral."""

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        self._build_header(main_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        map_container = QWidget()
        map_layout = QVBoxLayout(map_container)
        map_layout.setContentsMargins(0, 0, 0, 0)
        map_layout.setSpacing(8)

        self.map_widget = MapWidget()
        map_layout.addWidget(self.map_widget, 1)
        map_layout.addWidget(self._build_legend())

        splitter.addWidget(map_container)

        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(10)

        self._build_cost_cards(side_layout)
        self._build_controls(side_layout)
        self._build_details(side_layout)
        self._build_segments_table(side_layout)

        splitter.addWidget(side)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter, 1)

    def _build_header(self, layout: QVBoxLayout) -> None:
        """Cria o cabecalho que resume as tecnicas usadas no trabalho."""

        title = QLabel("Avatar Path")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(title)

        subtitle = QLabel(
            "A* no mapa  \u00b7  Algoritmo Genetico + Hill Climbing"
            " + Simulated Annealing nas equipes"
        )
        subtitle.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY}; margin-bottom: 2px;")
        layout.addWidget(subtitle)

    def _build_legend(self) -> QWidget:
        """Monta a legenda dos terrenos e checkpoints abaixo do mapa."""

        legend = QWidget()
        row = QHBoxLayout(legend)
        row.setContentsMargins(0, 4, 0, 0)
        row.setSpacing(12)

        for symbol in TERRAIN_LEGEND_ORDER:
            self._add_legend_item(row, TERRAIN_LABELS[symbol], TERRAIN_COLORS[symbol])
        self._add_legend_item(row, "Checkpoint", CHECKPOINT_COLOR)
        row.addStretch()
        return legend

    def _add_legend_item(self, layout: QHBoxLayout, label: str, color: str) -> None:
        """Desenha um item da legenda dos terrenos e checkpoints."""

        swatch = QLabel()
        px = QPixmap(16, 12)
        px.fill(QColor(color))
        swatch.setPixmap(px)
        layout.addWidget(swatch)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        layout.addWidget(lbl)

    def _build_controls(self, layout: QVBoxLayout) -> None:
        """Cria os botoes que controlam a animacao da solucao."""

        group = QGroupBox("Controles")
        gl = QVBoxLayout(group)
        gl.setSpacing(6)

        btn_row1 = QHBoxLayout()
        play_btn = QPushButton("Reproduzir")
        play_btn.setStyleSheet(
            f"background-color: {ACCENT}; color: white;"
            " font-weight: 600; border: none; border-radius: 4px; padding: 6px 14px;"
        )
        play_btn.clicked.connect(self._play)
        btn_row1.addWidget(play_btn)

        pause_btn = QPushButton("Pausar")
        pause_btn.clicked.connect(self._pause)
        btn_row1.addWidget(pause_btn)
        gl.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        step_btn = QPushButton("Avancar")
        step_btn.clicked.connect(self._step_once)
        btn_row2.addWidget(step_btn)

        reset_btn = QPushButton("Reiniciar")
        reset_btn.clicked.connect(self._reset)
        btn_row2.addWidget(reset_btn)
        gl.addLayout(btn_row2)

        layout.addWidget(group)

    def _build_cost_cards(self, layout: QVBoxLayout) -> None:
        """Cria os cartoes grandes com os tres custos principais no topo."""

        cards_row = QHBoxLayout()
        cards_row.setSpacing(8)

        self.total_card = self._make_cost_card("Total", "0.00")
        self.astar_card = self._make_cost_card("A*", "0.00")
        self.comb_card = self._make_cost_card("Comb.", "0.00")

        cards_row.addWidget(self.total_card[0])
        cards_row.addWidget(self.astar_card[0])
        cards_row.addWidget(self.comb_card[0])

        layout.addLayout(cards_row)

    def _make_cost_card(
        self, title: str, initial: str,
    ) -> tuple[QWidget, QLabel, QLabel]:
        """Cria um cartao individual com titulo e valor grande."""

        card = QWidget()
        card.setStyleSheet(
            f"background-color: {BG_CARD}; border: 1px solid {BORDER_COLOR};"
            " border-radius: 6px;"
        )
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(2)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {TEXT_SECONDARY};"
            " border: none;"
        )
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(title_lbl)

        value_lbl = QLabel(initial)
        value_lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {ACCENT};"
            " border: none;"
        )
        value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(value_lbl)

        return card, title_lbl, value_lbl

    def _build_details(self, layout: QVBoxLayout) -> None:
        """Cria o painel com detalhes da etapa atual."""

        group = QGroupBox("Detalhes")
        gl = QVBoxLayout(group)
        gl.setSpacing(6)

        self.status_label = self._add_info_row(gl, "Status")
        self.position_label = self._add_info_row(gl, "Posicao")
        self.progress_label = self._add_info_row(gl, "Progresso")
        self.nodes_label = self._add_info_row(gl, "Nos expandidos")
        self.segment_label = self._add_info_row(gl, "Trecho")
        self.team_label = self._add_info_row(gl, "Equipe")
        self.energy_label = self._add_info_row(gl, "Energia")

        layout.addWidget(group)

    def _add_info_row(self, layout: QVBoxLayout, label: str) -> QLabel:
        """Adiciona uma linha padrao de rotulo e valor ao painel lateral."""

        row = QHBoxLayout()
        row.setSpacing(12)
        row.setContentsMargins(0, 2, 0, 2)

        name = QLabel(f"{label}:")
        name.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
        name.setFixedWidth(110)
        row.addWidget(name)

        value = QLabel("")
        value.setStyleSheet("font-size: 12px;")
        value.setWordWrap(True)
        row.addWidget(value, 1)

        layout.addLayout(row)
        return value

    def _build_segments_table(self, layout: QVBoxLayout) -> None:
        """Cria a tabela com todos os trechos planejados da jornada."""

        group = QGroupBox("Trechos Planejados")
        gl = QVBoxLayout(group)

        self.segment_table = QTableWidget()
        self.segment_table.setColumnCount(4)
        self.segment_table.setHorizontalHeaderLabels(["Trecho", "A*", "Comb.", "Equipe"])
        self.segment_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.segment_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.segment_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.segment_table.verticalHeader().setVisible(False)
        self.segment_table.horizontalHeader().setStretchLastSection(True)
        self.segment_table.cellClicked.connect(self._on_segment_clicked)

        header = self.segment_table.horizontalHeader()
        header.resizeSection(0, 78)
        header.resizeSection(1, 108)
        header.resizeSection(2, 108)

        gl.addWidget(self.segment_table)
        layout.addWidget(group, 1)

    def _populate_segments(self) -> None:
        """Preenche a tabela com o resumo de cada trecho da jornada."""

        self.segment_table.setRowCount(len(self.result.segments))
        for index, segment in enumerate(self.result.segments):
            values = segment_row_values(segment)
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                if col < 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.segment_table.setItem(index, col, item)

    def _update_frame(self, frame_index: int, recenter: bool = False) -> None:
        """Atualiza mapa, marcador e painel lateral para um frame especifico."""

        previous_frame_index = self.current_frame_index
        frame = self.frames[frame_index]
        segment = self.result.segments[min(frame.segment_index, len(self.result.segments) - 1)]

        if frame_index == 0:
            self.current_path_points = build_path_points(
                self.frames, frame_index, self.cell_size, self.padding,
            )
        elif frame_index == previous_frame_index + 1 and self.current_path_points:
            self.current_path_points.append(
                coord_center(frame.coordinate, self.cell_size, self.padding)
            )
        else:
            self.current_path_points = build_path_points(
                self.frames, frame_index, self.cell_size, self.padding,
            )

        self.current_frame_index = frame_index
        self.map_widget.update_path(self.current_path_points)
        self.map_widget.update_marker(frame.coordinate)

        self.total_card[2].setText(format_cost(frame.total_cost))
        self.astar_card[2].setText(format_cost(frame.movement_cost))
        self.comb_card[2].setText(format_cost(frame.stage_cost))

        self.position_label.setText(f"linha {frame.coordinate[0]}, coluna {frame.coordinate[1]}")
        self.progress_label.setText(progress_text(frame_index, self.frames))
        self.segment_label.setText(f"{segment.start_symbol} -> {segment.end_symbol}")
        self.team_label.setText(team_text(segment, frame))
        self.nodes_label.setText(str(segment.nodes_expanded))
        self.energy_label.setText(energy_text(self.result, frame))
        self.status_label.setText(status_text(self.playing, frame_index, len(self.frames)))

        self._select_segment(frame.segment_index)
        if recenter or self.playing:
            self.map_widget.center_on_coord(frame.coordinate)

    def _select_segment(self, segment_index: int) -> None:
        """Mantem selecionada a linha da tabela ligada ao frame atual."""

        if segment_index >= self.segment_table.rowCount():
            return
        if self._selected_segment_index == segment_index:
            item = self.segment_table.item(segment_index, 0)
            if item is not None:
                self.segment_table.scrollToItem(item)
            return

        self._selected_segment_index = segment_index
        self.segment_table.selectRow(segment_index)
        item = self.segment_table.item(segment_index, 0)
        if item is not None:
            self.segment_table.scrollToItem(item)

    def _schedule_next(self) -> None:
        """Agenda o proximo frame enquanto a animacao estiver em execucao."""

        if not self.playing:
            self._timer.stop()
            return
        if self.current_frame_index >= len(self.frames) - 1:
            self.playing = False
            self._timer.stop()
            self.status_label.setText("Jornada concluida.")
            return

        self._update_frame(self.current_frame_index + 1)

    def _play(self) -> None:
        """Inicia ou retoma a animacao da jornada."""

        if self.playing:
            return
        self.playing = True
        self.status_label.setText("Animacao em execucao.")
        self._timer.start(max(5, self.speed_value))

    def _pause(self) -> None:
        """Interrompe temporariamente a animacao da jornada."""

        self.playing = False
        self._timer.stop()
        if self.current_frame_index < len(self.frames) - 1:
            self.status_label.setText("Animacao pausada.")

    def _reset(self) -> None:
        """Volta a exibicao para o primeiro frame da jornada."""

        self._pause()
        self._update_frame(0, recenter=True)

    def _step_once(self) -> None:
        """Avanca a visualizacao para o fim do trecho atual ou para o proximo trecho."""

        self._pause()
        current_segment_index = self.frames[self.current_frame_index].segment_index
        target_index = self.segment_last_frame_index.get(
            current_segment_index, self.current_frame_index,
        )
        if target_index <= self.current_frame_index:
            target_index = self.segment_last_frame_index.get(
                current_segment_index + 1, len(self.frames) - 1,
            )
        if target_index > self.current_frame_index:
            self._update_frame(target_index, recenter=True)

    def _on_segment_clicked(self, row: int, _column: int) -> None:
        """Permite saltar para um trecho especifico ao clicar na tabela."""

        self._pause()
        frame_index = self.segment_last_frame_index.get(row)
        if frame_index is not None:
            self._update_frame(frame_index, recenter=True)


def launch_gui(result: JourneyResult) -> None:
    """Abre a interface grafica que apresenta a solucao do trabalho."""

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    window = JourneyGUI(result)
    window.show()
    app.exec()
