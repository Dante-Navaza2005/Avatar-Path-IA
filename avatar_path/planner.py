"""Planejamento completo da jornada combinando busca no mapa e equipes.

Este modulo junta as duas partes principais do trabalho:
- encontrar o caminho entre checkpoints;
- escolher quais personagens cumprem cada etapa.
"""

from __future__ import annotations

from avatar_path.domain import JourneyConfig, JourneyResult, MapData, SegmentResult, StageAssignment
from avatar_path.map_loader import load_map
from avatar_path.pathfinding import find_path
from avatar_path.team_planner import TeamPlanner


class JourneyPlanner:
    """Coordena as duas partes do trabalho: mapa e combinatoria das etapas."""

    def __init__(
        self,
        config: JourneyConfig,
    ) -> None:
        """Guarda a configuracao usada na jornada."""

        self.config = config

    def solve(self) -> JourneyResult:
        """Resolve a jornada inteira, do checkpoint inicial ate o final.

        A ideia aqui e separar o problema em duas etapas do enunciado:
        primeiro escolhemos as equipes; depois calculamos cada deslocamento.
        """

        map_data = load_map(self.config)
        assignments, energy_usage, stage_cost = _optimize_teams(self.config)
        return _build_journey_result(
            config=self.config,
            map_data=map_data,
            assignments=assignments,
            energy_usage=energy_usage,
            stage_cost=stage_cost,
        )


def _optimize_teams(
    config: JourneyConfig,
) -> tuple[tuple[StageAssignment, ...], dict[str, int], float]:
    """Resolve apenas a parte combinatoria para as etapas com dificuldade."""

    team_planner = TeamPlanner(
        characters=config.characters,
        ordered_stage_symbols=config.checkpoint_order[1:],
        stage_difficulties=config.stage_difficulties,
    )
    return team_planner.optimize()


def _build_journey_result(
    config: JourneyConfig,
    map_data: MapData,
    assignments: tuple[StageAssignment, ...],
    energy_usage: dict[str, int],
    stage_cost: float,
) -> JourneyResult:
    """Monta o resultado completo trecho a trecho.

    Esta funcao transforma a resposta das duas etapas do trabalho em um unico
    objeto final, com custos acumulados que facilitam testes e visualizacao.
    """

    assignment_by_symbol = {
        assignment.stage_symbol: assignment
        for assignment in assignments
    }
    movement_cost = 0
    cumulative_stage_cost = 0.0
    segments: list[SegmentResult] = []

    for segment_index, (start_symbol, end_symbol) in enumerate(
        zip(config.checkpoint_order, config.checkpoint_order[1:])
    ):
        start = map_data.checkpoints[start_symbol]
        goal = map_data.checkpoints[end_symbol]

        # Checkpoints futuros podem ser tratados como bloqueados para evitar
        # atalhos que pulam a ordem exigida pela jornada.
        blocked = _blocked_future_checkpoints(config, map_data, segment_index)

        path, segment_movement_cost, nodes_expanded = find_path(
            map_data=map_data,
            start=start,
            goal=goal,
            algorithm="astar",
            blocked=blocked,
        )

        movement_cost += segment_movement_cost
        stage_assignment = assignment_by_symbol.get(end_symbol)
        stage_time = 0.0 if stage_assignment is None else stage_assignment.time_cost
        cumulative_stage_cost += stage_time

        segments.append(
            SegmentResult(
                start_symbol=start_symbol,
                end_symbol=end_symbol,
                path=path,
                steps=len(path) - 1,
                movement_cost=segment_movement_cost,
                stage_assignment=stage_assignment,
                cumulative_movement_cost=movement_cost,
                cumulative_stage_cost=cumulative_stage_cost,
                cumulative_total_cost=movement_cost + cumulative_stage_cost,
                nodes_expanded=nodes_expanded,
            )
        )

    return JourneyResult(
        config=config,
        map_data=map_data,
        segments=tuple(segments),
        movement_cost=movement_cost,
        stage_cost=stage_cost,
        total_cost=movement_cost + stage_cost,
        energy_usage=dict(energy_usage),
    )


def _blocked_future_checkpoints(
    config: JourneyConfig,
    map_data: MapData,
    segment_index: int,
) -> frozenset[tuple[int, int]]:
    """Bloqueia checkpoints futuros para preservar a ordem da jornada."""

    if not config.block_future_checkpoints:
        return frozenset()

    return frozenset(
        map_data.checkpoints[symbol]
        for symbol in config.checkpoint_order[segment_index + 2 :]
    )
