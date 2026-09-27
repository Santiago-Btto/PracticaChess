import chess
import pytest

from mobile.controller import (
    AnalysisRecord,
    AnalysisResult,
    GameAnalysisSummary,
    MobileGameController,
    ReviewEntry,
    display_to_square,
)


def test_structured_local_analysis_returns_a_legal_move_and_white_evaluation():
    game = MobileGameController("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1")

    result = game.analyse_position()

    assert isinstance(result, AnalysisResult)
    assert result.best_move in game.board.legal_moves
    assert isinstance(result.evaluation, int)
    assert result.fen == game.board.fen()


@pytest.mark.parametrize(
    "fen",
    (
        "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1",  # mate
        "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",  # stalemate
    ),
)
def test_structured_local_analysis_has_no_move_for_terminal_positions(fen):
    result = MobileGameController(fen).analyse_position()

    assert result.best_move is None
    assert result.terminal is True


def test_structured_analysis_normalizes_evaluation_for_both_sides():
    white = MobileGameController("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1").analyse_position()
    black = MobileGameController("4k3/4p3/8/8/8/8/8/4K3 b - - 0 1").analyse_position()

    assert white.evaluation > 0
    assert black.evaluation < 0


class AdvancingClock:
    def __init__(self, values):
        self._values = iter(values)
        self.last = 0.0

    def __call__(self):
        self.last = next(self._values, self.last + 1)
        return self.last


class QueuedExecutor:
    """Ejecutor determinista: la prueba decide cuándo entrega cada trabajo."""

    def __init__(self):
        self.jobs = []

    def submit(self, function):
        self.jobs.append(function)

    def run_next(self):
        self.jobs.pop(0)()


def test_iterative_search_preserves_a_completed_legal_result_when_budget_expires():
    game = MobileGameController("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1")

    result = game.analyse_position(purpose="hint", clock=AdvancingClock((0.0, 1.0)), budget_seconds=0.1)

    assert result.best_move in game.board.legal_moves
    assert result.depth == 0


def test_hint_and_review_use_independent_analysis_budgets():
    game = MobileGameController()

    assert game.analysis_budget("hint") < game.analysis_budget("review")
    assert game.analyse_position(purpose="hint").best_move in game.board.legal_moves
    assert game.analyse_position(purpose="review").best_move in game.board.legal_moves


@pytest.mark.parametrize("mutation", ("move", "undo", "reset"))
def test_stale_analysis_requests_cannot_replace_a_new_game_position(mutation):
    executor = QueuedExecutor()
    game = MobileGameController(executor=executor)
    old_fen = game.board.fen()
    game.request_analysis()

    if mutation == "move":
        game.tap(chess.E2)
        game.tap(chess.E4)
    elif mutation == "undo":
        game.tap(chess.E2)
        game.tap(chess.E4)
        game.undo()
    else:
        game.reset()

    while executor.jobs:
        executor.run_next()

    assert all(record.fen != old_fen or record.ply == len(game.san_history) for record in game.analysis_records)
    assert game.recommended_move in game.board.legal_moves


def test_current_analysis_result_is_recorded_by_fen_and_ply_not_material_proxy():
    game = MobileGameController()

    assert isinstance(game.analysis_records[0], AnalysisRecord)
    assert game.analysis_records[0].fen == game.board.fen()
    assert game.evaluation_curve == [game.analysis_records[0].evaluation]
    assert game.analysis_records[0].best_move in game.board.legal_moves


def test_undo_replaces_analysis_history_instead_of_resurrecting_discarded_ply():
    game = MobileGameController()
    for uci in ("e2e4", "e7e5"):
        game.tap(chess.Move.from_uci(uci).from_square)
        game.tap(chess.Move.from_uci(uci).to_square)
    discarded_fen = game.board.fen()

    game.undo()
    game.tap(chess.C7)
    game.tap(chess.C5)

    assert all(record.fen != discarded_fen for record in game.analysis_records)
    assert len(game.evaluation_curve) == len(game.san_history) + 1


def _finish_fools_mate(game):
    for uci in ("f2f3", "e7e5", "g2g4", "d8h4"):
        game.tap(chess.Move.from_uci(uci).from_square)
        game.tap(chess.Move.from_uci(uci).to_square)


