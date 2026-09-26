from pathlib import Path

from mobile.layout import CONTROLS_HEIGHT, mobile_layout_metrics


def test_portrait_mobile_layout_reserves_a_full_square_board_before_controls():
    """Los controles deben quedar debajo de un tablero completo en vertical."""
    metrics = mobile_layout_metrics(width=700, height=1450)

    assert metrics.board_side == 680
    assert metrics.board_area_height >= metrics.board_side
    assert metrics.fixed_content_height + metrics.board_side <= 1450


def test_mobile_layout_caps_the_board_to_available_height_on_short_screens():
    metrics = mobile_layout_metrics(width=700, height=600)

    assert metrics.board_side < 680
    assert metrics.board_side == metrics.board_area_height
    assert metrics.board_side > 0


def test_mobile_review_ui_exposes_progress_navigation_and_explanations():
    source = Path("mobile/app.py").read_text(encoding="utf-8")

    for text in (
        "Revisar partida",
        "Progreso de revisión",
        "Anterior",
        "Siguiente",
        "Salir revisión",
        "Jugada:",
        "Categoría:",
        "Evaluación:",
        "Alternativa:",
    ):
        assert text in source
    assert "Clock.schedule_once" in source


def test_mobile_review_controls_preserve_a_touch_sized_vertical_area():
    metrics = mobile_layout_metrics(width=700, height=1450)

    assert CONTROLS_HEIGHT >= 150
    assert metrics.board_side == 680
