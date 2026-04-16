"""Algoritmo Genetico para escolher equipes nas etapas da jornada.

Segue a estrutura classica de um AG conforme apresentado em aula:
populacao inicial -> avaliacao -> selecao -> crossover -> mutacao -> nova geracao.

Como AGs sao estocasticos, o algoritmo roda varias vezes com seeds diferentes
e retorna o melhor resultado encontrado.
"""

from __future__ import annotations

from random import Random

from avatar_path.team_planner_state import PlannerSolution, TeamPlannerState


PlannerCandidate = tuple[tuple[int, ...], tuple[int, ...], float]

EPSILON = 1e-12

# --- Parametros do Algoritmo Genetico ---
POPULATION_SIZE = 80
GENERATION_COUNT = 400
ELITE_COUNT = 6
TOURNAMENT_SIZE = 3
CROSSOVER_RATE = 0.8
GENE_MUTATION_RATE = 0.05
NUM_SEEDS = 50
BEST_SEED = 0


def optimize_with_genetic_algorithm(
    state: TeamPlannerState,
) -> PlannerSolution:
    """Resolve a combinatoria usando Algoritmo Genetico puro.

    Roda o AG com a melhor seed conhecida. Se o resultado nao for satisfatorio,
    a funcao find_best_seed pode ser usada para buscar uma seed melhor.
    """

    best_candidate = _run_genetic_algorithm(state, BEST_SEED)
    return state.build_assignments(dict(zip(state.stage_symbols, best_candidate[0])))


def find_best_seed(
    state: TeamPlannerState,
    num_seeds: int = NUM_SEEDS,
) -> tuple[int, float]:
    """Testa varias seeds e retorna a melhor encontrada.

    AGs sao estocasticos — rodar com seeds diferentes produz resultados
    diferentes. Esta funcao busca a seed que minimiza o custo total.
    """

    best_seed = 0
    best_cost = float("inf")

    for seed in range(num_seeds):
        candidate = _run_genetic_algorithm(state, seed)
        if candidate[2] + EPSILON < best_cost:
            best_cost = candidate[2]
            best_seed = seed
            print(f"Seed {seed}: custo {candidate[2]:.4f} (nova melhor)")
        else:
            print(f"Seed {seed}: custo {candidate[2]:.4f}")

    return best_seed, best_cost


def optimize_with_hill_climbing_simulated_annealing(
    state: TeamPlannerState,
) -> PlannerSolution:
    """Mantem o nome antigo da API publica, agora redirecionando para o GA."""

    return optimize_with_genetic_algorithm(state)


# ---------------------------------------------------------------------------
# Loop principal do AG
# ---------------------------------------------------------------------------


def _run_genetic_algorithm(
    state: TeamPlannerState,
    seed: int,
) -> PlannerCandidate:
    """Executa uma rodada completa do AG com uma seed especifica."""

    rng = Random(seed)

    # --- Fase 1: Populacao inicial ---
    population = _initialize_population(state, rng)
    best_candidate = min(population, key=lambda item: item[2])

    # --- Fase 2: Loop de geracoes ---
    for _ in range(GENERATION_COUNT):
        # Avaliacao ja esta no custo de cada individuo (item[2])

        # Ordenar por fitness (menor custo = melhor)
        population.sort(key=lambda item: item[2])

        # Elitismo: melhores passam direto para proxima geracao
        next_population = list(population[:ELITE_COUNT])

        # Gerar o resto da nova populacao
        while len(next_population) < POPULATION_SIZE:
            # Selecao dos pais
            parent_a = _tournament_select(population, rng)
            parent_b = _tournament_select(population, rng)

            # Crossover
            if rng.random() < CROSSOVER_RATE:
                child_masks = _uniform_crossover(parent_a[0], parent_b[0], rng)
            else:
                child_masks = parent_a[0] if rng.random() < 0.5 else parent_b[0]

            # Mutacao (por gene, taxa baixa)
            child_masks = _mutate(state, child_masks, rng)

            # Reparo para garantir viabilidade
            child = _repair(state, child_masks, rng)
            next_population.append(child)

        population = next_population

        # Atualizar melhor individuo
        generation_best = min(population, key=lambda item: item[2])
        if generation_best[2] + EPSILON < best_candidate[2]:
            best_candidate = generation_best

    return best_candidate


# ---------------------------------------------------------------------------
# Inicializacao da populacao
# ---------------------------------------------------------------------------


def _initialize_population(
    state: TeamPlannerState,
    rng: Random,
) -> list[PlannerCandidate]:
    """Gera a populacao inicial com uma semente gulosa e individuos aleatorios."""

    population: list[PlannerCandidate] = []

    # Um individuo vem da heuristica gulosa (garante boa qualidade inicial)
    greedy = _build_greedy_seed(state)
    population.append(greedy)

    # O resto da populacao e gerado aleatoriamente
    while len(population) < POPULATION_SIZE:
        masks = _random_individual(state, rng)
        candidate = _repair(state, masks, rng)
        population.append(candidate)

    return population


