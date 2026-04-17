"""Leitura da configuracao editavel do trabalho a partir de JSON.

Este modulo transforma o arquivo de configuracao em objetos simples do
dominio para que o restante do codigo trabalhe apenas com Python puro.
"""

from __future__ import annotations

import json
from pathlib import Path

from avatar_path.domain import CharacterConfig, JourneyConfig


def load_config(path: str | Path) -> JourneyConfig:
    """Le o arquivo de configuracao e monta os objetos usados no trabalho.

    Esta funcao resolve o problema de tirar os dados do JSON bruto e entregar
    ao planejador estruturas mais claras, com tipos proximos do dominio.
    """

    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))

    characters: list[CharacterConfig] = []
    for name, values in payload["characters"].items():
        characters.append(
            CharacterConfig(
                name=name,
                agility=float(values["agility"]),
                max_energy=int(values["max_energy"]),
            )
        )

    return JourneyConfig(
        map_path=Path(payload["map_path"]),
        expected_height=int(payload["expected_height"]),
        expected_width=int(payload["expected_width"]),
        terrain_costs={str(key): int(value) for key, value in payload["terrain_costs"].items()},
        checkpoint_order=tuple(payload["checkpoint_order"]),
        stage_difficulties={str(key): int(value) for key, value in payload["stage_difficulties"].items()},
        characters=tuple(characters),
        checkpoint_cost=int(payload["checkpoint_cost"]),
        block_future_checkpoints=bool(payload["block_future_checkpoints"]),
    )
