"""Preparacao dos dados usados pela etapa combinatoria do trabalho.

O objetivo deste modulo e deixar pronta toda a informacao fixa da parte de
equipes, para que o algoritmo genetico trabalhe apenas com escolhas.
"""

from __future__ import annotations

from dataclasses import dataclass

from avatar_path.domain import CharacterConfig, StageAssignment


PlannerSolution = tuple[tuple[StageAssignment, ...], dict[str, int], float]


@dataclass(frozen=True)
class TeamPlannerState:
    """Guarda os dados fixos usados para montar equipes em cada etapa.

    Esta estrutura evita recalcular nomes, indices, agilidades e somas de
    subconjuntos toda vez que o algoritmo avalia uma solucao candidata.
    """

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

    def stage_time(self, stage_symbol: str, mask: int) -> float:
        """Calcula o tempo da etapa com base na formula do enunciado."""

        difficulty = self.stage_difficulties[stage_symbol]
        return (difficulty * 10.0) / self.agility_sum_by_mask[mask]

    def indices_in_mask(self, mask: int) -> tuple[int, ...]:
        """Traduz uma mascara de bits nos personagens escolhidos para a etapa."""

        indices: list[int] = []
        for idx in range(len(self.characters)):
            if mask & (1 << idx):
                indices.append(idx)
        return tuple(indices)

    def build_assignments(self, mask_by_symbol: dict[str, int]) -> PlannerSolution:
        """Converte mascaras de bits na resposta final legivel do trabalho.

        O algoritmo genetico trabalha com mascaras porque elas sao praticas
        para combinar personagens. Aqui fazemos o caminho inverso para gerar
        nomes, usos e custo total da solucao final.
        """

        assignments: list[StageAssignment] = []
        usage = {name: 0 for name in self.names}

        for stage_symbol in self.stage_symbols:
            chosen_indices = self.indices_in_mask(mask_by_symbol[stage_symbol])
            chosen_names = tuple(self.names[idx] for idx in chosen_indices)

            for name in chosen_names:
                usage[name] += 1

            assignments.append(
                StageAssignment(
                    stage_symbol=stage_symbol,
                    characters=chosen_names,
                    time_cost=self.stage_time(stage_symbol, mask_by_symbol[stage_symbol]),
                )
            )

        total_cost = sum(assignment.time_cost for assignment in assignments)
        return tuple(assignments), usage, total_cost

    def usage_for_masks(self, masks: tuple[int, ...]) -> tuple[int, ...]:
        """Conta quanta energia cada personagem gastou em uma solucao candidata."""

        usage = [0] * len(self.characters)
        for mask in masks:
            for idx in self.indices_in_mask(mask):
                usage[idx] += 1
        return tuple(usage)


def build_team_planner_state(
    characters: tuple[CharacterConfig, ...],
    ordered_stage_symbols: tuple[str, ...],
    stage_difficulties: dict[str, int],
    reserved_final_energy: int = 0,
) -> TeamPlannerState:
    """Prepara os dados fixos da combinatoria antes da otimizacao.

    Esta funcao separa a parte estatica do problema:
    - quais etapas tem dificuldade;
    - quantas vezes cada personagem pode atuar;
    - qual e a soma de agilidade de cada subconjunto possivel.
    """

    stage_symbols = tuple(
        symbol
        for symbol in ordered_stage_symbols
        if symbol in stage_difficulties
    )
    names = tuple(character.name for character in characters)
    max_energies = tuple(character.max_energy for character in characters)

    # Multiplicar a agilidade por 10 evita ruido de ponto flutuante e preserva
    # a escala usada na formula do enunciado.
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
    )


def _build_agility_sums(agility_units: tuple[int, ...]) -> dict[int, int]:
    """Precalcula a soma de agilidade de todos os subconjuntos possiveis.

    Como o numero de personagens e pequeno, vale a pena montar essa tabela uma
    unica vez e reutiliza-la ao longo de toda a busca.
    """

    agility_sum_by_mask: dict[int, int] = {0: 0}
    total_masks = 1 << len(agility_units)

    for mask in range(1, total_masks):
        agility_sum = 0
        for idx in range(len(agility_units)):
            if mask & (1 << idx):
                agility_sum += agility_units[idx]
        agility_sum_by_mask[mask] = agility_sum

    return agility_sum_by_mask
