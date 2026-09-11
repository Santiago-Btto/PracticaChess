import chess
import pygame

from src.live_tracking_screen import LiveTrackingScreen


def _screen():
    pygame.init()
    return pygame.display.set_mode((1, 1))


def _images():
    return {piece: pygame.Surface((1, 1)) for piece in (
        chess.Piece(piece_type, color)
        for color in (chess.WHITE, chess.BLACK)
        for piece_type in chess.PIECE_TYPES
    )}


def test_tracking_screen_never_turns_a_board_click_into_a_move():
    tracking = LiveTrackingScreen(_screen(), _images(), chess.STARTING_FEN, white_bottom=True)

    tracking._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(120, 680)))

    assert tracking.state.san_history == []
    assert tracking.state.selected_square is None


def test_tracking_screen_requires_a_selected_region_before_it_can_start_monitoring():
    tracking = LiveTrackingScreen(_screen(), _images(), chess.STARTING_FEN, white_bottom=True)

    tracking._toggle_monitor()

    assert tracking.monitor.active is False
    assert "selecciona" in tracking.status_message.lower()


def test_tracking_screen_reads_the_selected_region_as_its_initial_position(monkeypatch):
    tracking = LiveTrackingScreen(_screen(), _images(), None, white_bottom=True)
    tracking.monitor.set_region((0, 0, 640, 640))
    tracking._orientation_confirmed = True
    tracking._turn_confirmed = True
    monkeypatch.setattr(
        tracking.monitor,
        "read_current_placement",
        lambda: "4k3/8/8/8/8/8/8/4K3",
    )

    tracking._toggle_monitor()

    assert tracking.monitor.active is True
    assert tracking._needs_initial_position is False
    assert tracking.state.board.board_fen() == "4k3/8/8/8/8/8/8/4K3"
