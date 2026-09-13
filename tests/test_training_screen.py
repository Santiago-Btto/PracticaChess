import chess
import pygame

from src.board_gui import square_to_pixel
from src.training import TrainingChallenge
from src.training_screen import TrainingScreen


class _Engine:
    def __init__(self, best_move=None, analysing=False, analysis_fen=None):
        self.best_move = best_move
        self.is_analysing = analysing
        self.analysis_fen = analysis_fen
        self.requests = []
        self.clear_calls = 0

    def clear(self):
        self.clear_calls += 1

    def request_analysis(self, board):
        self.requests.append(board.fen())


def _pieces():
    return {
        chess.Piece(piece_type, color): pygame.Surface((80, 80), pygame.SRCALPHA)
        for color in (chess.WHITE, chess.BLACK)
        for piece_type in range(chess.PAWN, chess.KING + 1)
    }


def _screen(engine):
    pygame.init()
    return TrainingScreen(
        pygame.display.set_mode((1100, 720)), _pieces(), engine,
        puzzles=(chess.STARTING_FEN, "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"),
    )


def test_training_screen_waits_for_an_engine_result_for_its_current_position():
    screen = _screen(_Engine(
        best_move=chess.Move.from_uci("e2e4"),
        analysis_fen="unrelated position",
    ))

    screen._make_challenge_when_ready()

    assert screen.challenge is None
    assert "preparando" in screen.message.lower()


def test_correct_attempt_keeps_solution_visible_and_next_retries_with_a_new_position():
    engine = _Engine()
    screen = _screen(engine)
    screen.challenge = TrainingChallenge.from_engine(
        screen.board, [chess.Move.from_uci("e2e4")]
    )

    screen.submit_move(chess.Move.from_uci("e2e4"))

    assert screen.solved is True
    assert screen.solution_move == chess.Move.from_uci("e2e4")
    assert "correcto" in screen.message.lower()

    previous_fen = screen.board.fen()
    screen.next_challenge()

    assert screen.board.fen() != previous_fen
    assert screen.challenge is None
    assert screen.selected is None
    assert engine.requests[-1] == screen.board.fen()


def test_clicking_a_legal_but_wrong_move_allows_another_attempt():
    screen = _screen(_Engine())
    screen.challenge = TrainingChallenge.from_engine(
        screen.board, [chess.Move.from_uci("e2e4")]
    )

    screen.submit_move(chess.Move.from_uci("g1f3"))

    assert screen.solved is False
    assert screen.challenge is not None
    assert "intenta" in screen.message.lower()

    source = square_to_pixel(chess.E2)
    target = square_to_pixel(chess.E4)
    screen._handle_click(source)
    screen._handle_click(target)

    assert screen.solved is True


def test_training_panel_routes_retry_next_and_menu_actions():
    engine = _Engine()
    screen = _screen(engine)
    screen.challenge = TrainingChallenge.from_engine(
        screen.board, [chess.Move.from_uci("e2e4")]
    )
    screen._draw_message()

    assert screen._handle_panel_click(screen.btn_retry.center) is True
    assert "intenta" in screen.message.lower()

    assert screen._handle_panel_click(screen.btn_next.center) is False

    screen.submit_move(chess.Move.from_uci("e2e4"))
    assert screen._handle_panel_click(screen.btn_next.center) is True
    assert engine.requests[-1] == screen.board.fen()
    assert screen._handle_panel_click(screen.btn_menu.center) is True
