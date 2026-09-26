import ast
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


def test_mobile_review_control_grid_has_a_slot_for_every_control():
    """Kivy aborta el layout si se añaden más hijos que filas por columnas."""
    tree = ast.parse(Path("mobile/app.py").read_text(encoding="utf-8"))
    build = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "build"
    )
    controls_grid = next(
        node.value
        for node in ast.walk(build)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "controls" for target in node.targets)
    )
    dimensions = {
        keyword.arg: keyword.value.value
        for keyword in controls_grid.keywords
        if keyword.arg in {"cols", "rows"} and isinstance(keyword.value, ast.Constant)
    }
    controls_added = sum(
        1
        for node in ast.walk(build)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "controls"
        and node.func.attr == "add_widget"
    )

    assert dimensions["cols"] * dimensions["rows"] >= controls_added


def test_mobile_review_controls_keep_touch_sized_rows():
    """Al añadir una fila, los botones siguen teniendo al menos 48 dp de alto."""
    tree = ast.parse(Path("mobile/app.py").read_text(encoding="utf-8"))
    build = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "build"
    )
    controls_grid = next(
        node.value
        for node in ast.walk(build)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "controls" for target in node.targets)
    )
    rows = next(
        keyword.value.value
        for keyword in controls_grid.keywords
        if keyword.arg == "rows" and isinstance(keyword.value, ast.Constant)
    )

    assert CONTROLS_HEIGHT / rows >= 48
