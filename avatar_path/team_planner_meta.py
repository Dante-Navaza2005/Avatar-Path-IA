"""Metaheuristicas para escolher equipes nas etapas da jornada."""

from __future__ import annotations

from math import exp
from random import Random

from avatar_path.team_planner_state import PlannerSolution, TeamPlannerState


PlannerCandidate = tuple[tuple[int, ...], tuple[int, ...], float]

EPSILON = 1e-12
RANDOM_SEED = 1771
POPULATION_SIZE = 24
GENERATION_COUNT = 20
ELITE_COUNT = 4
TOURNAMENT_SIZE = 3
INITIAL_POPULATION_STEPS = 10
INITIAL_POPULATION_GROWTH = 3
MUTATION_RATE = 0.85
MAX_MUTATION_STEPS = 4
ANNEALING_RESTARTS = 2
ANNEALING_ITERATIONS = 2000
ANNEALING_INITIAL_TEMPERATURE = 35.0
ANNEALING_COOLING_RATE = 0.999
ANNEALING_PERTURBATION_STEPS = 18


def optimize_with_genetic_hill_climbing_simulated_annealing(
    state: TeamPlannerState,
) -> PlannerSolution:
    """Resolve a combinatoria do enunciado usando um pipeline hibrido."""

    greedy_assignments, _, greedy_cost = optimize_with_greedy_balancing(state)
    greedy_masks = state.masks_from_assignments(greedy_assignments)
    greedy_usage = state.usage_for_masks(greedy_masks)
    best_candidate = hill_climb_polish(state, greedy_masks, greedy_usage, greedy_cost)

    genetic_candidate = optimize_with_genetic_algorithm(state, best_candidate)
    if genetic_candidate[2] + EPSILON < best_candidate[2]:
        best_candidate = genetic_candidate

    annealed_candidate = refine_with_simulated_annealing(state, best_candidate)
    if annealed_candidate[2] + EPSILON < best_candidate[2]:
        best_candidate = annealed_candidate

    return state.build_assignments(dict(zip(state.stage_symbols, best_candidate[0])))


def optimize_with_hill_climbing_simulated_annealing(
    state: TeamPlannerState,
) -> PlannerSolution:
    """Mantem o nome antigo da API publica, agora com a etapa genetica incluida."""

    return optimize_with_genetic_hill_climbing_simulated_annealing(state)


def optimize_with_greedy_balancing(
    state: TeamPlannerState,
    stage_symbols: tuple[str, ...] | None = None,
) -> PlannerSolution:
    """Monta uma solucao inicial gulosa para distribuir energia nas etapas."""

    if stage_symbols is None:
        stage_symbols = state.stage_symbols

    remaining_energy = list(state.max_energies)
    chosen_mask_by_symbol = {symbol: 0 for symbol in stage_symbols}
    chosen_agility_by_symbol = {symbol: 0 for symbol in stage_symbols}
    total_assigned_uses = 0

    stages_by_difficulty = sorted(
        stage_symbols,
        key=lambda symbol: state.stage_difficulties[symbol],
        reverse=True,
    )

    # Primeiro garantimos que toda etapa receba pelo menos um personagem.
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

    # Depois usamos a energia restante onde o ganho de tempo for maior.
    while total_assigned_uses < state.usable_energy_budget:
        best_gain = 0.0
        best_stage_symbol: str | None = None
        best_char_idx: int | None = None

        for stage_symbol in stage_symbols:
            current_mask = chosen_mask_by_symbol[stage_symbol]
            current_agility = chosen_agility_by_symbol[stage_symbol]
            difficulty = state.stage_difficulties[stage_symbol]

            for char_idx in state.character_indices_by_agility:
                if remaining_energy[char_idx] <= 0:
                    continue
                if current_mask & (1 << char_idx):
                    continue

                next_agility = current_agility + state.agility_units[char_idx]
                gain = (difficulty * 10.0 / current_agility) - (difficulty * 10.0 / next_agility)
                if gain > best_gain + EPSILON:
                    best_gain = gain
                    best_stage_symbol = stage_symbol
                    best_char_idx = char_idx

        if best_stage_symbol is None or best_char_idx is None:
            break

        chosen_mask_by_symbol[best_stage_symbol] |= 1 << best_char_idx
        chosen_agility_by_symbol[best_stage_symbol] += state.agility_units[best_char_idx]
        remaining_energy[best_char_idx] -= 1
        total_assigned_uses += 1

    return state.build_assignments(chosen_mask_by_symbol)


