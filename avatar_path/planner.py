from __future__ import annotations

from time import perf_counter

from avatar_path.domain import JourneyConfig, JourneyResult, MapData, SegmentResult
from avatar_path.map_loader import load_map
from avatar_path.pathfinding import find_path
from avatar_path.team_planner import TeamPlanner


CheckpointDistances = dict[tuple[str, str], int]


def _build_checkpoint_distances(
    map_data: MapData,
    checkpoint_order: tuple[str, ...],
    search_algorithm: str,
) -> CheckpointDistances:
    distances: CheckpointDistances = {}
    for start_symbol in checkpoint_order:
        start = map_data.checkpoints[start_symbol]
        for end_symbol in checkpoint_order:
            if start_symbol == end_symbol:
                continue
            goal = map_data.checkpoints[end_symbol]
            _, cost, _ = find_path(map_data, start, goal, search_algorithm)
            distances[(start_symbol, end_symbol)] = cost
    return distances


def _route_cost(route: tuple[str, ...], distances: CheckpointDistances) -> int:
    return sum(
        distances[(route[idx], route[idx + 1])]
        for idx in range(len(route) - 1)
    )


def _nearest_neighbor_route(
    start_symbol: str,
    end_symbol: str,
    middle_symbols: tuple[str, ...],
    distances: CheckpointDistances,
    forced_first_symbol: str | None = None,
) -> tuple[str, ...]:
    route = [start_symbol]
    remaining = set(middle_symbols)
    current = start_symbol

    if forced_first_symbol is not None:
        route.append(forced_first_symbol)
        remaining.remove(forced_first_symbol)
        current = forced_first_symbol

    while remaining:
        next_symbol = min(
            remaining,
            key=lambda symbol: (
                distances[(current, symbol)],
                distances[(symbol, end_symbol)],
                symbol,
            ),
        )
        route.append(next_symbol)
        remaining.remove(next_symbol)
        current = next_symbol

    route.append(end_symbol)
    return tuple(route)


def _best_two_opt_neighbor(
    route: tuple[str, ...],
    distances: CheckpointDistances,
) -> tuple[tuple[str, ...], int]:
    best_route = route
    best_cost = _route_cost(route, distances)

    for start_idx in range(1, len(route) - 2):
        for end_idx in range(start_idx + 1, len(route) - 1):
            candidate = (
                route[:start_idx]
                + tuple(reversed(route[start_idx : end_idx + 1]))
                + route[end_idx + 1 :]
            )
            candidate_cost = _route_cost(candidate, distances)
            if candidate_cost < best_cost:
                best_route = candidate
                best_cost = candidate_cost

    return best_route, best_cost


def _best_relocate_neighbor(
    route: tuple[str, ...],
    distances: CheckpointDistances,
) -> tuple[tuple[str, ...], int]:
    best_route = route
    best_cost = _route_cost(route, distances)
    route_list = list(route)

    for source_idx in range(1, len(route_list) - 1):
        moved_symbol = route_list[source_idx]
        remaining = route_list[:source_idx] + route_list[source_idx + 1 :]
        for target_idx in range(1, len(remaining)):
            if target_idx == source_idx:
                continue
            candidate_list = remaining[:]
            candidate_list.insert(target_idx, moved_symbol)
            candidate = tuple(candidate_list)
            candidate_cost = _route_cost(candidate, distances)
            if candidate_cost < best_cost:
                best_route = candidate
                best_cost = candidate_cost

    return best_route, best_cost


def _best_swap_neighbor(
    route: tuple[str, ...],
    distances: CheckpointDistances,
) -> tuple[tuple[str, ...], int]:
    best_route = route
    best_cost = _route_cost(route, distances)
    route_list = list(route)

    for left_idx in range(1, len(route_list) - 2):
        for right_idx in range(left_idx + 1, len(route_list) - 1):
            candidate_list = route_list[:]
            candidate_list[left_idx], candidate_list[right_idx] = (
                candidate_list[right_idx],
                candidate_list[left_idx],
            )
            candidate = tuple(candidate_list)
            candidate_cost = _route_cost(candidate, distances)
            if candidate_cost < best_cost:
                best_route = candidate
                best_cost = candidate_cost

    return best_route, best_cost


def _refine_route(
    route: tuple[str, ...],
    distances: CheckpointDistances,
) -> tuple[str, ...]:
    best_route = route
    best_cost = _route_cost(route, distances)

    while True:
        improved = False
        for optimizer in (
            _best_two_opt_neighbor,
            _best_relocate_neighbor,
            _best_swap_neighbor,
        ):
            candidate_route, candidate_cost = optimizer(best_route, distances)
            if candidate_cost < best_cost:
                best_route = candidate_route
                best_cost = candidate_cost
                improved = True
                break
        if not improved:
            return best_route


