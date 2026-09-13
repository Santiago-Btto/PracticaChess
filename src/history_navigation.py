"""Read-only navigation over the positions already played in a game."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

import chess

if TYPE_CHECKING:
    from src.game_state import GameState


class HistoryNavigator:
    """Keeps an independent, read-only cursor over a game's positions.

    Position index ``0`` is the initial position; each subsequent index is the
    board after that many played moves.  All boards are copied on input and
    output, so browsing never mutates the active :class:`GameState`.
    """

    def __init__(self, snapshots: Sequence[chess.Board], current_board: chess.Board):
        self._positions = [board.copy(stack=True) for board in snapshots]
        self._positions.append(current_board.copy(stack=True))
        self._active_index = len(self._positions) - 1

    @classmethod
    def from_game_state(cls, state: "GameState") -> "HistoryNavigator":
        """Create a navigator from the immutable history kept by ``state``."""
        return cls(state._snapshots, state.board)

    @property
    def active_index(self) -> int:
        return self._active_index

    @property
    def position_count(self) -> int:
        return len(self._positions)

    @property
    def view_board(self) -> chess.Board:
        """Return a defensive copy of the board at the active cursor."""
        return self._positions[self._active_index].copy(stack=True)

    def go_to(self, index: int) -> bool:
        """Move the cursor to a valid position, returning whether it changed."""
        if not 0 <= index < self.position_count:
            return False
        changed = index != self._active_index
        self._active_index = index
        return changed

    def first(self) -> bool:
        return self.go_to(0)

    def previous(self) -> bool:
        return self.go_to(self._active_index - 1)

    def next(self) -> bool:
        return self.go_to(self._active_index + 1)

    def latest(self) -> bool:
        return self.go_to(self.position_count - 1)
