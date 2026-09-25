import chess
import pygame
import pytest

from src.analysis_screen import AnalysisScreen, _BackToMenu
from src.engine_wrapper import AnalysisRequest, AnalysisResult


class _Service:
    def __init__(self):
        self.requests = []
        self.results = {}
        self.cancelled = []

    def submit_analysis(self, board, *, owner, purpose="live", replace=True):
        request = AnalysisRequest(str(len(self.requests)), board.fen(), owner, purpose)
        self.requests.append(request)
        return request

    def get_result(self, request_id):
        return self.results.get(request_id)

    def cancel_owner(self, owner):
        self.cancelled.append(owner)


def _screen(moves=(chess.Move.from_uci("e2e4"),)):
    pygame.init()
    board = chess.Board()
    snapshots = []
    san = []
    for move in moves:
        snapshots.append(board.copy())
        san.append(board.san(move))
        board.push(move)
    return AnalysisScreen(
        screen=pygame.Surface((1100, 720)), engine=_Service(), snapshots=snapshots,
        moves_played=list(moves), san_history=san, result_text="1-0", piece_images={},
    )


def test_review_submits_before_and_after_asynchronously_and_progresses_only_after_active_results():
    screen = _screen()
    service = screen.engine

    screen._start_analysis()
    before = service.requests[-1]
    screen._poll_analysis()
    assert screen.data == []
    assert len(service.requests) == 1

    service.results[before.request_id] = AnalysisResult(
        before.request_id, before.fen, chess.Move.from_uci("e2e4"), None, 12,
    )
    screen._poll_analysis()
    after = service.requests[-1]
    assert after.fen != before.fen
    assert screen.data == []

    service.results[after.request_id] = AnalysisResult(after.request_id, after.fen, None, None, 8)
    screen._poll_analysis()
    assert len(screen.data) == 1
    assert screen._analysis_active is False


def test_review_ignores_stale_results_across_multiple_moves_and_cancels_on_exit():
    screen = _screen((chess.Move.from_uci("e2e4"), chess.Move.from_uci("e7e5")))
    service = screen.engine
    screen._start_analysis()
    first = service.requests[-1]
    service.results[first.request_id] = AnalysisResult(
        first.request_id, first.fen, chess.Move.from_uci("e2e4"), None, 0,
    )
    screen._poll_analysis()
    after = service.requests[-1]
    service.results[after.request_id] = AnalysisResult(after.request_id, after.fen, None, None, 0)
    screen._poll_analysis()
    second_before = service.requests[-1]

    service.results[first.request_id] = AnalysisResult(first.request_id, first.fen, None, None, 999)
    screen._poll_analysis()
    assert len(screen.data) == 1
    assert screen._pending_before.request_id == second_before.request_id

    screen._cancel_analysis()
    assert service.cancelled == [screen._review_owner]
    assert screen._analysis_active is False


def test_review_cancels_its_owner_before_raising_the_menu_navigation_signal():
    screen = _screen()
    screen._start_analysis()

    with pytest.raises(_BackToMenu):
        screen._handle_click(screen._btn_menu.center)

    assert screen.engine.cancelled == [screen._review_owner]
