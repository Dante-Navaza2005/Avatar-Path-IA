from __future__ import annotations

from math import isclose

from avatar_path.domain import CharacterConfig, StageAssignment

try:
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import lil_matrix

    HAS_SCIPY = True
except Exception:  # pragma: no cover - fallback de ambiente
    HAS_SCIPY = False


class TeamPlanner:
    def __init__(
        self,
        characters: tuple[CharacterConfig, ...],
        ordered_stage_symbols: tuple[str, ...],
        stage_difficulties: dict[str, int],
    ) -> None:
        self.characters = characters
        self.stage_symbols = tuple(symbol for symbol in ordered_stage_symbols if symbol in stage_difficulties)
        self.stage_difficulties = stage_difficulties
        self.names = tuple(character.name for character in characters)
        self.max_energies = tuple(character.max_energy for character in characters)
        self.agility_units = tuple(round(character.agility * 10) for character in characters)
        self.all_masks = tuple(range(1, 1 << len(self.characters)))
        self.symmetry_groups = self._build_symmetry_groups()
        self.agility_sum_by_mask = self._build_agility_sums()
        self.submasks_by_mask = self._build_submasks()

    def _build_symmetry_groups(self) -> tuple[tuple[int, ...], ...]:
        groups: dict[int, list[int]] = {}
        for idx, agility in enumerate(self.agility_units):
            groups.setdefault(agility, []).append(idx)
        return tuple(tuple(indices) for indices in groups.values() if len(indices) > 1)

    def _build_submasks(self) -> dict[int, tuple[int, ...]]:
        submasks_by_mask: dict[int, tuple[int, ...]] = {}
        total_masks = 1 << len(self.characters)

        for mask in range(total_masks):
            submasks = []
            submask = mask
            while submask:
                submasks.append(submask)
                submask = (submask - 1) & mask
            submasks_by_mask[mask] = tuple(
                sorted(
                    submasks,
                    key=lambda current: (
                        -self.agility_sum_by_mask[current],
                        current.bit_count(),
                        current,
                    ),
                )
            )

        return submasks_by_mask

    def _build_agility_sums(self) -> dict[int, int]:
        agility_sum_by_mask: dict[int, int] = {0: 0}
        total_masks = 1 << len(self.characters)
        for mask in range(1, total_masks):
            agility_sum_by_mask[mask] = sum(
                self.agility_units[idx]
                for idx in range(len(self.characters))
                if mask & (1 << idx)
            )
        return agility_sum_by_mask

    def _mask_for_available_characters(self, energies: tuple[int, ...]) -> int:
        mask = 0
        for idx, energy in enumerate(energies):
            if energy > 0:
                mask |= 1 << idx
        return mask

    def _canonicalize(self, energies: tuple[int, ...]) -> tuple[int, ...]:
        energies_list = list(energies)
        for group in self.symmetry_groups:
            ordered = sorted((energies_list[idx] for idx in group), reverse=True)
            for idx, value in zip(group, ordered):
                energies_list[idx] = value
        return tuple(energies_list)

    def _apply_mask(self, energies: tuple[int, ...], mask: int) -> tuple[int, ...]:
        return tuple(
            energy - 1 if mask & (1 << idx) else energy
            for idx, energy in enumerate(energies)
        )

    def _stage_time(self, stage_symbol: str, mask: int) -> float:
        difficulty = self.stage_difficulties[stage_symbol]
        return (difficulty * 10.0) / self.agility_sum_by_mask[mask]

    def _deduplicated_actions(
        self,
        energies: tuple[int, ...],
    ) -> tuple[tuple[int, tuple[int, ...]], ...]:
        available_mask = self._mask_for_available_characters(energies)
        deduplicated_actions: dict[tuple[tuple[int, ...], int], int] = {}

        for mask in self.submasks_by_mask[available_mask]:
            next_energies = self._canonicalize(self._apply_mask(energies, mask))
            signature = (next_energies, self.agility_sum_by_mask[mask])
            deduplicated_actions.setdefault(signature, mask)

        return tuple((mask, next_energies) for (next_energies, _), mask in deduplicated_actions.items())

    def _dominates(self, left: tuple[int, ...], right: tuple[int, ...]) -> bool:
        return all(left_energy >= right_energy for left_energy, right_energy in zip(left, right))

    def _prune_layer(
        self,
        states: dict[tuple[int, ...], float],
        parents: dict[tuple[int, ...], tuple[tuple[int, ...], int]],
    ) -> tuple[dict[tuple[int, ...], float], dict[tuple[int, ...], tuple[tuple[int, ...], int]]]:
        kept: list[tuple[tuple[int, ...], float]] = []
        pruned_states: dict[tuple[int, ...], float] = {}
        pruned_parents: dict[tuple[int, ...], tuple[tuple[int, ...], int]] = {}

        ordered_states = sorted(
            states.items(),
            key=lambda item: (
                item[1],
                -sum(item[0]),
                tuple(-value for value in item[0]),
            ),
        )

        for energies, cost in ordered_states:
            dominated = False
            for kept_energies, kept_cost in kept:
                if kept_cost <= cost + 1e-12 and self._dominates(kept_energies, energies):
                    dominated = True
                    break
            if dominated:
                continue

            still_kept: list[tuple[tuple[int, ...], float]] = []
            for kept_energies, kept_cost in kept:
                if cost <= kept_cost + 1e-12 and self._dominates(energies, kept_energies):
                    pruned_states.pop(kept_energies, None)
                    pruned_parents.pop(kept_energies, None)
                    continue
                still_kept.append((kept_energies, kept_cost))

            kept = still_kept
            kept.append((energies, cost))
            pruned_states[energies] = cost
            pruned_parents[energies] = parents[energies]

        return pruned_states, pruned_parents

    def _optimize_with_milp(self) -> tuple[tuple[StageAssignment, ...], dict[str, int], float]:
        variables_per_stage = len(self.all_masks)
        variable_count = len(self.stage_symbols) * variables_per_stage
        objective = np.zeros(variable_count, dtype=float)
        constraints = lil_matrix((len(self.stage_symbols) + len(self.characters), variable_count), dtype=float)
        lower_bounds = np.zeros(len(self.stage_symbols) + len(self.characters), dtype=float)
        upper_bounds = np.zeros(len(self.stage_symbols) + len(self.characters), dtype=float)

        for stage_idx, stage_symbol in enumerate(self.stage_symbols):
            row = stage_idx
            lower_bounds[row] = 1.0
            upper_bounds[row] = 1.0
            for mask_idx, mask in enumerate(self.all_masks):
                variable_idx = stage_idx * variables_per_stage + mask_idx
                objective[variable_idx] = self._stage_time(stage_symbol, mask)
                constraints[row, variable_idx] = 1.0

        for char_idx, character in enumerate(self.characters):
            row = len(self.stage_symbols) + char_idx
            lower_bounds[row] = 0.0
            upper_bounds[row] = float(character.max_energy)
            for stage_idx, _stage_symbol in enumerate(self.stage_symbols):
                for mask_idx, mask in enumerate(self.all_masks):
                    if mask & (1 << char_idx):
                        variable_idx = stage_idx * variables_per_stage + mask_idx
                        constraints[row, variable_idx] = 1.0

        result = milp(
            c=objective,
            constraints=LinearConstraint(constraints.tocsr(), lower_bounds, upper_bounds),
            integrality=np.ones(variable_count, dtype=int),
            bounds=Bounds(np.zeros(variable_count), np.ones(variable_count)),
            options={"disp": False},
        )

        if not result.success:
            raise ValueError(f"O solver inteiro nÃ£o encontrou soluÃ§Ã£o vÃ¡lida: {result.message}")

        assignments = []
        usage = {name: 0 for name in self.names}
        solution = result.x

        for stage_idx, stage_symbol in enumerate(self.stage_symbols):
            start = stage_idx * variables_per_stage
            end = start + variables_per_stage
            stage_values = solution[start:end]
            chosen_mask_idx = max(
                range(len(stage_values)),
                key=lambda idx: stage_values[idx],
            )
            chosen_mask = self.all_masks[chosen_mask_idx]
            chosen = tuple(self.names[idx] for idx in range(len(self.names)) if chosen_mask & (1 << idx))
            for name in chosen:
                usage[name] += 1
            assignments.append(
                StageAssignment(
                    stage_symbol=stage_symbol,
                    characters=chosen,
                    time_cost=self._stage_time(stage_symbol, chosen_mask),
                )
            )

        total_cost = sum(assignment.time_cost for assignment in assignments)
        return tuple(assignments), usage, total_cost

    def _optimize_with_dynamic_programming(self) -> tuple[tuple[StageAssignment, ...], dict[str, int], float]:
        initial_energies = self._canonicalize(self.max_energies)
        layer_states: dict[tuple[int, ...], float] = {initial_energies: 0.0}
        layer_parents: list[dict[tuple[int, ...], tuple[tuple[int, ...], int]]] = []

        for stage_idx, stage_symbol in enumerate(self.stage_symbols):
            remaining_stage_count = len(self.stage_symbols) - stage_idx - 1
            next_states: dict[tuple[int, ...], float] = {}
            next_parents: dict[tuple[int, ...], tuple[tuple[int, ...], int]] = {}

            for energies, accumulated_cost in layer_states.items():
                if sum(energies) < remaining_stage_count + 1:
                    continue

                for mask, next_energies in self._deduplicated_actions(energies):
                    if sum(next_energies) < remaining_stage_count:
                        continue

                    total_cost = accumulated_cost + self._stage_time(stage_symbol, mask)
                    previous_best = next_states.get(next_energies, float("inf"))
                    if total_cost + 1e-12 < previous_best:
                        next_states[next_energies] = total_cost
                        next_parents[next_energies] = (energies, mask)
                        continue

                    if isclose(total_cost, previous_best, rel_tol=0.0, abs_tol=1e-12):
                        _, previous_mask = next_parents[next_energies]
                        if mask.bit_count() < previous_mask.bit_count():
                            next_parents[next_energies] = (energies, mask)
                        elif mask.bit_count() == previous_mask.bit_count() and mask < previous_mask:
                            next_parents[next_energies] = (energies, mask)

            if not next_states:
                raise ValueError("NÃ£o existe alocaÃ§Ã£o vÃ¡lida de personagens para todas as etapas.")

            pruned_states, pruned_parents = self._prune_layer(next_states, next_parents)
            layer_states = pruned_states
            layer_parents.append(pruned_parents)

        best_final_state, total_cost = min(
            layer_states.items(),
            key=lambda item: (item[1], -sum(item[0]), tuple(-value for value in item[0])),
        )
        if total_cost == float("inf"):
            raise ValueError("NÃ£o existe alocaÃ§Ã£o vÃ¡lida de personagens para todas as etapas.")

        masks: list[int] = []
        current_state = best_final_state
        for parents in reversed(layer_parents):
            previous_state, mask = parents[current_state]
            masks.append(mask)
            current_state = previous_state
        masks.reverse()

        assignments = []
        usage = {name: 0 for name in self.names}
        for stage_symbol, mask in zip(self.stage_symbols, masks):
            chosen = tuple(self.names[idx] for idx in range(len(self.names)) if mask & (1 << idx))
            for name in chosen:
                usage[name] += 1
            assignments.append(
                StageAssignment(
                    stage_symbol=stage_symbol,
                    characters=chosen,
                    time_cost=self._stage_time(stage_symbol, mask),
                )
            )

        return tuple(assignments), usage, total_cost

    def optimize(self) -> tuple[tuple[StageAssignment, ...], dict[str, int], float]:
        if HAS_SCIPY:
            return self._optimize_with_milp()
        return self._optimize_with_dynamic_programming()