def test_finished_game_snapshot_is_immutable_and_reconstructs_every_ply():
    game = MobileGameController()
    _finish_fools_mate(game)
    snapshot = game.finished_game
    assert snapshot is not None
    final_fen = game.board.fen()

    assert game.review_position(0).fen() == snapshot.initial_fen
    assert game.review_position(len(snapshot.moves)).fen() == final_fen
    assert game.board.fen() == final_fen


def test_review_snapshot_reconstructs_a_terminal_promotion_and_rejects_invalid_indices():
    game = MobileGameController("7k/5KP1/8/8/8/8/8/8 w - - 0 1")
    game.tap(chess.G7)
    game.tap(chess.G8)

    assert game.finished_game is not None
    assert game.review_position(1).is_checkmate()
    with pytest.raises(IndexError):
        game.review_position(-1)
    with pytest.raises(IndexError):
        game.review_position(2)


def test_review_classification_thresholds_and_terminal_entry_are_honest():
    categories = [
        MobileGameController.classify_loss(loss)
        for loss in (15, 16, 50, 51, 120, 121, 250, 251)
    ]
    assert categories == ["best move", "good move", "good move", "inaccuracy", "inaccuracy", "mistake", "mistake", "blunder"]

    entry = ReviewEntry(1, "Qh4#", "best move", 0, 1_000_000, None, True)
    assert entry.best_alternative_san is None
    assert entry.terminal is True


def test_postgame_review_emits_progress_and_one_entry_for_each_move():
    game = MobileGameController()
    _finish_fools_mate(game)

    game.start_review()

    assert game.review_progress == (len(game.san_history), len(game.san_history))
    assert len(game.review_entries) == len(game.san_history)
    assert all(isinstance(entry, ReviewEntry) for entry in game.review_entries)


def test_exiting_review_invalidates_late_review_results():
    executor = QueuedExecutor()
    game = MobileGameController(executor=executor)
    _finish_fools_mate(game)
    while executor.jobs:
        executor.run_next()

    game.start_review()
    game.exit_review()
    while executor.jobs:
        executor.run_next()

    assert game.review_active is False
    assert game.review_entries == []


def test_disabling_live_analysis_cancels_pending_hint_and_stops_board_refreshes():
    executor = QueuedExecutor()
    game = MobileGameController(executor=executor)
    pending = game._active_token

    game.set_live_analysis_enabled(False)

    assert game.live_analysis_enabled is False
    assert pending is not None and pending.cancelled.is_set()
    assert game.recommended_move is None
    queued_before_changes = len(executor.jobs)
    game.tap(chess.E2)
    game.tap(chess.E4)
    game.undo()
    game.reset()
    game.refresh_analysis()  # la vista llama esto después de voltear el tablero
    assert len(executor.jobs) == queued_before_changes

    while executor.jobs:
        executor.run_next()

    assert game.recommended_move is None


def test_reenabling_live_analysis_only_requests_current_position_and_review_stays_available():
    executor = QueuedExecutor()
    game = MobileGameController(executor=executor)
    game.set_live_analysis_enabled(False)
    executor.jobs.clear()
    game.tap(chess.F2)
    game.tap(chess.F3)
    current_fen = game.board.fen()

    game.set_live_analysis_enabled(True)

    assert game.live_analysis_enabled is True
    assert game._active_token is not None
    assert game._active_token.fen == current_fen
    executor.run_next()
    assert game.recommended_move in game.board.legal_moves

    game.set_live_analysis_enabled(False)
    executor.jobs.clear()
    _finish_fools_mate(game)
    assert game.finished_game is not None
    game.start_review()
    assert game.review_active is True
    assert executor.jobs


def test_general_review_summary_counts_categories_and_orders_highlights_deterministically():
    entries = (
        ReviewEntry(3, "Qh5", "blunder", 20, -300, "Qe2", False),
        ReviewEntry(1, "e4", "best move", 0, 0, None, False),
        ReviewEntry(5, "Nc3", "best move", 10, 5, None, False),
        ReviewEntry(2, "f6", "mistake", 0, -150, "e5", False),
        ReviewEntry(4, "a3", "inaccuracy", -10, -70, "Nf3", False),
        ReviewEntry(6, "d5", "good move", 5, 10, None, False),
    )

    summary = MobileGameController.summarize_review_entries(entries)

    assert isinstance(summary, GameAnalysisSummary)
    assert dict(summary.category_counts) == {
        "best move": 2,
        "good move": 1,
        "inaccuracy": 1,
        "mistake": 1,
        "blunder": 1,
    }
    assert [entry.san for entry in summary.best_moves] == ["e4", "Nc3"]
    assert [entry.san for entry in summary.critical_moments] == ["Qh5", "f6", "a3"]
    assert "IA local" in summary.explanation


