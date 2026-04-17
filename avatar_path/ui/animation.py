"""Animacao em terminal da jornada calculada pelo programa.

Este modulo reaproveita o resultado final do planejador e o converte em uma
sequencia de quadros que podem ser exibidos tanto no terminal quanto na GUI.
"""

from __future__ import annotations

from avatar_path.domain import (
    AnimationFrame,
    JourneyResult,
)


def build_animation_frames(
    result: JourneyResult,
    step_stride: int = 1,
) -> tuple[AnimationFrame, ...]:
    """Transforma a solucao final em quadros para o terminal e para a GUI.

    Cada frame registra posicao, custos acumulados e energia ja consumida.
    Isso permite que diferentes interfaces mostrem exatamente a mesma execucao.
    """

    frames: list[AnimationFrame] = []
    movement_cost = 0
    stage_cost = 0.0
    energy_usage = {character.name: 0 for character in result.config.characters}

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
            energy_usage=energy_usage.copy(),
        )
    )

    for segment_index, segment in enumerate(result.segments):
        path = segment.path if len(segment.path) == 1 else segment.path[1:]
        segment_movement = 0
        stage_time = 0.0 if segment.stage_assignment is None else segment.stage_assignment.time_cost
        completed_energy_usage: dict[str, int] | None = None

        for step_index, coordinate in enumerate(path, start=1):
            segment_movement += result.map_data.cost(coordinate)
            is_last_step = step_index == len(path)
            if step_index % max(1, step_stride) != 0 and not is_last_step:
                continue

            current_movement = movement_cost + segment_movement
            current_stage_cost = stage_cost + (stage_time if is_last_step else 0.0)
            current_energy_usage = energy_usage.copy()

            # O custo da etapa so entra quando o grupo chega ao checkpoint onde
            # aquele desafio e efetivamente resolvido.
            if is_last_step and segment.stage_assignment is not None:
                for name in segment.stage_assignment.characters:
                    current_energy_usage[name] += 1
                completed_energy_usage = current_energy_usage

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
                    energy_usage=current_energy_usage,
                )
            )

        movement_cost += segment.movement_cost
        stage_cost += stage_time
        if completed_energy_usage is not None:
            energy_usage = completed_energy_usage

    return tuple(frames)
