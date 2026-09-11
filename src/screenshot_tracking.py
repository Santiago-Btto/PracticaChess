"""Seguimiento de partidas a partir de posiciones detectadas en capturas."""
from __future__ import annotations

from dataclasses import dataclass

import chess

from src.game_state import GameState


@dataclass(frozen=True)
class TrackingResult:
    accepted: bool
    message: str
    san: str | None = None


class ScreenshotTracker:
    """Acepta solo una captura que represente exactamente una jugada legal."""

    def __init__(self, state: GameState):
        self.state = state

    def observe(self, placement: str) -> TrackingResult:
        board = self.state.board
        if placement == board.board_fen():
            return TrackingResult(False, "La captura está sin cambios respecto al tablero actual.")

        candidates: list[chess.Move] = []
        for move in board.legal_moves:
            after = board.copy(stack=False)
            after.push(move)
            if after.board_fen() == placement:
                candidates.append(move)

        if not candidates:
            return TrackingResult(
                False,
                "La captura no corresponde a una única jugada legal desde la posición actual.",
            )
        if len(candidates) > 1:
            return TrackingResult(
                False,
                "La captura es ambigua: coincide con más de una jugada legal.",
            )

        move = candidates[0]
        san = board.san(move)
        self.state.push_ai_move(move)
        return TrackingResult(True, f"Jugada detectada: {san}", san)
