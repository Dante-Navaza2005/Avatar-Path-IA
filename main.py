from __future__ import annotations

import argparse

from avatar_path.config import load_config
from avatar_path.domain import JourneyResult
from avatar_path.planner import JourneyPlanner, build_team_plan, compare_search_algorithms
from avatar_path.visualization import animate_journey


def format_search_algorithm_label(algorithm: str) -> str:
    labels = {
        "astar": "A*",
        "dijkstra": "Dijkstra",
        "greedy": "Greedy",
    }
    return labels.get(algorithm, algorithm)


def format_cost(value: float) -> str:
    return f"{value:.6f}"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Planeja a jornada do Avatar usando A* no mapa do trabalho."
    )
    parser.add_argument(
        "--config",
        default="config/default_config.json",
        help="Caminho para o arquivo JSON de configuração.",
    )
    parser.add_argument(
        "--animate",
        action="store_true",
        help="Exibe uma animação simples dos movimentos no terminal.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Abre uma interface grafica com mapa, custos e controles de animacao.",
    )
    parser.add_argument(
        "--search",
        choices=("auto", "astar", "dijkstra", "greedy"),
        default="auto",
        help="Algoritmo de busca para os trajetos entre checkpoints.",
    )
    parser.add_argument(
        "--compare-search",
        action="store_true",
        help="Compara A*, Dijkstra e Greedy no mapa atual antes de executar.",
    )
    return parser


def print_search_comparison(comparison: tuple[dict[str, float | int | str], ...]) -> None:
    print("Comparacao de algoritmos de busca")
    for item in comparison:
        algorithm_label = format_search_algorithm_label(str(item["algorithm"]))
        print(
            f"- {algorithm_label}: "
            f"busca={format_cost(float(item['movement_cost']))}, "
            f"combinatoria={format_cost(float(item['stage_cost']))}, "
            f"total={format_cost(float(item['total_cost']))}, "
            f"nos={item['nodes_expanded']}, "
            f"tempo={item['elapsed_ms']:.2f}ms"
        )
    print()


def print_summary(result: JourneyResult, algorithm: str) -> None:
    max_energy_by_name = {
        character.name: character.max_energy
        for character in result.config.characters
    }
    algorithm_label = format_search_algorithm_label(algorithm)

    print("Resumo da jornada")
    print(f"Algoritmo de busca usado: {algorithm_label}")
    print(f"Trechos planejados: {len(result.segments)}")
    print(f"Custo total da busca ({algorithm_label}): {format_cost(float(result.movement_cost))}")
    print(f"Custo total da combinatoria dos personagens: {format_cost(result.stage_cost)}")
    print(f"Custo total final: {format_cost(result.total_cost)}")
    print()
    print("Uso de energia")
    for name, usages in result.energy_usage.items():
        print(f"- {name}: {usages}/{max_energy_by_name[name]}")
    print()
    print("Detalhamento por trecho")
    for segment in result.segments:
        assignment = segment.stage_assignment
        if assignment is None:
            print(
                f"- {segment.start_symbol} -> {segment.end_symbol}: "
                f"passos={segment.steps}, movimento={format_cost(float(segment.movement_cost))}, "
                f"custo acumulado={format_cost(segment.cumulative_total_cost)}"
            )
            continue

        team = ", ".join(assignment.characters)
        print(
            f"- {segment.start_symbol} -> {segment.end_symbol}: "
            f"passos={segment.steps}, movimento={format_cost(float(segment.movement_cost))}, "
            f"etapa={assignment.stage_symbol}, equipe=[{team}], "
            f"tempo da etapa={format_cost(assignment.time_cost)}, "
            f"custo acumulado={format_cost(segment.cumulative_total_cost)}"
        )


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    config = load_config(args.config)
    selected_algorithm = args.search
    comparison: tuple[dict[str, float | int | str], ...] = tuple()
    team_plan = None

    if args.search == "auto" or args.compare_search:
        team_plan = build_team_plan(config)
        comparison = compare_search_algorithms(config, team_plan=team_plan)
        selected_algorithm = str(comparison[0]["algorithm"])

    if args.compare_search:
        print_search_comparison(comparison)

    result = JourneyPlanner(config, search_algorithm=selected_algorithm, team_plan=team_plan).solve()

    if args.gui:
        from avatar_path.gui import launch_gui

        try:
            launch_gui(result)
        except Exception as exc:
            raise SystemExit(f"Falha ao abrir a interface grafica: {exc}") from exc
        return

    print_summary(result, selected_algorithm)

    if args.animate:
        animate_journey(result, config.visualization)


if __name__ == "__main__":
    main()
