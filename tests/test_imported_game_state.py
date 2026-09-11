import chess

from src.game_state import GameMode, GameState


def test_game_state_starts_from_imported_fen_with_selected_turn():
    fen = "4k3/8/8/3Q4/8/8/8/4K3 b - - 0 1"

    state = GameState(mode=GameMode.HUMAN_VS_HUMAN, initial_fen=fen)

    assert state.board.fen() == fen
    assert state.board.turn is chess.BLACK


def test_restart_returns_to_the_imported_position():
    fen = "4k3/8/8/3Q4/8/8/8/4K3 w - - 0 1"
    state = GameState(initial_fen=fen)
    state.board.push(next(iter(state.board.legal_moves)))

    state.reset()

    assert state.board.fen() == fen
