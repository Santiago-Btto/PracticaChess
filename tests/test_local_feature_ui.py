import chess
import pygame

from src.board_gui import BoardGUI
from src.game_state import GameMode, GameState
from src.history_navigation import HistoryNavigator
from src.menu import MenuResult
from main import ChessApp


def _pieces():
    return {
        chess.Piece(piece_type, color): pygame.Surface((80, 80), pygame.SRCALPHA)
        for color in (chess.WHITE, chess.BLACK)
        for piece_type in range(chess.PAWN, chess.KING + 1)
    }


def test_menu_result_can_open_the_local_training_mode():
    result = MenuResult(GameMode.HUMAN_VS_HUMAN, chess.WHITE, 0, training_mode=True)

    assert result.training_mode is True
    assert result.tracking_mode is False


def test_board_panel_exposes_read_only_history_controls_and_accepts_chart_data():
    pygame.init()
    screen = pygame.display.set_mode((1100, 720))
    gui = BoardGUI(screen, _pieces())

    gui.draw(
        chess.Board(), None, [], None, None, None, None, (0, 0), ["e4", "c5"],
        "Humano vs Humano", True,
        evaluation_samples=[(0, 0), (1, 35), (2, -20)],
        opening_label="Defensa Siciliana (B20)",
        history_index=1,
        history_position_count=3,
    )

    assert gui.btn_history_previous.width > 0
    assert gui.btn_history_live.width > 0
    assert 1 in gui.history_move_rects


def test_main_history_view_and_opening_label_do_not_mutate_the_live_game():
    state = GameState()
    state.push_ai_move(chess.Move.from_uci("e2e4"))
    state.push_ai_move(chess.Move.from_uci("c7c5"))
    original_fen = state.board.fen()
    app = ChessApp.__new__(ChessApp)
    app.state = state
    app.history_navigator = HistoryNavigator.from_game_state(state)

    app.history_navigator.first()

    assert app._history_is_live() is False
    assert app._display_board().fen() == chess.Board().fen()
    assert state.board.fen() == original_fen
    assert app._opening_label() == "Defensa Siciliana (B20)"
