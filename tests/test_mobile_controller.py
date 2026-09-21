import chess

from mobile.controller import MobileGameController, display_to_square


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
