"""Interfaz táctil Kivy de PracticaChess para Android."""
from __future__ import annotations

import chess

from controller import MobileGameController, display_to_square

try:
    from kivy.app import App
    from kivy.metrics import dp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.label import Label
except ModuleNotFoundError as exc:  # permite usar la lógica sin instalar Kivy
    raise RuntimeError(
        "La interfaz móvil requiere Kivy. Instala mobile/requirements-mobile.txt "
        "o compila el APK con Buildozer."
    ) from exc


LIGHT_SQUARE = (0.93, 0.89, 0.72, 1)
DARK_SQUARE = (0.47, 0.60, 0.31, 1)
SELECTED_SQUARE = (0.95, 0.74, 0.22, 1)
LEGAL_TARGET = (0.67, 0.81, 0.40, 1)
PIECE_SYMBOLS = {
    chess.Piece(chess.PAWN, chess.WHITE): "♙",
    chess.Piece(chess.KNIGHT, chess.WHITE): "♘",
    chess.Piece(chess.BISHOP, chess.WHITE): "♗",
    chess.Piece(chess.ROOK, chess.WHITE): "♖",
    chess.Piece(chess.QUEEN, chess.WHITE): "♕",
    chess.Piece(chess.KING, chess.WHITE): "♔",
    chess.Piece(chess.PAWN, chess.BLACK): "♟",
    chess.Piece(chess.KNIGHT, chess.BLACK): "♞",
    chess.Piece(chess.BISHOP, chess.BLACK): "♝",
    chess.Piece(chess.ROOK, chess.BLACK): "♜",
    chess.Piece(chess.QUEEN, chess.BLACK): "♛",
    chess.Piece(chess.KING, chess.BLACK): "♚",
}


class ChessMobileApp(App):
    """Partida local Humano vs Humano optimizada para toques."""

    title = "PracticaChess"

    def build(self):
        self.controller = MobileGameController()
        self.flipped = False

        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        root.add_widget(Label(text="[b]PracticaChess[/b]", markup=True, font_size="26sp", size_hint_y=None, height=dp(42)))
        self.status = Label(size_hint_y=None, height=dp(28), color=(0.2, 0.25, 0.36, 1))
        root.add_widget(self.status)

        self.board_grid = GridLayout(cols=8, spacing=0)
        root.add_widget(self.board_grid)

        self.history = Label(
            size_hint_y=None,
            height=dp(55),
            color=(0.2, 0.25, 0.36, 1),
            halign="center",
            valign="middle",
        )
        self.history.bind(size=lambda instance, value: setattr(instance, "text_size", value))
        root.add_widget(self.history)

        controls = GridLayout(cols=3, size_hint_y=None, height=dp(48), spacing=dp(6))
        controls.add_widget(self._control_button("Deshacer", self._undo))
        controls.add_widget(self._control_button("Voltear", self._flip))
        controls.add_widget(self._control_button("Reiniciar", self._reset))
        root.add_widget(controls)
        self._redraw()
        return root

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
                button = Button(
                    text=PIECE_SYMBOLS.get(piece, ""),
                    font_size="39sp",
                    color=(0.96, 0.96, 0.96, 1) if piece and piece.color else (0.08, 0.08, 0.08, 1),
                    background_normal="",
                    background_color=color,
                )
                button.bind(on_release=lambda _button, selected=square: self._tap_square(selected))
                self.board_grid.add_widget(button)

        turn = "Blancas" if self.controller.board.turn == chess.WHITE else "Negras"
        if self.controller.board.is_game_over(claim_draw=True):
            self.status.text = f"Partida terminada: {self.controller.board.result(claim_draw=True)}"
        else:
            self.status.text = f"Turno: {turn} · toca una pieza y luego su destino"
        moves = self.controller.san_history[-10:]
        self.history.text = "  ".join(moves) if moves else "Partida local sin conexión"
