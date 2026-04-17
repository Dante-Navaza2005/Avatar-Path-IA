"""Algoritmo Genetico usado para escolher equipes para cada etapa.

O trabalho pede que o programa escolha combinacoes de personagens respeitando
o limite de energia e minimizando o tempo total das etapas. Neste modulo,
cada individuo do AG representa uma proposta completa de distribuicao de
equipes ao longo da jornada.
"""

from __future__ import annotations

from dataclasses import dataclass
from random import Random

from avatar_path.team_planner_state import PlannerSolution, TeamPlannerState


FLOAT_TOLERANCE = 1e-12
POPULATION_SIZE = 60
GENERATION_COUNT = 400
ELITE_COUNT = 5
TOURNAMENT_SIZE = 3
CROSSOVER_RATE = 0.8
GENE_MUTATION_RATE = 0.03
DEFAULT_RANDOM_SEED = 277


@dataclass(frozen=True)
class GeneticCandidate:
    """Representa uma solucao candidata da parte combinatoria.

    Cada posicao de ``masks`` corresponde a uma etapa da jornada. O valor da
    mascara indica quais personagens foram escolhidos para aquela etapa.
    """

    masks: tuple[int, ...]
    usage: tuple[int, ...]
    total_cost: float


def optimize_with_genetic_algorithm(state: TeamPlannerState) -> PlannerSolution:
    """Executa o AG e devolve a resposta final no formato pedido pelo trabalho.

    O algoritmo opera internamente com mascaras de bits, mas no final a
    resposta volta a conter nomes de personagens e custos por etapa.
    """

    best_candidate = _run_genetic_algorithm(state, DEFAULT_RANDOM_SEED)
    chosen_masks = dict(zip(state.stage_symbols, best_candidate.masks))
    return state.build_assignments(chosen_masks)


def _run_genetic_algorithm(state: TeamPlannerState, seed: int) -> GeneticCandidate:
    """Executa uma rodada completa do AG para a parte combinatoria.

    O fluxo segue a estrutura ensinada em sala:
    populacao inicial, selecao, crossover, mutacao, reparo e nova geracao.
    """

    rng = Random(seed)
    population = _initialize_population(state, rng)
    best_candidate = min(population, key=lambda candidate: candidate.total_cost)

    for _ in range(GENERATION_COUNT):
        population.sort(key=lambda candidate: candidate.total_cost)
        next_population = list(population[:ELITE_COUNT])

        while len(next_population) < POPULATION_SIZE:
            parent_a = _tournament_select(population, rng)
            parent_b = _tournament_select(population, rng)

            if rng.random() < CROSSOVER_RATE:
                child_masks = _uniform_crossover(parent_a.masks, parent_b.masks, rng)
            else:
                child_masks = parent_a.masks if rng.random() < 0.5 else parent_b.masks

            mutated_masks = _mutate(state, child_masks, rng)
            next_population.append(_repair(state, mutated_masks, rng))

        population = next_population
        generation_best = min(population, key=lambda candidate: candidate.total_cost)
        if generation_best.total_cost + FLOAT_TOLERANCE < best_candidate.total_cost:
            best_candidate = generation_best

    return best_candidate


def _initialize_population(
    state: TeamPlannerState,
    rng: Random,
) -> list[GeneticCandidate]:
    """Monta a populacao inicial do AG.

    A populacao comeca com uma semente gulosa e depois recebe individuos
    aleatorios. Isso ajuda os estudantes a enxergar que o AG pode partir de
    um chute razoavel sem deixar de explorar outras possibilidades.
    """

    population = [_build_greedy_seed(state)]

    while len(population) < POPULATION_SIZE:
        random_masks = _random_individual(state, rng)
        population.append(_repair(state, random_masks, rng))

    return population


