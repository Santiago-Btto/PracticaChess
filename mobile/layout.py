"""Medidas puras para mantener el tablero móvil visible en pantallas verticales."""
from __future__ import annotations

from dataclasses import dataclass


OUTER_PADDING = 10
SECTION_SPACING = 6
TITLE_HEIGHT = 38
STATUS_HEIGHT = 26
EVALUATION_LABEL_HEIGHT = 18
EVALUATION_CURVE_HEIGHT = 50
CONTROLS_HEIGHT = 100
FIXED_WIDGET_COUNT = 5


@dataclass(frozen=True)
class MobileLayoutMetrics:
    """Espacio fijo y superficie disponible para el tablero dentro de una ventana."""

    board_side: float
    board_area_height: float
    fixed_content_height: float


def mobile_layout_metrics(width: float, height: float) -> MobileLayoutMetrics:
    """Devuelve un tablero cuadrado que no invade la grilla de controles.

    La interfaz deja la superficie del tablero como la única zona flexible. Así,
    si la pantalla es baja, se reduce el tablero antes de ocultar los botones.
    """
    fixed_content_height = (
        2 * OUTER_PADDING
        + FIXED_WIDGET_COUNT * SECTION_SPACING
        + TITLE_HEIGHT
        + STATUS_HEIGHT
        + EVALUATION_LABEL_HEIGHT
        + EVALUATION_CURVE_HEIGHT
        + CONTROLS_HEIGHT
    )
    board_area_height = max(0.0, height - fixed_content_height)
    available_width = max(0.0, width - 2 * OUTER_PADDING)
    return MobileLayoutMetrics(
        board_side=min(available_width, board_area_height),
        board_area_height=board_area_height,
        fixed_content_height=fixed_content_height,
    )
