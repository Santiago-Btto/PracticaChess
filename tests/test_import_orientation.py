import chess
import pytest


@pytest.mark.parametrize("white_bottom", [True, False])
def test_orientation_maps_squares_without_swapping_piece_colors(white_bottom):
    from src.position_import import orient_placement

    raw = "RN2RK2/PP4PP/8/8/8/8/pp4pp/r1b2k1r"
    board = chess.Board(f"{orient_placement(raw, white_bottom=white_bottom)} w - - 0 1")
    assert board.piece_at(chess.A8 if white_bottom else chess.H1) == chess.Piece(chess.ROOK, chess.WHITE)
    assert board.piece_at(chess.H1 if white_bottom else chess.A8) == chess.Piece(chess.ROOK, chess.BLACK)
    assert board.piece_at(chess.A7 if white_bottom else chess.H2) == chess.Piece(chess.PAWN, chess.WHITE)
    assert orient_placement(board.board_fen(), white_bottom=white_bottom) == raw


@pytest.mark.parametrize("white_bottom", [True, False])
def test_upright_sprites_in_both_capture_orientations_recover_same_position(white_bottom):
    from pathlib import Path
    from test_position_import import _board_image
    from src.position_import import detect_position_from_image, orient_placement

    pieces = {"e1": "wK", "a2": "wP", "b7": "wP", "e8": "bK", "h7": "bP", "g2": "bP"}
    if not white_bottom:
        pieces = {chess.square_name(63 - chess.parse_square(sq)): piece for sq, piece in pieces.items()}
    assets = Path("assets/pieces")
    raw = detect_position_from_image(_board_image(pieces, assets), assets)
    assert orient_placement(raw, white_bottom=white_bottom) == "4k3/1P5p/8/8/8/8/P5p1/4K3"


@pytest.mark.parametrize("flipped", [True, False])
@pytest.mark.parametrize("human_vs_ai", [True, False])
def test_imported_game_preserves_explicit_capture_view(flipped, human_vs_ai):
    from unittest.mock import Mock
    import pygame
    from main import ChessApp
    from src.menu import MenuResult
    from src.game_state import GameMode

    pygame.init()
    app = ChessApp.__new__(ChessApp)
    app.screen = pygame.display.set_mode((1, 1))
    app.piece_images = {}
    app.engine = Mock()
    app.engine.is_available.return_value = False
    mode = GameMode.HUMAN_VS_AI if human_vs_ai else GameMode.HUMAN_VS_HUMAN
    result = MenuResult(mode, chess.BLACK, 0, initial_fen=chess.STARTING_FEN, initial_flipped=flipped)
    app._start_game(result)
    assert app.gui.flipped is flipped
    assert app.state.board.fen() == chess.STARTING_FEN
