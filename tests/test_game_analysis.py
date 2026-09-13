import chess

from src.game_analysis import (
    EvaluationHistory,
    MoveQuality,
    chart_points,
    review_move,
    summarize_game,
)


def test_evaluation_history_keeps_an_initial_sample_and_one_per_move():
    history = EvaluationHistory(initial_score_cp=15)

    history.record("e4", 42)
    history.record("c5", -31)

    assert [(sample.ply, sample.san, sample.score_cp) for sample in history.samples] == [
        (0, None, 15),
        (1, "e4", 42),
        (2, "c5", -31),
    ]


def test_chart_points_maps_positive_and_negative_evaluations_around_the_middle():
    history = EvaluationHistory(initial_score_cp=0)
    history.record("e4", 400)
    history.record("c5", -400)

    assert chart_points(history.samples, (10, 20, 100, 80), score_limit_cp=400) == [
        (10, 60),
        (60, 20),
        (110, 100),
    ]


def test_chart_points_clips_extreme_scores_and_handles_an_empty_history():
    history = EvaluationHistory(initial_score_cp=900)
    history.record("e4", -900)

    assert chart_points(history.samples, (0, 0, 20, 20), score_limit_cp=400) == [
        (0, 0),
        (20, 20),
    ]
    assert chart_points([], (0, 0, 20, 20)) == []


def test_review_move_marks_the_engine_move_as_best_with_a_short_explanation():
    move = chess.Move.from_uci("e2e4")
    review = review_move(
        ply=1,
        san="e4",
        score_before_cp=10,
        score_after_cp=8,
        mover=chess.WHITE,
        played_move=move,
        best_move=move,
    )

    assert review.quality is MoveQuality.BEST
    assert review.centipawn_loss == 0
    assert "mejor jugada" in review.explanation.lower()


def test_review_move_measures_lost_evaluation_from_the_moving_side_perspective():
    white_blunder = review_move(
        ply=1,
        san="f3",
        score_before_cp=20,
        score_after_cp=-180,
        mover=chess.WHITE,
    )
    black_error = review_move(
        ply=2,
        san="Nc6",
        score_before_cp=20,
        score_after_cp=150,
        mover=chess.BLACK,
        best_san="d5",
    )

    assert white_blunder.quality is MoveQuality.BLUNDER
    assert white_blunder.centipawn_loss == 200
    assert "2.0" in white_blunder.explanation
    assert black_error.quality is MoveQuality.ERROR
    assert black_error.centipawn_loss == 130
    assert "d5" in black_error.explanation


def test_summary_groups_best_moves_errors_and_blunders_for_the_end_screen():
    reviews = [
        review_move(1, "e4", 0, 0, chess.WHITE, played_move=chess.Move.from_uci("e2e4"), best_move=chess.Move.from_uci("e2e4")),
        review_move(2, "f6", 0, 70, chess.BLACK),
        review_move(3, "Qh5", 70, 320, chess.BLACK),
        review_move(4, "e5", 0, 25, chess.WHITE),
    ]

    summary = summarize_game(reviews)

    assert [review.san for review in summary.best_moves] == ["e4"]
    assert [review.san for review in summary.errors] == ["f6"]
    assert [review.san for review in summary.blunders] == ["Qh5"]
    assert [review.san for review in summary.good_moves] == ["e5"]
