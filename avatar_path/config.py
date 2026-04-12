"""Leitura da configuracao editavel do trabalho a partir de JSON."""

from __future__ import annotations

import json
from pathlib import Path

from avatar_path.domain import CharacterConfig, JourneyConfig, VisualizationConfig


def load_config(path: str | Path) -> JourneyConfig:
    """Le a configuracao do trabalho e transforma o JSON em objetos do dominio."""

    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))

    characters = tuple(
        CharacterConfig(
            name=name,
            agility=float(values["agility"]),
            max_energy=int(values["max_energy"]),
        )
        for name, values in payload["characters"].items()
    )

    visualization_data = payload["visualization"]
    visualization = VisualizationConfig(
        delay_seconds=float(visualization_data["delay_seconds"]),
        viewport_height=int(visualization_data["viewport_height"]),
        viewport_width=int(visualization_data["viewport_width"]),
        step_stride=int(visualization_data["step_stride"]),
    )

    return JourneyConfig(
        map_path=Path(payload["map_path"]),
        expected_height=int(payload["expected_height"]),
        expected_width=int(payload["expected_width"]),
        terrain_costs={str(key): int(value) for key, value in payload["terrain_costs"].items()},
        checkpoint_order=tuple(payload["checkpoint_order"]),
        stage_difficulties={str(key): int(value) for key, value in payload["stage_difficulties"].items()},
        characters=characters,
        checkpoint_cost=int(payload["checkpoint_cost"]),
        block_future_checkpoints=bool(payload["block_future_checkpoints"]),
        visualization=visualization,
    )
