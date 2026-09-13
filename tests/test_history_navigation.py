import chess

from src.game_state import GameState
from src.history_navigation import HistoryNavigator


def _play(state: GameState, uci: str) -> None:
    move = chess.Move.from_uci(uci)
    assert state.push_ai_move(move) is not None


def test_navigator_views_each_historical_position_without_changing_active_game():
    state = GameState()
    _play(state, "e2e4")
    _play(state, "e7e5")
    active_fen = state.board.fen()
    active_moves = list(state.moves_played)

    navigator = HistoryNavigator.from_game_state(state)

    assert navigator.active_index == 2
    assert navigator.first() is True
    assert navigator.active_index == 0
    assert navigator.view_board.fen() == chess.Board().fen()
    assert navigator.next() is True
    assert navigator.view_board.peek().uci() == "e2e4"
    assert state.board.fen() == active_fen
    assert state.moves_played == active_moves


def test_navigator_clamps_at_ends_and_returns_defensive_board_copies():
    state = GameState()
    _play(state, "d2d4")
    navigator = HistoryNavigator.from_game_state(state)

    assert navigator.previous() is True
    assert navigator.previous() is False
    assert navigator.next() is True
    assert navigator.next() is False

    viewed = navigator.view_board
    viewed.clear()
    assert navigator.view_board.fen() == state.board.fen()


def test_navigator_can_jump_to_any_position_and_keeps_its_own_snapshot():
    state = GameState()
    _play(state, "g1f3")
    _play(state, "d7d5")
    _play(state, "c2c4")
    navigator = HistoryNavigator.from_game_state(state)
    recorded_latest_fen = state.board.fen()

    assert navigator.go_to(1) is True
    assert navigator.active_index == 1
    assert navigator.view_board.peek().uci() == "g1f3"
    assert navigator.go_to(99) is False
    assert navigator.active_index == 1

    assert state.undo() is True
    assert navigator.latest() is True
    assert navigator.view_board.fen() == recorded_latest_fen
