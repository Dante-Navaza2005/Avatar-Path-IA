"""Fachada publica da etapa combinatoria de escolha de equipes.

Este modulo deixa a logica de equipes com uma interface pequena e facil de
usar pelo planejador principal.
"""

from __future__ import annotations

from avatar_path.domain import CharacterConfig
from avatar_path.team_planner_meta import optimize_with_genetic_algorithm
from avatar_path.team_planner_seed_hunt import (SEED_HUNT_CSV_PATH, SEED_HUNT_MAX_RUNS, SEED_HUNT_START, hunt_best_seed_with_genetic_algorithm)
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
        """Prepara o estado fixo da parte combinatoria do trabalho."""

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
        """Procura uma distribuicao de equipes respeitando a energia maxima.

        O objetivo e minimizar o tempo total das etapas sem ultrapassar o
        limite de uso de cada personagem.
        """

        return optimize_with_genetic_algorithm(self.state)

    def hunt_best_seed(
        self,
        start_seed: int = SEED_HUNT_START,
        max_runs: int | None = SEED_HUNT_MAX_RUNS,
        csv_path: str = SEED_HUNT_CSV_PATH,
        emit_progress: bool = True,
    ) -> tuple[int, float]:
        """Testa seeds em sequencia e salva os resultados em CSV."""

        return hunt_best_seed_with_genetic_algorithm(
            self.state,
            start_seed=start_seed,
            max_runs=max_runs,
            csv_path=csv_path,
            emit_progress=emit_progress,
        )


__all__ = ["TeamPlanner", "TeamPlannerState"]
