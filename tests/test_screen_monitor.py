import chess

from src.game_state import GameState
from src.screen_monitor import ScreenRegionMonitor, selection_to_desktop_bbox
from src.screenshot_tracking import ScreenshotTracker


def test_monitor_reads_only_the_selected_region_and_records_a_legal_transition():
    state = GameState()
    board = chess.Board()
    board.push_uci("e2e4")
    requested = []
    monitor = ScreenRegionMonitor(
        ScreenshotTracker(state),
        assets_dir=None,
        white_bottom=True,
        capture=lambda *, bbox: requested.append(bbox) or object(),
        detect_placement=lambda _image, _assets: board.board_fen(),
    )
    monitor.set_region((100, 200, 700, 800))
    monitor.start()

    result = monitor.poll()

    assert requested == [(100, 200, 700, 800)]
    assert result.accepted is True
    assert state.san_history == ["e4"]


def test_monitor_reports_invalid_frame_without_changing_the_recorded_game():
    state = GameState()
    monitor = ScreenRegionMonitor(
        ScreenshotTracker(state),
        assets_dir=None,
        white_bottom=True,
        capture=lambda *, bbox: object(),
        detect_placement=lambda _image, _assets: "4k3/8/8/8/8/8/8/4K3",
    )
    monitor.set_region((0, 0, 640, 640))
    monitor.start()

    result = monitor.poll()

    assert result.accepted is False
    assert "no corresponde" in result.message.lower()
    assert state.san_history == []


def test_selection_is_mapped_back_to_the_desktop_pixels():
    bbox = selection_to_desktop_bbox(
        selection=(110, 70, 310, 270),
        preview_rect=(10, 20, 400, 400),
        desktop_size=(1600, 900),
    )

    assert bbox == (400, 112, 1200, 562)


def test_monitor_can_read_the_initial_position_before_starting_periodic_tracking():
    state = GameState()
    monitor = ScreenRegionMonitor(
        ScreenshotTracker(state),
        assets_dir=None,
        white_bottom=True,
        capture=lambda *, bbox: object(),
        detect_placement=lambda _image, _assets: "4k3/8/8/8/8/8/8/4K3",
    )
    monitor.set_region((0, 0, 640, 640))

    assert monitor.read_current_placement() == "4k3/8/8/8/8/8/8/4K3"