def _random_individual(
    state: TeamPlannerState,
    rng: Random,
) -> tuple[int, ...]:
    """Gera um individuo aleatorio (pode ser invalido — sera reparado depois)."""

    num_chars = len(state.characters)
    masks: list[int] = []

    for _ in state.stage_symbols:
        mask = 0
        # Cada etapa recebe 1 a 3 personagens aleatorios
        num_assigned = 1 + rng.randrange(min(3, num_chars))
        assigned = rng.sample(range(num_chars), num_assigned)
        for char_idx in assigned:
            mask |= 1 << char_idx
        masks.append(mask)

    return tuple(masks)


def _build_greedy_seed(state: TeamPlannerState) -> PlannerCandidate:
    """Monta uma solucao gulosa como semente para a populacao inicial."""

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

    masks = tuple(chosen_mask_by_symbol[s] for s in state.stage_symbols)
    usage = state.usage_for_masks(masks)
    cost = _total_cost(state, masks)
    return masks, usage, cost


# ---------------------------------------------------------------------------
# Operadores geneticos
# ---------------------------------------------------------------------------


def _tournament_select(
    population: list[PlannerCandidate],
    rng: Random,
) -> PlannerCandidate:
    """Selecao por torneio: escolhe o melhor entre TOURNAMENT_SIZE individuos."""

    best: PlannerCandidate | None = None
    for _ in range(TOURNAMENT_SIZE):
        candidate = population[rng.randrange(len(population))]
        if best is None or candidate[2] < best[2]:
            best = candidate
    assert best is not None
    return best


def _uniform_crossover(
    left_masks: tuple[int, ...],
    right_masks: tuple[int, ...],
    rng: Random,
) -> tuple[int, ...]:
    """Crossover uniforme: para cada gene (etapa), escolhe de um dos dois pais."""

    return tuple(
        left_mask if rng.random() < 0.5 else right_mask
        for left_mask, right_mask in zip(left_masks, right_masks)
    )


def _mutate(
    state: TeamPlannerState,
    masks: tuple[int, ...],
    rng: Random,
) -> tuple[int, ...]:
    """Mutacao por gene: cada etapa tem GENE_MUTATION_RATE de chance de ser alterada.

    Tipos de mutacao (analogos ao exemplo do caixeiro viajante na aula):
    - add: adicionar um personagem a uma etapa
    - remove: remover um personagem de uma etapa
    - swap: trocar um personagem por outro na mesma etapa
    - move: mover um personagem de uma etapa para outra
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
            char_idx = rng.choice(absent)
            mutated[stage_idx] = mask | (1 << char_idx)

        elif action == "remove" and len(present) > 1:
            char_idx = rng.choice(present)
            mutated[stage_idx] = mask ^ (1 << char_idx)

        elif action == "swap" and present and absent:
            old_char = rng.choice(present)
            new_char = rng.choice(absent)
            mutated[stage_idx] = (mask ^ (1 << old_char)) | (1 << new_char)

        elif action == "move" and len(present) > 1 and num_stages > 1:
            # Move um personagem desta etapa para outra aleatoria
            char_idx = rng.choice(present)
            bit = 1 << char_idx
            target_idx = rng.randrange(num_stages - 1)
            if target_idx >= stage_idx:
                target_idx += 1
            if not (mutated[target_idx] & bit):
                mutated[stage_idx] = mask ^ bit
                mutated[target_idx] = mutated[target_idx] | bit

    return tuple(mutated)


# ---------------------------------------------------------------------------
# Reparo de cromossomo
# ---------------------------------------------------------------------------


def _repair(
    state: TeamPlannerState,
    masks: tuple[int, ...],
    rng: Random,
) -> PlannerCandidate:
    """Conserta um cromossomo para que ele respeite as regras de energia.

    Operadores de reparo sao padrao em AGs com restricoes — garantem que
    todo individuo gerado por crossover/mutacao seja uma solucao viavel.
    """

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

    # Se algum personagem passou do limite de energia, removemos ou substituimos.
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
            # Forca a remocao do personagem da primeira etapa onde ele aparece
            for stage_idx, mask in enumerate(current_masks):
                if (mask & overused_bit) and mask.bit_count() > 1:
                    current_masks[stage_idx] ^= overused_bit
                    usage[overused_char_idx] -= 1
                    best_fix = (0.0, stage_idx, None)
                    break

        if best_fix is None:
            raise ValueError("Nao foi possivel reparar um cromossomo invalido.")

        _, stage_idx, replacement_idx = best_fix
        current_masks[stage_idx] ^= overused_bit
        usage[overused_char_idx] -= 1
        if replacement_idx is not None:
            current_masks[stage_idx] |= 1 << replacement_idx
            usage[replacement_idx] += 1

    # Se ainda sobrar energia global, adiciona personagens onde reduz mais tempo.
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
    repaired_cost = _total_cost(state, repaired_masks)
    return repaired_masks, repaired_usage, repaired_cost


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def _total_cost(
    state: TeamPlannerState,
    masks: tuple[int, ...],
) -> float:
    """Soma o tempo total de uma distribuicao de equipes."""

    return sum(
        state.stage_time(stage_symbol, mask)
        for stage_symbol, mask in zip(state.stage_symbols, masks)
    )
