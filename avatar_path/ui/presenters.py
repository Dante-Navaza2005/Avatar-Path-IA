"""Funcoes que transformam o resultado da jornada em textos para a GUI."""

from __future__ import annotations

from avatar_path.domain import AnimationFrame, JourneyResult, SegmentResult
from avatar_path.formatting import format_cost


def build_segment_index(frames: tuple[AnimationFrame, ...]) -> dict[int, int]:
    """Mapeia cada trecho para o ultimo frame em que ele aparece na animacao."""

    last_index: dict[int, int] = {}
    for index, frame in enumerate(frames):
        last_index[frame.segment_index] = index
    return last_index


def segment_row_values(segment: SegmentResult) -> tuple[str, str, str, str]:
    """Monta uma linha legivel da tabela de trechos da interface."""

    assignment = segment.stage_assignment
    if assignment is None:
        stage_label = "-"
        team_label = "Chegada final"
    else:
        stage_label = format_cost(assignment.time_cost)
        team_label = ", ".join(assignment.characters)

    return (
        f"{segment.start_symbol}->{segment.end_symbol}",
        format_cost(segment.movement_cost),
        stage_label,
        team_label,
    )


def progress_text(frame_index: int, frames: tuple[AnimationFrame, ...]) -> str:
    """Resume o progresso atual da animacao em frames e passos."""

    frame = frames[frame_index]
    return (
        f"frame {frame_index + 1}/{len(frames)}"
        f"  |  passo {frame.segment_step_index}/{frame.segment_steps}"
    )


def status_text(playing: bool, frame_index: int, frame_count: int) -> str:
    """Escolhe a mensagem de estado exibida no painel lateral."""

    if playing:
        return "Animacao em execucao."
    if frame_index == 0:
        return "Pronto para reproduzir a jornada."
    if frame_index == frame_count - 1:
        return "Jornada concluida."
    return "Animacao pausada."


def team_text(segment: SegmentResult, frame: AnimationFrame) -> str:
    """Resume a equipe responsavel pela etapa ligada ao trecho atual."""

    if segment.stage_assignment is None:
        return "Fim da jornada"

    team = ", ".join(segment.stage_assignment.characters)
    if frame.stage_applied:
        return f"{team}  |  etapa concluida"
    return f"{team}  |  em deslocamento"


def energy_text(result: JourneyResult, frame: AnimationFrame) -> str:
    """Formata o consumo de energia dos personagens para a interface."""

    parts = []
    for character in result.config.characters:
        parts.append(
            f"{character.name} {frame.energy_usage[character.name]}/{character.max_energy}"
        )
    return " | ".join(parts)
