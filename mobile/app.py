"""Interfaz móvil táctil, deliberadamente más simple que la versión de PC."""
from __future__ import annotations

import math
from pathlib import Path

import chess

if __package__:
    from .controller import MobileGameController, display_to_square
    from .layout import (
        CONTROLS_HEIGHT,
        EVALUATION_CURVE_HEIGHT,
        EVALUATION_LABEL_HEIGHT,
        OUTER_PADDING,
        SECTION_SPACING,
        STATUS_HEIGHT,
        TITLE_HEIGHT,
    )
else:  # Buildozer ejecuta main.py como script dentro del APK.
    from controller import MobileGameController, display_to_square
    from layout import (
        CONTROLS_HEIGHT,
        EVALUATION_CURVE_HEIGHT,
        EVALUATION_LABEL_HEIGHT,
        OUTER_PADDING,
        SECTION_SPACING,
        STATUS_HEIGHT,
        TITLE_HEIGHT,
    )

try:
    from kivy.app import App
    from kivy.graphics import Color, Ellipse, Line, RoundedRectangle, Triangle
    from kivy.metrics import dp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.floatlayout import FloatLayout
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.image import Image
    from kivy.uix.label import Label
    from kivy.uix.widget import Widget
except ModuleNotFoundError as exc:  # permite usar la lógica sin instalar Kivy
    raise RuntimeError(
        "La interfaz móvil requiere Kivy. Instala mobile/requirements-mobile.txt "
        "o compila el APK con Buildozer."
    ) from exc


LIGHT_SQUARE = (0.93, 0.89, 0.72, 1)
DARK_SQUARE = (0.47, 0.60, 0.31, 1)
SELECTED_SQUARE = (0.95, 0.74, 0.22, 1)
LEGAL_TARGET = (0.67, 0.81, 0.40, 1)
ORANGE = (0.95, 0.48, 0.04, 0.88)
PIECE_ASSET_DIRECTORY = Path(__file__).resolve().parent / "assets/pieces"


def piece_asset_path(piece: chess.Piece) -> str:
    """Devuelve la imagen local de la pieza, incluida dentro del APK."""
    color = "w" if piece.color == chess.WHITE else "b"
    letter = piece.symbol().upper()
    return str(PIECE_ASSET_DIRECTORY / f"{color}{letter}.png")


class PieceWidget(Image):
    """Pieza Cburnett local, legible y sin depender de glifos Android."""

    def __init__(self, piece: chess.Piece, **kwargs):
        super().__init__(
            source=piece_asset_path(piece),
            allow_stretch=True,
            keep_ratio=True,
            mipmap=True,
            **kwargs,
        )
        self.piece = piece


class EvaluationCurve(Widget):
    """Curva compacta de material en centipeones, visible durante toda la partida."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.values: list[int] = [0]
        self.bind(pos=self._draw, size=self._draw)

    def set_values(self, values: list[int]) -> None:
        self.values = values or [0]
        self._draw()

    def _draw(self, *_args) -> None:
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return
        x, y, w, h = self.x, self.y, self.width, self.height
        with self.canvas:
            Color(0.10, 0.12, 0.20, 0.18)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[dp(8)])
            Color(0.68, 0.72, 0.82, 0.45)
            Line(points=[x + dp(8), y + h / 2, x + w - dp(8), y + h / 2], width=dp(1))
            scale = max(300, max(abs(value) for value in self.values))
            points = []
            denominator = max(1, len(self.values) - 1)
            for index, value in enumerate(self.values):
                point_x = x + dp(10) + (w - dp(20)) * index / denominator
                point_y = y + h / 2 + (h * 0.38) * value / scale
                points.extend([point_x, point_y])
            Color(0.20, 0.52, 0.91, 1)
            if len(points) == 2:
                Ellipse(pos=(points[0] - dp(2), points[1] - dp(2)), size=(dp(4), dp(4)))
            else:
                Line(points=points, width=dp(2.2))


class MoveArrow(Widget):
    """Flecha naranja sobrepuesta; no consume los toques destinados al tablero."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.move: chess.Move | None = None
        self.flipped = False
        self.bind(pos=self._draw, size=self._draw)

    def set_move(self, move: chess.Move | None, flipped: bool) -> None:
        self.move = move
        self.flipped = flipped
        self._draw()

    def _draw(self, *_args) -> None:
        self.canvas.clear()
        if self.move is None or self.width <= 0 or self.height <= 0:
            return
        start = self._center(self.move.from_square)
        end = self._center(self.move.to_square)
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        head = min(self.width, self.height) * 0.075
        left = (end[0] - head * math.cos(angle - 0.55), end[1] - head * math.sin(angle - 0.55))
        right = (end[0] - head * math.cos(angle + 0.55), end[1] - head * math.sin(angle + 0.55))
        with self.canvas:
            Color(*ORANGE)
            Line(points=[start[0], start[1], end[0], end[1]], width=dp(5))
            Triangle(points=[end[0], end[1], left[0], left[1], right[0], right[1]])

    def _center(self, square: chess.Square) -> tuple[float, float]:
        file_index = chess.square_file(square)
        rank_index = chess.square_rank(square)
        column = 7 - file_index if self.flipped else file_index
        row = rank_index if self.flipped else 7 - rank_index
        return (
            self.x + (column + 0.5) * self.width / 8,
            self.y + (7 - row + 0.5) * self.height / 8,
        )


