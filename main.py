from __future__ import annotations

import argparse

from avatar_path.config import load_config
from avatar_path.domain import JourneyResult
from avatar_path.formatting import format_cost
from avatar_path.planner import JourneyPlanner
from avatar_path.team_planner import TeamPlanner


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Planeja a jornada do Avatar usando A* no mapa do trabalho."
    )
    parser.add_argument(
        "--config",
        default="config/default_config.json",
        help="Caminho para o arquivo JSON de configuracao.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Abre uma interface grafica com mapa, custos e controles de animacao.",
    )
    parser.add_argument(
        "--search",
        action="store_true",
        help="Executa a busca padrao com A*.",
    )
    parser.add_argument(
        "--genetic-hunt",
        action="store_true",
        help="Caca a melhor seed do algoritmo genetico e salva os resultados em CSV.",
    )
    return parser


def print_summary(result: JourneyResult) -> None:
    max_energy_by_name = {
        character.name: character.max_energy
        for character in result.config.characters
    }

    print("Resumo da jornada")
    print("Algoritmo de busca usado: A*")
    print(f"Trechos planejados: {len(result.segments)}")
    print(f"Custo total de movimento: {format_cost(result.movement_cost)}")
    print(f"Custo total das etapas: {format_cost(result.stage_cost)}")
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
                f"passos={segment.steps}, movimento={format_cost(segment.movement_cost)}, "
                f"custo acumulado={format_cost(segment.cumulative_total_cost)}"
            )
            continue

        team = ", ".join(assignment.characters)
        print(
            f"- {segment.start_symbol} -> {segment.end_symbol}: "
            f"passos={segment.steps}, movimento={format_cost(segment.movement_cost)}, "
            f"etapa={assignment.stage_symbol}, equipe=[{team}], "
            f"tempo da etapa={format_cost(assignment.time_cost)}, "
            f"custo acumulado={format_cost(segment.cumulative_total_cost)}"
        )


def print_search_value(result: JourneyResult) -> None:
    print(format_cost(result.movement_cost))


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    config = load_config(args.config)

    if args.genetic_hunt:
        TeamPlanner(
            config.characters,
            config.checkpoint_order[1:],
            config.stage_difficulties,
        ).hunt_best_seed()
        return

    result = JourneyPlanner(config).solve()

    if args.gui:
        from avatar_path.gui import launch_gui

        try:
            launch_gui(result)
        except Exception as exc:
            raise SystemExit(f"Falha ao abrir a interface grafica: {exc}") from exc
        return

    if args.search:
        print_search_value(result)
        return

    print_summary(result)


if __name__ == "__main__":
    main()
