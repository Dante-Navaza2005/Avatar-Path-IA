"""Formatacao simples dos custos exibidos ao usuario."""

from __future__ import annotations


def format_cost(value: float | int) -> str:
    """Padroniza a exibicao dos custos do trabalho com seis casas decimais."""

    return f"{float(value):.6f}"
