from __future__ import annotations

from math import exp
from random import Random

from avatar_path.team_planner_state import PlannerSolution, TeamPlannerState


PlannerCandidate = tuple[tuple[int, ...], tuple[int, ...], float]

EPSILON = 1e-12

GENETIC_SEEDS = (1771,)
GENETIC_POPULATION_SIZE = 24
GENETIC_GENERATIONS = 20
GENETIC_ELITE_COUNT = 4
GENETIC_TOURNAMENT_SIZE = 3
GENETIC_MUTATION_RATE = 0.85
GENETIC_MUTATION_MAX_STEPS = 4
GENETIC_INITIAL_PERTURBATION_STEPS = 10
GENETIC_PERTURBATION_GROWTH = 3

ANNEALING_SEEDS = (1771,)
ANNEALING_RESTARTS = 2
ANNEALING_ITERATIONS_PER_RESTART = 2000
INITIAL_TEMPERATURE = 35.0
COOLING_RATE = 0.999
PERTURBATION_STEPS = 18


def optimize_with_genetic_hill_climbing_simulated_annealing(
    state: TeamPlannerState,
) -> PlannerSolution:
    # O pipeline agora combina populacao, recombinacao e busca local:
    # o genetico amplia a exploracao e o hill climbing faz o acabamento.
    greedy_assignments, _, greedy_cost = optimize_with_greedy_balancing(state)
    greedy_masks = state.masks_from_assignments(greedy_assignments)
    greedy_usage = state.usage_for_masks(greedy_masks)
    best_candidate = hill_climb_polish(
        state,
        greedy_masks,
        greedy_usage,
        greedy_cost,
    )

    genetic_candidate = optimize_with_genetic_algorithm(state, best_candidate)
    if genetic_candidate[2] + EPSILON < best_candidate[2]:
        best_candidate = genetic_candidate

    annealed_candidate = refine_with_simulated_annealing(state, best_candidate)
    if annealed_candidate[2] + EPSILON < best_candidate[2]:
        best_candidate = annealed_candidate

    return _build_solution(state, best_candidate)


def optimize_with_hill_climbing_simulated_annealing(
    state: TeamPlannerState,
) -> PlannerSolution:
    return optimize_with_genetic_hill_climbing_simulated_annealing(state)


def optimize_with_genetic_algorithm(
    state: TeamPlannerState,
    base_candidate: PlannerCandidate,
) -> PlannerCandidate:
    best_candidate = base_candidate

    for seed in GENETIC_SEEDS:
        rng = Random(seed)
        population = _build_initial_population(state, base_candidate, rng)

        for generation_idx in range(GENETIC_GENERATIONS):
            population.sort(key=lambda item: item[2])
            next_population = list(population[:GENETIC_ELITE_COUNT])
            seen_masks = {candidate[0] for candidate in next_population}

            while len(next_population) < GENETIC_POPULATION_SIZE:
                left_parent = _select_parent(population, rng)
                right_parent = _select_parent(population, rng)
                child_masks = _uniform_crossover(left_parent[0], right_parent[0], rng)
                child_candidate = repair_candidate(state, child_masks, rng)

                if rng.random() < GENETIC_MUTATION_RATE:
                    child_candidate = _perturb_candidate(
                        state,
                        child_candidate,
                        rng,
                        1 + rng.randrange(GENETIC_MUTATION_MAX_STEPS),
                    )
                    child_candidate = repair_candidate(state, child_candidate[0], rng)

                if generation_idx % 3 == 0 or len(next_population) < GENETIC_ELITE_COUNT * 2:
                    child_candidate = hill_climb_polish(state, *child_candidate)

                if child_candidate[0] in seen_masks:
                    continue

                next_population.append(child_candidate)
                seen_masks.add(child_candidate[0])

            population = next_population

        candidate = min(population, key=lambda item: item[2])
        candidate = hill_climb_polish(state, *candidate)
        if candidate[2] + EPSILON < best_candidate[2]:
            best_candidate = candidate

    return best_candidate


