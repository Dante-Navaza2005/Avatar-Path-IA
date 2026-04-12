from __future__ import annotations

from math import exp
from random import Random

from avatar_path.team_planner_state import PlannerSolution, TeamPlannerState


SEEDS = (1771, 1949, 2213, 2591, 3001, 3253)
RESTARTS = 14
ITERATIONS_PER_RESTART = 14000
INITIAL_TEMPERATURE = 45.0
COOLING_RATE = 0.999
NEIGHBOR_BATCH_SIZE = 5
BEST_BATCH_SELECTION_PROBABILITY = 0.75
RANDOMIZED_GREEDY_ALPHA_MIN = 0.15
RANDOMIZED_GREEDY_ALPHA_MAX = 0.40
RANDOMIZED_GREEDY_TOP_CHOICES = 3
RANDOMIZED_GREEDY_STAGE_NOISE = 25.0


def optimize_with_hill_climbing_simulated_annealing(
    state: TeamPlannerState,
) -> PlannerSolution:
    # Seguindo a ideia discutida nas aulas de busca local, usamos:
    # 1) uma boa solucao inicial gulosa;
    # 2) varios reinicios com solucao inicial diversificada;
    # 3) simulated annealing para escapar de otimos locais;
    # 4) hill climbing no fim para polir o melhor candidato.
    greedy_assignments, _, greedy_cost = optimize_with_greedy_balancing(state)
    greedy_masks = state.masks_from_assignments(greedy_assignments)
    greedy_usage = state.usage_for_masks(greedy_masks)
    greedy_masks, greedy_usage, greedy_cost = hill_climb_polish(
        state,
        greedy_masks,
        greedy_usage,
        greedy_cost,
    )

    best_masks = greedy_masks
    best_usage = greedy_usage
    best_cost = greedy_cost

    for seed in SEEDS:
        rng = Random(seed)
        for restart_idx in range(RESTARTS):
            if restart_idx == 0:
                # O primeiro reinicio de cada semente reaproveita a melhor
                # solucao global conhecida ate ali, em vez de sempre voltar
                # para o mesmo guloso deterministico.
                current_masks = best_masks
                current_usage = best_usage
                current_cost = best_cost
            else:
                current_masks, current_usage, current_cost = build_randomized_start(state, rng)

            temperature = INITIAL_TEMPERATURE
            for _ in range(ITERATIONS_PER_RESTART):
                neighbor = sample_neighbor_batch(
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
                # O criterio de Boltzmann permite aceitar piores vizinhos de vez
                # em quando, reduzindo a chance de parar cedo em um maximo local.
                if delta <= 0.0 or rng.random() < exp(-delta / temperature):
                    current_masks = next_masks
                    current_usage = next_usage
                    current_cost = next_cost
                    if current_cost < best_cost:
                        best_masks = current_masks
                        best_usage = current_usage
                        best_cost = current_cost

                temperature *= COOLING_RATE

            current_masks, current_usage, current_cost = hill_climb_polish(
                state,
                current_masks,
                current_usage,
                current_cost,
            )
            if current_cost < best_cost:
                best_masks = current_masks
                best_usage = current_usage
                best_cost = current_cost

    return state.build_assignments(dict(zip(state.stage_symbols, best_masks)))


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

    while total_assigned_uses < state.usable_energy_budget:
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
                if gain > best_gain + 1e-12:
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


def optimize_with_randomized_greedy_balancing(
    state: TeamPlannerState,
    rng: Random,
    alpha: float,
) -> PlannerSolution:
    remaining_energy = list(state.max_energies)
    chosen_mask_by_symbol = {symbol: 0 for symbol in state.stage_symbols}
    chosen_agility_by_symbol = {symbol: 0 for symbol in state.stage_symbols}
    total_assigned_uses = 0

    # A aula destaca a importancia de partir de solucoes iniciais aleatorias.
    # Aqui mantemos a intuicao gulosa, mas com diversidade controlada.
    stage_order = list(state.stage_symbols)
    stage_order.sort(
        key=lambda symbol: state.stage_difficulties[symbol] + rng.random() * RANDOMIZED_GREEDY_STAGE_NOISE,
        reverse=True,
    )

    for stage_symbol in stage_order:
        candidates = [
            idx
            for idx in state.character_indices_by_agility
            if remaining_energy[idx] > 0
        ]
        if not candidates:
            raise ValueError("Nao existe alocacao valida de personagens para todas as etapas.")

        top_count = max(1, min(len(candidates), RANDOMIZED_GREEDY_TOP_CHOICES))
        char_idx = candidates[rng.randrange(top_count)]
        chosen_mask_by_symbol[stage_symbol] |= 1 << char_idx
        chosen_agility_by_symbol[stage_symbol] += state.agility_units[char_idx]
        remaining_energy[char_idx] -= 1
        total_assigned_uses += 1

    while total_assigned_uses < state.usable_energy_budget:
        best_gain = 0.0
        candidates: list[tuple[float, str, int]] = []

        for stage_symbol in state.stage_symbols:
            current_agility = chosen_agility_by_symbol[stage_symbol]
            current_mask = chosen_mask_by_symbol[stage_symbol]
            difficulty = state.stage_difficulties[stage_symbol]

            for char_idx in state.character_indices_by_agility:
                if remaining_energy[char_idx] <= 0:
                    continue
                if current_mask & (1 << char_idx):
                    continue

                next_agility = current_agility + state.agility_units[char_idx]
                gain = (difficulty * 10.0 / current_agility) - (difficulty * 10.0 / next_agility)
                if gain > best_gain:
                    best_gain = gain
                candidates.append((gain, stage_symbol, char_idx))

        if not candidates:
            break

        cutoff = best_gain * (1.0 - alpha)
        restricted_candidates = [
            candidate
            for candidate in candidates
            if candidate[0] >= cutoff - 1e-12
        ]
        gain, stage_symbol, char_idx = restricted_candidates[rng.randrange(len(restricted_candidates))]
        chosen_mask_by_symbol[stage_symbol] |= 1 << char_idx
        chosen_agility_by_symbol[stage_symbol] += state.agility_units[char_idx]
        remaining_energy[char_idx] -= 1
        total_assigned_uses += 1

    return state.build_assignments(chosen_mask_by_symbol)


def build_randomized_start(
    state: TeamPlannerState,
    rng: Random,
) -> tuple[tuple[int, ...], tuple[int, ...], float]:
    alpha = RANDOMIZED_GREEDY_ALPHA_MIN + (
        (RANDOMIZED_GREEDY_ALPHA_MAX - RANDOMIZED_GREEDY_ALPHA_MIN) * rng.random()
    )
    assignments, _, cost = optimize_with_randomized_greedy_balancing(state, rng, alpha)
    masks = state.masks_from_assignments(assignments)
    usage = state.usage_for_masks(masks)
    return hill_climb_polish(state, masks, usage, cost)


def sample_neighbor_batch(
    state: TeamPlannerState,
    masks: tuple[int, ...],
    usage: tuple[int, ...],
    total_cost: float,
    rng: Random,
) -> tuple[tuple[int, ...], tuple[int, ...], float] | None:
    candidates = []
    for _ in range(NEIGHBOR_BATCH_SIZE):
        neighbor = sample_neighbor(state, masks, usage, total_cost, rng)
        if neighbor is not None:
            candidates.append(neighbor)

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[2])
    if rng.random() < BEST_BATCH_SELECTION_PROBABILITY:
        return candidates[0]
    return candidates[rng.randrange(len(candidates))]


def sample_neighbor(
    state: TeamPlannerState,
    masks: tuple[int, ...],
    usage: tuple[int, ...],
    total_cost: float,
    rng: Random,
) -> tuple[tuple[int, ...], tuple[int, ...], float] | None:
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
) -> tuple[tuple[int, ...], tuple[int, ...], float]:
    current_masks = list(masks)
    current_usage = list(usage)
    current_cost = total_cost
    stage_count = len(current_masks)
    character_count = len(state.characters)

    while True:
        best_delta = -1e-12
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
