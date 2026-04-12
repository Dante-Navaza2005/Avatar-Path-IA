"""Implementacao dos algoritmos de busca usados entre checkpoints do trabalho."""

from __future__ import annotations

from heapq import heappop, heappush

from avatar_path.domain import Coordinate, MapData


NEIGHBOR_DELTAS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def manhattan_distance(a: Coordinate, b: Coordinate) -> int:
    """Calcula a heuristica Manhattan usada pelo A* no mapa ortogonal do enunciado."""

    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reconstruct_path(
    came_from: dict[Coordinate, Coordinate],
    goal: Coordinate,
) -> tuple[Coordinate, ...]:
    """Reconstrui o caminho encontrado pelo algoritmo de busca."""

    path = [goal]
    current = goal
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return tuple(path)


def _priority_for_search(mode: str, movement_cost: int, heuristic_cost: int) -> int:
    """Escolhe a prioridade correta para A*, Dijkstra ou Greedy."""

    if mode == "astar":
        return movement_cost + heuristic_cost
    if mode == "dijkstra":
        return movement_cost
    if mode == "greedy":
        return heuristic_cost
    raise ValueError(f"Algoritmo de busca desconhecido: {mode}.")


def _neighbor_coordinates(map_data: MapData, coord: Coordinate) -> tuple[Coordinate, ...]:
    """Lista os vizinhos validos, sem diagonal, como pede o enunciado."""

    row, col = coord
    neighbors: list[Coordinate] = []
    for row_delta, col_delta in NEIGHBOR_DELTAS:
        neighbor = (row + row_delta, col + col_delta)
        if map_data.inside(neighbor):
            neighbors.append(neighbor)
    return tuple(neighbors)


def _best_first_search(
    map_data: MapData,
    start: Coordinate,
    goal: Coordinate,
    priority_mode: str,
    blocked: frozenset[Coordinate] = frozenset(),
) -> tuple[tuple[Coordinate, ...], int, int]:
    """Executa uma busca com fila de prioridade para ligar dois checkpoints."""

    heuristic_factor = map_data.minimum_step_cost
    frontier: list[tuple[int, int, Coordinate]] = [
        (
            _priority_for_search(
                priority_mode,
                movement_cost=0,
                heuristic_cost=manhattan_distance(start, goal) * heuristic_factor,
            ),
            0,
            start,
        )
    ]
    came_from: dict[Coordinate, Coordinate] = {}
    best_cost = {start: 0}
    closed: set[Coordinate] = set()
    expanded_nodes = 0

    while frontier:
        _, current_cost, current = heappop(frontier)
        if current_cost != best_cost.get(current):
            continue

        if priority_mode != "greedy":
            if current in closed:
                continue
            closed.add(current)

        expanded_nodes += 1
        if current == goal:
            return reconstruct_path(came_from, goal), current_cost, expanded_nodes

        for neighbor in _neighbor_coordinates(map_data, current):
            if neighbor != goal and neighbor in blocked:
                continue

            next_cost = current_cost + map_data.cost(neighbor)
            if next_cost >= best_cost.get(neighbor, float("inf")):
                continue

            best_cost[neighbor] = next_cost
            came_from[neighbor] = current
            heuristic_cost = manhattan_distance(neighbor, goal) * heuristic_factor
            priority = _priority_for_search(priority_mode, next_cost, heuristic_cost)
            heappush(frontier, (priority, next_cost, neighbor))

    raise ValueError(f"Nao existe caminho entre {start} e {goal}.")


def astar_shortest_path(
    map_data: MapData,
    start: Coordinate,
    goal: Coordinate,
    blocked: frozenset[Coordinate] = frozenset(),
) -> tuple[tuple[Coordinate, ...], int, int]:
    """Resolve um trecho com A*, algoritmo principal pedido pelo enunciado."""

    return _best_first_search(map_data, start, goal, "astar", blocked)


def dijkstra_shortest_path(
    map_data: MapData,
    start: Coordinate,
    goal: Coordinate,
    blocked: frozenset[Coordinate] = frozenset(),
) -> tuple[tuple[Coordinate, ...], int, int]:
    """Resolve um trecho com Dijkstra para comparacao com o A*."""

    return _best_first_search(map_data, start, goal, "dijkstra", blocked)


def greedy_best_first_search(
    map_data: MapData,
    start: Coordinate,
    goal: Coordinate,
    blocked: frozenset[Coordinate] = frozenset(),
) -> tuple[tuple[Coordinate, ...], int, int]:
    """Resolve um trecho com busca gulosa para fins de comparacao didatica."""

    return _best_first_search(map_data, start, goal, "greedy", blocked)


def find_path(
    map_data: MapData,
    start: Coordinate,
    goal: Coordinate,
    algorithm: str = "astar",
    blocked: frozenset[Coordinate] = frozenset(),
) -> tuple[tuple[Coordinate, ...], int, int]:
    """Despacha o algoritmo de busca escolhido para um trecho da jornada."""

    if algorithm == "astar":
        return astar_shortest_path(map_data, start, goal, blocked)
    if algorithm == "dijkstra":
        return dijkstra_shortest_path(map_data, start, goal, blocked)
    if algorithm == "greedy":
        return greedy_best_first_search(map_data, start, goal, blocked)
    raise ValueError(f"Algoritmo de busca desconhecido: {algorithm}.")
