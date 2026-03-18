from __future__ import annotations

from avatar_path.domain import JourneyConfig, JourneyResult, SegmentResult
from avatar_path.map_loader import load_map
from avatar_path.pathfinding import astar_shortest_path
from avatar_path.team_planner import TeamPlanner


class JourneyPlanner:
    def __init__(self, config: JourneyConfig) -> None:
        self.config = config

    def solve(self) -> JourneyResult:
        map_data = load_map(self.config)
        team_planner = TeamPlanner(
            characters=self.config.characters,
            ordered_stage_symbols=self.config.checkpoint_order[1:-1],
            stage_difficulties=self.config.stage_difficulties,
        )
        assignments, energy_usage, stage_cost = team_planner.optimize()
        assignment_by_symbol = {assignment.stage_symbol: assignment for assignment in assignments}

        movement_cost = 0
        cumulative_stage_cost = 0.0
        segments = []

        for idx in range(len(self.config.checkpoint_order) - 1):
            start_symbol = self.config.checkpoint_order[idx]
            end_symbol = self.config.checkpoint_order[idx + 1]
            start = map_data.checkpoints[start_symbol]
            goal = map_data.checkpoints[end_symbol]

            blocked = frozenset()
            if self.config.block_future_checkpoints:
                blocked = frozenset(
                    map_data.checkpoints[symbol]
                    for symbol in self.config.checkpoint_order[idx + 2 :]
                )

            path, segment_movement_cost, nodes_expanded = astar_shortest_path(
                map_data=map_data,
                start=start,
                goal=goal,
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
            config=self.config,
            map_data=map_data,
            segments=tuple(segments),
            movement_cost=movement_cost,
            stage_cost=stage_cost,
            total_cost=movement_cost + stage_cost,
            energy_usage=energy_usage,
        )