def _random_individual(
    state: TeamPlannerState,
    rng: Random,
) -> tuple[int, ...]:
    """Gera um individuo aleatorio escolhendo de 1 a 3 personagens por etapa."""

    num_chars = len(state.characters)
    masks: list[int] = []

    for _ in state.stage_symbols:
        chosen_count = 1 + rng.randrange(min(3, num_chars))
        mask = 0
        for char_idx in rng.sample(range(num_chars), chosen_count):
            mask |= 1 << char_idx
        masks.append(mask)

    return tuple(masks)


def _build_greedy_seed(state: TeamPlannerState) -> GeneticCandidate:
    """Cria uma solucao inicial gulosa para orientar a primeira geracao.

    A ideia e simples:
    1. garantir pelo menos um personagem por etapa;
    2. priorizar personagens mais ageis nas etapas mais dificeis;
    3. gastar a energia restante onde o ganho de tempo for maior.
    """

    remaining_energy = list(state.max_energies)
    chosen_mask_by_symbol = {symbol: 0 for symbol in state.stage_symbols}
    chosen_agility_by_symbol = {symbol: 0 for symbol in state.stage_symbols}
    total_assigned_uses = 0

    stages_by_difficulty = sorted(
        state.stage_symbols,
        key=lambda symbol: state.stage_difficulties[symbol],
        reverse=True,
    )

    for stage_symbol in stages_by_difficulty:
        for char_idx in state.character_indices_by_agility:
            if remaining_energy[char_idx] <= 0:
                continue

            chosen_mask_by_symbol[stage_symbol] |= 1 << char_idx
            chosen_agility_by_symbol[stage_symbol] += state.agility_units[char_idx]
            remaining_energy[char_idx] -= 1
            total_assigned_uses += 1
            break
        else:
            raise ValueError("Nao existe alocacao valida de personagens para todas as etapas.")

    while total_assigned_uses < state.usable_energy_budget:
        best_gain = 0.0
        best_stage_symbol: str | None = None
        best_char_idx: int | None = None

        for stage_symbol in state.stage_symbols:
            current_mask = chosen_mask_by_symbol[stage_symbol]
            current_agility = chosen_agility_by_symbol[stage_symbol]
            difficulty = state.stage_difficulties[stage_symbol]

            for char_idx in state.character_indices_by_agility:
                if remaining_energy[char_idx] <= 0:
                    continue
                if current_mask & (1 << char_idx):
                    continue

                next_agility = current_agility + state.agility_units[char_idx]
                current_time = (difficulty * 10.0) / current_agility
                next_time = (difficulty * 10.0) / next_agility
                gain = current_time - next_time

                if gain > best_gain + FLOAT_TOLERANCE:
                    best_gain = gain
                    best_stage_symbol = stage_symbol
                    best_char_idx = char_idx

        if best_stage_symbol is None or best_char_idx is None:
            break

        chosen_mask_by_symbol[best_stage_symbol] |= 1 << best_char_idx
        chosen_agility_by_symbol[best_stage_symbol] += state.agility_units[best_char_idx]
        remaining_energy[best_char_idx] -= 1
        total_assigned_uses += 1

    masks = tuple(chosen_mask_by_symbol[symbol] for symbol in state.stage_symbols)
    usage = state.usage_for_masks(masks)
    return GeneticCandidate(masks=masks, usage=usage, total_cost=_total_cost(state, masks))


def _tournament_select(
    population: list[GeneticCandidate],
    rng: Random,
) -> GeneticCandidate:
    """Seleciona um pai usando torneio entre poucos individuos da populacao."""

    best: GeneticCandidate | None = None

    for _ in range(TOURNAMENT_SIZE):
        candidate = population[rng.randrange(len(population))]
        if best is None or candidate.total_cost < best.total_cost:
            best = candidate

    assert best is not None
    return best


def _uniform_crossover(
    left_masks: tuple[int, ...],
    right_masks: tuple[int, ...],
    rng: Random,
) -> tuple[int, ...]:
    """Combina dois pais escolhendo gene a gene qual mascara sera herdada."""

    child_masks: list[int] = []
    for left_mask, right_mask in zip(left_masks, right_masks):
        child_masks.append(left_mask if rng.random() < 0.5 else right_mask)
    return tuple(child_masks)


