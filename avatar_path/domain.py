from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


Coordinate = tuple[int, int]


@dataclass(frozen=True)
class CharacterConfig:
    name: str
    agility: float
    max_energy: int


@dataclass(frozen=True)
class VisualizationConfig:
    delay_seconds: float
    viewport_height: int
    viewport_width: int
    step_stride: int


@dataclass(frozen=True)
class JourneyConfig:
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
    grid: tuple[str, ...]
    terrain_costs: dict[str, int]
    checkpoint_cost: int
    checkpoints: dict[str, Coordinate]
    cell_costs: tuple[int, ...]

    @property
    def height(self) -> int:
        return len(self.grid)

    @property
    def width(self) -> int:
        return len(self.grid[0])

    @property
    def minimum_step_cost(self) -> int:
        return min(min(self.terrain_costs.values()), self.checkpoint_cost)

    def inside(self, coord: Coordinate) -> bool:
        row, col = coord
        return 0 <= row < self.height and 0 <= col < self.width

    def cell(self, coord: Coordinate) -> str:
        row, col = coord
        return self.grid[row][col]

    def cost(self, coord: Coordinate) -> int:
        symbol = self.cell(coord)
        return self.terrain_costs.get(symbol, self.checkpoint_cost)

    def index(self, coord: Coordinate) -> int:
        row, col = coord
        return row * self.width + col

    def coordinate(self, index: int) -> Coordinate:
        return divmod(index, self.width)

    def bitmap_for_coordinates(self, coordinates: Iterable[Coordinate]) -> tuple[int, ...]:
        rows = [0] * self.height
        for row, col in coordinates:
            rows[row] |= 1 << col
        return tuple(rows)


@dataclass(frozen=True)
class StageAssignment:
    stage_symbol: str
    characters: tuple[str, ...]
    time_cost: float


@dataclass(frozen=True)
class SegmentResult:
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
    config: JourneyConfig
    map_data: MapData
    segments: tuple[SegmentResult, ...]
    movement_cost: int
    stage_cost: float
    total_cost: float
    energy_usage: dict[str, int]


@dataclass(frozen=True)
class AnimationFrame:
    coordinate: Coordinate
    segment_index: int
    segment_step_index: int
    segment_steps: int
    movement_cost: int
    stage_cost: float
    total_cost: float
    stage_applied: bool
