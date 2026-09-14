import chess
import pygame

import config as cfg
from src.board_gui import BoardGUI, square_to_rect
from src.game_state import GameMode
from src.menu import MenuScreen


def _screen():
    pygame.init()
    return pygame.display.set_mode((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT))


def test_board_uses_the_palette_selected_for_each_supported_visual_theme():
    screen = _screen()

    chess_com = BoardGUI(screen, {}, visual_theme=cfg.VISUAL_THEME_CHESS_COM)
    chess_com._draw_board_squares(chess.Board(), None, [], None)
    assert screen.get_at(square_to_rect(chess.A1).center)[:3] == cfg.C_DARK_SQ

    lichess = BoardGUI(screen, {}, visual_theme=cfg.VISUAL_THEME_LICHESS)
    lichess._draw_board_squares(chess.Board(), None, [], None)
    assert screen.get_at(square_to_rect(chess.A1).center)[:3] == (181, 136, 99)
    assert screen.get_at(square_to_rect(chess.B1).center)[:3] == (240, 217, 181)


def test_menu_theme_selection_is_returned_with_the_game_result():
    menu = MenuScreen(_screen(), engine_available=True)

    menu._handle_click(menu._btn_theme_lichess.rect.center)
    result = menu._handle_click(menu._btn_play.rect.center)

    assert result.mode is GameMode.HUMAN_VS_AI
    assert result.visual_theme == cfg.VISUAL_THEME_LICHESS


def test_menu_can_switch_back_to_chess_com_after_lichess_is_selected():
    menu = MenuScreen(_screen(), visual_theme=cfg.VISUAL_THEME_LICHESS)

    menu._handle_click(menu._btn_theme_chess.rect.center)
    result = menu._handle_click(menu._btn_play.rect.center)

    assert result.visual_theme == cfg.VISUAL_THEME_CHESS_COM
