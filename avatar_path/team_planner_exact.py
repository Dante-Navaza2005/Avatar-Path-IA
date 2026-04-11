from __future__ import annotations

from avatar_path.team_planner_state import PlannerSolution, TeamPlannerState

try:
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import lil_matrix

    HAS_SCIPY = True
except Exception:  # pragma: no cover - fallback de ambiente
    HAS_SCIPY = False


def optimize_with_milp(state: TeamPlannerState) -> PlannerSolution:
    if not HAS_SCIPY:
        raise RuntimeError("SciPy nao esta disponivel para o solver exato.")

    # Cada variavel binaria representa "usar este subconjunto de personagens
    # nesta etapa". O solver escolhe exatamente um subconjunto por etapa.
    variables_per_stage = len(state.all_masks)
    variable_count = len(state.stage_symbols) * variables_per_stage
    constraint_count = len(state.stage_symbols) + len(state.characters) + 1
    objective = np.zeros(variable_count, dtype=float)
    constraints = lil_matrix((constraint_count, variable_count), dtype=float)
    lower_bounds = np.zeros(constraint_count, dtype=float)
    upper_bounds = np.zeros(constraint_count, dtype=float)

    for stage_idx, stage_symbol in enumerate(state.stage_symbols):
        row = stage_idx
        lower_bounds[row] = 1.0
        upper_bounds[row] = 1.0
        for mask_idx, mask in enumerate(state.all_masks):
            variable_idx = stage_idx * variables_per_stage + mask_idx
            objective[variable_idx] = state.stage_time(stage_symbol, mask)
            constraints[row, variable_idx] = 1.0

    for char_idx, character in enumerate(state.characters):
        row = len(state.stage_symbols) + char_idx
        lower_bounds[row] = 0.0
        upper_bounds[row] = float(character.max_energy)
        for stage_idx, _stage_symbol in enumerate(state.stage_symbols):
            for mask_idx, mask in enumerate(state.all_masks):
                if mask & (1 << char_idx):
                    variable_idx = stage_idx * variables_per_stage + mask_idx
                    constraints[row, variable_idx] = 1.0

    reserve_row = len(state.stage_symbols) + len(state.characters)
    lower_bounds[reserve_row] = 0.0
    upper_bounds[reserve_row] = float(state.usable_energy_budget)
    for stage_idx, _stage_symbol in enumerate(state.stage_symbols):
        for mask_idx, mask in enumerate(state.all_masks):
            variable_idx = stage_idx * variables_per_stage + mask_idx
            constraints[reserve_row, variable_idx] = float(mask.bit_count())

    result = milp(
        c=objective,
        constraints=LinearConstraint(constraints.tocsr(), lower_bounds, upper_bounds),
        integrality=np.ones(variable_count, dtype=int),
        bounds=Bounds(np.zeros(variable_count), np.ones(variable_count)),
        options={"disp": False},
    )

    if not result.success:
        raise ValueError(f"O solver inteiro nao encontrou solucao valida: {result.message}")

    mask_by_symbol: dict[str, int] = {}
    solution = result.x
    for stage_idx, stage_symbol in enumerate(state.stage_symbols):
        start = stage_idx * variables_per_stage
        end = start + variables_per_stage
        stage_values = solution[start:end]
        chosen_mask_idx = max(
            range(len(stage_values)),
            key=lambda idx: stage_values[idx],
        )
        mask_by_symbol[stage_symbol] = state.all_masks[chosen_mask_idx]

    return state.build_assignments(mask_by_symbol)