def optimize_with_genetic_algorithm(
    state: TeamPlannerState,
    base_candidate: PlannerCandidate,
) -> PlannerCandidate:
    """Usa recombinacao e mutacao para escapar de otimos locais da solucao gulosa."""

    rng = Random(RANDOM_SEED)
    population = [base_candidate]
    seen_masks = {base_candidate[0]}
    perturbation_steps = INITIAL_POPULATION_STEPS

    while len(population) < POPULATION_SIZE:
        candidate = _perturb_candidate(state, base_candidate, rng, perturbation_steps)
        candidate = repair_candidate(state, candidate[0], rng)
        candidate = hill_climb_polish(state, *candidate)
        perturbation_steps += INITIAL_POPULATION_GROWTH

        if candidate[0] in seen_masks:
            continue

        population.append(candidate)
        seen_masks.add(candidate[0])

    best_candidate = min(population, key=lambda item: item[2])

    for generation_idx in range(GENERATION_COUNT):
        population.sort(key=lambda item: item[2])
        next_population = list(population[:ELITE_COUNT])
        next_seen_masks = {candidate[0] for candidate in next_population}

        while len(next_population) < POPULATION_SIZE:
            left_parent = _select_parent(population, rng)
            right_parent = _select_parent(population, rng)
            child_masks = _uniform_crossover(left_parent[0], right_parent[0], rng)
            child_candidate = repair_candidate(state, child_masks, rng)

            if rng.random() < MUTATION_RATE:
                mutation_steps = 1 + rng.randrange(MAX_MUTATION_STEPS)
                child_candidate = _perturb_candidate(state, child_candidate, rng, mutation_steps)
                child_candidate = repair_candidate(state, child_candidate[0], rng)

            if generation_idx % 3 == 0 or len(next_population) < ELITE_COUNT * 2:
                child_candidate = hill_climb_polish(state, *child_candidate)

            if child_candidate[0] in next_seen_masks:
                continue

            next_population.append(child_candidate)
            next_seen_masks.add(child_candidate[0])

        population = next_population
        generation_best = min(population, key=lambda item: item[2])
        if generation_best[2] + EPSILON < best_candidate[2]:
            best_candidate = generation_best

    return hill_climb_polish(state, *best_candidate)


def refine_with_simulated_annealing(
    state: TeamPlannerState,
    initial_candidate: PlannerCandidate,
) -> PlannerCandidate:
    """Faz ajustes finos aceitando, ocasionalmente, passos piores para explorar mais."""

    rng = Random(RANDOM_SEED)
    best_candidate = initial_candidate

    for restart_idx in range(ANNEALING_RESTARTS):
        current_candidate = initial_candidate
        if restart_idx > 0:
            steps = ANNEALING_PERTURBATION_STEPS + restart_idx * 4
            current_candidate = _perturb_candidate(state, current_candidate, rng, steps)

        current_masks, current_usage, current_cost = current_candidate
        temperature = ANNEALING_INITIAL_TEMPERATURE

        for _ in range(ANNEALING_ITERATIONS):
            neighbor = sample_neighbor(state, current_masks, current_usage, current_cost, rng)
            if neighbor is None:
                break

            next_masks, next_usage, next_cost = neighbor
            delta = next_cost - current_cost
            if delta <= 0.0 or rng.random() < exp(-delta / temperature):
                current_masks = next_masks
                current_usage = next_usage
                current_cost = next_cost
                if current_cost + EPSILON < best_candidate[2]:
                    best_candidate = (current_masks, current_usage, current_cost)

            temperature *= ANNEALING_COOLING_RATE

        polished_candidate = hill_climb_polish(state, current_masks, current_usage, current_cost)
        if polished_candidate[2] + EPSILON < best_candidate[2]:
            best_candidate = polished_candidate

    return best_candidate


