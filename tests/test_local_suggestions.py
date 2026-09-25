from types import SimpleNamespace

import chess
import pygame

import config as cfg
from main import ChessApp
from src.board_gui import BoardGUI
from src.engine_wrapper import AnalysisRequest, AnalysisResult, ranked_moves
from src.game_state import GameMode, GameState


def test_ranked_moves_returns_the_best_and_second_engine_variation():
    best = chess.Move.from_uci("e2e4")
    alternative = chess.Move.from_uci("d2d4")

    assert ranked_moves([
        {"pv": [best]},
        {"pv": [alternative]},
    ]) == (best, alternative)


def test_ranked_moves_ignores_missing_or_duplicate_second_variation():
    best = chess.Move.from_uci("e2e4")

    assert ranked_moves([{"pv": [best]}, {"pv": [best]}, {"pv": []}]) == (best, None)


def test_blue_arrow_is_available_only_for_local_human_vs_human_games():
    alternative = chess.Move.from_uci("d2d4")
    app = ChessApp.__new__(ChessApp)
    app.show_ai_indicator = True
    app.show_blue_alternative = True
    app.engine = SimpleNamespace(
        is_available=lambda: True,
        get_result=lambda request_id: AnalysisResult(request_id, chess.STARTING_FEN, None, alternative, 0),
    )
    app._live_request = AnalysisRequest("live", chess.STARTING_FEN, "live", "live")

    app.state = GameState(mode=GameMode.HUMAN_VS_HUMAN)
    assert app._blue_suggestion_move() == alternative

    app.state = GameState(mode=GameMode.HUMAN_VS_AI)
    assert app._blue_suggestion_move() is None


def test_blue_arrow_toggle_hides_the_local_alternative():
    app = ChessApp.__new__(ChessApp)
    app.show_ai_indicator = True
    app.show_blue_alternative = False
    app.engine = SimpleNamespace(is_available=lambda: True)
    app._live_request = None
    app.state = GameState(mode=GameMode.HUMAN_VS_HUMAN)

    assert app._blue_suggestion_move() is None


def test_board_renders_blue_alternative_before_orange_best_move(monkeypatch):
    pygame.init()
    gui = BoardGUI(pygame.Surface((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT)), {})
    calls = []
    monkeypatch.setattr(
        "src.board_gui._draw_arrow",
        lambda surface, start, end, fill_color=None, outline_color=None: calls.append((fill_color, outline_color)),
    )

    gui._draw_arrow_overlay(chess.Move.from_uci("e2e4"), chess.Move.from_uci("d2d4"))

    assert calls == [
        (cfg.C_ALT_ARROW_FILL, cfg.C_ALT_ARROW_OUTLINE),
        (cfg.C_ARROW_FILL, cfg.C_ARROW_OUTLINE),
    ]


def test_board_does_not_draw_blue_arrow_when_it_duplicates_the_best_move(monkeypatch):
    pygame.init()
    gui = BoardGUI(pygame.Surface((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT)), {})
    calls = []
    monkeypatch.setattr(
        "src.board_gui._draw_arrow",
        lambda *args, **kwargs: calls.append(args),
    )
    best = chess.Move.from_uci("e2e4")

    gui._draw_arrow_overlay(best, best)

    assert len(calls) == 1


def test_blue_arrow_control_is_drawn_only_when_local_suggestions_are_enabled():
    pygame.init()
    gui = BoardGUI(pygame.Surface((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT)), {})
    kwargs = dict(
        board=chess.Board(), selected_square=None, legal_targets=[], last_move=None,
        best_move=None, score=None, dragging_piece=None, drag_pos=(0, 0),
        san_history=[], mode_label="Humano vs Humano", engine_available=True,
    )

    gui.draw(**kwargs, show_blue_arrow_toggle=True, blue_arrow_enabled=True)
    assert gui.btn_toggle_blue_arrow.width > 0

    gui.draw(**kwargs, show_blue_arrow_toggle=False)
    assert gui.btn_toggle_blue_arrow.width == 0
