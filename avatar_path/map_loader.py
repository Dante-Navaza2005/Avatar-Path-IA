from __future__ import annotations

from avatar_path.domain import JourneyConfig, MapData


def load_map(config: JourneyConfig) -> MapData:
    lines = config.map_path.read_text(encoding="utf-8").splitlines()
    if len(lines) != config.expected_height:
        raise ValueError(
            f"Mapa inválido: esperado {config.expected_height} linhas, recebido {len(lines)}."
        )

    widths = {len(line) for line in lines}
    if widths != {config.expected_width}:
        raise ValueError(
            f"Mapa inválido: esperado {config.expected_width} colunas por linha, recebido {sorted(widths)}."
        )

    checkpoints: dict[str, tuple[int, int]] = {}
    valid_symbols = set(config.terrain_costs) | set(config.checkpoint_order)

    for row, line in enumerate(lines):
        for col, symbol in enumerate(line):
            if symbol not in valid_symbols:
                raise ValueError(f"Símbolo desconhecido no mapa: {symbol!r} em ({row}, {col}).")
            if symbol in config.checkpoint_order:
                if symbol in checkpoints:
                    raise ValueError(f"Checkpoint duplicado no mapa: {symbol!r}.")
                checkpoints[symbol] = (row, col)

    missing = [symbol for symbol in config.checkpoint_order if symbol not in checkpoints]
    if missing:
        raise ValueError(f"Checkpoints ausentes no mapa: {missing}.")

    return MapData(
        grid=tuple(lines),
        terrain_costs=config.terrain_costs,
        checkpoint_cost=config.checkpoint_cost,
        checkpoints=checkpoints,
    )

