import chess
import pygame

import config
from src.board_gui import BoardGUI, square_to_rect


def test_board_uses_chess_com_green_and_cream_squares():
    assert config.C_LIGHT_SQ == (238, 238, 210)
    assert config.C_DARK_SQ == (118, 150, 86)


def test_a1_is_dark_and_square_colors_follow_the_logical_board_when_flipped():
    pygame.init()
    screen = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    gui = BoardGUI(screen, {})

    gui._draw_board_squares(chess.Board(), None, [], None)
    assert screen.get_at(square_to_rect(chess.A1).center)[:3] == config.C_DARK_SQ
    assert screen.get_at(square_to_rect(chess.B1).center)[:3] == config.C_LIGHT_SQ

    gui.flipped = True
    gui._draw_board_squares(chess.Board(), None, [], None)
    assert screen.get_at(square_to_rect(chess.A1, flipped=True).center)[:3] == config.C_DARK_SQ
    assert screen.get_at(square_to_rect(chess.H1, flipped=True).center)[:3] == config.C_LIGHT_SQ
