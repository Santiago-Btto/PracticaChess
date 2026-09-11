import pygame

from src.game_state import GameMode
from src.menu import MenuScreen


def _screen():
    pygame.init()
    return pygame.display.set_mode((1, 1))


def test_without_stockfish_menu_defaults_to_human_vs_human():
    menu = MenuScreen(_screen(), engine_available=False)

    result = menu._handle_click(menu._btn_play.rect.center)

    assert result is not None
    assert result.mode is GameMode.HUMAN_VS_HUMAN


def test_without_stockfish_cannot_start_human_vs_ai():
    menu = MenuScreen(_screen(), engine_available=False)

    menu._handle_click(menu._btn_hvai.rect.center)
    result = menu._handle_click(menu._btn_play.rect.center)

    assert result is not None
    assert result.mode is GameMode.HUMAN_VS_HUMAN


def test_with_stockfish_menu_keeps_human_vs_ai_default():
    menu = MenuScreen(_screen(), engine_available=True)

    result = menu._handle_click(menu._btn_play.rect.center)

    assert result is not None
    assert result.mode is GameMode.HUMAN_VS_AI
