import chess

from src.game_state import GameState
from src.screenshot_tracking import ScreenshotTracker


def _placement_after(board: chess.Board, uci: str) -> str:
    board.push_uci(uci)
    return board.board_fen()


def test_tracker_records_the_unique_legal_move_from_a_new_capture():
    state = GameState()
    tracker = ScreenshotTracker(state)
    board = chess.Board()

    result = tracker.observe(_placement_after(board, "e2e4"))

    assert result.accepted is True
    assert result.san == "e4"
    assert state.san_history == ["e4"]
    assert state.board.board_fen() == board.board_fen()


def test_tracker_accepts_consecutive_white_and_black_captures():
    state = GameState()
    tracker = ScreenshotTracker(state)
    board = chess.Board()

    tracker.observe(_placement_after(board, "d2d4"))
    result = tracker.observe(_placement_after(board, "d7d5"))

    assert result.accepted is True
    assert result.san == "d5"
    assert state.san_history == ["d4", "d5"]


def test_tracker_rejects_a_capture_without_a_new_legal_move():
    state = GameState()
    tracker = ScreenshotTracker(state)

    result = tracker.observe(state.board.board_fen())

    assert result.accepted is False
    assert "sin cambios" in result.message.lower()