def refine_with_simulated_annealing(
    state: TeamPlannerState,
    initial_candidate: PlannerCandidate,
) -> PlannerCandidate:
    best_candidate = initial_candidate

    for seed in ANNEALING_SEEDS:
        rng = Random(seed)
        for restart_idx in range(ANNEALING_RESTARTS):
            current_candidate = initial_candidate
            if restart_idx > 0:
                current_candidate = _perturb_candidate(
                    state,
                    current_candidate,
                    rng,
                    PERTURBATION_STEPS + restart_idx * 4,
                )

            current_masks, current_usage, current_cost = current_candidate
            temperature = INITIAL_TEMPERATURE

            for _ in range(ANNEALING_ITERATIONS_PER_RESTART):
                neighbor = sample_neighbor(
                    state,
                    current_masks,
                    current_usage,
                    current_cost,
                    rng,
                )
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

                temperature *= COOLING_RATE

            polished_candidate = hill_climb_polish(
                state,
                current_masks,
                current_usage,
                current_cost,
            )
            if polished_candidate[2] + EPSILON < best_candidate[2]:
                best_candidate = polished_candidate

    return best_candidate


def optimize_with_greedy_balancing(
    state: TeamPlannerState,
    stage_symbols: tuple[str, ...] | None = None,
) -> PlannerSolution:
    if stage_symbols is None:
        stage_symbols = state.stage_symbols

    remaining_energy = list(state.max_energies)
    chosen_mask_by_symbol = {symbol: 0 for symbol in stage_symbols}
    chosen_agility_by_symbol = {symbol: 0 for symbol in stage_symbols}
    total_assigned_uses = 0

    stage_indices_by_difficulty = sorted(
        stage_symbols,
        key=lambda symbol: state.stage_difficulties[symbol],
        reverse=True,
    )
    character_indices_by_agility = state.character_indices_by_agility

    for stage_symbol in stage_indices_by_difficulty:
        for char_idx in character_indices_by_agility:
            if remaining_energy[char_idx] <= 0:
                continue
            chosen_mask_by_symbol[stage_symbol] |= 1 << char_idx
            chosen_agility_by_symbol[stage_symbol] += state.agility_units[char_idx]
            remaining_energy[char_idx] -= 1
            total_assigned_uses += 1
            break
        else:
            raise ValueError("Nao existe alocacao valida de personagens para todas as etapas.")

    while True:
        if total_assigned_uses >= state.usable_energy_budget:
            break

        best_gain = 0.0
        best_stage_idx = -1
        best_char_idx = -1

        for stage_symbol in stage_symbols:
            current_agility = chosen_agility_by_symbol[stage_symbol]
            current_mask = chosen_mask_by_symbol[stage_symbol]
            difficulty = state.stage_difficulties[stage_symbol]

            for char_idx in character_indices_by_agility:
                if remaining_energy[char_idx] <= 0:
                    continue
                if current_mask & (1 << char_idx):
                    continue

                # O ganho mede quanto o tempo daquela etapa cai ao incluir
                # mais um personagem na equipe atual.
                next_agility = current_agility + state.agility_units[char_idx]
                gain = (difficulty * 10.0 / current_agility) - (difficulty * 10.0 / next_agility)
                if gain > best_gain + EPSILON:
                    best_gain = gain
                    best_stage_idx = stage_symbol
                    best_char_idx = char_idx

        if best_stage_idx == -1:
            break

        chosen_mask_by_symbol[best_stage_idx] |= 1 << best_char_idx
        chosen_agility_by_symbol[best_stage_idx] += state.agility_units[best_char_idx]
        remaining_energy[best_char_idx] -= 1
        total_assigned_uses += 1

    return state.build_assignments(chosen_mask_by_symbol)