def repair_candidate(
    state: TeamPlannerState,
    masks: tuple[int, ...],
    rng: Random,
) -> PlannerCandidate:
    """Conserta um cromossomo para que ele respeite as regras de energia do enunciado."""

    current_masks = list(masks)
    usage = [0] * len(state.characters)

    # Toda etapa precisa ter pelo menos um personagem.
    for stage_idx, mask in enumerate(current_masks):
        if mask == 0:
            available_chars = tuple(
                idx
                for idx in range(len(state.characters))
                if usage[idx] < state.max_energies[idx]
            )
            if not available_chars:
                available_chars = tuple(range(len(state.characters)))

            best_char_idx = max(
                available_chars,
                key=lambda idx: (state.agility_units[idx], -usage[idx]),
            )
            current_masks[stage_idx] = 1 << best_char_idx

        for char_idx in state.indices_in_mask(current_masks[stage_idx]):
            usage[char_idx] += 1

    # Se algum personagem passou de 8 usos, removemos ou substituimos onde o dano for menor.
    while True:
        overused_chars = [
            idx
            for idx, count in enumerate(usage)
            if count > state.max_energies[idx]
        ]
        if not overused_chars:
            break

        overused_char_idx = max(
            overused_chars,
            key=lambda idx: (
                usage[idx] - state.max_energies[idx],
                state.agility_units[idx],
            ),
        )
        overused_bit = 1 << overused_char_idx
        best_fix: tuple[float, int, int | None] | None = None

        for stage_idx, mask in enumerate(current_masks):
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
            raise ValueError("Nao foi possivel reparar um cromossomo invalido.")

        _, stage_idx, replacement_idx = best_fix
        current_masks[stage_idx] ^= overused_bit
        usage[overused_char_idx] -= 1
        if replacement_idx is not None:
            current_masks[stage_idx] |= 1 << replacement_idx
            usage[replacement_idx] += 1

    # Se ainda sobrar energia global, tentamos aproveita-la onde reduzir mais tempo.
    while sum(usage) < state.usable_energy_budget:
        additions: list[tuple[float, float, int, int]] = []

        for stage_idx, mask in enumerate(current_masks):
            current_time = state.stage_time(state.stage_symbols[stage_idx], mask)
            for char_idx in range(len(state.characters)):
                bit = 1 << char_idx
                if usage[char_idx] >= state.max_energies[char_idx]:
                    continue
                if mask & bit:
                    continue

                next_time = state.stage_time(state.stage_symbols[stage_idx], mask | bit)
                additions.append((next_time - current_time, rng.random(), stage_idx, char_idx))

        if not additions:
            break

        additions.sort(key=lambda item: (item[0], item[1]))
        _, _, stage_idx, char_idx = additions[
            min(len(additions) - 1, rng.randrange(min(4, len(additions))))
        ]
        current_masks[stage_idx] |= 1 << char_idx
        usage[char_idx] += 1

    repaired_masks = tuple(current_masks)
    repaired_usage = tuple(usage)
    repaired_cost = _total_cost_for_masks(state, repaired_masks)
    return repaired_masks, repaired_usage, repaired_cost


