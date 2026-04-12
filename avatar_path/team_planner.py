"""Fachada publica da etapa combinatoria de escolha de equipes."""

from __future__ import annotations

from avatar_path.domain import CharacterConfig
from avatar_path.team_planner_meta import optimize_with_genetic_hill_climbing_simulated_annealing
from avatar_path.team_planner_state import PlannerSolution, TeamPlannerState, build_team_planner_state


class TeamPlanner:
    """Resolve a parte do enunciado que distribui personagens pelas etapas."""

    def __init__(
        self,
        characters: tuple[CharacterConfig, ...],
        ordered_stage_symbols: tuple[str, ...],
        stage_difficulties: dict[str, int],
        reserved_final_energy: int = 0,
    ) -> None:
        """Monta o estado fixo da combinatoria antes de executar as metaheuristicas."""

        self.state = build_team_planner_state(
            characters=characters,
            ordered_stage_symbols=ordered_stage_symbols,
            stage_difficulties=stage_difficulties,
            reserved_final_energy=reserved_final_energy,
        )

    @property
    def stage_symbols(self) -> tuple[str, ...]:
        """Expoe as etapas que realmente entram na otimizacao das equipes."""

        return self.state.stage_symbols

    def optimize(self) -> PlannerSolution:
        """Procura uma boa distribuicao de equipes respeitando a energia maxima."""

        return optimize_with_genetic_hill_climbing_simulated_annealing(self.state)


__all__ = ["TeamPlanner", "TeamPlannerState"]
