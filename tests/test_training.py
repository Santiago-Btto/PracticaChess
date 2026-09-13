import chess
import pytest

from src.training import TrainingChallenge


def test_training_challenge_accepts_one_of_the_engine_best_moves_without_changing_position():
    board = chess.Board()
    challenge = TrainingChallenge.from_engine(board, [
        chess.Move.from_uci("e2e4"),
        chess.Move.from_uci("d2d4"),
    ])

    result = challenge.check_move(chess.Move.from_uci("d2d4"))

    assert result.correct is True
    assert result.san == "d4"
    assert board.fen() == chess.Board().fen()


def test_training_challenge_rejects_a_legal_move_outside_engine_best_moves():
    challenge = TrainingChallenge.from_engine(chess.Board(), [chess.Move.from_uci("e2e4")])

    result = challenge.check_move(chess.Move.from_uci("g1f3"))

    assert result.correct is False
    assert result.san == "Nf3"
    assert "mejor" in result.message.lower()


def test_training_challenge_validates_the_side_to_move_in_a_custom_position():
    board = chess.Board()
    board.push_uci("e2e4")
    challenge = TrainingChallenge.from_engine(board, [chess.Move.from_uci("c7c5")])

    result = challenge.check_move(chess.Move.from_uci("c7c5"))

    assert result.correct is True
    assert result.san == "c5"
    assert board.peek() == chess.Move.from_uci("e2e4")


def test_training_challenge_rejects_engine_moves_that_are_not_legal_in_its_position():
    with pytest.raises(ValueError, match="legal"):
        TrainingChallenge.from_engine(chess.Board(), [chess.Move.from_uci("e7e5")])
