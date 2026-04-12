"""Interface grafica para visualizar a jornada resolvida pelo programa."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from avatar_path.domain import JourneyResult
from avatar_path.formatting import format_cost
from avatar_path.ui.animation import build_animation_frames
from avatar_path.ui.map_canvas import (
    MapCanvasState,
    build_path_points,
    center_on_coordinate,
    coord_center,
    draw_static_map,
    update_marker_position,
)
from avatar_path.ui.presenters import (
    build_segment_index,
    energy_text,
    progress_text,
    segment_row_values,
    status_text,
    team_text,
)
from avatar_path.ui.theme import (
    BG,
    BG_CARD,
    CHECKPOINT_COLOR,
    MAP_BACKGROUND,
    SEPARATOR_COLOR,
    TERRAIN_COLORS,
    TERRAIN_LABELS,
    TERRAIN_LEGEND_ORDER,
    configure_style,
)


class JourneyGUI(tk.Tk):
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
        self.after_handle: str | None = None
        self.current_frame_index = 0
        self.current_path_points: list[float] = []
        self._selected_segment_index: int | None = None
        self.map_state: MapCanvasState | None = None

        self.title("Avatar Path IA")
        self.geometry("1540x920")
        self.minsize(1320, 760)
        self.configure(bg=BG)

        self.speed_var = tk.IntVar(value=18)
        self.status_var = tk.StringVar(value="Pronto para reproduzir a jornada.")
        self.position_var = tk.StringVar()
        self.progress_var = tk.StringVar()
        self.movement_var = tk.StringVar()
        self.stage_var = tk.StringVar()
        self.total_var = tk.StringVar()
        self.segment_var = tk.StringVar()
        self.team_var = tk.StringVar()
        self.energy_var = tk.StringVar()
        self.nodes_var = tk.StringVar()

        configure_style(self)
        self._build_layout()
        self._draw_map()
        self._populate_segments()
        self._update_frame(0, recenter=True)

    def _build_layout(self) -> None:
        """Organiza os grandes blocos da interface: cabecalho, mapa e painel lateral."""

        root = ttk.Frame(self, style="App.TFrame", padding=16)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=4)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(1, weight=1)

        self._build_header(root)
        self._build_map_panel(root)
        self._build_side_panel(root)

    def _build_header(self, parent: ttk.Frame) -> None:
        """Cria o cabecalho que resume as tecnicas usadas no trabalho."""

        header = ttk.Frame(parent, style="App.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Avatar Path IA", style="Header.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="A* no mapa  |  Algoritmo Genetico + Hill Climbing + Simulated Annealing nas equipes",
            style="Subheader.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

    def _build_map_panel(self, parent: ttk.Frame) -> None:
        """Monta a area do mapa com scroll e legenda dos terrenos."""

        map_card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        map_card.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        map_card.columnconfigure(0, weight=1)
        map_card.rowconfigure(1, weight=1)

        ttk.Label(map_card, text="Mapa da Jornada", style="MapTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        canvas_frame = ttk.Frame(map_card, style="Card.TFrame")
        canvas_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            canvas_frame,
            bg=MAP_BACKGROUND,
            highlightthickness=0,
            width=1020,
            height=650,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)

        legend = ttk.Frame(map_card, style="Card.TFrame")
        legend.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        for index, symbol in enumerate(TERRAIN_LEGEND_ORDER):
            self._add_legend_item(legend, index, TERRAIN_LABELS[symbol], TERRAIN_COLORS[symbol])
        self._add_legend_item(legend, len(TERRAIN_LEGEND_ORDER), "Checkpoint", CHECKPOINT_COLOR)
        legend.columnconfigure(len(TERRAIN_LEGEND_ORDER) * 2 + 2, weight=1)

    def _build_side_panel(self, parent: ttk.Frame) -> None:
        """Monta os controles e resumos exibidos ao lado do mapa."""

        side_panel = ttk.Frame(parent, style="App.TFrame")
        side_panel.grid(row=1, column=1, sticky="nsew")
        side_panel.columnconfigure(0, weight=1)
        side_panel.rowconfigure(2, weight=1)

        self._build_controls(side_panel)
        self._build_summary(side_panel)
        self._build_segments_table(side_panel)

    def _build_controls(self, parent: ttk.Frame) -> None:
        """Cria os botoes que controlam a animacao da solucao."""

        controls = ttk.LabelFrame(parent, text="Controles", style="Panel.TLabelframe", padding=10)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)

        ttk.Button(controls, text="Reproduzir", command=self._play, style="Accent.TButton").grid(
            row=0, column=0, sticky="ew", padx=(0, 4), pady=(0, 6)
        )
        ttk.Button(controls, text="Pausar", command=self._pause, style="Secondary.TButton").grid(
            row=0, column=1, sticky="ew", padx=(4, 0), pady=(0, 6)
        )
        ttk.Button(controls, text="Avancar", command=self._step_once, style="Secondary.TButton").grid(
            row=1, column=0, sticky="ew", padx=(0, 4)
        )
        ttk.Button(controls, text="Reiniciar", command=self._reset, style="Secondary.TButton").grid(
            row=1, column=1, sticky="ew", padx=(4, 0)
        )

        ttk.Label(controls, text="Velocidade (ms)", style="Body.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(10, 4)
        )
        ttk.Scale(
            controls,
            from_=5,
            to=120,
            orient="horizontal",
            variable=self.speed_var,
        ).grid(row=3, column=0, columnspan=2, sticky="ew")

    def _build_summary(self, parent: ttk.Frame) -> None:
        """Cria o painel textual com custos, equipe e energia da etapa atual."""

        summary = ttk.LabelFrame(parent, text="Estado Atual", style="Panel.TLabelframe", padding=10)
        summary.grid(row=1, column=0, sticky="ew", pady=(10, 10))
        summary.columnconfigure(1, weight=1)

        row_idx = 0
        row_idx = self._add_info_row(summary, row_idx, "Status", self.status_var)
        row_idx = self._add_info_row(summary, row_idx, "Posicao", self.position_var)
        row_idx = self._add_info_row(summary, row_idx, "Progresso", self.progress_var)

        self._add_section_separator(summary, row_idx, "Custo A* (pathfinding)")
        row_idx += 1
        row_idx = self._add_info_row(summary, row_idx, "Custo A*", self.movement_var)
        row_idx = self._add_info_row(summary, row_idx, "Nos expandidos", self.nodes_var)

        self._add_section_separator(summary, row_idx, "Custo Combinatorio (equipes)")
        row_idx += 1
        row_idx = self._add_info_row(summary, row_idx, "Trecho", self.segment_var)
        row_idx = self._add_info_row(summary, row_idx, "Equipe", self.team_var)
        row_idx = self._add_info_row(summary, row_idx, "Custo comb.", self.stage_var)
        row_idx = self._add_info_row(summary, row_idx, "Energia", self.energy_var)

        self._add_section_separator(summary, row_idx, "Total (A* + Combinatorio)")
        row_idx += 1
        self._add_info_row(summary, row_idx, "Custo total", self.total_var)

    def _build_segments_table(self, parent: ttk.Frame) -> None:
        """Cria a tabela com todos os trechos planejados da jornada."""

        segments_frame = ttk.LabelFrame(
            parent, text="Trechos Planejados", style="Panel.TLabelframe", padding=8
        )
        segments_frame.grid(row=2, column=0, sticky="nsew")
        segments_frame.columnconfigure(0, weight=1)
        segments_frame.rowconfigure(0, weight=1)

        self.segment_tree = ttk.Treeview(
            segments_frame,
            columns=("trecho", "movimento", "etapa", "equipe"),
            show="headings",
            height=14,
        )
        self.segment_tree.grid(row=0, column=0, sticky="nsew")
        self.segment_tree.heading("trecho", text="Trecho")
        self.segment_tree.heading("movimento", text="A*")
        self.segment_tree.heading("etapa", text="Comb.")
        self.segment_tree.heading("equipe", text="Equipe")
        self.segment_tree.column("trecho", width=78, anchor="center")
        self.segment_tree.column("movimento", width=108, anchor="center")
        self.segment_tree.column("etapa", width=108, anchor="center")
        self.segment_tree.column("equipe", width=180, anchor="w")
        self.segment_tree.bind("<ButtonRelease-1>", self._on_segment_clicked)

        tree_scroll = ttk.Scrollbar(segments_frame, orient="vertical", command=self.segment_tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.segment_tree.configure(yscrollcommand=tree_scroll.set)

    def _add_section_separator(self, parent: ttk.Frame, row: int, title: str) -> None:
        """Insere um subtitulo visual entre grupos de informacao."""

        sep_frame = ttk.Frame(parent, style="Card.TFrame")
        sep_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        ttk.Label(sep_frame, text=title, style="SectionTitle.TLabel").pack(anchor="w")
        tk.Frame(sep_frame, height=1, bg=SEPARATOR_COLOR).pack(fill="x", pady=(2, 0))

    def _add_info_row(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar) -> int:
        """Adiciona uma linha padrao de rotulo e valor ao painel lateral."""

        ttk.Label(parent, text=f"{label}:", style="Body.TLabel").grid(
            row=row, column=0, sticky="nw", padx=(0, 8), pady=2
        )
        ttk.Label(parent, textvariable=variable, style="Value.TLabel", wraplength=340, justify="left").grid(
            row=row, column=1, sticky="w", pady=2
        )
        return row + 1

    def _add_legend_item(self, parent: ttk.Frame, column: int, label: str, color: str) -> None:
        """Desenha um item da legenda dos terrenos e checkpoints."""

        swatch = tk.Canvas(parent, width=22, height=16, bg=BG_CARD, highlightthickness=0)
        swatch.grid(row=0, column=column * 2, padx=(0, 3))
        swatch.create_rectangle(2, 2, 20, 14, fill=color, outline=color, width=0)
        ttk.Label(parent, text=label, style="Legend.TLabel").grid(
            row=0, column=column * 2 + 1, padx=(0, 14)
        )

    def _draw_map(self) -> None:
        """Desenha a versao estatica do mapa antes da animacao comecar."""

        self.map_state = draw_static_map(
            canvas=self.canvas,
            result=self.result,
            frames=self.frames,
            cell_size=self.cell_size,
            padding=self.padding,
        )

    def _populate_segments(self) -> None:
        """Preenche a tabela com o resumo de cada trecho da jornada."""

        for index, segment in enumerate(self.result.segments):
            self.segment_tree.insert(
                "",
                "end",
                iid=f"segment-{index}",
                values=segment_row_values(segment),
            )

    def _update_frame(self, frame_index: int, recenter: bool = False) -> None:
        """Atualiza mapa, marcador e painel lateral para um frame especifico."""

        if self.map_state is None:
            return

        previous_frame_index = self.current_frame_index
        frame = self.frames[frame_index]
        segment = self.result.segments[min(frame.segment_index, len(self.result.segments) - 1)]

        if frame_index == 0:
            self.current_path_points = build_path_points(
                self.frames,
                frame_index,
                self.cell_size,
                self.padding,
            )
        elif frame_index == previous_frame_index + 1 and self.current_path_points:
            center_x, center_y = coord_center(frame.coordinate, self.cell_size, self.padding)
            self.current_path_points.extend((center_x, center_y))
        else:
            self.current_path_points = build_path_points(
                self.frames,
                frame_index,
                self.cell_size,
                self.padding,
            )

        self.current_frame_index = frame_index
        self.canvas.coords(self.map_state.path_line_id, *self.current_path_points)
        update_marker_position(
            self.canvas,
            self.map_state.marker_id,
            frame.coordinate,
            self.cell_size,
            self.padding,
        )

        self.position_var.set(f"linha {frame.coordinate[0]}, coluna {frame.coordinate[1]}")
        self.progress_var.set(progress_text(frame_index, self.frames))
        self.movement_var.set(format_cost(frame.movement_cost))
        self.stage_var.set(format_cost(frame.stage_cost))
        self.total_var.set(format_cost(frame.total_cost))
        self.segment_var.set(f"{segment.start_symbol} -> {segment.end_symbol}")
        self.team_var.set(team_text(segment, frame))
        self.nodes_var.set(str(segment.nodes_expanded))
        self.energy_var.set(energy_text(self.result, frame))
        self.status_var.set(status_text(self.playing, frame_index, len(self.frames)))

        self._select_segment(frame.segment_index)
        if recenter or self.playing:
            center_on_coordinate(
                self.canvas,
                frame.coordinate,
                self.cell_size,
                self.padding,
            )

    def _select_segment(self, segment_index: int) -> None:
        """Mantem selecionada a linha da tabela ligada ao frame atual."""

        item_id = f"segment-{segment_index}"
        if not self.segment_tree.exists(item_id):
            return
        if self._selected_segment_index == segment_index:
            self.segment_tree.see(item_id)
            return

        self._selected_segment_index = segment_index
        self.segment_tree.selection_set(item_id)
        self.segment_tree.see(item_id)

    def _schedule_next(self) -> None:
        """Agenda o proximo frame enquanto a animacao estiver em execucao."""

        if not self.playing:
            return
        if self.current_frame_index >= len(self.frames) - 1:
            self.playing = False
            self.status_var.set("Jornada concluida.")
            return

        self._update_frame(self.current_frame_index + 1)
        self.after_handle = self.after(max(5, self.speed_var.get()), self._schedule_next)

    def _play(self) -> None:
        """Inicia ou retoma a animacao da jornada."""

        if self.playing:
            return
        self.playing = True
        self.status_var.set("Animacao em execucao.")
        self._schedule_next()

    def _pause(self) -> None:
        """Interrompe temporariamente a animacao da jornada."""

        self.playing = False
        if self.after_handle is not None:
            self.after_cancel(self.after_handle)
            self.after_handle = None
        if self.current_frame_index < len(self.frames) - 1:
            self.status_var.set("Animacao pausada.")

    def _reset(self) -> None:
        """Volta a exibicao para o primeiro frame da jornada."""

        self._pause()
        self._update_frame(0, recenter=True)

    def _step_once(self) -> None:
        """Avanca a visualizacao para o fim do trecho atual ou para o proximo trecho."""

        self._pause()
        current_segment_index = self.frames[self.current_frame_index].segment_index
        target_index = self.segment_last_frame_index.get(current_segment_index, self.current_frame_index)
        if target_index <= self.current_frame_index:
            target_index = self.segment_last_frame_index.get(current_segment_index + 1, len(self.frames) - 1)
        if target_index > self.current_frame_index:
            self._update_frame(target_index, recenter=True)

    def _on_segment_clicked(self, event: tk.Event) -> None:
        """Permite saltar para um trecho especifico ao clicar na tabela."""

        item_id = self.segment_tree.identify_row(event.y)
        if not item_id or not item_id.startswith("segment-"):
            return

        self._pause()
        segment_index = int(item_id.split("-")[1])
        frame_index = self.segment_last_frame_index.get(segment_index)
        if frame_index is not None:
            self._update_frame(frame_index, recenter=True)


def launch_gui(result: JourneyResult) -> None:
    """Abre a interface grafica que apresenta a solucao do trabalho."""

    app = JourneyGUI(result)
    app.mainloop()