def test_review_publishes_summary_only_after_all_entries_and_never_after_reset():
    executor = QueuedExecutor()
    game = MobileGameController(executor=executor)
    game.set_live_analysis_enabled(False)
    executor.jobs.clear()
    _finish_fools_mate(game)

    game.start_review()
    executor.run_next()

    assert len(game.review_entries) == 1
    assert game.review_summary is None
    while executor.jobs:
        executor.run_next()
    assert game.review_summary is not None
    assert sum(dict(game.review_summary.category_counts).values()) == len(game.san_history)

    game.start_review()
    game.reset()
    while executor.jobs:
        executor.run_next()
    assert game.review_summary is None


def test_empty_local_summary_has_every_category_without_highlights():
    summary = MobileGameController.summarize_review_entries(())

    assert dict(summary.category_counts) == {
        "best move": 0,
        "good move": 0,
        "inaccuracy": 0,
        "mistake": 0,
        "blunder": 0,
    }
    assert summary.best_moves == ()
    assert summary.critical_moments == ()


def test_terminal_review_entry_is_included_without_an_invented_alternative():
    terminal = ReviewEntry(1, "Qh4#", "best move", 0, 1_000_000, None, True)

    summary = MobileGameController.summarize_review_entries((terminal,))

    assert dict(summary.category_counts)["best move"] == 1
    assert summary.best_moves == (terminal,)
    assert summary.critical_moments == ()
    assert terminal.best_alternative_san is None


def test_completed_summary_keeps_review_navigation_and_clears_on_exit():
    executor = QueuedExecutor()
    game = MobileGameController(executor=executor)
    game.set_live_analysis_enabled(False)
    executor.jobs.clear()
    _finish_fools_mate(game)
    final_fen = game.board.fen()

    game.start_review()
    while executor.jobs:
        executor.run_next()

    assert game.review_summary is not None
    assert game.review_position(0).fen() == game.finished_game.initial_fen
    assert game.review_position(len(game.finished_game.moves)).fen() == final_fen
    game.exit_review()
    assert game.review_summary is None
    assert game.board.fen() == final_fen


def test_tapping_a_piece_selects_it_and_then_plays_a_legal_move():
    game = MobileGameController()

    selected = game.tap(chess.E2)
    assert selected.kind == "selected"
    assert game.selected_square == chess.E2
    assert set(game.legal_targets) == {chess.E3, chess.E4}

    moved = game.tap(chess.E4)
    assert moved.kind == "moved"
    assert moved.san == "e4"
    assert game.board.piece_at(chess.E4) == chess.Piece(chess.PAWN, chess.WHITE)
    assert game.board.turn == chess.BLACK
    assert game.san_history == ["e4"]


def test_illegal_backward_pawn_tap_keeps_the_position_and_turn():
    game = MobileGameController("4k3/8/8/8/4P3/8/8/4K3 w - - 0 1")

    game.tap(chess.E4)
    outcome = game.tap(chess.E3)

    assert outcome.kind == "deselected"
    assert game.board.piece_at(chess.E4) == chess.Piece(chess.PAWN, chess.WHITE)
    assert game.board.piece_at(chess.E3) is None
    assert game.board.turn == chess.WHITE


def test_mobile_controller_promotes_a_pawn_to_a_queen():
    game = MobileGameController("4k3/P7/8/8/8/8/8/4K3 w - - 0 1")

    game.tap(chess.A7)
    outcome = game.tap(chess.A8)

    assert outcome.kind == "moved"
    assert outcome.san == "a8=Q+"
    assert game.board.piece_at(chess.A8) == chess.Piece(chess.QUEEN, chess.WHITE)


def test_display_coordinates_follow_the_selected_orientation():
    assert display_to_square(0, 0, flipped=False) == chess.A8
    assert display_to_square(7, 7, flipped=False) == chess.H1
    assert display_to_square(0, 0, flipped=True) == chess.H1
    assert display_to_square(7, 7, flipped=True) == chess.A8