def sample_neighbor(
    state: TeamPlannerState,
    masks: tuple[int, ...],
    usage: tuple[int, ...],
    total_cost: float,
    rng: Random,
) -> PlannerCandidate | None:
    """Gera uma solucao vizinha mudando, trocando, adicionando ou removendo personagens."""

    stage_count = len(masks)
    current_total_usage = sum(usage)
    action_kinds = ("move", "move", "swap", "add", "remove")

    for _ in range(96):
        action = action_kinds[rng.randrange(len(action_kinds))]

        if action == "move":
            source_idx = rng.randrange(stage_count)
            source_mask = masks[source_idx]
            source_chars = state.indices_in_mask(source_mask)
            if len(source_chars) <= 1:
                continue

            char_idx = source_chars[rng.randrange(len(source_chars))]
            bit = 1 << char_idx
            target_idx = rng.randrange(stage_count - 1)
            if target_idx >= source_idx:
                target_idx += 1

            target_mask = masks[target_idx]
            if target_mask & bit:
                continue

            next_masks = list(masks)
            next_masks[source_idx] = source_mask ^ bit
            next_masks[target_idx] = target_mask | bit

            next_cost = (
                total_cost
                - state.stage_time(state.stage_symbols[source_idx], source_mask)
                - state.stage_time(state.stage_symbols[target_idx], target_mask)
                + state.stage_time(state.stage_symbols[source_idx], next_masks[source_idx])
                + state.stage_time(state.stage_symbols[target_idx], next_masks[target_idx])
            )
            return tuple(next_masks), usage, next_cost

        if action == "swap":
            left_idx = rng.randrange(stage_count)
            right_idx = rng.randrange(stage_count - 1)
            if right_idx >= left_idx:
                right_idx += 1

            left_mask = masks[left_idx]
            right_mask = masks[right_idx]
            left_options = tuple(
                idx
                for idx in state.indices_in_mask(left_mask)
                if not (right_mask & (1 << idx))
            )
            right_options = tuple(
                idx
                for idx in state.indices_in_mask(right_mask)
                if not (left_mask & (1 << idx))
            )
            if not left_options or not right_options:
                continue

            left_char_idx = left_options[rng.randrange(len(left_options))]
            right_char_idx = right_options[rng.randrange(len(right_options))]
            left_bit = 1 << left_char_idx
            right_bit = 1 << right_char_idx

            next_masks = list(masks)
            next_masks[left_idx] = (left_mask ^ left_bit) | right_bit
            next_masks[right_idx] = (right_mask ^ right_bit) | left_bit

            next_cost = (
                total_cost
                - state.stage_time(state.stage_symbols[left_idx], left_mask)
                - state.stage_time(state.stage_symbols[right_idx], right_mask)
                + state.stage_time(state.stage_symbols[left_idx], next_masks[left_idx])
                + state.stage_time(state.stage_symbols[right_idx], next_masks[right_idx])
            )
            return tuple(next_masks), usage, next_cost

        if action == "add":
            if current_total_usage >= state.usable_energy_budget:
                continue

            stage_idx = rng.randrange(stage_count)
            stage_mask = masks[stage_idx]
            available_chars = tuple(
                idx
                for idx in range(len(state.characters))
                if usage[idx] < state.max_energies[idx] and not (stage_mask & (1 << idx))
            )
            if not available_chars:
                continue

            char_idx = available_chars[rng.randrange(len(available_chars))]
            bit = 1 << char_idx
            next_masks = list(masks)
            next_masks[stage_idx] = stage_mask | bit
            next_usage = list(usage)
            next_usage[char_idx] += 1
            next_cost = (
                total_cost
                - state.stage_time(state.stage_symbols[stage_idx], stage_mask)
                + state.stage_time(state.stage_symbols[stage_idx], next_masks[stage_idx])
            )
            return tuple(next_masks), tuple(next_usage), next_cost

        stage_idx = rng.randrange(stage_count)
        stage_mask = masks[stage_idx]
        stage_chars = state.indices_in_mask(stage_mask)
        if len(stage_chars) <= 1:
            continue

        char_idx = stage_chars[rng.randrange(len(stage_chars))]
        bit = 1 << char_idx
        next_masks = list(masks)
        next_masks[stage_idx] = stage_mask ^ bit
        next_usage = list(usage)
        next_usage[char_idx] -= 1
        next_cost = (
            total_cost
            - state.stage_time(state.stage_symbols[stage_idx], stage_mask)
            + state.stage_time(state.stage_symbols[stage_idx], next_masks[stage_idx])
        )
        return tuple(next_masks), tuple(next_usage), next_cost

    return None


