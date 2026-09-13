"""Libro breve de aperturas para identificar la línea jugada localmente."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import chess


@dataclass(frozen=True)
class Opening:
    """Una apertura reconocida por su prefijo de movimientos UCI."""

    name: str
    eco: str
    moves: tuple[str, ...]


OPENINGS: tuple[Opening, ...] = (
    Opening("Ruy López", "C60", ("e2e4", "e7e5", "g1f3", "b8c6", "f1b5")),
    Opening("Defensa Siciliana", "B20", ("e2e4", "c7c5")),
    Opening("Defensa Francesa", "C00", ("e2e4", "e7e6")),
    Opening("Defensa Caro-Kann", "B10", ("e2e4", "c7c6")),
    Opening("Gambito de Dama", "D06", ("d2d4", "d7d5", "c2c4")),
    Opening("Defensa India de Rey", "E60", ("d2d4", "g8f6", "c2c4", "g7g6")),
)


def detect_opening(moves: Iterable[chess.Move | str]) -> Opening | None:
    """Devuelve la línea conocida más específica que coincide con ``moves``.

    La detección usa los movimientos ya realizados; conserva la apertura aun
    después de que la secuencia continúe con jugadas que no están en el libro.
    """
    played = tuple(move.uci() if isinstance(move, chess.Move) else move for move in moves)
    matches = [
        opening
        for opening in OPENINGS
        if len(played) >= len(opening.moves) and played[:len(opening.moves)] == opening.moves
    ]
    return max(matches, key=lambda opening: len(opening.moves), default=None)
