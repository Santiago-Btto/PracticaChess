"""Reglas puras para retos de entrenamiento basados en análisis del motor."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import chess


@dataclass(frozen=True)
class TrainingAttempt:
    """Resultado de comprobar una jugada, sin alterar el tablero del reto."""

    correct: bool
    message: str
    san: str | None


@dataclass(frozen=True)
class TrainingChallenge:
    """Una posición y las mejores jugadas propuestas por el motor.

    El reto guarda la FEN, no una referencia al tablero original. Por eso la
    interfaz puede validar intentos sin ejecutar movimientos de IA ni cambiar
    la posición que el jugador está viendo.
    """

    fen: str
    best_moves: tuple[chess.Move, ...]

    @classmethod
    def from_engine(
        cls,
        board: chess.Board,
        best_moves: Iterable[chess.Move],
    ) -> "TrainingChallenge":
        moves = tuple(dict.fromkeys(best_moves))
        if not moves:
            raise ValueError("El motor debe proporcionar al menos una mejor jugada.")
        illegal = next((move for move in moves if move not in board.legal_moves), None)
        if illegal is not None:
            raise ValueError("Las mejores jugadas del motor deben ser legales en la posición.")
        return cls(board.fen(), moves)

    def check_move(self, move: chess.Move) -> TrainingAttempt:
        """Comprueba el intento sin aplicarlo a la posición del reto."""
        board = chess.Board(self.fen)
        if move not in board.legal_moves:
            return TrainingAttempt(False, "Esa jugada no es legal en esta posición.", None)

        san = board.san(move)
        if move in self.best_moves:
            return TrainingAttempt(True, "¡Correcto! Es una de las mejores jugadas.", san)
        return TrainingAttempt(False, "Es legal, pero el motor prefiere una mejor jugada.", san)