def hill_climb_polish(
    state: TeamPlannerState,
    masks: tuple[int, ...],
    usage: tuple[int, ...],
    total_cost: float,
) -> PlannerCandidate:
    """Aplica melhorias locais ate a solucao estabilizar."""

    current_masks = list(masks)
    current_usage = list(usage)
    current_cost = total_cost

    while True:
        best_delta = -EPSILON
        best_move: tuple[str, int, int, int | None] | None = None
        current_total_usage = sum(current_usage)

        for stage_idx, stage_mask in enumerate(current_masks):
            if current_total_usage >= state.usable_energy_budget:
                break

            current_time = state.stage_time(state.stage_symbols[stage_idx], stage_mask)
            for char_idx in range(len(state.characters)):
                bit = 1 << char_idx
                if current_usage[char_idx] >= state.max_energies[char_idx]:
                    continue
                if stage_mask & bit:
                    continue

                delta = state.stage_time(state.stage_symbols[stage_idx], stage_mask | bit) - current_time
                if delta < best_delta:
                    best_delta = delta
                    best_move = ("add", stage_idx, char_idx, None)

        for source_idx, source_mask in enumerate(current_masks):
            source_chars = state.indices_in_mask(source_mask)
            if len(source_chars) <= 1:
                continue

            source_time = state.stage_time(state.stage_symbols[source_idx], source_mask)
            for target_idx, target_mask in enumerate(current_masks):
                if source_idx == target_idx:
                    continue

                target_time = state.stage_time(state.stage_symbols[target_idx], target_mask)
                for char_idx in source_chars:
                    bit = 1 << char_idx
                    if target_mask & bit:
                        continue

                    delta = (
                        state.stage_time(state.stage_symbols[source_idx], source_mask ^ bit)
                        + state.stage_time(state.stage_symbols[target_idx], target_mask | bit)
                        - source_time
                        - target_time
                    )
                    if delta < best_delta:
                        best_delta = delta
                        best_move = ("move", source_idx, target_idx, char_idx)

        for left_idx, left_mask in enumerate(current_masks):
            left_chars = state.indices_in_mask(left_mask)
            left_time = state.stage_time(state.stage_symbols[left_idx], left_mask)

            for right_idx in range(left_idx + 1, len(current_masks)):
                right_mask = current_masks[right_idx]
                right_chars = state.indices_in_mask(right_mask)
                right_time = state.stage_time(state.stage_symbols[right_idx], right_mask)

                left_only = tuple(idx for idx in left_chars if not (right_mask & (1 << idx)))
                right_only = tuple(idx for idx in right_chars if not (left_mask & (1 << idx)))
                if not left_only or not right_only:
                    continue

                for left_char_idx in left_only:
                    left_bit = 1 << left_char_idx
                    for right_char_idx in right_only:
                        right_bit = 1 << right_char_idx
                        delta = (
                            state.stage_time(state.stage_symbols[left_idx], (left_mask ^ left_bit) | right_bit)
                            + state.stage_time(state.stage_symbols[right_idx], (right_mask ^ right_bit) | left_bit)
                            - left_time
                            - right_time
                        )
                        if delta < best_delta:
                            best_delta = delta
                            packed_chars = (left_char_idx << 8) | right_char_idx
                            best_move = ("swap", left_idx, right_idx, packed_chars)

        if best_move is None:
            return tuple(current_masks), tuple(current_usage), current_cost

        move_type, first_idx, second_idx, payload = best_move
        if move_type == "add":
            current_masks[first_idx] |= 1 << second_idx
            current_usage[second_idx] += 1
        elif move_type == "move":
            assert payload is not None
            bit = 1 << payload
            current_masks[first_idx] ^= bit
            current_masks[second_idx] |= bit
        else:
            assert payload is not None
            left_char_idx = payload >> 8
            right_char_idx = payload & 0xFF
            left_bit = 1 << left_char_idx
            right_bit = 1 << right_char_idx
            current_masks[first_idx] = (current_masks[first_idx] ^ left_bit) | right_bit
            current_masks[second_idx] = (current_masks[second_idx] ^ right_bit) | left_bit

        current_cost += best_delta


def _perturb_candidate(
    state: TeamPlannerState,
    candidate: PlannerCandidate,
    rng: Random,
    steps: int,
) -> PlannerCandidate:
    """Aplica alguns vizinhos aleatorios para diversificar uma solucao."""

    current_masks, current_usage, current_cost = candidate

    for _ in range(steps):
        neighbor = sample_neighbor(state, current_masks, current_usage, current_cost, rng)
        if neighbor is None:
            break
        current_masks, current_usage, current_cost = neighbor

    return current_masks, current_usage, current_cost


def _select_parent(
    population: list[PlannerCandidate],
    rng: Random,
) -> PlannerCandidate:
    """Escolhe um pai pelo esquema de torneio, simples e didatico."""

    best_candidate: PlannerCandidate | None = None
    for _ in range(TOURNAMENT_SIZE):
        candidate = population[rng.randrange(len(population))]
        if best_candidate is None or candidate[2] < best_candidate[2]:
            best_candidate = candidate
    assert best_candidate is not None
    return best_candidate


def _uniform_crossover(
    left_masks: tuple[int, ...],
    right_masks: tuple[int, ...],
    rng: Random,
) -> tuple[int, ...]:
    """Monta um filho escolhendo, etapa a etapa, um dos dois pais."""

    return tuple(
        left_mask if rng.random() < 0.5 else right_mask
        for left_mask, right_mask in zip(left_masks, right_masks)
    )


def _total_cost_for_masks(
    state: TeamPlannerState,
    masks: tuple[int, ...],
) -> float:
    """Soma o tempo total de uma distribuicao de equipes."""

    return sum(
        state.stage_time(stage_symbol, mask)
        for stage_symbol, mask in zip(state.stage_symbols, masks)
    )