def _mutate(
    state: TeamPlannerState,
    masks: tuple[int, ...],
    rng: Random,
) -> tuple[int, ...]:
    """Aplica pequenas alteracoes aleatorias em algumas etapas do cromossomo.

    As mutacoes trabalham sempre dentro de uma representacao simples:
    adicionar, remover, trocar ou mover um personagem entre etapas.
    """

    mutated = list(masks)
    num_chars = len(state.characters)
    num_stages = len(mutated)

    for stage_idx in range(num_stages):
        if rng.random() >= GENE_MUTATION_RATE:
            continue

        mask = mutated[stage_idx]
        present = [idx for idx in range(num_chars) if mask & (1 << idx)]
        absent = [idx for idx in range(num_chars) if not (mask & (1 << idx))]
        action = rng.choice(["add", "remove", "swap", "move", "move"])

        if action == "add" and absent:
            mutated[stage_idx] = mask | (1 << rng.choice(absent))

        elif action == "remove" and len(present) > 1:
            mutated[stage_idx] = mask ^ (1 << rng.choice(present))

        elif action == "swap" and present and absent:
            old_char = rng.choice(present)
            new_char = rng.choice(absent)
            mutated[stage_idx] = (mask ^ (1 << old_char)) | (1 << new_char)

        elif action == "move" and len(present) > 1 and num_stages > 1:
            char_idx = rng.choice(present)
            target_idx = rng.randrange(num_stages - 1)
            if target_idx >= stage_idx:
                target_idx += 1

            char_bit = 1 << char_idx
            if not (mutated[target_idx] & char_bit):
                mutated[stage_idx] = mask ^ char_bit
                mutated[target_idx] |= char_bit

    return tuple(mutated)


def _repair(
    state: TeamPlannerState,
    masks: tuple[int, ...],
    rng: Random,
) -> GeneticCandidate:
    """Repara um cromossomo para que ele volte a ser valido.

    O reparo resolve tres exigencias do enunciado:
    - toda etapa precisa ter pelo menos um personagem;
    - nenhum personagem pode ultrapassar sua energia maxima;
    - se ainda sobrar energia disponivel, ela pode ser usada para reduzir tempo.
    """

    current_masks = list(masks)
    usage = [0] * len(state.characters)

    _ensure_each_stage_has_team(state, current_masks, usage)
    _remove_energy_excess(state, current_masks, usage)
    _spend_remaining_energy(state, current_masks, usage, rng)

    repaired_masks = tuple(current_masks)
    repaired_usage = tuple(usage)
    total_cost = _total_cost(state, repaired_masks)
    return GeneticCandidate(masks=repaired_masks, usage=repaired_usage, total_cost=total_cost)


def _ensure_each_stage_has_team(
    state: TeamPlannerState,
    masks: list[int],
    usage: list[int],
) -> None:
    """Garante que toda etapa tenha ao menos um personagem.

    Isso atende a regra basica do trabalho: nao existe checkpoint com desafio
    sem equipe responsavel por cumpri-lo.
    """

    for stage_idx, mask in enumerate(masks):
        if mask == 0:
            available_chars = [
                idx
                for idx in range(len(state.characters))
                if usage[idx] < state.max_energies[idx]
            ]
            if not available_chars:
                available_chars = list(range(len(state.characters)))

            best_char_idx = max(
                available_chars,
                key=lambda idx: (state.agility_units[idx], -usage[idx]),
            )
            masks[stage_idx] = 1 << best_char_idx

        for char_idx in state.indices_in_mask(masks[stage_idx]):
            usage[char_idx] += 1


