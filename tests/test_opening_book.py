import chess

from src.opening_book import detect_opening


def _moves(*uci: str) -> list[chess.Move]:
    return [chess.Move.from_uci(move) for move in uci]


def test_detect_opening_prefers_the_most_specific_matching_line():
    opening = detect_opening(_moves("e2e4", "e7e5", "g1f3", "b8c6", "f1b5"))

    assert opening is not None
    assert opening.name == "Ruy López"
    assert opening.eco == "C60"


def test_detect_opening_keeps_a_known_opening_after_more_moves_are_played():
    opening = detect_opening(_moves("e2e4", "c7c5", "g1f3", "d7d6"))

    assert opening is not None
    assert opening.name == "Defensa Siciliana"


def test_detect_opening_returns_none_for_an_unrecognised_move_order():
    assert detect_opening(_moves("b1c3", "g8f6")) is None
