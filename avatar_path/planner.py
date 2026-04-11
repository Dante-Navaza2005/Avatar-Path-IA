from __future__ import annotations

from time import perf_counter

from avatar_path.domain import JourneyConfig, JourneyResult, MapData, SegmentResult, StageAssignment
from avatar_path.map_loader import load_map
from avatar_path.pathfinding import find_path
from avatar_path.team_planner import TeamPlanner


class JourneyPlanner:
    def __init__(
        self,
        config: JourneyConfig,
        search_algorithm: str = "astar",
    ) -> None:
        self.config = config
        self.search_algorithm = search_algorithm

    def solve(self) -> JourneyResult:
        map_data = load_map(self.config)
        assignments, energy_usage, stage_cost = _optimize_teams(self.config)
        return _build_journey_result(
            config=self.config,
            map_data=map_data,
            search_algorithm=self.search_algorithm,
            assignments=assignments,
            energy_usage=energy_usage,
            stage_cost=stage_cost,
        )


def compare_search_algorithms(
    config: JourneyConfig,
    algorithms: tuple[str, ...] = ("astar", "dijkstra", "greedy"),
) -> tuple[dict[str, float | int | str], ...]:
    map_data = load_map(config)
    assignments, energy_usage, stage_cost = _optimize_teams(config)

    results: list[dict[str, float | int | str]] = []
    for algorithm in algorithms:
        start = perf_counter()
        result = _build_journey_result(
            config=config,
            map_data=map_data,
            search_algorithm=algorithm,
            assignments=assignments,
            energy_usage=energy_usage,
            stage_cost=stage_cost,
        )
        elapsed_ms = (perf_counter() - start) * 1000.0
        results.append(
            {
                "algorithm": algorithm,
                "movement_cost": result.movement_cost,
                "stage_cost": round(stage_cost, 6),
                "total_cost": round(result.movement_cost + stage_cost, 6),
                "nodes_expanded": sum(segment.nodes_expanded for segment in result.segments),
                "elapsed_ms": round(elapsed_ms, 6),
            }
        )

    return tuple(
        sorted(
            results,
            key=lambda item: (
                item["total_cost"],
                0 if item["algorithm"] == "astar" else 1,
                item["nodes_expanded"],
                item["elapsed_ms"],
            ),
        )
    )


def _optimize_teams(
    config: JourneyConfig,
) -> tuple[tuple[StageAssignment, ...], dict[str, int], float]:
    team_planner = TeamPlanner(
        characters=config.characters,
        ordered_stage_symbols=config.checkpoint_order[1:],
        stage_difficulties=config.stage_difficulties,
    )
    return team_planner.optimize()


def _build_journey_result(
    config: JourneyConfig,
    map_data: MapData,
    search_algorithm: str,
    assignments: tuple[StageAssignment, ...],
    energy_usage: dict[str, int],
    stage_cost: float,
) -> JourneyResult:
    assignment_by_symbol = {
        assignment.stage_symbol: assignment
        for assignment in assignments
    }
    movement_cost = 0
    cumulative_stage_cost = 0.0
    segments: list[SegmentResult] = []

    for idx, (start_symbol, end_symbol) in enumerate(
        zip(config.checkpoint_order, config.checkpoint_order[1:])
    ):
        start = map_data.checkpoints[start_symbol]
        goal = map_data.checkpoints[end_symbol]
        blocked = _blocked_future_checkpoints(config, map_data, idx)

        path, segment_movement_cost, nodes_expanded = find_path(
            map_data=map_data,
            start=start,
            goal=goal,
            algorithm=search_algorithm,
            blocked=blocked,
        )

        movement_cost += segment_movement_cost
        # A etapa combinatoria do simbolo de destino so entra quando
        # o caminho daquele trecho termina no checkpoint correspondente.
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
    if not config.block_future_checkpoints:
        return frozenset()
    return frozenset(
        map_data.checkpoints[symbol]
        for symbol in config.checkpoint_order[segment_index + 2 :]
    )