def repair_candidate(
    state: TeamPlannerState,
    masks: tuple[int, ...],
    rng: Random,
) -> PlannerCandidate:
    current_masks = list(masks)
    character_count = len(state.characters)
    usage = [0] * character_count

    for stage_idx, mask in enumerate(current_masks):
        if mask == 0:
            available_chars = tuple(
                idx
                for idx in range(character_count)
                if usage[idx] < state.max_energies[idx]
            )
            if not available_chars:
                available_chars = tuple(range(character_count))

            best_char_idx = max(
                available_chars,
                key=lambda idx: (state.agility_units[idx], -usage[idx]),
            )
            current_masks[stage_idx] = 1 << best_char_idx

        for char_idx in state.character_indices_by_mask[current_masks[stage_idx]]:
            usage[char_idx] += 1

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

            current_cost = state.stage_time(state.stage_symbols[stage_idx], mask)

            if mask.bit_count() > 1:
                next_mask = mask ^ overused_bit
                remove_delta = (
                    state.stage_time(state.stage_symbols[stage_idx], next_mask)
                    - current_cost
                )
                candidate_fix = (remove_delta, stage_idx, None)
                if best_fix is None or candidate_fix < best_fix:
                    best_fix = candidate_fix

            for replacement_idx in range(character_count):
                replacement_bit = 1 << replacement_idx
                if replacement_idx == overused_char_idx:
                    continue
                if usage[replacement_idx] >= state.max_energies[replacement_idx]:
                    continue
                if mask & replacement_bit:
                    continue

                next_mask = (mask ^ overused_bit) | replacement_bit
                replace_delta = (
                    state.stage_time(state.stage_symbols[stage_idx], next_mask)
                    - current_cost
                )
                candidate_fix = (replace_delta, stage_idx, replacement_idx)
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

    total_usage = sum(usage)
    while total_usage < state.usable_energy_budget:
        best_additions: list[tuple[float, float, int, int]] = []

        for stage_idx, mask in enumerate(current_masks):
            current_cost = state.stage_time(state.stage_symbols[stage_idx], mask)

            for char_idx in range(character_count):
                bit = 1 << char_idx
                if usage[char_idx] >= state.max_energies[char_idx]:
                    continue
                if mask & bit:
                    continue

                delta = (
                    state.stage_time(state.stage_symbols[stage_idx], mask | bit)
                    - current_cost
                )
                best_additions.append((delta, rng.random(), stage_idx, char_idx))

        if not best_additions:
            break

        best_additions.sort(key=lambda item: (item[0], item[1]))
        delta, _, stage_idx, char_idx = best_additions[
            min(len(best_additions) - 1, rng.randrange(min(4, len(best_additions))))
        ]
        if delta > EPSILON:
            break

        current_masks[stage_idx] |= 1 << char_idx
        usage[char_idx] += 1
        total_usage += 1

    repaired_masks = tuple(current_masks)
    repaired_usage = tuple(usage)
    return repaired_masks, repaired_usage, _total_cost_for_masks(state, repaired_masks)


