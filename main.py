from __future__ import annotations

import argparse

from avatar_path.config import load_config
from avatar_path.domain import JourneyResult
from avatar_path.planner import JourneyPlanner
from avatar_path.visualization import animate_journey


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
    return parser


def print_summary(result: JourneyResult) -> None:
    max_energy_by_name = {
        character.name: character.max_energy
        for character in result.config.characters
    }

    print("Resumo da jornada")
    print(f"Trechos planejados: {len(result.segments)}")
    print(f"Custo total de movimento: {result.movement_cost}")
    print(f"Custo total das etapas: {result.stage_cost:.4f}")
    print(f"Custo total final: {result.total_cost:.4f}")
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
                f"passos={segment.steps}, movimento={segment.movement_cost}, "
                f"custo acumulado={segment.cumulative_total_cost:.4f}"
            )
            continue

        team = ", ".join(assignment.characters)
        print(
            f"- {segment.start_symbol} -> {segment.end_symbol}: "
            f"passos={segment.steps}, movimento={segment.movement_cost}, "
            f"etapa={assignment.stage_symbol}, equipe=[{team}], "
            f"tempo da etapa={assignment.time_cost:.4f}, "
            f"custo acumulado={segment.cumulative_total_cost:.4f}"
        )


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    config = load_config(args.config)
    result = JourneyPlanner(config).solve()

    if args.gui:
        from avatar_path.gui import launch_gui

        try:
            launch_gui(result)
        except Exception as exc:
            raise SystemExit(f"Falha ao abrir a interface grafica: {exc}") from exc
        return

    print_summary(result)

    if args.animate:
        animate_journey(result, config.visualization)


if __name__ == "__main__":
    main()
