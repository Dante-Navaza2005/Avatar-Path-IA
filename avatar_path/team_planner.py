from __future__ import annotations

from avatar_path.domain import CharacterConfig
from avatar_path.team_planner_meta import optimize_with_hill_climbing_simulated_annealing
from avatar_path.team_planner_state import PlannerSolution, TeamPlannerState, build_team_planner_state


class TeamPlanner:
    """Fachada publica da etapa de alocacao de equipes da jornada."""

    def __init__(
        self,
        characters: tuple[CharacterConfig, ...],
        ordered_stage_symbols: tuple[str, ...],
        stage_difficulties: dict[str, int],
        reserved_final_energy: int = 0,
    ) -> None:
        self.state = build_team_planner_state(
            characters=characters,
            ordered_stage_symbols=ordered_stage_symbols,
            stage_difficulties=stage_difficulties,
            reserved_final_energy=reserved_final_energy,
        )

    @property
    def stage_symbols(self) -> tuple[str, ...]:
        return self.state.stage_symbols

    def optimize(self) -> PlannerSolution:
        return optimize_with_hill_climbing_simulated_annealing(self.state)


__all__ = ["TeamPlanner", "TeamPlannerState"]