class ChessMobileApp(App):
    """Partida local legible: tablero, curva, flecha y cuatro controles."""

    title = "PracticaChess"

    def build(self):
        self.controller = MobileGameController()
        self.flipped = False

        root = BoxLayout(
            orientation="vertical", padding=dp(OUTER_PADDING), spacing=dp(SECTION_SPACING)
        )
        root.add_widget(
            Label(
                text="[b]PracticaChess[/b]", markup=True, font_size="24sp",
                size_hint_y=None, height=dp(TITLE_HEIGHT),
            )
        )
        self.status = Label(
            size_hint_y=None, height=dp(STATUS_HEIGHT), color=(0.36, 0.42, 0.58, 1)
        )
        root.add_widget(self.status)

        root.add_widget(
            Label(
                text="Evaluación", size_hint_y=None, height=dp(EVALUATION_LABEL_HEIGHT),
                color=(0.42, 0.47, 0.61, 1),
            )
        )
        self.evaluation = EvaluationCurve(size_hint_y=None, height=dp(EVALUATION_CURVE_HEIGHT))
        root.add_widget(self.evaluation)

        # La superficie es el único tramo flexible. El tablero se calcula dentro
        # de ella y queda cuadrado, sin desplazar ni cubrir los controles.
        self.board_surface = FloatLayout(size_hint_y=1)
        self.board_surface.bind(pos=self._layout_board, size=self._layout_board)
        self.board_grid = GridLayout(cols=8, spacing=0, size_hint=(None, None))
        self.board_surface.add_widget(self.board_grid)
        self.arrow = MoveArrow(size_hint=(None, None))
        self.board_surface.add_widget(self.arrow)
        root.add_widget(self.board_surface)

        controls = GridLayout(
            cols=2, size_hint_y=None, height=dp(CONTROLS_HEIGHT), spacing=dp(SECTION_SPACING)
        )
        controls.add_widget(self._control_button("Voltear", self._flip))
        controls.add_widget(self._control_button("Deshacer", self._undo))
        controls.add_widget(self._control_button("Reiniciar", self._reset))
        controls.add_widget(
            Label(text="Análisis automático", color=(0.42, 0.70, 0.95, 1))
        )
        root.add_widget(controls)
        self._redraw()
        return root

    def _layout_board(self, *_args) -> None:
        """Ubica el tablero completo al inicio de su área flexible."""
        side = min(self.board_surface.width, self.board_surface.height)
        x = self.board_surface.x + (self.board_surface.width - side) / 2
        y = self.board_surface.top - side
        self.board_grid.pos = (x, y)
        self.board_grid.size = (side, side)
        self.arrow.pos = (x, y)
        self.arrow.size = (side, side)

    def _control_button(self, text: str, callback) -> Button:
        button = Button(text=text, background_normal="", background_color=(0.18, 0.40, 0.72, 1))
        button.bind(on_release=callback)
        return button

    def _tap_square(self, square: chess.Square) -> None:
        self.controller.tap(square)
        self._redraw()

    def _undo(self, _button) -> None:
        self.controller.undo()
        self._redraw()

    def _flip(self, _button) -> None:
        self.flipped = not self.flipped
        self.controller.refresh_analysis()
        self._redraw()

    def _reset(self, _button) -> None:
        self.controller.reset()
        self._redraw()

    def _redraw(self) -> None:
        self.board_grid.clear_widgets()
        for row in range(8):
            for column in range(8):
                square = display_to_square(row, column, flipped=self.flipped)
                piece = self.controller.board.piece_at(square)
                color = LIGHT_SQUARE if (row + column) % 2 == 0 else DARK_SQUARE
                if square == self.controller.selected_square:
                    color = SELECTED_SQUARE
                elif square in self.controller.legal_targets:
                    color = LEGAL_TARGET
                button = Button(text="", background_normal="", background_color=color)
                if piece:
                    piece_widget = PieceWidget(piece=piece, pos=button.pos, size=button.size)
                    button.bind(
                        pos=lambda _button, value, view=piece_widget: setattr(view, "pos", value),
                        size=lambda _button, value, view=piece_widget: setattr(view, "size", value),
                    )
                    button.add_widget(piece_widget)
                button.bind(on_release=lambda _button, selected=square: self._tap_square(selected))
                self.board_grid.add_widget(button)

        self.evaluation.set_values(self.controller.evaluation_curve)
        self.arrow.set_move(self.controller.recommended_move, self.flipped)
        turn = "Blancas" if self.controller.board.turn == chess.WHITE else "Negras"
        if self.controller.board.is_game_over(claim_draw=True):
            self.status.text = f"Partida terminada: {self.controller.board.result(claim_draw=True)}"
        elif self.controller.recommended_move:
            self.status.text = (
                f"Turno: {turn} · sugerencia: {self.controller.recommended_move.uci()}"
            )
        else:
            self.status.text = f"Turno: {turn} · toca una pieza y luego su destino"
