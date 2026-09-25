import threading

import chess
import pytest

import config
from src.engine_wrapper import AnalysisResult, EngineWrapper, result_matches


class _BlockingEngine:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls = []
        self.quit_called = False

    def analyse(self, board, limit, multipv):
        self.calls.append((board.fen(), limit.time, multipv))
        self.started.set()
        assert self.release.wait(1)
        return {"pv": [next(iter(board.legal_moves))], "score": 0}

    def configure(self, options):
        pass

    def quit(self):
        self.quit_called = True


class _FailingEngine(_BlockingEngine):
    def analyse(self, board, limit, multipv):
        raise RuntimeError("uci exploded")


class _ImmediateEngine:
    def __init__(self):
        self.calls = []
        self.configurations = []

    def configure(self, options):
        self.configurations.append(options)

    def analyse(self, board, limit, multipv):
        self.calls.append((limit.time, multipv))
        return {"pv": [next(iter(board.legal_moves))], "score": 0}

    def quit(self):
        pass


def test_analysis_result_is_immutable_and_matches_its_exact_request_and_fen():
    board = chess.Board()
    result = AnalysisResult(
        request_id="live-1",
        fen=board.fen(),
        best_move=chess.Move.from_uci("e2e4"),
        alternative_move=chess.Move.from_uci("d2d4"),
        score=42,
    )

    assert result_matches(result, "live-1", board.fen()) is True
    assert result.best_move == chess.Move.from_uci("e2e4")
    assert result.alternative_move == chess.Move.from_uci("d2d4")
    assert result.score == 42
    with pytest.raises(AttributeError):
        result.request_id = "changed"


def test_analysis_result_requires_both_matching_request_id_and_fen():
    first_board = chess.Board()
    second_board = chess.Board()
    second_board.push_uci("e2e4")
    result = AnalysisResult(
        request_id="review-2",
        fen=second_board.fen(),
        best_move=chess.Move.from_uci("e7e5"),
        alternative_move=None,
        score=-15,
    )

    assert result_matches(result, "review-2", second_board.fen()) is True
    assert result_matches(result, "review-1", second_board.fen()) is False
    assert result_matches(result, "review-2", first_board.fen()) is False


def test_result_retrieval_is_scoped_to_the_requested_id():
    engine = EngineWrapper("unused")
    result = AnalysisResult("request-2", chess.STARTING_FEN, None, None, 0)

    engine._store_result(result)

    assert engine.get_result("request-1") is None
    assert engine.get_result("request-2") == result


def test_newer_request_replaces_queued_or_running_work_without_delivering_stale_result():
    fake = _BlockingEngine()
    service = EngineWrapper("unused", engine_factory=lambda _: fake)
    assert service.start() is True
    first = service.submit_analysis(chess.Board(), owner="live")
    assert fake.started.wait(1)
    newer_board = chess.Board()
    newer_board.push_uci("e2e4")
    second = service.submit_analysis(newer_board, owner="live")

    fake.release.set()
    result = service.wait_for_result(second.request_id, timeout=1)

    assert service.get_result(first.request_id) is None
    assert result_matches(result, second.request_id, newer_board.fen()) is True
    service.shutdown()
    assert fake.quit_called is True


def test_cancel_owner_and_shutdown_invalidate_outstanding_results():
    fake = _BlockingEngine()
    service = EngineWrapper("unused", engine_factory=lambda _: fake)
    service.start()
    request = service.submit_analysis(chess.Board(), owner="review-session")
    assert fake.started.wait(1)

    service.cancel_owner("review-session")
    fake.release.set()
    assert service.wait_for_result(request.request_id, timeout=0.1) is None

    queued = service.submit_analysis(chess.Board(), owner="second-session")
    service.shutdown()
    assert service.get_result(queued.request_id) is None


def test_unavailable_and_failed_engines_deliver_scoped_outcomes_without_raising():
    unavailable = EngineWrapper(
        "missing", engine_factory=lambda _: (_ for _ in ()).throw(FileNotFoundError())
    )
    assert unavailable.start() is False
    request = unavailable.submit_analysis(chess.Board(), owner="live")
    assert unavailable.get_result(request.request_id).outcome == "unavailable"

    failed = EngineWrapper("unused", engine_factory=lambda _: _FailingEngine())
    failed.start()
    failed_request = failed.submit_analysis(chess.Board(), owner="live")
    assert failed.wait_for_result(failed_request.request_id, timeout=1).outcome == "failed"
    failed.shutdown()


def test_analysis_budgets_are_explicit_and_do_not_change_with_opponent_difficulty():
    assert config.LIVE_ANALYSIS_TIME_S == 0.15
    assert config.REVIEW_ANALYSIS_TIME_S == 0.25
    original = (config.LIVE_ANALYSIS_TIME_S, config.REVIEW_ANALYSIS_TIME_S)
    selected_difficulty = config.DIFFICULTY_LEVELS[-1]

    assert original == (config.LIVE_ANALYSIS_TIME_S, config.REVIEW_ANALYSIS_TIME_S)
    assert selected_difficulty["move_time"] == 0.60


def test_mixed_purpose_jobs_apply_separate_budget_and_skill_profiles():
    fake = _ImmediateEngine()
    service = EngineWrapper("unused", engine_factory=lambda _: fake, live_analysis_time=0.12, review_analysis_time=0.34)
    service.start()
    service.set_opponent_profile(skill=3, time=0.45)

    live = service.submit_analysis(chess.Board(), owner="live", purpose="live")
    assert service.wait_for_result(live.request_id, timeout=1)
    opponent = service.submit_analysis(chess.Board(), owner="ai", purpose="opponent")
    assert service.wait_for_result(opponent.request_id, timeout=1)
    review = service.submit_analysis(chess.Board(), owner="review", purpose="review")
    assert service.wait_for_result(review.request_id, timeout=1)

    assert [time for time, _ in fake.calls] == [0.12, 0.45, 0.34]
    assert fake.configurations == [
        {"Skill Level": config.ANALYSIS_SKILL_LEVEL},
        {"Skill Level": 3},
        {"Skill Level": config.ANALYSIS_SKILL_LEVEL},
    ]
    service.shutdown()


def test_analysis_budgets_clamp_to_a_safe_minimum():
    fake = _ImmediateEngine()
    service = EngineWrapper("unused", engine_factory=lambda _: fake, live_analysis_time=0, review_analysis_time=-1)
    service.start()
    live = service.submit_analysis(chess.Board(), owner="live", purpose="live")
    assert service.wait_for_result(live.request_id, timeout=1)
    review = service.submit_analysis(chess.Board(), owner="review", purpose="review")
    assert service.wait_for_result(review.request_id, timeout=1)

    assert [time for time, _ in fake.calls] == [0.05, 0.05]
    service.shutdown()
