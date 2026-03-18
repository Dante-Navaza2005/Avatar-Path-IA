from __future__ import annotations

import time

from avatar_path.domain import (
    AnimationFrame,
    Coordinate,
    JourneyResult,
    MapData,
    SegmentResult,
    VisualizationConfig,
)


CLEAR_SCREEN = "\033[2J\033[H"


def _display_symbol(
    map_data: MapData,
    coord: Coordinate,
    current: Coordinate,
    visited: set[Coordinate],
) -> str:
    if coord == current:
        return "@"

    symbol = map_data.cell(coord)
    if coord in visited and symbol in map_data.terrain_costs:
        return "*"
    return symbol


def _render_viewport(
    map_data: MapData,
    current: Coordinate,
    visited: set[Coordinate],
    viewport_height: int,
    viewport_width: int,
) -> str:
    center_row, center_col = current
    half_height = viewport_height // 2
    half_width = viewport_width // 2

    top = max(0, center_row - half_height)
    left = max(0, center_col - half_width)
    bottom = min(map_data.height, top + viewport_height)
    right = min(map_data.width, left + viewport_width)

    top = max(0, bottom - viewport_height)
    left = max(0, right - viewport_width)

    lines = []
    for row in range(top, bottom):
        line = "".join(
            _display_symbol(map_data, (row, col), current, visited)
            for col in range(left, right)
        )
        lines.append(line)
    return "\n".join(lines)


def _segment_status(segment: SegmentResult) -> str:
    if segment.stage_assignment is None:
        return f"Trecho {segment.start_symbol} -> {segment.end_symbol} | chegada final"

    team = ", ".join(segment.stage_assignment.characters)
    return (
        f"Trecho {segment.start_symbol} -> {segment.end_symbol} | "
        f"etapa {segment.end_symbol} | equipe: {team} | "
        f"movimento: {segment.movement_cost} | etapa: {segment.stage_assignment.time_cost:.4f} | "
        f"total acumulado: {segment.cumulative_total_cost:.4f}"
    )


def build_animation_frames(
    result: JourneyResult,
    step_stride: int = 1,
) -> tuple[AnimationFrame, ...]:
    frames: list[AnimationFrame] = []
    movement_cost = 0
    stage_cost = 0.0

    start_coordinate = result.map_data.checkpoints[result.config.checkpoint_order[0]]
    frames.append(
        AnimationFrame(
            coordinate=start_coordinate,
            segment_index=0,
            segment_step_index=0,
            segment_steps=0,
            movement_cost=0,
            stage_cost=0.0,
            total_cost=0.0,
            stage_applied=False,
        )
    )

    for segment_index, segment in enumerate(result.segments):
        path = segment.path if len(segment.path) == 1 else segment.path[1:]
        segment_movement = 0
        stage_time = 0.0 if segment.stage_assignment is None else segment.stage_assignment.time_cost

        for step_index, coordinate in enumerate(path, start=1):
            segment_movement += result.map_data.cost(coordinate)
            is_last_step = step_index == len(path)
            if step_index % max(1, step_stride) != 0 and not is_last_step:
                continue

            current_movement = movement_cost + segment_movement
            current_stage_cost = stage_cost + (stage_time if is_last_step else 0.0)
            frames.append(
                AnimationFrame(
                    coordinate=coordinate,
                    segment_index=segment_index,
                    segment_step_index=step_index,
                    segment_steps=len(path),
                    movement_cost=current_movement,
                    stage_cost=current_stage_cost,
                    total_cost=current_movement + current_stage_cost,
                    stage_applied=is_last_step and segment.stage_assignment is not None,
                )
            )

        movement_cost += segment.movement_cost
        stage_cost += stage_time

    return tuple(frames)


def animate_journey(result: JourneyResult, visualization: VisualizationConfig) -> None:
    visited: set[Coordinate] = set()
    frames = build_animation_frames(result, visualization.step_stride)

    for frame in frames[1:]:
        segment = result.segments[frame.segment_index]
        visited.add(frame.coordinate)
        segment_stage_cost = frame.stage_cost
        movement_cost = frame.movement_cost
        total_cost = frame.total_cost
        if not frame.stage_applied and segment.stage_assignment is not None:
            segment_stage_cost -= segment.stage_assignment.time_cost

        coord = frame.coordinate
        frame_text = _render_viewport(
            map_data=result.map_data,
            current=coord,
            visited=visited,
            viewport_height=visualization.viewport_height,
            viewport_width=visualization.viewport_width,
        )
        print(
            CLEAR_SCREEN
            + frame_text
            + "\n\n"
            + _segment_status(segment)
            + f"\nMovimento acumulado: {movement_cost}"
            + f"\nCusto acumulado das etapas: {segment_stage_cost:.4f}"
            + f"\nCusto total acumulado: {total_cost:.4f}"
        )
        time.sleep(visualization.delay_seconds)
