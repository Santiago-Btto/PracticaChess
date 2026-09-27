"""Lógica de juego independiente de Kivy para la aplicación móvil."""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from threading import Event
from typing import Callable

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
MAX_SEARCH_DEPTH = 4
ANALYSIS_BUDGET_SECONDS = {"hint": 0.20, "review": 0.75}
ANALYSIS_LIMITATION = (
    "Análisis local: libro de aperturas pequeño y búsqueda breve; no sustituye a Stockfish."
)
REVIEW_CATEGORIES = ("best move", "good move", "inaccuracy", "mistake", "blunder")
CRITICAL_CATEGORY_RANK = {"inaccuracy": 1, "mistake": 2, "blunder": 3}


@dataclass(frozen=True)
class AnalysisResult:
    """Resultado inmutable de una posición, expresado desde blancas."""

    fen: str
    best_move: chess.Move | None
    evaluation: int
    terminal: bool
    depth: int = 0


@dataclass(frozen=True)
class AnalysisRecord:
    fen: str
    ply: int
    evaluation: int
    best_move: chess.Move | None


@dataclass(frozen=True)
class FinishedGame:
    initial_fen: str
    moves: tuple[str, ...]
    san_moves: tuple[str, ...]
    result: str


@dataclass(frozen=True)
class ReviewEntry:
    ply: int
    san: str
    category: str
    evaluation_before: int
    evaluation_after: int
    best_alternative_san: str | None
    terminal: bool


@dataclass(frozen=True)
class GameAnalysisSummary:
    """Lectura general, local e inmutable de una revisión ya completa."""

    category_counts: tuple[tuple[str, int], ...]
    best_moves: tuple[ReviewEntry, ...]
    critical_moments: tuple[ReviewEntry, ...]
    explanation: str


@dataclass(frozen=True)
class _RequestToken:
    request_id: int
    fen: str
    generation: int
    review_generation: int
    cancelled: Event


class _InlineExecutor:
    def submit(self, function: Callable[[], None]) -> None:
        function()


class AnalysisCoordinator:
    """Una cola de CPU; sus callbacks sólo llegan a través del despachador UI."""

    def __init__(self, executor=None, dispatch: Callable[[Callable[[], None]], None] | None = None):
        self.executor = executor or _InlineExecutor()
        self.dispatch = dispatch or (lambda callback: callback())

    def submit(
        self,
        work: Callable[[], AnalysisResult | ReviewEntry],
        deliver: Callable[[AnalysisResult | ReviewEntry], None],
    ) -> None:
        def run() -> None:
            result = work()
            self.dispatch(lambda: deliver(result))

        self.executor.submit(run)