def _remove_energy_excess(
    state: TeamPlannerState,
    masks: list[int],
    usage: list[int],
) -> None:
    """Remove excessos de energia substituindo ou retirando personagens.

    A heuristica usada tenta fazer o conserto menos danoso possivel para o
    tempo total, trocando primeiro onde o prejuizo e menor.
    """

    while True:
        overused_chars = [
            idx
            for idx, count in enumerate(usage)
            if count > state.max_energies[idx]
        ]
        if not overused_chars:
            return

        overused_char_idx = max(
            overused_chars,
            key=lambda idx: (
                usage[idx] - state.max_energies[idx],
                state.agility_units[idx],
            ),
        )
        overused_bit = 1 << overused_char_idx
        best_fix: tuple[float, int, int | None] | None = None

        for stage_idx, mask in enumerate(masks):
            if not (mask & overused_bit):
                continue

            current_time = state.stage_time(state.stage_symbols[stage_idx], mask)

            if mask.bit_count() > 1:
                next_mask = mask ^ overused_bit
                delta = state.stage_time(state.stage_symbols[stage_idx], next_mask) - current_time
                candidate_fix = (delta, stage_idx, None)
                if best_fix is None or candidate_fix < best_fix:
                    best_fix = candidate_fix

            for replacement_idx in range(len(state.characters)):
                replacement_bit = 1 << replacement_idx
                if replacement_idx == overused_char_idx:
                    continue
                if usage[replacement_idx] >= state.max_energies[replacement_idx]:
                    continue
                if mask & replacement_bit:
                    continue

                next_mask = (mask ^ overused_bit) | replacement_bit
                delta = state.stage_time(state.stage_symbols[stage_idx], next_mask) - current_time
                candidate_fix = (delta, stage_idx, replacement_idx)
                if best_fix is None or candidate_fix < best_fix:
                    best_fix = candidate_fix

        if best_fix is None:
            for stage_idx, mask in enumerate(masks):
                if (mask & overused_bit) and mask.bit_count() > 1:
                    masks[stage_idx] ^= overused_bit
                    usage[overused_char_idx] -= 1
                    best_fix = (0.0, stage_idx, None)
                    break

        if best_fix is None:
            raise ValueError("Nao foi possivel reparar um cromossomo invalido.")

        _, stage_idx, replacement_idx = best_fix
        masks[stage_idx] ^= overused_bit
        usage[overused_char_idx] -= 1

        if replacement_idx is not None:
            masks[stage_idx] |= 1 << replacement_idx
            usage[replacement_idx] += 1


def _spend_remaining_energy(
    state: TeamPlannerState,
    masks: list[int],
    usage: list[int],
    rng: Random,
) -> None:
    """Usa energia ainda disponivel onde ela mais reduz o tempo total.

    Depois do reparo, pode sobrar energia global. Neste caso o AG completa a
    solucao adicionando personagens em etapas onde o ganho tende a ser maior.
    """

    while sum(usage) < state.usable_energy_budget:
        additions: list[tuple[float, float, int, int]] = []

        for stage_idx, mask in enumerate(masks):
            current_time = state.stage_time(state.stage_symbols[stage_idx], mask)

            for char_idx in range(len(state.characters)):
                char_bit = 1 << char_idx
                if usage[char_idx] >= state.max_energies[char_idx]:
                    continue
                if mask & char_bit:
                    continue

                next_time = state.stage_time(state.stage_symbols[stage_idx], mask | char_bit)
                additions.append((next_time - current_time, rng.random(), stage_idx, char_idx))

        if not additions:
            return

        additions.sort(key=lambda item: (item[0], item[1]))
        best_candidates = min(4, len(additions))
        _, _, stage_idx, char_idx = additions[rng.randrange(best_candidates)]
        masks[stage_idx] |= 1 << char_idx
        usage[char_idx] += 1


def _total_cost(
    state: TeamPlannerState,
    masks: tuple[int, ...],
) -> float:
    """Soma o tempo total das etapas para uma distribuicao completa de equipes."""

    total_cost = 0.0
    for stage_symbol, mask in zip(state.stage_symbols, masks):
        total_cost += state.stage_time(stage_symbol, mask)
    return total_cost
