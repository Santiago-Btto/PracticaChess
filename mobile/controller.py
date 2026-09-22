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
SEARCH_DEPTH = 2
ANALYSIS_LIMITATION = (
    "Análisis local: libro de aperturas pequeño y búsqueda breve; no sustituye a Stockfish."
)


def _position_key(board: chess.Board) -> tuple[str, chess.Color, int, chess.Square | None]:
    """Clave de una posición de libro, sin depender de su contador de jugadas."""
    return (
        board.board_fen(),
        board.turn,
        int(board.clean_castling_rights()),
        board.ep_square,
    )


def _build_opening_book() -> dict[tuple[str, chess.Color, int, chess.Square | None], str]:
    """Construye un libro local deliberadamente pequeño de posiciones exactas.

    Cada fila contiene las jugadas que deben haberse alcanzado y la única
    continuación que sugerimos. No se hacen inferencias de nombres de apertura:
    fuera de estas posiciones exactas se usa la búsqueda local.
    """
    lines = (
        ((), "e2e4"),
        (("e2e4",), "e7e5"),
        (("e2e4", "e7e5"), "g1f3"),
        (("e2e4", "e7e5", "g1f3"), "b8c6"),
        (("e2e4", "e7e5", "g1f3", "b8c6"), "f1b5"),  # Ruy López
        (("e2e4", "e7e5", "g1f3", "b8c6", "f1b5"), "a7a6"),
        (("e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6"), "b5a4"),
        (("e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5a4"), "g8f6"),
        (("e2e4", "c7c5"), "g1f3"),  # Siciliana
        (("e2e4", "c7c5", "g1f3"), "d7d6"),
        (("e2e4", "c7c5", "g1f3", "d7d6"), "d2d4"),
        (("e2e4", "c7c5", "g1f3", "d7d6", "d2d4"), "c5d4"),
        (("e2e4", "e7e6"), "d2d4"),  # Francesa
        (("e2e4", "e7e6", "d2d4"), "d7d5"),
        (("e2e4", "c7c6"), "d2d4"),  # Caro-Kann
        (("e2e4", "c7c6", "d2d4"), "d7d5"),
        (("d2d4",), "d7d5"),
        (("d2d4", "d7d5"), "c2c4"),  # Gambito de Dama
        (("d2d4", "d7d5", "c2c4"), "e7e6"),
        (("d2d4", "g8f6"), "c2c4"),  # India de Rey
        (("d2d4", "g8f6", "c2c4"), "g7g6"),
        (("d2d4", "g8f6", "c2c4", "g7g6"), "b1c3"),
        (("d2d4", "g8f6", "c2c4", "g7g6", "b1c3"), "f8g7"),
        (("d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "f8g7"), "e2e4"),
        (("d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "f8g7", "e2e4"), "d7d6"),
    )
    book: dict[tuple[str, chess.Color, int, chess.Square | None], str] = {}
    for moves, recommended_uci in lines:
        board = chess.Board()
        for uci in moves:
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                raise RuntimeError(f"Línea de apertura inválida: {uci}")
            board.push(move)
        recommended = chess.Move.from_uci(recommended_uci)
        if recommended not in board.legal_moves:
            raise RuntimeError(f"Recomendación de apertura inválida: {recommended_uci}")
        book[_position_key(board)] = recommended_uci
    return book


OPENING_BOOK = _build_opening_book()


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
        self.analysis_source = "search"
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
        """Sugiere una jugada legal con libro exacto o búsqueda local breve.

        El libro evita recomendar aperturas inventadas: solo interviene en una
        posición estándar idéntica. El resto usa negamax a dos plies con una
        evaluación posicional ligera, por lo que sigue siendo una guía local y
        no pretende sustituir a Stockfish.
        """
        moves = list(self.board.legal_moves)
        if not moves:
            self.analysis_source = "search"
            return None

        book_move = self._book_move()
        if book_move is not None:
            self.analysis_source = "book"
            return book_move

        self.analysis_source = "search"
        return self._search_best_move(moves)

    def _book_move(self) -> chess.Move | None:
        recommended_uci = OPENING_BOOK.get(_position_key(self.board))
        if recommended_uci is None:
            return None
        move = chess.Move.from_uci(recommended_uci)
        return move if move in self.board.legal_moves else None

    def _search_best_move(self, moves: list[chess.Move]) -> chess.Move:
        """Negamax corto: suficiente para réplicas inmediatas sin bloquear la UI."""
        best_move: chess.Move | None = None
        best_score = -MATE_SCORE * 2
        for move in self._ordered_moves(self.board, moves):
            self.board.push(move)
            score = -self._negamax(self.board, SEARCH_DEPTH - 1, -MATE_SCORE * 2, MATE_SCORE * 2)
            self.board.pop()
            score += self._early_move_penalty(move)
            if best_move is None or (score, move.uci()) > (best_score, best_move.uci()):
                best_score = score
                best_move = move
        assert best_move is not None
        return best_move

    @classmethod
    def _negamax(cls, board: chess.Board, depth: int, alpha: int, beta: int) -> int:
        if board.is_checkmate():
            return -MATE_SCORE - depth
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        if depth == 0:
            return cls._positional_evaluation(board, board.turn)

        best_score = -MATE_SCORE * 2
        for move in cls._ordered_moves(board, list(board.legal_moves)):
            board.push(move)
            score = -cls._negamax(board, depth - 1, -beta, -alpha)
            board.pop()
            best_score = max(best_score, score)
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        return best_score

    @classmethod
    def _ordered_moves(cls, board: chess.Board, moves: list[chess.Move]) -> list[chess.Move]:
        """Explora primero capturas y promociones para que la poda sea barata."""
        return sorted(
            moves,
            key=lambda move: (
                cls._captured_value_on(board, move),
                PIECE_VALUES.get(move.promotion, 0),
                board.gives_check(move),
                move.uci(),
            ),
            reverse=True,
        )

    def _early_move_penalty(self, move: chess.Move) -> int:
        """Evita hábitos de apertura poco sanos sin restringir jugadas legales."""
        if self.board.fullmove_number > 8:
            return 0
        piece = self.board.piece_at(move.from_square)
        if piece is None:
            return 0

        penalty = 0
        if piece.piece_type == chess.QUEEN:
            penalty -= 45
        if any(previous.to_square == move.from_square for previous in self.board.move_stack[-6:]):
            penalty -= 24
        return penalty

    @classmethod
    def _positional_evaluation(cls, board: chess.Board, color: chess.Color) -> int:
        """Evalúa material y principios básicos, siempre desde ``color``."""
        opponent = not color
        score = cls._material_for(board, color)

        center = (chess.D4, chess.E4, chess.D5, chess.E5)
        for square in center:
            score += 5 * (
                len(board.attackers(color, square)) - len(board.attackers(opponent, square))
            )
            occupant = board.piece_at(square)
            if occupant and occupant.color == color:
                score += 12
            elif occupant and occupant.color == opponent:
                score -= 12

        score += cls._development_score(board, color) - cls._development_score(board, opponent)
        score += cls._king_safety_score(board, color) - cls._king_safety_score(board, opponent)
        score += cls._early_queen_score(board, color) - cls._early_queen_score(board, opponent)
        return score

    @staticmethod
    def _development_score(board: chess.Board, color: chess.Color) -> int:
        home_squares = (chess.B1, chess.G1, chess.C1, chess.F1) if color else (
            chess.B8, chess.G8, chess.C8, chess.F8
        )
        developed = 0
        for square in board.pieces(chess.KNIGHT, color) | board.pieces(chess.BISHOP, color):
            if square not in home_squares:
                developed += 11
        return developed

    @staticmethod
    def _king_safety_score(board: chess.Board, color: chess.Color) -> int:
        king_square = board.king(color)
        if king_square in ((chess.G1, chess.C1) if color else (chess.G8, chess.C8)):
            return 35
        return 0

    @staticmethod
    def _early_queen_score(board: chess.Board, color: chess.Color) -> int:
        if board.fullmove_number > 8:
            return 0
        queens = board.pieces(chess.QUEEN, color)
        home_square = chess.D1 if color else chess.D8
        return -35 if queens and home_square not in queens else 0

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