class _SearchStopped(Exception):
    """La búsqueda cooperativa agotó su presupuesto o fue cancelada."""


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

    def __init__(self, initial_fen: str | None = None, *, executor=None, dispatch=None):
        self._initial_fen = initial_fen
        self.board = chess.Board(initial_fen) if initial_fen else chess.Board()
        self.selected_square: chess.Square | None = None
        self.legal_targets: list[chess.Square] = []
        self.san_history: list[str] = []
        self._snapshots: list[chess.Board] = []
        self.evaluation_curve: list[int] = []
        self.recommended_move: chess.Move | None = None
        self.live_analysis_enabled = True
        self.analysis_source = "search"
        self.analysis_records: list[AnalysisRecord] = []
        self._generation = 0
        self._review_generation = 0
        self._next_request_id = 0
        self._active_token: _RequestToken | None = None
        self._coordinator = AnalysisCoordinator(executor, dispatch)
        self.finished_game: FinishedGame | None = None
        self.review_active = False
        self.review_entries: list[ReviewEntry] = []
        self.review_progress = (0, 0)
        self.review_summary: GameAnalysisSummary | None = None
        self._review_snapshot: FinishedGame | None = None
        self._review_cancel: Event | None = None
        self.refresh_analysis()

    def tap(self, square: chess.Square) -> TapOutcome:
        """Selecciona una pieza del turno o ejecuta una jugada legal al tocar destino."""
        if self.selected_square is None:
            return self._select(square)

        move = self._build_move(self.selected_square, square)
        if move in self.board.legal_moves:
            self._invalidate_requests()
            san = self.board.san(move)
            self._snapshots.append(self.board.copy(stack=True))
            self.board.push(move)
            self.san_history.append(san)
            self._clear_selection()
            self.refresh_analysis()
            if self.board.is_game_over(claim_draw=True):
                self.finished_game = FinishedGame(
                    self._initial_fen or chess.STARTING_FEN,
                    tuple(item.uci() for item in self.board.move_stack),
                    tuple(self.san_history),
                    self.board.result(claim_draw=True),
                )
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
        self._invalidate_requests()
        self.board = self._snapshots.pop()
        self.san_history.pop()
        self._discard_records_after_current_ply()
        self.finished_game = None
        self._clear_selection()
        self.refresh_analysis()
        return True

    def reset(self) -> None:
        self._invalidate_requests()
        self.board = chess.Board(self._initial_fen) if self._initial_fen else chess.Board()
        self.san_history = []
        self._snapshots = []
        self.analysis_records = []
        self.evaluation_curve = []
        self.finished_game = None
        self.exit_review()
        self._clear_selection()
        self.refresh_analysis()

    def refresh_analysis(self) -> chess.Move | None:
        """Recalcula la sugerencia local para que la interfaz nunca quede obsoleta."""
        if not self.live_analysis_enabled:
            self.recommended_move = None
            return None
        self.request_analysis()
        return self.recommended_move

    def set_live_analysis_enabled(self, enabled: bool) -> None:
        """Activa o desactiva las sugerencias automáticas de esta sesión."""
        if self.live_analysis_enabled == enabled:
            return
        self.live_analysis_enabled = enabled
        if not enabled:
            self._invalidate_live_hint()
            return
        if not self.review_active:
            self.refresh_analysis()

    def request_analysis(self, *, purpose: str = "hint") -> _RequestToken | None:
        """Solicita análisis de una instantánea; nunca entrega datos sin validar token."""
        if purpose == "hint" and not self.live_analysis_enabled:
            return None
        self._next_request_id += 1
        token = _RequestToken(
            self._next_request_id, self.board.fen(), self._generation, self._review_generation, Event()
        )
        self._active_token = token

        def work() -> AnalysisResult:
            return self._analyse_fen(token.fen, purpose, token.cancelled.is_set)

        self._coordinator.submit(work, lambda result: self._accept_analysis(token, result))
        return token

    def _analyse_fen(
        self, fen: str, purpose: str, cancelled: Callable[[], bool] | None = None
    ) -> AnalysisResult:
        # Una instancia desnuda evita que el worker vea o mute el tablero vivo.
        worker = object.__new__(MobileGameController)
        worker.board = chess.Board(fen)
        worker.analysis_source = "search"
        return worker.analyse_position(purpose=purpose, cancelled=cancelled)

    def _accept_analysis(self, token: _RequestToken, result: AnalysisResult | ReviewEntry) -> bool:
        if (
            not isinstance(result, AnalysisResult)
            or not self.live_analysis_enabled
            or not self._token_is_current(token)
        ):
            return False
        self.recommended_move = result.best_move
        self._upsert_record(AnalysisRecord(result.fen, len(self.san_history), result.evaluation, result.best_move))
        return True

    def _token_is_current(self, token: _RequestToken) -> bool:
        return (
            self._active_token == token
            and token.fen == self.board.fen()
            and token.generation == self._generation
            and token.review_generation == self._review_generation
        )

    def _invalidate_requests(self) -> None:
        if self._active_token is not None:
            self._active_token.cancelled.set()
        if self._review_cancel is not None:
            self._review_cancel.set()
        self._generation += 1
        self._review_generation += 1
        self._active_token = None
        self.recommended_move = None

    def _invalidate_live_hint(self) -> None:
        if self._active_token is not None:
            self._active_token.cancelled.set()
        self._generation += 1
        self._active_token = None
        self.recommended_move = None

    def _upsert_record(self, record: AnalysisRecord) -> None:
        if any(
            item.ply == record.ply and item.fen == record.fen
            for item in self.analysis_records
        ):
            return
        self.analysis_records = [item for item in self.analysis_records if item.ply != record.ply]
        self.analysis_records.append(record)
        self.analysis_records.sort(key=lambda item: item.ply)
        self.evaluation_curve = [item.evaluation for item in self.analysis_records]

    def _discard_records_after_current_ply(self) -> None:
        ply = len(self.san_history)
        self.analysis_records = [item for item in self.analysis_records if item.ply <= ply]
        self.evaluation_curve = [item.evaluation for item in self.analysis_records]

    def analyse_position(
        self,
        *,
        purpose: str = "hint",
        clock: Callable[[], float] = monotonic,
        budget_seconds: float | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> AnalysisResult:
        """Analiza la posición actual sin inventar una jugada en posiciones terminales."""
        terminal = self.board.is_game_over(claim_draw=True)
        if terminal:
            self.analysis_source = "search"
            return AnalysisResult(self.board.fen(), None, self._white_evaluation(), True)
        moves = list(self.board.legal_moves)
        book_move = self._book_move()
        if book_move is not None:
            self.analysis_source = "book"
            return AnalysisResult(self.board.fen(), book_move, self._white_evaluation(), False)
        self.analysis_source = "search"
        budget = self.analysis_budget(purpose) if budget_seconds is None else budget_seconds
        return self._search_result(moves, clock() + max(0.0, budget), clock, cancelled)

    @staticmethod
    def analysis_budget(purpose: str) -> float:
        try:
            return ANALYSIS_BUDGET_SECONDS[purpose]
        except KeyError as exc:
            raise ValueError(f"Propósito de análisis desconocido: {purpose}") from exc

    def _white_evaluation(self) -> int:
        """Normaliza el evaluador local a la perspectiva de las blancas."""
        if self.board.is_checkmate():
            return -MATE_SCORE if self.board.turn == chess.WHITE else MATE_SCORE
        return self._positional_evaluation(self.board, chess.WHITE)

    @staticmethod
    def classify_loss(loss: int) -> str:
        if loss <= 15:
            return "best move"
        if loss <= 50:
            return "good move"
        if loss <= 120:
            return "inaccuracy"
        if loss <= 250:
            return "mistake"
        return "blunder"

    def review_position(self, ply: int) -> chess.Board:
        """Reconstruye una posición sólo desde la instantánea final inmutable."""
        snapshot = self._review_snapshot or self.finished_game
        if snapshot is None:
            raise ValueError("No hay partida finalizada para revisar")
        return self._review_position_from_snapshot(snapshot, ply)

    @staticmethod
    def _review_position_from_snapshot(snapshot: FinishedGame, ply: int) -> chess.Board:
        if not 0 <= ply <= len(snapshot.moves):
            raise IndexError("Ply de revisión fuera de rango")
        board = chess.Board(snapshot.initial_fen)
        for uci in snapshot.moves[:ply]:
            board.push_uci(uci)
        return board

    def start_review(self) -> None:
        if self.finished_game is None:
            raise ValueError("La revisión sólo está disponible al terminar la partida")
        self._invalidate_requests()
        self._review_snapshot = self.finished_game
        self._review_cancel = Event()
        self.review_active = True
        self.review_entries = []
        self.review_summary = None
        self.review_progress = (0, len(self._review_snapshot.moves))
        if not self._review_snapshot.moves:
            self.review_summary = self.summarize_review_entries(())
            return
        self._request_next_review_entry(0)

    def exit_review(self) -> None:
        if self._review_cancel is not None:
            self._review_cancel.set()
        self._review_generation += 1
        self._active_token = None
        self.review_active = False
        self.review_entries = []
        self.review_progress = (0, 0)
        self.review_summary = None
        self._review_snapshot = None
        self._review_cancel = None

    def _request_next_review_entry(self, index: int) -> None:
        snapshot = self._review_snapshot
        if not self.review_active or snapshot is None or index >= len(snapshot.moves):
            return
        generation = self._review_generation
        cancel = self._review_cancel

        def work() -> ReviewEntry:
            before = self._review_position_from_snapshot(snapshot, index)
            played = chess.Move.from_uci(snapshot.moves[index])
            san = before.san(played)
            before_result = self._analyse_fen(before.fen(), "review", cancel.is_set if cancel else None)
            before.push(played)
            after_result = self._analyse_fen(before.fen(), "review", cancel.is_set if cancel else None)
            mover = not before.turn
            loss = (
                max(0, before_result.evaluation - after_result.evaluation)
                if mover == chess.WHITE
                else max(0, after_result.evaluation - before_result.evaluation)
            )
            alternative = None
            original = self._review_position_from_snapshot(snapshot, index)
            if before_result.best_move is not None and before_result.best_move != played:
                alternative = original.san(before_result.best_move)
            return ReviewEntry(
                index + 1,
                san,
                self.classify_loss(loss),
                before_result.evaluation,
                after_result.evaluation,
                alternative,
                after_result.terminal,
            )

        def deliver(result: AnalysisResult | ReviewEntry) -> None:
            if (
                not isinstance(result, ReviewEntry)
                or not self.review_active
                or self._review_snapshot != snapshot
                or self._review_generation != generation
                or result.ply != index + 1
            ):
                return
            self.review_entries.append(result)
            self.review_progress = (len(self.review_entries), len(snapshot.moves))
            if self._review_entries_complete(snapshot):
                self.review_summary = self.summarize_review_entries(tuple(self.review_entries))
            else:
                self._request_next_review_entry(index + 1)

        self._coordinator.submit(work, deliver)

    def _review_entries_complete(self, snapshot: FinishedGame) -> bool:
        return (
            len(self.review_entries) == len(snapshot.moves)
            and tuple(entry.ply for entry in self.review_entries) == tuple(range(1, len(snapshot.moves) + 1))
        )

    @staticmethod
    def summarize_review_entries(entries: tuple[ReviewEntry, ...] | list[ReviewEntry]) -> GameAnalysisSummary:
        """Resume entradas completas sin atribuirlas a un motor o servicio externo."""
        ordered_entries = tuple(sorted(entries, key=lambda entry: entry.ply))
        category_counts = tuple(
            (category, sum(entry.category == category for entry in ordered_entries))
            for category in REVIEW_CATEGORIES
        )
        best_moves = tuple(entry for entry in ordered_entries if entry.category == "best move")
        critical_moments = tuple(
            sorted(
                (entry for entry in ordered_entries if entry.category in CRITICAL_CATEGORY_RANK),
                key=lambda entry: (-CRITICAL_CATEGORY_RANK[entry.category], entry.ply),
            )[:3]
        )
        counts = dict(category_counts)
        explanation = (
            "IA local: "
            f"{counts['best move']} mejores, {counts['good move']} buenas, "
            f"{counts['inaccuracy']} imprecisiones, {counts['mistake']} errores y "
            f"{counts['blunder']} blunders. "
            f"Se destacaron {len(best_moves)} mejores jugadas y {len(critical_moments)} momentos críticos."
        )
        return GameAnalysisSummary(category_counts, best_moves, critical_moments, explanation)

    def analysis_move(self) -> chess.Move | None:
        """Sugiere una jugada legal con libro exacto o búsqueda local breve.

        El libro evita recomendar aperturas inventadas: solo interviene en una
        posición estándar idéntica. El resto usa negamax a dos plies con una
        evaluación posicional ligera, por lo que sigue siendo una guía local y
        no pretende sustituir a Stockfish.
        """
        return self.analyse_position().best_move

    def _book_move(self) -> chess.Move | None:
        recommended_uci = OPENING_BOOK.get(_position_key(self.board))
        if recommended_uci is None:
            return None
        move = chess.Move.from_uci(recommended_uci)
        return move if move in self.board.legal_moves else None

    def _search_result(
        self,
        moves: list[chess.Move],
        deadline: float,
        clock: Callable[[], float],
        cancelled: Callable[[], bool] | None,
    ) -> AnalysisResult:
        """Itera profundidades; conserva sólo la última iteración terminada."""
        ordered = self._ordered_moves(self.board, moves)
        # El respaldo de profundidad cero está completo antes de entrar a la
        # búsqueda y garantiza una sugerencia legal aun en un dispositivo lento.
        best_move = ordered[0]
        best_score = self.analysis_score(best_move)
        completed_depth = 0
        # Dos plies es la primera iteración útil: reproduce la defensa ante
        # la réplica inmediata que ya ofrecía la versión anterior.
        for depth in range(2, MAX_SEARCH_DEPTH + 1):
            try:
                self._check_search_stop(deadline, clock, cancelled)
                candidate, score = self._search_at_depth(ordered, depth, deadline, clock, cancelled)
            except _SearchStopped:
                break
            best_move, best_score, completed_depth = candidate, score, depth
            if abs(best_score) >= MATE_SCORE:
                break
        white_score = best_score if self.board.turn == chess.WHITE else -best_score
        return AnalysisResult(self.board.fen(), best_move, self._normalize_evaluation(white_score), False, completed_depth)

    def _search_at_depth(
        self,
        moves: list[chess.Move],
        depth: int,
        deadline: float,
        clock: Callable[[], float],
        cancelled: Callable[[], bool] | None,
    ) -> tuple[chess.Move, int]:
        best_move: chess.Move | None = None
        best_score = -MATE_SCORE * 2
        for move in moves:
            self._check_search_stop(deadline, clock, cancelled)
            self.board.push(move)
            try:
                score = -self._negamax(self.board, depth - 1, -MATE_SCORE * 2, MATE_SCORE * 2, deadline, clock, cancelled)
            finally:
                self.board.pop()
            score += self._early_move_penalty(move)
            if best_move is None or (score, move.uci()) > (best_score, best_move.uci()):
                best_score, best_move = score, move
        assert best_move is not None
        return best_move, best_score

    @classmethod
    def _negamax(
        cls,
        board: chess.Board,
        depth: int,
        alpha: int,
        beta: int,
        deadline: float,
        clock: Callable[[], float],
        cancelled: Callable[[], bool] | None,
    ) -> int:
        cls._check_search_stop(deadline, clock, cancelled)
        if board.is_checkmate():
            return -MATE_SCORE - depth
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        if depth == 0:
            return cls._positional_evaluation(board, board.turn)

        best_score = -MATE_SCORE * 2
        for move in cls._ordered_moves(board, list(board.legal_moves)):
            board.push(move)
            try:
                score = -cls._negamax(board, depth - 1, -beta, -alpha, deadline, clock, cancelled)
            finally:
                board.pop()
            best_score = max(best_score, score)
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        return best_score

    @staticmethod
    def _check_search_stop(
        deadline: float,
        clock: Callable[[], float],
        cancelled: Callable[[], bool] | None,
    ) -> None:
        if (cancelled is not None and cancelled()) or clock() >= deadline:
            raise _SearchStopped

    @staticmethod
    def _normalize_evaluation(score: int) -> int:
        """Limita las evaluaciones mate para gráficos y clasificación estables."""
        return max(-MATE_SCORE, min(MATE_SCORE, score))

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
        # La penalización es deliberadamente menor que una captura segura de
        # peón: desarrolla la dama con cautela sin anular una ganancia material.
        if piece.piece_type == chess.QUEEN:
            penalty -= 30
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
