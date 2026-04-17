"""Formatacao simples dos custos exibidos ao usuario.

Manter a formatacao em um unico ponto evita espalhar detalhes visuais pelo
restante do projeto.
"""

from __future__ import annotations


def format_cost(value: float | int) -> str:
    """Padroniza a exibicao dos custos com seis casas decimais.

    O trabalho soma custos inteiros de movimento e custos fracionarios das
    etapas, entao a interface usa sempre a mesma representacao textual.
    """

    return f"{float(value):.6f}"
