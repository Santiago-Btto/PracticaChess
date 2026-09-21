"""Interfaz móvil táctil, deliberadamente más simple que la versión de PC."""
from __future__ import annotations

import math

import chess

if __package__:
    from .controller import MobileGameController, display_to_square
else:  # Buildozer ejecuta main.py como script dentro del APK.
    from controller import MobileGameController, display_to_square

try:
    from kivy.app import App
    from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle, Triangle
    from kivy.metrics import dp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.floatlayout import FloatLayout
    from kivy.uix.gridlayout import GridLayout
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


class PieceWidget(Widget):
    """Pieza vectorial local: no depende de los glifos Unicode de Android."""

    def __init__(self, piece: chess.Piece, **kwargs):
        super().__init__(**kwargs)
        self.piece = piece
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_args) -> None:
        self.canvas.clear()
        if self.piece is None or self.width <= 0 or self.height <= 0:
            return
        x, y = self.x, self.y
        width, height = self.width, self.height
        fill = (0.96, 0.96, 0.93, 1) if self.piece.color else (0.16, 0.16, 0.15, 1)
        outline = (0.10, 0.10, 0.10, 1) if self.piece.color else (0.02, 0.02, 0.02, 1)
        with self.canvas:
            Color(*fill)
            self._piece_shape(x, y, width, height)
            Color(*outline)
            self._piece_outline(x, y, width, height)

    def _piece_shape(self, x: float, y: float, w: float, h: float) -> None:
        """Siluetas simples, reconocibles y renderizadas por Kivy en cualquier Android."""
        unit = min(w, h)
        center = x + w / 2
        base_y = y + h * 0.13
        kind = self.piece.piece_type

        RoundedRectangle(pos=(x + w * 0.16, base_y), size=(w * 0.68, h * 0.13), radius=[unit * 0.04])
        if kind == chess.PAWN:
            Ellipse(pos=(center - w * 0.15, y + h * 0.58), size=(w * 0.30, h * 0.25))
            RoundedRectangle(pos=(center - w * 0.22, y + h * 0.30), size=(w * 0.44, h * 0.30), radius=[unit * 0.14])
        elif kind == chess.ROOK:
            Rectangle(pos=(center - w * 0.25, y + h * 0.28), size=(w * 0.50, h * 0.46))
            Rectangle(pos=(center - w * 0.32, y + h * 0.70), size=(w * 0.64, h * 0.12))
            for offset in (-0.27, -0.09, 0.09, 0.27):
                Rectangle(pos=(center + w * offset - w * 0.055, y + h * 0.78), size=(w * 0.11, h * 0.10))
        elif kind == chess.KNIGHT:
            Ellipse(pos=(center - w * 0.16, y + h * 0.60), size=(w * 0.32, h * 0.24))
            Triangle(points=[center - w * 0.17, y + h * 0.67, center - w * 0.10, y + h * 0.89, center, y + h * 0.70])
            Triangle(points=[center + w * 0.03, y + h * 0.62, center + w * 0.28, y + h * 0.31, center - w * 0.22, y + h * 0.31])
            RoundedRectangle(pos=(center - w * 0.25, y + h * 0.27), size=(w * 0.50, h * 0.20), radius=[unit * 0.08])
        elif kind == chess.BISHOP:
            Ellipse(pos=(center - w * 0.16, y + h * 0.62), size=(w * 0.32, h * 0.24))
            Triangle(points=[center, y + h * 0.64, center - w * 0.26, y + h * 0.31, center + w * 0.26, y + h * 0.31])
            RoundedRectangle(pos=(center - w * 0.24, y + h * 0.27), size=(w * 0.48, h * 0.13), radius=[unit * 0.06])
        elif kind == chess.QUEEN:
            for offset in (-0.22, 0, 0.22):
                Ellipse(pos=(center + w * offset - w * 0.075, y + h * 0.73), size=(w * 0.15, h * 0.15))
            Triangle(points=[center - w * 0.30, y + h * 0.70, center + w * 0.30, y + h * 0.70, center + w * 0.24, y + h * 0.31])
            RoundedRectangle(pos=(center - w * 0.27, y + h * 0.27), size=(w * 0.54, h * 0.13), radius=[unit * 0.06])
        elif kind == chess.KING:
            Rectangle(pos=(center - w * 0.045, y + h * 0.76), size=(w * 0.09, h * 0.16))
            Rectangle(pos=(center - w * 0.14, y + h * 0.82), size=(w * 0.28, h * 0.07))
            Ellipse(pos=(center - w * 0.16, y + h * 0.58), size=(w * 0.32, h * 0.23))
            Triangle(points=[center - w * 0.27, y + h * 0.63, center + w * 0.27, y + h * 0.63, center + w * 0.22, y + h * 0.31])
            RoundedRectangle(pos=(center - w * 0.27, y + h * 0.27), size=(w * 0.54, h * 0.13), radius=[unit * 0.06])

    def _piece_outline(self, x: float, y: float, w: float, h: float) -> None:
        """Un borde suave mantiene las piezas legibles sobre ambos colores."""
        Line(rectangle=(x + w * 0.16, y + h * 0.13, w * 0.68, h * 0.13), width=dp(1.1))
        if self.piece.piece_type == chess.BISHOP:
            Line(points=[x + w * 0.42, y + h * 0.65, x + w * 0.58, y + h * 0.80], width=dp(1.4))
        elif self.piece.piece_type == chess.KNIGHT:
            Line(points=[x + w * 0.42, y + h * 0.73, x + w * 0.55, y + h * 0.73], width=dp(1.4))


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
        self.recommended_move: chess.Move | None = None

        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        root.add_widget(Label(text="[b]PracticaChess[/b]", markup=True, font_size="26sp", size_hint_y=None, height=dp(42)))
        self.status = Label(size_hint_y=None, height=dp(28), color=(0.36, 0.42, 0.58, 1))
        root.add_widget(self.status)

        root.add_widget(Label(text="Evaluación", size_hint_y=None, height=dp(20), color=(0.42, 0.47, 0.61, 1)))
        self.evaluation = EvaluationCurve(size_hint_y=None, height=dp(58))
        root.add_widget(self.evaluation)

        self.board_surface = FloatLayout(size_hint_y=None)
        self.board_surface.bind(width=self._keep_board_square)
        self.board_grid = GridLayout(cols=8, spacing=0, size_hint=(1, 1))
        self.board_surface.add_widget(self.board_grid)
        self.arrow = MoveArrow(size_hint=(1, 1))
        self.board_surface.add_widget(self.arrow)
        root.add_widget(self.board_surface)

        controls = GridLayout(cols=2, size_hint_y=None, height=dp(104), spacing=dp(6))
        controls.add_widget(self._control_button("Voltear", self._flip))
        controls.add_widget(self._control_button("Deshacer", self._undo))
        controls.add_widget(self._control_button("Reiniciar", self._reset))
        controls.add_widget(self._control_button("Análisis", self._analyse))
        root.add_widget(controls)
        self._redraw()
        return root

    def _keep_board_square(self, _surface, width: float) -> None:
        self.board_surface.height = width

    def _control_button(self, text: str, callback) -> Button:
        button = Button(text=text, background_normal="", background_color=(0.18, 0.40, 0.72, 1))
        button.bind(on_release=callback)
        return button

    def _tap_square(self, square: chess.Square) -> None:
        outcome = self.controller.tap(square)
        if outcome.kind == "moved":
            self.recommended_move = None
        self._redraw()

    def _undo(self, _button) -> None:
        self.controller.undo()
        self.recommended_move = None
        self._redraw()

    def _flip(self, _button) -> None:
        self.flipped = not self.flipped
        self._redraw()

    def _reset(self, _button) -> None:
        self.controller.reset()
        self.recommended_move = None
        self._redraw()

    def _analyse(self, _button) -> None:
        self.recommended_move = self.controller.analysis_move()
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
        self.arrow.set_move(self.recommended_move, self.flipped)
        turn = "Blancas" if self.controller.board.turn == chess.WHITE else "Negras"
        if self.controller.board.is_game_over(claim_draw=True):
            self.status.text = f"Partida terminada: {self.controller.board.result(claim_draw=True)}"
        elif self.recommended_move:
            self.status.text = f"Análisis local: {self.recommended_move.uci()}"
        else:
            self.status.text = f"Turno: {turn} · toca una pieza y luego su destino"
