"""Rotina operacional para caçar seeds do algoritmo genetico.

Este modulo separa a parte de execucao em lote da logica central do AG.
Assim, o algoritmo continua concentrado em "team_planner_meta.py", enquanto
o fluxo de CSV, progresso e interrupcao fica isolado aqui.
"""

from __future__ import annotations

import csv
from pathlib import Path

from avatar_path.team_planner_meta import (
    DEFAULT_RANDOM_SEED,
    FLOAT_TOLERANCE,
    _run_genetic_algorithm,
)
from avatar_path.team_planner_state import TeamPlannerState


SEED_HUNT_START = DEFAULT_RANDOM_SEED
SEED_HUNT_MAX_RUNS: int | None = None
SEED_HUNT_CSV_PATH = "genetic_seed_hunt.csv"


def hunt_best_seed_with_genetic_algorithm(
    state: TeamPlannerState,
    start_seed: int = SEED_HUNT_START,
    max_runs: int | None = SEED_HUNT_MAX_RUNS,
    csv_path: str = SEED_HUNT_CSV_PATH,
    emit_progress: bool = True,
) -> tuple[int, float]:
    """Testa seeds em sequencia, salva tudo em CSV e devolve a melhor encontrada.

    A busca continua ate atingir ``max_runs`` ou ate o usuario interromper com
    ``Ctrl+C``. O CSV e atualizado a cada seed para nao perder resultados.
    """

    if start_seed < 0:
        raise ValueError("A seed inicial nao pode ser negativa.")
    if max_runs is not None and max_runs <= 0:
        raise ValueError("O limite de seeds deve ser maior que zero.")

    output_path = Path(csv_path)
    if output_path.parent != Path():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    best_seed: int | None = None
    best_cost = float("inf")
    current_seed = start_seed
    tested_runs = 0

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["seed", "total_cost", "is_best_so_far"])

        try:
            while max_runs is None or tested_runs < max_runs:
                candidate = _run_genetic_algorithm(state, current_seed)
                is_best = candidate.total_cost + FLOAT_TOLERANCE < best_cost

                if is_best:
                    best_seed = current_seed
                    best_cost = candidate.total_cost
                    if emit_progress:
                        print(f"Seed {current_seed}: custo {candidate.total_cost:.6f} (nova melhor)")
                elif emit_progress:
                    print(f"Seed {current_seed}: custo {candidate.total_cost:.6f}")

                writer.writerow([current_seed, f"{candidate.total_cost:.6f}", int(is_best)])
                csv_file.flush()

                current_seed += 1
                tested_runs += 1
        except KeyboardInterrupt:
            if emit_progress:
                print("\nBusca interrompida pelo usuario.")

    if best_seed is None:
        raise ValueError("Nenhuma seed foi testada.")

    if emit_progress:
        print(f"CSV salvo em: {output_path}")
        print(f"Melhor seed encontrada: {best_seed}")
        print(f"Melhor custo encontrado: {best_cost:.6f}")
    return best_seed, best_cost


__all__ = [
    "SEED_HUNT_CSV_PATH",
    "SEED_HUNT_MAX_RUNS",
    "SEED_HUNT_START",
    "hunt_best_seed_with_genetic_algorithm",
]
