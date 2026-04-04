from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from avatar_path.domain import AnimationFrame, Coordinate, JourneyResult, SegmentResult
from avatar_path.visualization import build_animation_frames


BG = "#1e1e2e"
BG_SURFACE = "#262637"
BG_CARD = "#2e2e42"
BG_CARD_HOVER = "#363650"
TEXT_PRIMARY = "#e0e0f0"
TEXT_SECONDARY = "#a0a0c0"
TEXT_MUTED = "#707090"
ACCENT = "#7c9ff5"
ACCENT_DIM = "#5a7ad4"
PATH_COLOR = "#f07070"
MARKER_COLOR = "#f5c842"
CHECKPOINT_COLOR = "#e06040"
SEPARATOR_COLOR = "#3a3a55"
BORDER_COLOR = "#3a3a55"

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
    "V": "Floresta",
    "A": "Agua",
    "M": "Montanha",
}


class JourneyGUI(tk.Tk):
    def __init__(self, result: JourneyResult) -> None:
        super().__init__()
        self.result = result
        self.frames = build_animation_frames(result, step_stride=1)
        self.cell_size = 5
        self.padding = 18
        self.playing = False
        self.after_handle: str | None = None
        self.current_frame_index = 0
        self.current_path_points: list[float] = []
        self._selected_segment_index: int | None = None
        self.segment_last_frame_index = self._build_segment_index()

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

        self._configure_style()
        self._build_layout()
        self._draw_map()
        self._populate_segments()
        self._update_frame(0, recenter=True)

    def _build_segment_index(self) -> dict[int, int]:
        last_index: dict[int, int] = {}
        for index, frame in enumerate(self.frames):
            last_index[frame.segment_index] = index
        return last_index

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background=BG)
        style.configure("Card.TFrame", background=BG_CARD)
        style.configure("Surface.TFrame", background=BG_SURFACE)
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

    def _build_layout(self) -> None:
        root = ttk.Frame(self, style="App.TFrame", padding=16)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=4)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(1, weight=1)

        header = ttk.Frame(root, style="App.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Avatar Path IA", style="Header.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Busca heuristica no mapa  |  Alocacao otima das equipes por etapa",
            style="Subheader.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        map_card = ttk.Frame(root, style="Card.TFrame", padding=12)
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
            bg="#1a1a2a",
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
        col = 0
        for symbol in (".", "R", "V", "A", "M"):
            self._add_legend_item(legend, col, TERRAIN_LABELS[symbol], TERRAIN_COLORS[symbol])
            col += 1
        self._add_legend_item(legend, col, "Checkpoint", CHECKPOINT_COLOR)
        legend.columnconfigure(col * 2 + 2, weight=1)

        side_panel = ttk.Frame(root, style="App.TFrame")
        side_panel.grid(row=1, column=1, sticky="nsew")
        side_panel.columnconfigure(0, weight=1)
        side_panel.rowconfigure(2, weight=1)

        controls = ttk.LabelFrame(side_panel, text="Controles", style="Panel.TLabelframe", padding=10)
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

        summary = ttk.LabelFrame(side_panel, text="Estado Atual", style="Panel.TLabelframe", padding=10)
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
        row_idx = self._add_info_row(summary, row_idx, "Custo total", self.total_var)

        segments_frame = ttk.LabelFrame(
            side_panel, text="Trechos Planejados", style="Panel.TLabelframe", padding=8
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
        self.segment_tree.column("movimento", width=60, anchor="center")
        self.segment_tree.column("etapa", width=70, anchor="center")
        self.segment_tree.column("equipe", width=220, anchor="w")
        self.segment_tree.bind("<ButtonRelease-1>", self._on_segment_clicked)

        tree_scroll = ttk.Scrollbar(segments_frame, orient="vertical", command=self.segment_tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.segment_tree.configure(yscrollcommand=tree_scroll.set)

    def _add_section_separator(self, parent: ttk.Frame, row: int, title: str) -> None:
        sep_frame = ttk.Frame(parent, style="Card.TFrame")
        sep_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        ttk.Label(sep_frame, text=title, style="SectionTitle.TLabel").pack(anchor="w")
        tk.Frame(sep_frame, height=1, bg=SEPARATOR_COLOR).pack(fill="x", pady=(2, 0))

    def _add_info_row(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar) -> int:
        ttk.Label(parent, text=f"{label}:", style="Body.TLabel").grid(
            row=row, column=0, sticky="nw", padx=(0, 8), pady=2
        )
        ttk.Label(parent, textvariable=variable, style="Value.TLabel", wraplength=340, justify="left").grid(
            row=row, column=1, sticky="w", pady=2
        )
        return row + 1

    def _add_legend_item(self, parent: ttk.Frame, column: int, label: str, color: str) -> None:
        swatch = tk.Canvas(parent, width=22, height=16, bg=BG_CARD, highlightthickness=0)
        swatch.grid(row=0, column=column * 2, padx=(0, 3))
        swatch.create_rectangle(2, 2, 20, 14, fill=color, outline=color, width=0)
        ttk.Label(parent, text=label, style="Legend.TLabel").grid(
            row=0, column=column * 2 + 1, padx=(0, 14)
        )

    def _draw_map(self) -> None:
        map_data = self.result.map_data
        width = map_data.width * self.cell_size + self.padding * 2
        height = map_data.height * self.cell_size + self.padding * 2
        self.canvas.configure(scrollregion=(0, 0, width, height))

        self.canvas.create_rectangle(0, 0, width, height, fill="#1a1a2a", outline="")
        self.base_map_photo = tk.PhotoImage(width=map_data.width, height=map_data.height)

        terrain_colors = TERRAIN_COLORS.copy()
        for symbol in self.result.config.checkpoint_order:
            if symbol not in terrain_colors:
                terrain_colors[symbol] = CHECKPOINT_COLOR

        for row, line in enumerate(map_data.grid):
            row_colors = "{" + " ".join(terrain_colors.get(symbol, BG_CARD) for symbol in line) + "}"
            self.base_map_photo.put(row_colors, to=(0, row))

        self.scaled_map_photo = self.base_map_photo.zoom(self.cell_size, self.cell_size)
        self.canvas.create_image(
            self.padding,
            self.padding,
            image=self.scaled_map_photo,
            anchor="nw",
        )

        for checkpoint, coord in map_data.checkpoints.items():
            x1, y1, x2, y2 = self._coord_bounds(coord)
            inset = max(1, self.cell_size // 3)
            self.canvas.create_oval(
                x1 + inset,
                y1 + inset,
                x2 - inset,
                y2 - inset,
                fill=CHECKPOINT_COLOR,
                outline="#a03020",
                width=1,
            )
            self.canvas.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                text=checkpoint,
                fill="white",
                font=("Segoe UI", 7, "bold"),
            )

        start_coord = self.frames[0].coordinate
        start_x, start_y = self._coord_center(start_coord)
        self.path_line = self.canvas.create_line(
            start_x,
            start_y,
            start_x,
            start_y,
            fill=PATH_COLOR,
            width=max(2, self.cell_size - 1),
            capstyle=tk.ROUND,
            joinstyle=tk.ROUND,
        )
        self.current_marker = self.canvas.create_oval(0, 0, 0, 0, fill=MARKER_COLOR, outline="white", width=2)

    def _coord_bounds(self, coord: Coordinate) -> tuple[float, float, float, float]:
        row, col = coord
        x1 = self.padding + col * self.cell_size
        y1 = self.padding + row * self.cell_size
        x2 = x1 + self.cell_size
        y2 = y1 + self.cell_size
        return x1, y1, x2, y2

    def _coord_center(self, coord: Coordinate) -> tuple[float, float]:
        x1, y1, x2, y2 = self._coord_bounds(coord)
        return (x1 + x2) / 2, (y1 + y2) / 2

    def _populate_segments(self) -> None:
        for index, segment in enumerate(self.result.segments):
            assignment = segment.stage_assignment
            if assignment is None:
                stage_label = "-"
                team_label = "Chegada final"
            else:
                stage_label = f"{assignment.time_cost:.2f}"
                team_label = ", ".join(assignment.characters)
            self.segment_tree.insert(
                "",
                "end",
                iid=f"segment-{index}",
                values=(
                    f"{segment.start_symbol}->{segment.end_symbol}",
                    segment.movement_cost,
                    stage_label,
                    team_label,
                ),
            )

    def _frame_path_points(self, frame_index: int) -> list[float]:
        points: list[float] = []
        for frame in self.frames[: frame_index + 1]:
            x, y = self._coord_center(frame.coordinate)
            points.extend((x, y))
        if len(points) == 2:
            points.extend(points)
        return points

    def _update_frame(self, frame_index: int, recenter: bool = False) -> None:
        previous_frame_index = self.current_frame_index
        frame = self.frames[frame_index]
        segment = self.result.segments[min(frame.segment_index, len(self.result.segments) - 1)]

        if frame_index == 0:
            self.current_path_points = self._frame_path_points(frame_index)
        elif frame_index == previous_frame_index + 1 and self.current_path_points:
            center_x, center_y = self._coord_center(frame.coordinate)
            self.current_path_points.extend((center_x, center_y))
        else:
            self.current_path_points = self._frame_path_points(frame_index)

        self.current_frame_index = frame_index
        self.canvas.coords(self.path_line, *self.current_path_points)

        marker_radius = max(5, self.cell_size + 2)
        center_x, center_y = self._coord_center(frame.coordinate)
        self.canvas.coords(
            self.current_marker,
            center_x - marker_radius,
            center_y - marker_radius,
            center_x + marker_radius,
            center_y + marker_radius,
        )
        self.canvas.tag_raise(self.current_marker)

        self.position_var.set(f"linha {frame.coordinate[0]}, coluna {frame.coordinate[1]}")
        self.progress_var.set(
            f"frame {frame_index + 1}/{len(self.frames)}  |  passo {frame.segment_step_index}/{frame.segment_steps}"
        )
        self.movement_var.set(str(frame.movement_cost))
        self.stage_var.set(f"{frame.stage_cost:.4f}")
        self.total_var.set(f"{frame.total_cost:.4f}")
        self.segment_var.set(f"{segment.start_symbol} -> {segment.end_symbol}")
        self.team_var.set(self._team_text(segment, frame))
        self.nodes_var.set(str(segment.nodes_expanded))
        self.energy_var.set(self._energy_text())

        if self.playing:
            self.status_var.set("Animacao em execucao.")
        elif frame_index == 0:
            self.status_var.set("Pronto para reproduzir a jornada.")
        elif frame_index == len(self.frames) - 1:
            self.status_var.set("Jornada concluida.")
        else:
            self.status_var.set("Animacao pausada.")

        self._select_segment(frame.segment_index)
        if recenter or self.playing:
            self._center_on_coordinate(frame.coordinate)

    def _team_text(self, segment: SegmentResult, frame: AnimationFrame) -> str:
        if segment.stage_assignment is None:
            return "Fim da jornada"

        team = ", ".join(segment.stage_assignment.characters)
        if frame.stage_applied:
            return f"{team}  |  etapa concluida"
        return f"{team}  |  em deslocamento"

    def _energy_text(self) -> str:
        parts = []
        max_energy = {character.name: character.max_energy for character in self.result.config.characters}
        for name, usage in self.result.energy_usage.items():
            parts.append(f"{name} {usage}/{max_energy[name]}")
        return " | ".join(parts)

    def _center_on_coordinate(self, coord: Coordinate) -> None:
        self.update_idletasks()
        center_x, center_y = self._coord_center(coord)
        scroll_region = self.canvas.cget("scrollregion").split()
        if len(scroll_region) != 4:
            return

        _, _, max_x, max_y = (float(value) for value in scroll_region)
        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())

        x_fraction = max(0.0, min((center_x - canvas_width / 2) / max(1.0, max_x - canvas_width), 1.0))
        y_fraction = max(0.0, min((center_y - canvas_height / 2) / max(1.0, max_y - canvas_height), 1.0))
        self.canvas.xview_moveto(x_fraction)
        self.canvas.yview_moveto(y_fraction)

    def _select_segment(self, segment_index: int) -> None:
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
        if not self.playing:
            return
        if self.current_frame_index >= len(self.frames) - 1:
            self.playing = False
            self.status_var.set("Jornada concluida.")
            return

        self._update_frame(self.current_frame_index + 1)
        self.after_handle = self.after(max(5, self.speed_var.get()), self._schedule_next)

    def _play(self) -> None:
        if self.playing:
            return
        self.playing = True
        self.status_var.set("Animacao em execucao.")
        self._schedule_next()

    def _pause(self) -> None:
        self.playing = False
        if self.after_handle is not None:
            self.after_cancel(self.after_handle)
            self.after_handle = None
        if self.current_frame_index < len(self.frames) - 1:
            self.status_var.set("Animacao pausada.")

    def _reset(self) -> None:
        self._pause()
        self._update_frame(0, recenter=True)

    def _step_once(self) -> None:
        self._pause()
        current_segment_index = self.frames[self.current_frame_index].segment_index
        target_index = self.segment_last_frame_index.get(current_segment_index, self.current_frame_index)

        if target_index <= self.current_frame_index:
            target_index = self.segment_last_frame_index.get(current_segment_index + 1, len(self.frames) - 1)

        if target_index > self.current_frame_index:
            self._update_frame(target_index, recenter=True)

    def _on_segment_clicked(self, event: tk.Event) -> None:
        item_id = self.segment_tree.identify_row(event.y)
        if not item_id or not item_id.startswith("segment-"):
            return

        self._pause()
        segment_index = int(item_id.split("-")[1])
        frame_index = self.segment_last_frame_index.get(segment_index)
        if frame_index is None:
            return
        self._update_frame(frame_index, recenter=True)


def launch_gui(result: JourneyResult) -> None:
    app = JourneyGUI(result)
    app.mainloop()
