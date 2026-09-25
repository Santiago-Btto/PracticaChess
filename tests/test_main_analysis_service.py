import chess
from types import SimpleNamespace

import main
from main import ChessApp
from src.engine_wrapper import AnalysisRequest, AnalysisResult
from src.game_analysis import EvaluationHistory
from src.game_state import GameMode, GameState


class _Service:
    def __init__(self):
        self.requests = []
        self.results = {}
        self.cancelled = []

    def is_available(self):
        return True

    def submit_analysis(self, board, *, owner, purpose="live", replace=True):
        request = AnalysisRequest(f"{owner}-{len(self.requests)}", board.fen(), owner, purpose)
        self.requests.append(request)
        return request

    def get_result(self, request_id):
        return self.results.get(request_id)

    def cancel_owner(self, owner):
        self.cancelled.append(owner)


def _app():
    app = ChessApp.__new__(ChessApp)
    app.engine = _Service()
    app.state = GameState(mode=GameMode.HUMAN_VS_AI, human_color=chess.WHITE)
    app._last_fen = ""
    app._live_request = None
    app._ai_request = None
    app._review_pending = None
    app._ai_move_pending = True
    app._ai_move_time = 1.0
    app._AI_DELAY = 0.0
    app.move_reviews = []
    app.evaluation_history = EvaluationHistory()
    return app


def test_live_result_is_ignored_after_board_changes_while_analysis_is_in_flight():
    app = _app()
    app._maybe_request_analysis()
    request = app._live_request
    app.engine.results[request.request_id] = AnalysisResult(
        request.request_id, request.fen, chess.Move.from_uci("e2e4"), None, 10,
    )
    app.state.board.push_uci("e2e4")

    assert app._live_result() is None
    app._maybe_request_analysis()
    assert app._live_request.fen == app.state.board.fen()
    assert app._live_request.request_id != request.request_id


def test_ai_never_applies_an_old_or_illegal_result_for_either_side_to_move():
    app = _app()
    request = app.engine.submit_analysis(app.state.board, owner="ai", purpose="opponent")
    app._ai_request = request
    app.engine.results[request.request_id] = AnalysisResult(
        request.request_id, request.fen, chess.Move.from_uci("e7e5"), None, 0,
    )

    app._handle_ai_turn(0)
    assert app.state.board.fen() == request.fen  # e7e5 is illegal with white to move

    app.state.board.push_uci("e2e4")
    app._ai_move_pending = True
    app._handle_ai_turn(0)
    assert app.state.board.peek() == chess.Move.from_uci("e2e4")  # old result is stale


def test_post_game_review_receives_the_existing_managed_service(monkeypatch):
    app = _app()
    app.screen = object()
    app.piece_images = {}
    app.visual_theme = "chesscom"
    app.state = SimpleNamespace(
        moves_played=[chess.Move.from_uci("e2e4")],
        _snapshots=[chess.Board()],
        san_history=["e4"],
        result_text="1-0",
    )
    captured = {}

    class _Screen:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def run(self):
            pass

    monkeypatch.setattr(main, "AnalysisScreen", _Screen)
    app._open_analysis()

    assert captured["engine"] is app.engine
