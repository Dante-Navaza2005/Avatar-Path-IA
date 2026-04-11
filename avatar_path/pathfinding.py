from __future__ import annotations

from heapq import heappop, heappush

from avatar_path.domain import Coordinate, MapData


NEIGHBOR_DELTAS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def manhattan_distance(a: Coordinate, b: Coordinate) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reconstruct_path(
    came_from: list[int],
    current_index: int,
    width: int,
) -> tuple[Coordinate, ...]:
    path: list[Coordinate] = []
    while current_index != -1:
        path.append(divmod(current_index, width))
        current_index = came_from[current_index]
    path.reverse()
    return tuple(path)


def _best_first_search(
    map_data: MapData,
    start: Coordinate,
    goal: Coordinate,
    priority_mode: str,
    blocked: frozenset[Coordinate] = frozenset(),
) -> tuple[tuple[Coordinate, ...], int, int]:
    minimum_step_cost = map_data.minimum_step_cost
    frontier: list[tuple[int, int, int]] = []
    start_heuristic = manhattan_distance(start, goal) * minimum_step_cost
    if priority_mode == "astar":
        start_priority = start_heuristic
    elif priority_mode == "dijkstra":
        start_priority = 0
    elif priority_mode == "greedy":
        start_priority = start_heuristic
    else:
        raise ValueError(f"Algoritmo de busca desconhecido: {priority_mode}.")

    width = map_data.width
    height = map_data.height
    cell_costs = map_data.cell_costs
    goal_row, goal_col = goal
    total_cells = len(cell_costs)
    start_index = map_data.index(start)
    goal_index = map_data.index(goal)
    # Guardamos checkpoints bloqueados e nos fechados em bitmaps por linha
    # para reduzir custo de memoria e deixar as checagens O(1).
    blocked_rows = map_data.bitmap_for_coordinates(blocked)
    use_closed_bitmap = priority_mode != "greedy"

    heappush(frontier, (start_priority, 0, start_index))

    came_from = [-1] * total_cells
    best_cost = [-1] * total_cells
    best_cost[start_index] = 0
    closed_rows = [0] * height
    expanded_nodes = 0

    while frontier:
        _, current_cost, current_index = heappop(frontier)
        if current_cost != best_cost[current_index]:
            continue

        current_row, current_col = divmod(current_index, width)
        current_bit = 1 << current_col
        if use_closed_bitmap and closed_rows[current_row] & current_bit:
            continue
        if use_closed_bitmap:
            closed_rows[current_row] |= current_bit

        expanded_nodes += 1
        if current_index == goal_index:
            return reconstruct_path(came_from, current_index, width), current_cost, expanded_nodes

        for row_delta, col_delta in NEIGHBOR_DELTAS:
            neighbor_row = current_row + row_delta
            neighbor_col = current_col + col_delta
            if not (0 <= neighbor_row < height and 0 <= neighbor_col < width):
                continue

            neighbor_index = current_index + row_delta * width + col_delta
            neighbor_bit = 1 << neighbor_col
            if neighbor_index != goal_index and blocked_rows[neighbor_row] & neighbor_bit:
                continue

            tentative_cost = current_cost + cell_costs[neighbor_index]
            known_cost = best_cost[neighbor_index]
            if known_cost != -1 and tentative_cost >= known_cost:
                continue

            best_cost[neighbor_index] = tentative_cost
            came_from[neighbor_index] = current_index
            # O mesmo loop atende A*, Dijkstra e Greedy; o que muda e so
            # a prioridade usada na fila.
            heuristic = (abs(neighbor_row - goal_row) + abs(neighbor_col - goal_col)) * minimum_step_cost
            if priority_mode == "astar":
                priority = tentative_cost + heuristic
            elif priority_mode == "dijkstra":
                priority = tentative_cost
            else:
                priority = heuristic
            heappush(frontier, (priority, tentative_cost, neighbor_index))

    raise ValueError(f"Nao existe caminho entre {start} e {goal}.")


def astar_shortest_path(
    map_data: MapData,
    start: Coordinate,
    goal: Coordinate,
    blocked: frozenset[Coordinate] = frozenset(),
) -> tuple[tuple[Coordinate, ...], int, int]:
    return _best_first_search(map_data, start, goal, "astar", blocked)


def dijkstra_shortest_path(
    map_data: MapData,
    start: Coordinate,
    goal: Coordinate,
    blocked: frozenset[Coordinate] = frozenset(),
) -> tuple[tuple[Coordinate, ...], int, int]:
    return _best_first_search(map_data, start, goal, "dijkstra", blocked)


def greedy_best_first_search(
    map_data: MapData,
    start: Coordinate,
    goal: Coordinate,
    blocked: frozenset[Coordinate] = frozenset(),
) -> tuple[tuple[Coordinate, ...], int, int]:
    return _best_first_search(map_data, start, goal, "greedy", blocked)


def find_path(
    map_data: MapData,
    start: Coordinate,
    goal: Coordinate,
    algorithm: str = "astar",
    blocked: frozenset[Coordinate] = frozenset(),
) -> tuple[tuple[Coordinate, ...], int, int]:
    if algorithm == "astar":
        return astar_shortest_path(map_data, start, goal, blocked)
    if algorithm == "dijkstra":
        return dijkstra_shortest_path(map_data, start, goal, blocked)
    if algorithm == "greedy":
        return greedy_best_first_search(map_data, start, goal, blocked)
    raise ValueError(f"Algoritmo de busca desconhecido: {algorithm}.")