def sample_neighbor(
    state: TeamPlannerState,
    masks: tuple[int, ...],
    usage: tuple[int, ...],
    total_cost: float,
    rng: Random,
) -> PlannerCandidate | None:
    stage_count = len(masks)
    # "move" aparece duas vezes de proposito porque costuma gerar vizinhos
    # melhores do que add/remove em menos passos.
    action_kinds = ("move", "move", "swap", "add", "remove")
    current_total_usage = sum(usage)

    for _ in range(96):
        action = action_kinds[rng.randrange(len(action_kinds))]

        if action == "move":
            source_idx = rng.randrange(stage_count)
            source_mask = masks[source_idx]
            source_chars = state.character_indices_by_mask[source_mask]
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

            updated_cost = (
                total_cost
                - state.stage_time(state.stage_symbols[source_idx], source_mask)
                - state.stage_time(state.stage_symbols[target_idx], target_mask)
                + state.stage_time(state.stage_symbols[source_idx], next_masks[source_idx])
                + state.stage_time(state.stage_symbols[target_idx], next_masks[target_idx])
            )
            return tuple(next_masks), usage, updated_cost

        if action == "swap":
            left_idx = rng.randrange(stage_count)
            right_idx = rng.randrange(stage_count - 1)
            if right_idx >= left_idx:
                right_idx += 1

            left_mask = masks[left_idx]
            right_mask = masks[right_idx]
            left_options = tuple(
                idx
                for idx in state.character_indices_by_mask[left_mask]
                if not (right_mask & (1 << idx))
            )
            right_options = tuple(
                idx
                for idx in state.character_indices_by_mask[right_mask]
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

            updated_cost = (
                total_cost
                - state.stage_time(state.stage_symbols[left_idx], left_mask)
                - state.stage_time(state.stage_symbols[right_idx], right_mask)
                + state.stage_time(state.stage_symbols[left_idx], next_masks[left_idx])
                + state.stage_time(state.stage_symbols[right_idx], next_masks[right_idx])
            )
            return tuple(next_masks), usage, updated_cost

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
            updated_cost = (
                total_cost
                - state.stage_time(state.stage_symbols[stage_idx], stage_mask)
                + state.stage_time(state.stage_symbols[stage_idx], next_masks[stage_idx])
            )
            return tuple(next_masks), tuple(next_usage), updated_cost

        stage_idx = rng.randrange(stage_count)
        stage_mask = masks[stage_idx]
        stage_chars = state.character_indices_by_mask[stage_mask]
        if len(stage_chars) <= 1:
            continue

        char_idx = stage_chars[rng.randrange(len(stage_chars))]
        bit = 1 << char_idx
        next_masks = list(masks)
        next_masks[stage_idx] = stage_mask ^ bit
        next_usage = list(usage)
        next_usage[char_idx] -= 1
        updated_cost = (
            total_cost
            - state.stage_time(state.stage_symbols[stage_idx], stage_mask)
            + state.stage_time(state.stage_symbols[stage_idx], next_masks[stage_idx])
        )
        return tuple(next_masks), tuple(next_usage), updated_cost

    return None


def hill_climb_polish(
    state: TeamPlannerState,
    masks: tuple[int, ...],
    usage: tuple[int, ...],
    total_cost: float,
) -> PlannerCandidate:
    current_masks = list(masks)
    current_usage = list(usage)
    current_cost = total_cost
    stage_count = len(current_masks)
    character_count = len(state.characters)

    while True:
        best_delta = -EPSILON
        best_move: tuple[str, int, int, int | None] | None = None
        current_total_usage = sum(current_usage)

        # Primeiro tentamos adicionar energia onde ainda exista folga global.
        for stage_idx, stage_mask in enumerate(current_masks):
            stage_cost = state.stage_time(state.stage_symbols[stage_idx], stage_mask)

            if current_total_usage >= state.usable_energy_budget:
                continue

            for char_idx in range(character_count):
                bit = 1 << char_idx
                if current_usage[char_idx] >= state.max_energies[char_idx] or stage_mask & bit:
                    continue

                delta = state.stage_time(state.stage_symbols[stage_idx], stage_mask | bit) - stage_cost
                if delta < best_delta:
                    best_delta = delta
                    best_move = ("add", stage_idx, char_idx, None)

        for source_idx, source_mask in enumerate(current_masks):
            source_chars = state.character_indices_by_mask[source_mask]
            if len(source_chars) <= 1:
                continue

            source_cost = state.stage_time(state.stage_symbols[source_idx], source_mask)
            for target_idx, target_mask in enumerate(current_masks):
                if source_idx == target_idx:
                    continue

                target_cost = state.stage_time(state.stage_symbols[target_idx], target_mask)
                for char_idx in source_chars:
                    bit = 1 << char_idx
                    if target_mask & bit:
                        continue

                    delta = (
                        state.stage_time(state.stage_symbols[source_idx], source_mask ^ bit)
                        + state.stage_time(state.stage_symbols[target_idx], target_mask | bit)
                        - source_cost
                        - target_cost
                    )
                    if delta < best_delta:
                        best_delta = delta
                        best_move = ("move", source_idx, target_idx, char_idx)

        for left_idx, left_mask in enumerate(current_masks):
            left_cost = state.stage_time(state.stage_symbols[left_idx], left_mask)
            left_chars = state.character_indices_by_mask[left_mask]
            for right_idx in range(left_idx + 1, stage_count):
                right_mask = current_masks[right_idx]
                right_cost = state.stage_time(state.stage_symbols[right_idx], right_mask)
                right_chars = state.character_indices_by_mask[right_mask]

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
                            - left_cost
                            - right_cost
                        )
                        if delta < best_delta:
                            best_delta = delta
                            best_move = ("swap", left_idx, right_idx, (left_char_idx << 8) | right_char_idx)

        if best_move is None:
            return tuple(current_masks), tuple(current_usage), current_cost

        # Depois de escolher o melhor delta disponivel, aplicamos a alteracao
        # diretamente na solucao atual e repetimos ate estabilizar.
        move_type, first_idx, second_idx, payload = best_move
        if move_type == "move":
            assert payload is not None
            bit = 1 << payload
            current_masks[first_idx] ^= bit
            current_masks[second_idx] |= bit
        elif move_type == "swap":
            assert payload is not None
            left_char_idx = payload >> 8
            right_char_idx = payload & 0xFF
            left_bit = 1 << left_char_idx
            right_bit = 1 << right_char_idx
            current_masks[first_idx] = (current_masks[first_idx] ^ left_bit) | right_bit
            current_masks[second_idx] = (current_masks[second_idx] ^ right_bit) | left_bit
        else:
            current_masks[first_idx] |= 1 << second_idx
            current_usage[second_idx] += 1

        current_cost += best_delta


