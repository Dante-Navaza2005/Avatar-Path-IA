from __future__ import annotations

from heapq import heappop, heappush

from avatar_path.domain import Coordinate, MapData


def manhattan_distance(a: Coordinate, b: Coordinate) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reconstruct_path(
    came_from: dict[Coordinate, Coordinate],
    current: Coordinate,
) -> tuple[Coordinate, ...]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return tuple(path)


def astar_shortest_path(
    map_data: MapData,
    start: Coordinate,
    goal: Coordinate,
    blocked: frozenset[Coordinate] = frozenset(),
) -> tuple[tuple[Coordinate, ...], int, int]:
    frontier: list[tuple[int, int, Coordinate]] = []
    start_heuristic = manhattan_distance(start, goal) * map_data.minimum_step_cost
    heappush(frontier, (start_heuristic, 0, start))

    came_from: dict[Coordinate, Coordinate] = {}
    best_cost = {start: 0}
    expanded_nodes = 0

    while frontier:
        _, current_cost, current = heappop(frontier)
        if current_cost != best_cost.get(current):
            continue

        expanded_nodes += 1
        if current == goal:
            return reconstruct_path(came_from, current), current_cost, expanded_nodes

        row, col = current
        neighbors = ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))

        for neighbor in neighbors:
            if not map_data.inside(neighbor):
                continue
            if neighbor in blocked and neighbor != goal:
                continue

            step_cost = map_data.cost(neighbor)
            tentative_cost = current_cost + step_cost
            if tentative_cost >= best_cost.get(neighbor, float("inf")):
                continue

            best_cost[neighbor] = tentative_cost
            came_from[neighbor] = current
            priority = tentative_cost + manhattan_distance(neighbor, goal) * map_data.minimum_step_cost
            heappush(frontier, (priority, tentative_cost, neighbor))

    raise ValueError(f"Não existe caminho entre {start} e {goal}.")

