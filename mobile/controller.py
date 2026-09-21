"""Lógica de juego independiente de Kivy para la aplicación móvil."""
from __future__ import annotations

from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class TapOutcome:
    """Resultado de tocar una casilla en la interfaz móvil."""

    kind: str
    san: str | None = None


def display_to_square(row: int, column: int, *, flipped: bool) -> chess.Square:
    """Convierte una celda visual (fila superior=0) en una casilla de ajedrez."""
    if not 0 <= row < 8 or not 0 <= column < 8:
        raise ValueError("Las coordenadas del tablero deben estar entre 0 y 7")

    file_index = 7 - column if flipped else column
    rank_index = row if flipped else 7 - row
    return chess.square(file_index, rank_index)


class MobileGameController:
    """Estado táctil mínimo: selección, jugadas legales, historial y promoción."""

    def __init__(self, initial_fen: str | None = None):
        self._initial_fen = initial_fen
        self.board = chess.Board(initial_fen) if initial_fen else chess.Board()
        self.selected_square: chess.Square | None = None
        self.legal_targets: list[chess.Square] = []
        self.san_history: list[str] = []
        self._snapshots: list[chess.Board] = []
        self.evaluation_curve: list[int] = [self._material_evaluation()]

    def tap(self, square: chess.Square) -> TapOutcome:
        """Selecciona una pieza del turno o ejecuta una jugada legal al tocar destino."""
        if self.selected_square is None:
            return self._select(square)

        move = self._build_move(self.selected_square, square)
        if move in self.board.legal_moves:
            san = self.board.san(move)
            self._snapshots.append(self.board.copy(stack=True))
            self.board.push(move)
            self.san_history.append(san)
            self.evaluation_curve.append(self._material_evaluation())
            self._clear_selection()
            return TapOutcome("moved", san)

        piece = self.board.piece_at(square)
        if piece and piece.color == self.board.turn:
            return self._select(square)

        self._clear_selection()
        return TapOutcome("deselected")

    def undo(self) -> bool:
        """Restaura la posición inmediatamente anterior, si existe."""
        if not self._snapshots:
            return False
        self.board = self._snapshots.pop()
        self.san_history.pop()
        self.evaluation_curve.pop()
        self._clear_selection()
        return True

    def reset(self) -> None:
        self.board = chess.Board(self._initial_fen) if self._initial_fen else chess.Board()
        self.san_history = []
        self._snapshots = []
        self.evaluation_curve = [self._material_evaluation()]
        self._clear_selection()

    def analysis_move(self) -> chess.Move | None:
        """Devuelve una recomendación legal local, sin motor ni red.

        El APK no empaqueta Stockfish; por eso prioriza de modo determinista
        promociones, capturas, jaques y enroques. Es suficiente para dibujar
        una flecha de prueba y nunca propone una jugada ilegal.
        """
        moves = list(self.board.legal_moves)
        if not moves:
            return None
        return max(moves, key=lambda move: (self._move_priority(move), move.uci()))

    def _select(self, square: chess.Square) -> TapOutcome:
        piece = self.board.piece_at(square)
        if piece is None or piece.color != self.board.turn:
            self._clear_selection()
            return TapOutcome("deselected")
        self.selected_square = square
        self.legal_targets = [
            move.to_square for move in self.board.legal_moves if move.from_square == square
        ]
        return TapOutcome("selected")

    def _build_move(self, from_square: chess.Square, to_square: chess.Square) -> chess.Move:
        piece = self.board.piece_at(from_square)
        promotion = None
        if piece and piece.piece_type == chess.PAWN and chess.square_rank(to_square) in (0, 7):
            promotion = chess.QUEEN
        return chess.Move(from_square, to_square, promotion=promotion)

    def _clear_selection(self) -> None:
        self.selected_square = None
        self.legal_targets = []

    def _material_evaluation(self) -> int:
        values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0,
        }
        return 100 * sum(
            (1 if piece.color == chess.WHITE else -1) * values[piece.piece_type]
            for piece in self.board.piece_map().values()
        )

    def _move_priority(self, move: chess.Move) -> int:
        captured = self.board.piece_at(move.to_square)
        if captured is None and self.board.is_en_passant(move):
            captured = chess.Piece(chess.PAWN, not self.board.turn)
        capture_value = 0 if captured is None else captured.piece_type * 100
        promotion_value = 0 if move.promotion is None else move.promotion * 100
        check_bonus = 20 if self.board.gives_check(move) else 0
        castle_bonus = 10 if self.board.is_castling(move) else 0
        return capture_value + promotion_value + check_bonus + castle_bonus
