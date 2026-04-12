from __future__ import annotations

from dataclasses import dataclass

from avatar_path.domain import CharacterConfig, StageAssignment


PlannerSolution = tuple[tuple[StageAssignment, ...], dict[str, int], float]


@dataclass(frozen=True)
class TeamPlannerState:
    characters: tuple[CharacterConfig, ...]
    stage_symbols: tuple[str, ...]
    stage_difficulties: dict[str, int]
    names: tuple[str, ...]
    name_to_index: dict[str, int]
    max_energies: tuple[int, ...]
    usable_energy_budget: int
    agility_units: tuple[int, ...]
    character_indices_by_agility: tuple[int, ...]
    agility_sum_by_mask: dict[int, int]
    character_indices_by_mask: dict[int, tuple[int, ...]]

    def stage_time(self, stage_symbol: str, mask: int) -> float:
        # O trabalho define o tempo como dificuldade dividida pela soma
        # das agilidades do grupo que atravessa aquela etapa.
        difficulty = self.stage_difficulties[stage_symbol]
        return (difficulty * 10.0) / self.agility_sum_by_mask[mask]

    def build_assignments(self, mask_by_symbol: dict[str, int]) -> PlannerSolution:
        assignments: list[StageAssignment] = []
        usage = {name: 0 for name in self.names}

        for stage_symbol in self.stage_symbols:
            mask = mask_by_symbol[stage_symbol]
            chosen = tuple(
                self.names[idx]
                for idx in range(len(self.names))
                if mask & (1 << idx)
            )
            for name in chosen:
                usage[name] += 1
            assignments.append(
                StageAssignment(
                    stage_symbol=stage_symbol,
                    characters=chosen,
                    time_cost=self.stage_time(stage_symbol, mask),
                )
            )

        total_cost = sum(assignment.time_cost for assignment in assignments)
        return tuple(assignments), usage, total_cost

    def masks_from_assignments(
        self,
        assignments: tuple[StageAssignment, ...],
    ) -> tuple[int, ...]:
        masks = []
        for assignment in assignments:
            mask = 0
            for name in assignment.characters:
                mask |= 1 << self.name_to_index[name]
            masks.append(mask)
        return tuple(masks)

    def usage_for_masks(self, masks: tuple[int, ...]) -> tuple[int, ...]:
        usage = [0] * len(self.characters)
        for mask in masks:
            for idx in self.character_indices_by_mask[mask]:
                usage[idx] += 1
        return tuple(usage)


def build_team_planner_state(
    characters: tuple[CharacterConfig, ...],
    ordered_stage_symbols: tuple[str, ...],
    stage_difficulties: dict[str, int],
    reserved_final_energy: int = 0,
) -> TeamPlannerState:
    stage_symbols = tuple(
        symbol
        for symbol in ordered_stage_symbols
        if symbol in stage_difficulties
    )
    names = tuple(character.name for character in characters)
    max_energies = tuple(character.max_energy for character in characters)
    # Multiplicar por 10 preserva a mesma escala das agilidades sem espalhar
    # erro de ponto flutuante na comparacao de subconjuntos.
    agility_units = tuple(round(character.agility * 10) for character in characters)
    usable_energy_budget = sum(max_energies) - reserved_final_energy
    if usable_energy_budget < len(stage_symbols):
        raise ValueError("Nao existe energia suficiente para cobrir todas as etapas.")

    return TeamPlannerState(
        characters=characters,
        stage_symbols=stage_symbols,
        stage_difficulties=stage_difficulties,
        names=names,
        name_to_index={name: idx for idx, name in enumerate(names)},
        max_energies=max_energies,
        usable_energy_budget=usable_energy_budget,
        agility_units=agility_units,
        character_indices_by_agility=tuple(
            sorted(
                range(len(characters)),
                key=lambda idx: (agility_units[idx], names[idx]),
                reverse=True,
            )
        ),
        agility_sum_by_mask=_build_agility_sums(agility_units),
        character_indices_by_mask=_build_character_indices(len(characters)),
    )


def _build_agility_sums(agility_units: tuple[int, ...]) -> dict[int, int]:
    agility_sum_by_mask: dict[int, int] = {0: 0}
    total_masks = 1 << len(agility_units)
    for mask in range(1, total_masks):
        agility_sum_by_mask[mask] = sum(
            agility_units[idx]
            for idx in range(len(agility_units))
            if mask & (1 << idx)
        )
    return agility_sum_by_mask


def _build_character_indices(
    character_count: int,
) -> dict[int, tuple[int, ...]]:
    indices_by_mask: dict[int, tuple[int, ...]] = {0: tuple()}
    total_masks = 1 << character_count
    for mask in range(1, total_masks):
        indices_by_mask[mask] = tuple(
            idx
            for idx in range(character_count)
            if mask & (1 << idx)
        )
    return indices_by_mask
