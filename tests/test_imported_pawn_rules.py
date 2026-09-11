"""Regression coverage for imported pawns in both display orientations."""
import chess
import pytest

from src.board_gui import pixel_to_square, square_to_pixel
from src.game_state import GameState


@pytest.mark.parametrize("flipped", [False, True])
@pytest.mark.parametrize("method", ["click", "drag", "ai"])
@pytest.mark.parametrize(
    "placement,turn,origin,forward,backward",
    [
        ("7k/4P3/8/8/8/8/8/K7", "w", "e7", "e8", "e6"),
        ("7k/8/8/8/8/8/4p3/K7", "b", "e2", "e1", "e3"),
    ],
)
def test_imported_pawns_only_promote_forward_in_either_view(
    flipped, method, placement, turn, origin, forward, backward
):
    state = GameState(initial_fen=f"{placement} {turn} - - 0 1")
    before = state.board.fen()

    def square_clicked(name):
        # Exercise the same mapping used by the game mouse handlers.
        return pixel_to_square(*square_to_pixel(chess.parse_square(name), flipped), flipped)

    def move_to(destination):
        start, end = square_clicked(origin), square_clicked(destination)
        if method == "click":
            assert state.select(start)
            return state.try_move(end)
        if method == "drag":
            return state.try_move_drag(start, end)
        return state.push_ai_move(chess.Move(start, end, promotion=chess.QUEEN))

    assert move_to(backward) is None
    assert state.board.fen() == before
    move = move_to(forward)
    assert move == chess.Move.from_uci(origin + forward + "q")
    assert state.board.piece_at(chess.parse_square(forward)) == chess.Piece(
        chess.QUEEN, turn == "w"
    )
    assert state.undo()
    assert state.board.fen() == before
    state.reset()
    assert state.board.fen() == before


def test_reported_app_position_explains_the_apparent_backward_promotion():
    # Position visible in the user's app screenshot (already imported).
    state = GameState(initial_fen="RN2RK2/PPn3PP/3B4/8/5p2/p2N4/1p1p2pp/r1b2k1r w - - 0 1")
    assert state.try_move_drag(chess.H7, chess.H6) is None
    assert state.try_move_drag(chess.H7, chess.H8) == chess.Move.from_uci("h7h8q")