def optimize_checkpoint_order(
    map_data: MapData,
    checkpoint_order: tuple[str, ...],
    search_algorithm: str,
) -> tuple[str, ...]:
    """Otimiza a ordem mantendo o primeiro e o último checkpoint fixos."""
    if len(checkpoint_order) <= 3:
        return checkpoint_order

    start_symbol = checkpoint_order[0]
    end_symbol = checkpoint_order[-1]
    middle_symbols = checkpoint_order[1:-1]
    distances = _build_checkpoint_distances(map_data, checkpoint_order, search_algorithm)

    candidate_routes = {checkpoint_order}
    candidate_routes.add(
        _nearest_neighbor_route(start_symbol, end_symbol, middle_symbols, distances)
    )

    for first_symbol in middle_symbols:
        candidate_routes.add(
            _nearest_neighbor_route(
                start_symbol,
                end_symbol,
                middle_symbols,
                distances,
                forced_first_symbol=first_symbol,
            )
        )

    best_route = checkpoint_order
    best_cost = _route_cost(best_route, distances)

    for candidate in candidate_routes:
        refined_route = _refine_route(candidate, distances)
        refined_cost = _route_cost(refined_route, distances)
        if refined_cost < best_cost:
            best_route = refined_route
            best_cost = refined_cost

    return best_route


class JourneyPlanner:
    def __init__(
        self,
        config: JourneyConfig,
        search_algorithm: str = "astar",
        optimize_order: bool = False    ) -> None:
        self.config = config
        self.search_algorithm = search_algorithm
        self.optimize_order = optimize_order

    def solve(self) -> JourneyResult:
        map_data = load_map(self.config)
        effective_config = self.config

        if self.optimize_order:
            optimized_order = optimize_checkpoint_order(
                map_data,
                self.config.checkpoint_order,
                self.search_algorithm,
            )
            effective_config = type(self.config)(
                **{**self.config.__dict__, "checkpoint_order": optimized_order}
            )

        team_planner = TeamPlanner(
            characters=effective_config.characters,
            ordered_stage_symbols=effective_config.checkpoint_order[1:],
            stage_difficulties=effective_config.stage_difficulties,
        )
        assignments, energy_usage, stage_cost = team_planner.optimize()
        assignment_by_symbol = {assignment.stage_symbol: assignment for assignment in assignments}

        movement_cost = 0
        cumulative_stage_cost = 0.0
        segments = []

        for idx in range(len(effective_config.checkpoint_order) - 1):
            start_symbol = effective_config.checkpoint_order[idx]
            end_symbol = effective_config.checkpoint_order[idx + 1]
            start = map_data.checkpoints[start_symbol]
            goal = map_data.checkpoints[end_symbol]

            blocked = frozenset()
            if effective_config.block_future_checkpoints:
                blocked = frozenset(
                    map_data.checkpoints[symbol]
                    for symbol in effective_config.checkpoint_order[idx + 2 :]
                )

            path, segment_movement_cost, nodes_expanded = find_path(
                map_data=map_data,
                start=start,
                goal=goal,
                algorithm=self.search_algorithm,
                blocked=blocked,
            )

            movement_cost += segment_movement_cost
            stage_assignment = assignment_by_symbol.get(end_symbol)
            stage_time = 0.0 if stage_assignment is None else stage_assignment.time_cost
            cumulative_stage_cost += stage_time
            cumulative_total = movement_cost + cumulative_stage_cost

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
                    cumulative_total_cost=cumulative_total,
                    nodes_expanded=nodes_expanded,
                )
            )

        return JourneyResult(
            config=effective_config,
            map_data=map_data,
            segments=tuple(segments),
            movement_cost=movement_cost,
            stage_cost=stage_cost,
            total_cost=movement_cost + stage_cost,
            energy_usage=energy_usage,
        )


def compare_search_algorithms(
    config: JourneyConfig,
    algorithms: tuple[str, ...] = ("astar", "dijkstra", "greedy"),
) -> tuple[dict[str, float | int | str], ...]:
    team_planner = TeamPlanner(
        characters=config.characters,
        ordered_stage_symbols=config.checkpoint_order[1:],
        stage_difficulties=config.stage_difficulties,
    )
    _, _, stage_cost = team_planner.optimize()

    results: list[dict[str, float | int | str]] = []
    for algorithm in algorithms:
        start = perf_counter()
        result = JourneyPlanner(config, search_algorithm=algorithm).solve()
        elapsed_ms = (perf_counter() - start) * 1000.0
        results.append(
            {
                "algorithm": algorithm,
                "movement_cost": result.movement_cost,
                "stage_cost": round(stage_cost, 4),
                "total_cost": round(result.movement_cost + stage_cost, 4),
                "nodes_expanded": sum(segment.nodes_expanded for segment in result.segments),
                "elapsed_ms": round(elapsed_ms, 2),
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
