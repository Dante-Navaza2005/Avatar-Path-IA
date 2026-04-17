"""Estruturas de dados compartilhadas pela solucao do trabalho do Avatar.

Cada classe deste modulo representa uma parte do enunciado:
- personagens e seus limites de energia;
- configuracao geral da jornada;
- mapa com checkpoints e custos;
- resultado final produzido pelo planejador.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


Coordinate = tuple[int, int]


@dataclass(frozen=True)
class CharacterConfig:
    """Representa um personagem disponivel para cumprir etapas da jornada.

    No trabalho, cada personagem tem agilidade propria e pode ser usado
    apenas um numero limitado de vezes.
    """

    name: str
    agility: float
    max_energy: int


@dataclass(frozen=True)
class JourneyConfig:
    """Reune toda a entrada configuravel usada para resolver a jornada.

    Com este objeto, o restante do programa nao precisa conhecer o formato
    bruto do JSON nem detalhes de onde os dados foram lidos.
    """

    map_path: Path
    expected_height: int
    expected_width: int
    terrain_costs: dict[str, int]
    checkpoint_order: tuple[str, ...]
    stage_difficulties: dict[str, int]
    characters: tuple[CharacterConfig, ...]
    checkpoint_cost: int
    block_future_checkpoints: bool


@dataclass(frozen=True)
class MapData:
    """Guarda a grade do mapa e os dados necessarios para navegar nele.

    O planejador consulta esta classe para descobrir se uma coordenada e
    valida, qual simbolo aparece nela e quanto custa entrar naquela celula.
    """

    grid: tuple[str, ...]
    terrain_costs: dict[str, int]
    checkpoint_cost: int
    checkpoints: dict[str, Coordinate]

    @property
    def height(self) -> int:
        """Retorna a quantidade de linhas do mapa carregado."""

        return len(self.grid)

    @property
    def width(self) -> int:
        """Retorna a quantidade de colunas do mapa carregado."""

        return len(self.grid[0])

    @property
    def minimum_step_cost(self) -> int:
        """Fornece o menor custo por passo usado para a heuristica do A*."""

        return min(min(self.terrain_costs.values()), self.checkpoint_cost)

    def inside(self, coord: Coordinate) -> bool:
        """Verifica se uma coordenada ainda esta dentro dos limites do mapa."""

        row, col = coord
        return 0 <= row < self.height and 0 <= col < self.width

    def cell(self, coord: Coordinate) -> str:
        """Devolve o simbolo original armazenado em uma posicao do mapa."""

        row, col = coord
        return self.grid[row][col]

    def cost(self, coord: Coordinate) -> int:
        """Traduz uma coordenada no custo de entrar naquela celula."""

        symbol = self.cell(coord)
        return self.terrain_costs.get(symbol, self.checkpoint_cost)


@dataclass(frozen=True)
class StageAssignment:
    """Registra qual equipe foi escolhida para um checkpoint com dificuldade."""

    stage_symbol: str
    characters: tuple[str, ...]
    time_cost: float


@dataclass(frozen=True)
class SegmentResult:
    """Resume um trecho da jornada entre dois checkpoints consecutivos.

    Cada trecho combina duas informacoes do enunciado:
    - o caminho encontrado no mapa;
    - o custo da etapa realizada ao chegar no checkpoint final do trecho.
    """

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
    """Agrupa tudo o que o programa precisa exibir ao final da jornada."""

    config: JourneyConfig
    map_data: MapData
    segments: tuple[SegmentResult, ...]
    movement_cost: int
    stage_cost: float
    total_cost: float
    energy_usage: dict[str, int]


@dataclass(frozen=True)
class AnimationFrame:
    """Representa um quadro da animacao da solucao no terminal ou na GUI."""

    coordinate: Coordinate
    segment_index: int
    segment_step_index: int
    segment_steps: int
    movement_cost: int
    stage_cost: float
    total_cost: float
    stage_applied: bool
    energy_usage: dict[str, int]
