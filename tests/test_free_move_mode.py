from types import SimpleNamespace

import chess
import pygame
import pytest

import config as cfg
from main import ChessApp
from src.board_gui import BoardGUI, square_to_pixel
from src.game_state import GameMode, GameState


def _pieces():
    return {
        chess.Piece(piece_type, color): pygame.Surface((80, 80), pygame.SRCALPHA)
        for color in (chess.WHITE, chess.BLACK)
        for piece_type in range(chess.PAWN, chess.KING + 1)
    }


def test_free_relocation_resets_history_and_transient_rights():
    state = GameState()
    state.push_ai_move(chess.Move.from_uci("e2e4"))
    state.board.ep_square = chess.E3

    moved = state.relocate_piece_for_test(chess.A7, chess.A3)

    assert moved == chess.Piece(chess.PAWN, chess.BLACK)
    assert state.board.piece_at(chess.A7) is None
    assert state.board.piece_at(chess.A3) == chess.Piece(chess.PAWN, chess.BLACK)
    assert state.board.castling_rights == chess.BB_EMPTY
    assert state.board.ep_square is None
    assert state.san_history == []
    assert state.moves_played == []
    assert state.last_move is None
    assert state.board.move_stack == []


@pytest.mark.parametrize("side_to_move", [chess.WHITE, chess.BLACK])
def test_free_relocation_keeps_the_selected_side_to_move(side_to_move):
    state = GameState()
    state.board.turn = side_to_move

    state.relocate_piece_for_test(chess.A7, chess.A3)

    assert state.board.turn is side_to_move


def test_manual_turn_selection_resets_old_history_and_enables_that_side_moves():
    state = GameState()
    state.push_ai_move(chess.Move.from_uci("e2e4"))

    changed = state.set_turn_for_test(chess.WHITE)

    assert changed is True
    assert state.board.turn is chess.WHITE
    assert state.san_history == []
    assert state.moves_played == []
    assert state.board.move_stack == []
    state.select(chess.G1)
    assert chess.F3 in state.legal_targets


def test_free_relocation_refuses_to_capture_a_king_without_mutating_game():
    state = GameState()
    before = state.board.fen()

    moved = state.relocate_piece_for_test(chess.D1, chess.E8)

    assert moved is None
    assert state.board.fen() == before


def test_right_click_relocates_only_in_human_vs_human_and_resets_analysis():
    app = ChessApp.__new__(ChessApp)
    app.state = GameState(mode=GameMode.HUMAN_VS_HUMAN)
    app.gui = SimpleNamespace(flipped=False)
    app.test_mode_enabled = True
    app._dragging_piece = None
    app._drag_from = None
    app._drag_pos = (0, 0)
    app._on_test_position_edited = lambda: setattr(app, "edit_count", getattr(app, "edit_count", 0) + 1)

    app._handle_mouse(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=3, pos=square_to_pixel(chess.A7)
    ))
    app._handle_mouse(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=3, pos=square_to_pixel(chess.A3)
    ))

    assert app.state.board.piece_at(chess.A3) == chess.Piece(chess.PAWN, chess.BLACK)
    assert app.edit_count == 1

    app.state = GameState(mode=GameMode.HUMAN_VS_AI)
    app.test_mode_enabled = True
    app._handle_mouse(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=3, pos=square_to_pixel(chess.A7)
    ))
    assert app.state.selected_square is None


def test_right_click_source_is_independent_from_a_normal_left_click_selection():
    app = ChessApp.__new__(ChessApp)
    app.state = GameState(mode=GameMode.HUMAN_VS_HUMAN)
    app.gui = SimpleNamespace(flipped=False)
    app.test_mode_enabled = True
    app._dragging_piece = None
    app._drag_from = None
    app._drag_pos = (0, 0)
    app._on_test_position_edited = lambda: None

    app._handle_mouse(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=square_to_pixel(chess.E2)
    ))
    app._handle_mouse(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=3, pos=square_to_pixel(chess.A7)
    ))
    app._handle_mouse(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=3, pos=square_to_pixel(chess.A3)
    ))

    assert app.state.board.piece_at(chess.E2) == chess.Piece(chess.PAWN, chess.WHITE)
    assert app.state.board.piece_at(chess.A3) == chess.Piece(chess.PAWN, chess.BLACK)


def test_board_panel_shows_test_mode_toggle_only_when_requested():
    pygame.init()
    gui = BoardGUI(pygame.Surface((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT)), _pieces())
    kwargs = dict(
        board=chess.Board(), selected_square=None, legal_targets=[], last_move=None,
        best_move=None, score=None, dragging_piece=None, drag_pos=(0, 0),
        san_history=[], mode_label="Humano vs Humano", engine_available=True,
    )

    gui.draw(**kwargs, show_test_mode_toggle=True, test_mode_enabled=True)
    assert gui.btn_toggle_test_mode.width > 0

    gui.draw(**kwargs, show_test_mode_toggle=False)
    assert gui.btn_toggle_test_mode.width == 0


def test_board_panel_shows_turn_controls_only_while_test_mode_is_active():
    pygame.init()
    gui = BoardGUI(pygame.Surface((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT)), _pieces())
    kwargs = dict(
        board=chess.Board(), selected_square=None, legal_targets=[], last_move=None,
        best_move=None, score=None, dragging_piece=None, drag_pos=(0, 0),
        san_history=[], mode_label="Humano vs Humano", engine_available=True,
        show_test_mode_toggle=True,
    )

    gui.draw(**kwargs, test_mode_enabled=True, show_test_turn_controls=True)
    assert gui.btn_set_white_turn.width > 0
    assert gui.btn_set_black_turn.width > 0

    gui.draw(**kwargs, test_mode_enabled=False, show_test_turn_controls=False)
    assert gui.btn_set_white_turn.width == 0
    assert gui.btn_set_black_turn.width == 0


def test_test_mode_turn_buttons_set_either_side_and_reset_derived_data():
    pygame.init()
    gui = BoardGUI(pygame.Surface((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT)), _pieces())
    gui.draw(
        board=chess.Board(), selected_square=None, legal_targets=[], last_move=None,
        best_move=None, score=None, dragging_piece=None, drag_pos=(0, 0),
        san_history=[], mode_label="Humano vs Humano", engine_available=True,
        show_test_mode_toggle=True, test_mode_enabled=True,
        show_test_turn_controls=True,
    )
    app = ChessApp.__new__(ChessApp)
    app.state = GameState(mode=GameMode.HUMAN_VS_HUMAN)
    app.gui = gui
    app.history_navigator = None
    app.show_ai_indicator = True
    app.show_blue_alternative = True
    app.test_mode_enabled = True
    app._test_move_from = None
    app._on_test_position_edited = lambda: setattr(
        app, "edit_count", getattr(app, "edit_count", 0) + 1
    )

    assert app._handle_ui_click(gui.btn_set_black_turn.center) == "set_turn_black"
    assert app.state.board.turn is chess.BLACK
    assert app.edit_count == 1

    assert app._handle_ui_click(gui.btn_set_white_turn.center) == "set_turn_white"
    assert app.state.board.turn is chess.WHITE
    assert app.edit_count == 2