def test_mobile_analysis_exposes_a_legal_orange_arrow_and_evaluation_curve():
    game = MobileGameController()

    move = game.analysis_move()

    assert move in game.board.legal_moves
    assert game.evaluation_curve == [0]

    game.tap(move.from_square)
    game.tap(move.to_square)

    assert len(game.evaluation_curve) == 2
    assert isinstance(game.evaluation_curve[-1], int)


def test_mobile_analysis_is_available_immediately_and_refreshes_after_game_lifecycle():
    game = MobileGameController()

    assert game.recommended_move in game.board.legal_moves

    game.tap(chess.E2)
    game.tap(chess.E4)
    assert game.recommended_move in game.board.legal_moves

    assert game.undo() is True
    assert game.recommended_move in game.board.legal_moves

    game.reset()
    assert game.recommended_move in game.board.legal_moves


def test_mobile_analysis_uses_an_exact_local_opening_book_for_standard_lines():
    game = MobileGameController()

    assert game.analysis_move() == chess.Move.from_uci("e2e4")
    assert game.analysis_source == "book"

    game.tap(chess.E2)
    game.tap(chess.E4)
    assert game.analysis_move() == chess.Move.from_uci("e7e5")
    assert game.analysis_source == "book"

    sicilian = MobileGameController()
    for uci in ("e2e4", "c7c5"):
        sicilian.tap(chess.Move.from_uci(uci).from_square)
        sicilian.tap(chess.Move.from_uci(uci).to_square)
    assert sicilian.analysis_move() == chess.Move.from_uci("g1f3")
    assert sicilian.analysis_source == "book"


def test_mobile_analysis_falls_back_to_search_outside_the_exact_opening_book():
    game = MobileGameController()
    game.tap(chess.A2)
    game.tap(chess.A3)

    move = game.analysis_move()

    assert move in game.board.legal_moves
    assert game.analysis_source == "search"


@pytest.mark.parametrize(
    ("played_moves", "expected"),
    [
        (("e2e4", "e7e6"), "d2d4"),  # Francesa
        (("d2d4", "d7d5", "c2c4"), "e7e6"),  # Gambito de Dama
        (("d2d4", "g8f6", "c2c4"), "g7g6"),  # India de Rey
    ],
)
def test_mobile_opening_book_covers_other_standard_exact_positions(played_moves, expected):
    game = MobileGameController()
    for uci in played_moves:
        move = chess.Move.from_uci(uci)
        game.tap(move.from_square)
        game.tap(move.to_square)

    assert game.analysis_move() == chess.Move.from_uci(expected)
    assert game.analysis_source == "book"


def test_mobile_analysis_prioritizes_a_forced_checkmate_over_material():
    game = MobileGameController("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1")

    move = game.analysis_move()
    after_move = game.board.copy(stack=False)
    after_move.push(move)

    assert after_move.is_checkmate()


def test_mobile_analysis_avoids_a_move_that_allows_mate_in_one():
    game = MobileGameController(
        "rn2k3/3p4/p1p3P1/1p2p1B1/PP1qP1Qr/3P3p/2PR1PB1/2KR2N1 b - - 2 32"
    )

    move = game.analysis_move()

    assert move not in {chess.Move.from_uci("d7d6"), chess.Move.from_uci("d7d5")}


def test_local_analysis_prioritizes_capture_and_undo_restores_the_curve():
    game = MobileGameController("r3k3/8/8/8/8/8/8/Q3K3 w - - 0 1")

    move = game.analysis_move()

    assert move == chess.Move.from_uci("a1a8")
    start_curve = game.evaluation_curve[:]
    game.tap(move.from_square)
    game.tap(move.to_square)
    assert game.evaluation_curve[-1] > start_curve[-1]

    assert game.undo() is True
    assert game.evaluation_curve == start_curve


def test_local_analysis_prefers_a_safe_capture_over_a_quiet_move():
    game = MobileGameController("4k3/8/8/8/8/8/3p4/K2Q4 w - - 0 1")

    move = game.analysis_move()

    assert move == chess.Move.from_uci("d1d2")
    assert move in game.board.legal_moves


def test_local_analysis_avoids_a_capture_that_loses_the_queen_to_the_king():
    game = MobileGameController("1k6/r7/8/8/8/8/8/Q3K3 w - - 0 1")

    move = game.analysis_move()

    assert move in game.board.legal_moves
    assert move != chess.Move.from_uci("a1a8")
