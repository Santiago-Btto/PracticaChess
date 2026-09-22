"""Lógica de juego independiente de Kivy para la aplicación móvil."""
from __future__ import annotations

from dataclasses import dataclass

import chess


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}
MATE_SCORE = 1_000_000


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
        self.recommended_move: chess.Move | None = None
        self.refresh_analysis()

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
            self.refresh_analysis()
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
        self.refresh_analysis()
        return True

    def reset(self) -> None:
        self.board = chess.Board(self._initial_fen) if self._initial_fen else chess.Board()
        self.san_history = []
        self._snapshots = []
        self.evaluation_curve = [self._material_evaluation()]
        self._clear_selection()
        self.refresh_analysis()

    def refresh_analysis(self) -> chess.Move | None:
        """Recalcula la sugerencia local para que la interfaz nunca quede obsoleta."""
        self.recommended_move = self.analysis_move()
        return self.recommended_move

    def analysis_move(self) -> chess.Move | None:
        """Elige la mejor jugada legal con una evaluación local reproducible.

        No intenta sustituir a un motor: pondera material, capturas seguras,
        amenazas al destino, jaque/enroque y movilidad del rival. La jugada se
        simula en una copia, por lo que la flecha nunca puede señalar algo
        ilegal ni alterar la partida activa.
        """
        moves = list(self.board.legal_moves)
        if not moves:
            return None
        return max(moves, key=lambda move: (self.analysis_score(move), move.uci()))

    def analysis_score(self, move: chess.Move) -> int:
        """Puntúa una jugada legal desde el punto de vista del bando que mueve."""
        if move not in self.board.legal_moves:
            raise ValueError("El análisis solo puede puntuar jugadas legales")

        mover_color = self.board.turn
        captured_value = self._captured_value(move)

        position_after = self.board.copy(stack=False)
        position_after.push(move)
        if position_after.is_checkmate():
            return MATE_SCORE
        if self._opponent_has_mate_in_one(position_after):
            return -MATE_SCORE

        moved_piece = position_after.piece_at(move.to_square)
        assert moved_piece is not None  # garantizado por ``legal_moves``

        material = self._material_for(position_after, mover_color)
        safety = self._destination_safety(position_after, move.to_square, mover_color, moved_piece)
        opponent_mobility = sum(1 for _ in position_after.legal_moves)
        reply_risk = self._opponent_reply_risk(position_after)
        check_bonus = 35 if position_after.is_check() else 0
        castle_bonus = 30 if self.board.is_castling(move) else 0
        promotion_bonus = (
            PIECE_VALUES[move.promotion] - PIECE_VALUES[chess.PAWN]
            if move.promotion is not None
            else 0
        )

        # El material ya incluye el valor de una captura. Este pequeño extra
        # rompe empates a favor de tomar una pieza sin convertir la IA en una
        # máquina de sacrificios.
        return (
            material
            + captured_value // 8
            + promotion_bonus
            + safety
            + check_bonus
            + castle_bonus
            - opponent_mobility * 2
            - reply_risk
        )

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
        return 100 * sum(
            (1 if piece.color == chess.WHITE else -1) * (PIECE_VALUES[piece.piece_type] // 100)
            for piece in self.board.piece_map().values()
        )

    @staticmethod
    def _material_for(board: chess.Board, color: chess.Color) -> int:
        return sum(
            (1 if piece.color == color else -1) * PIECE_VALUES[piece.piece_type]
            for piece in board.piece_map().values()
        )

    def _captured_value(self, move: chess.Move) -> int:
        return self._captured_value_on(self.board, move)

    @staticmethod
    def _captured_value_on(board: chess.Board, move: chess.Move) -> int:
        captured = board.piece_at(move.to_square)
        if captured is None and board.is_en_passant(move):
            captured = chess.Piece(chess.PAWN, not board.turn)
        return 0 if captured is None else PIECE_VALUES[captured.piece_type]

    @staticmethod
    def _opponent_has_mate_in_one(position: chess.Board) -> bool:
        """Evita una sugerencia que permita mate inmediato al rival."""
        for reply in position.legal_moves:
            after_reply = position.copy(stack=False)
            after_reply.push(reply)
            if after_reply.is_checkmate():
                return True
        return False

    @classmethod
    def _opponent_reply_risk(cls, position: chess.Board) -> int:
        """Descuenta capturas y jaques disponibles para el rival en la réplica."""
        best_risk = 0
        for reply in position.legal_moves:
            risk = cls._captured_value_on(position, reply) // 5
            after_reply = position.copy(stack=False)
            after_reply.push(reply)
            if after_reply.is_check():
                risk += 25
            best_risk = max(best_risk, risk)
        return best_risk

    @staticmethod
    def _destination_safety(
        board: chess.Board,
        square: chess.Square,
        mover_color: chess.Color,
        moving_piece: chess.Piece,
    ) -> int:
        """Penaliza dejar una pieza valiosa atacada tras moverla.

        Es una aproximación conservadora al intercambio estático: tomar una
        torre con la dama no es buena si el rey o un peón puede capturarla al
        instante. Una pieza defendida conserva una bonificación menor.
        """
        attackers = board.attackers(not mover_color, square)
        if not attackers:
            return 12 if board.attackers(mover_color, square) else 0

        attacker_values = [
            PIECE_VALUES[board.piece_at(attacker).piece_type]
            for attacker in attackers
            if board.piece_at(attacker) is not None
        ]
        cheapest_attacker = min(attacker_values, default=0)
        loss_risk = max(0, PIECE_VALUES[moving_piece.piece_type] - cheapest_attacker)
        support_bonus = 20 if board.attackers(mover_color, square) else 0
        return support_bonus - loss_risk
