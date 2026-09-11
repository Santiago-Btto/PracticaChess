import pygame

import config as cfg
from src.game_state import GameMode
from src.menu import MenuScreen


def _screen():
    pygame.init()
    return pygame.display.set_mode((1, 1))


def _indicator_center(menu):
    """Centro esperado del selector en el diseño del modo actualmente elegido."""
    cx = cfg.WINDOW_WIDTH // 2
    indicator_y = 330 if menu._mode is GameMode.HUMAN_VS_HUMAN else 498
    return cx + 75, indicator_y + 21


def test_ai_indicator_can_be_turned_off_immediately_after_switching_to_human_vs_human():
    menu = MenuScreen(_screen(), engine_available=True)
    menu._draw((0, 0))  # Deja el selector en la distribución de Humano vs IA.

    menu._handle_click(menu._btn_hvh.rect.center)
    menu._handle_click(_indicator_center(menu))

    assert menu._mode is GameMode.HUMAN_VS_HUMAN
    assert menu._ai_indicator is False
    assert menu._btn_ind_on.selected is False
    assert menu._btn_ind_off.selected is True
    assert menu._handle_click(menu._btn_play.rect.center).show_ai_indicator is False


def test_ai_indicator_choice_is_preserved_when_switching_back_to_human_vs_ai():
    menu = MenuScreen(_screen(), engine_available=True)
    menu._mode = GameMode.HUMAN_VS_HUMAN
    menu._draw((0, 0))  # Deja el selector en la distribución de Humano vs Humano.

    menu._handle_click(_indicator_center(menu))
    menu._handle_click(menu._btn_hvai.rect.center)

    assert menu._mode is GameMode.HUMAN_VS_AI
    assert menu._ai_indicator is False
    assert menu._handle_click(menu._btn_play.rect.center).show_ai_indicator is False

    # Sin esperar otro frame, el clic debe usar la geometría del nuevo modo.
    menu._handle_click((cfg.WINDOW_WIDTH // 2 - 75, 498 + 21))

    assert menu._ai_indicator is True
    assert menu._btn_ind_on.selected is True
    assert menu._btn_ind_off.selected is False
    assert menu._handle_click(menu._btn_play.rect.center).show_ai_indicator is True
