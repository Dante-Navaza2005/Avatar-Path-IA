"""Estruturas de dados compartilhadas pela solucao do trabalho do Avatar."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


Coordinate = tuple[int, int]


@dataclass(frozen=True)
class CharacterConfig:
    """Guarda os dados de um personagem usados na etapa combinatoria do enunciado."""

    name: str
    agility: float
    max_energy: int


@dataclass(frozen=True)
class VisualizationConfig:
    """Reune os parametros da animacao exigida pelo trabalho."""

    delay_seconds: float
    viewport_height: int
    viewport_width: int
    step_stride: int


@dataclass(frozen=True)
class JourneyConfig:
    """Agrupa toda a configuracao da jornada descrita no enunciado."""

    map_path: Path
    expected_height: int
    expected_width: int
    terrain_costs: dict[str, int]
    checkpoint_order: tuple[str, ...]
    stage_difficulties: dict[str, int]
    characters: tuple[CharacterConfig, ...]
    checkpoint_cost: int
    block_future_checkpoints: bool
    visualization: VisualizationConfig


@dataclass(frozen=True)
class MapData:
    """Representa o mapa configuravel do trabalho com terrenos e checkpoints."""

    grid: tuple[str, ...]
    terrain_costs: dict[str, int]
    checkpoint_cost: int
    checkpoints: dict[str, Coordinate]

    @property
    def height(self) -> int:
        """Retorna a quantidade de linhas da matriz do mapa."""

        return len(self.grid)

    @property
    def width(self) -> int:
        """Retorna a quantidade de colunas da matriz do mapa."""

        return len(self.grid[0])

    @property
    def minimum_step_cost(self) -> int:
        """Retorna o menor custo de uma celula para compor a heuristica do A*."""

        return min(min(self.terrain_costs.values()), self.checkpoint_cost)

    def inside(self, coord: Coordinate) -> bool:
        """Verifica se uma coordenada pertence ao mapa do trabalho."""

        row, col = coord
        return 0 <= row < self.height and 0 <= col < self.width

    def cell(self, coord: Coordinate) -> str:
        """Devolve o simbolo bruto armazenado em uma posicao do mapa."""

        row, col = coord
        return self.grid[row][col]

    def cost(self, coord: Coordinate) -> int:
        """Converte uma coordenada do mapa no custo de atravessar aquela celula."""

        symbol = self.cell(coord)
        return self.terrain_costs.get(symbol, self.checkpoint_cost)


@dataclass(frozen=True)
class StageAssignment:
    """Representa a equipe escolhida para cumprir uma etapa do enunciado."""

    stage_symbol: str
    characters: tuple[str, ...]
    time_cost: float


@dataclass(frozen=True)
class SegmentResult:
    """Resume o deslocamento entre dois checkpoints consecutivos da jornada."""

    start_symbol: str
    end_symbol: str
    path: tuple[Coordinate, ...]
    steps: int
    movement_cost: int
    stage_assignment: StageAssignment | None
    cumulative_movement_cost: int
    cumulative_stage_cost: float
    cumulative_total_cost: float
    nodes_expanded: int


@dataclass(frozen=True)
class JourneyResult:
    """Agrupa o resultado final pedido pelo trabalho para a jornada completa."""

    config: JourneyConfig
    map_data: MapData
    segments: tuple[SegmentResult, ...]
    movement_cost: int
    stage_cost: float
    total_cost: float
    energy_usage: dict[str, int]


@dataclass(frozen=True)
class AnimationFrame:
    """Representa um quadro da animacao que mostra a execucao da solucao."""

    coordinate: Coordinate
    segment_index: int
    segment_step_index: int
    segment_steps: int
    movement_cost: int
    stage_cost: float
    total_cost: float
    stage_applied: bool
    energy_usage: dict[str, int]