def _build_initial_population(
    state: TeamPlannerState,
    base_candidate: PlannerCandidate,
    rng: Random,
) -> list[PlannerCandidate]:
    population = [base_candidate]
    seen_masks = {base_candidate[0]}
    seed_idx = 0

    while len(population) < GENETIC_POPULATION_SIZE:
        candidate = _perturb_candidate(
            state,
            base_candidate,
            rng,
            GENETIC_INITIAL_PERTURBATION_STEPS + seed_idx * GENETIC_PERTURBATION_GROWTH,
        )
        candidate = repair_candidate(state, candidate[0], rng)
        candidate = hill_climb_polish(state, *candidate)
        seed_idx += 1

        if candidate[0] in seen_masks:
            continue

        population.append(candidate)
        seen_masks.add(candidate[0])

    return population


def _build_solution(
    state: TeamPlannerState,
    candidate: PlannerCandidate,
) -> PlannerSolution:
    return state.build_assignments(dict(zip(state.stage_symbols, candidate[0])))


def _perturb_candidate(
    state: TeamPlannerState,
    candidate: PlannerCandidate,
    rng: Random,
    steps: int,
) -> PlannerCandidate:
    current_masks, current_usage, current_cost = candidate

    for _ in range(steps):
        neighbor = sample_neighbor(
            state,
            current_masks,
            current_usage,
            current_cost,
            rng,
        )
        if neighbor is None:
            break
        current_masks, current_usage, current_cost = neighbor

    return current_masks, current_usage, current_cost


def _select_parent(
    population: list[PlannerCandidate],
    rng: Random,
) -> PlannerCandidate:
    best_candidate: PlannerCandidate | None = None
    for _ in range(GENETIC_TOURNAMENT_SIZE):
        candidate = population[rng.randrange(len(population))]
        if best_candidate is None or candidate[2] < best_candidate[2]:
            best_candidate = candidate
    assert best_candidate is not None
    return best_candidate


def _total_cost_for_masks(
    state: TeamPlannerState,
    masks: tuple[int, ...],
) -> float:
    return sum(
        state.stage_time(stage_symbol, mask)
        for stage_symbol, mask in zip(state.stage_symbols, masks)
    )


def _uniform_crossover(
    left_masks: tuple[int, ...],
    right_masks: tuple[int, ...],
    rng: Random,
) -> tuple[int, ...]:
    return tuple(
        left_mask if rng.random() < 0.5 else right_mask
        for left_mask, right_mask in zip(left_masks, right_masks)
    )
