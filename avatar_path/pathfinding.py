"""Implementacao do A* usado entre checkpoints do trabalho.

O enunciado pede que a jornada seja percorrida entre checkpoints sucessivos.
Este modulo resolve cada trecho isoladamente com A* sobre o mesmo mapa
ortogonal.
"""

from __future__ import annotations

from heapq import heappop, heappush

from avatar_path.domain import Coordinate, MapData


NEIGHBOR_DELTAS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def manhattan_distance(a: Coordinate, b: Coordinate) -> int:
    """Calcula a distancia Manhattan usada como heuristica no mapa.

    Como o agente so pode andar para cima, baixo, esquerda e direita, essa
    distancia fornece uma estimativa simples e didatica para o A*.
    """

    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reconstruct_path(
    came_from: dict[Coordinate, Coordinate],
    goal: Coordinate,
) -> tuple[Coordinate, ...]:
    """Reconstrui o caminho final a partir dos predecessores registrados."""

    path = [goal]
    current = goal
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return tuple(path)


def _neighbor_coordinates(map_data: MapData, coord: Coordinate) -> tuple[Coordinate, ...]:
    """Lista os vizinhos validos sem diagonais, como pede o enunciado."""

    row, col = coord
    neighbors: list[Coordinate] = []
    for row_delta, col_delta in NEIGHBOR_DELTAS:
        neighbor = (row + row_delta, col + col_delta)
        if map_data.inside(neighbor):
            neighbors.append(neighbor)
    return tuple(neighbors)


def find_path(
    map_data: MapData,
    start: Coordinate,
    goal: Coordinate,
    blocked: frozenset[Coordinate] = frozenset(),
) -> tuple[tuple[Coordinate, ...], int, int]:
    """Resolve um trecho com A* e devolve caminho, custo e expansoes."""

    heuristic_factor = map_data.minimum_step_cost
    frontier: list[tuple[int, int, Coordinate]] = [
        (
            manhattan_distance(start, goal) * heuristic_factor,
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
            priority = next_cost + heuristic_cost
            heappush(frontier, (priority, next_cost, neighbor))

    raise ValueError(f"Nao existe caminho entre {start} e {goal}.")
