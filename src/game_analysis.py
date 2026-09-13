"""Componentes puros para historial de evaluación y resumen de partida.

Las evaluaciones están expresadas en centipeones desde la perspectiva de las
blancas: un valor positivo favorece a las blancas y uno negativo a las negras.
Este módulo no dibuja ni consulta Stockfish; la interfaz puede alimentarlo con
los resultados del motor y usar ``chart_points`` para renderizar el gráfico.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence

import chess


class MoveQuality(str, Enum):
    """Clasificación sencilla para el informe final de una partida."""

    BEST = "mejor"
    GOOD = "buena"
    ERROR = "error"
    BLUNDER = "blunder"


@dataclass(frozen=True)
class EvaluationSample:
    """Evaluación de una posición, después de la jugada indicada."""

    ply: int
    score_cp: int
    san: str | None = None


class EvaluationHistory:
    """Historial ordenado que siempre incluye la evaluación inicial."""

    def __init__(self, initial_score_cp: int = 0):
        self._samples: list[EvaluationSample] = [
            EvaluationSample(ply=0, score_cp=initial_score_cp)
        ]

    @property
    def samples(self) -> tuple[EvaluationSample, ...]:
        """Muestras inmutables aptas para el panel de evaluación."""
        return tuple(self._samples)

    def record(self, san: str, score_cp: int) -> EvaluationSample:
        """Añade la evaluación obtenida tras una jugada SAN."""
        sample = EvaluationSample(
            ply=len(self._samples), san=san, score_cp=score_cp
        )
        self._samples.append(sample)
        return sample


def chart_points(
    samples: Sequence[EvaluationSample],
    rect: tuple[int, int, int, int],
    *,
    score_limit_cp: int = 400,
) -> list[tuple[int, int]]:
    """Convierte muestras a puntos de píxeles para dibujar una curva.

    ``rect`` usa ``(x, y, ancho, alto)``. La línea media representa igualdad;
    las evaluaciones se limitan a ``score_limit_cp`` para que un mate no aplaste
    el resto del gráfico.
    """
    if not samples:
        return []
    if score_limit_cp <= 0:
        raise ValueError("score_limit_cp debe ser mayor que cero")

    x, y, width, height = rect
    middle_y = y + height / 2
    amplitude = height / 2
    denominator = max(1, len(samples) - 1)
    points: list[tuple[int, int]] = []

    for index, sample in enumerate(samples):
        normalized = max(-score_limit_cp, min(score_limit_cp, sample.score_cp))
        point_x = x + width * index / denominator
        point_y = middle_y - amplitude * normalized / score_limit_cp
        points.append((round(point_x), round(point_y)))
    return points


@dataclass(frozen=True)
class MoveReview:
    """Calidad de una jugada y una explicación legible para el usuario."""

    ply: int
    san: str
    quality: MoveQuality
    centipawn_loss: int
    explanation: str
    best_san: str | None = None


@dataclass(frozen=True)
class GameSummary:
    """Colecciones listas para el resumen que se muestra al terminar."""

    reviews: tuple[MoveReview, ...]
    best_moves: tuple[MoveReview, ...]
    good_moves: tuple[MoveReview, ...]
    errors: tuple[MoveReview, ...]
    blunders: tuple[MoveReview, ...]


def review_move(
    ply: int,
    san: str,
    score_before_cp: int,
    score_after_cp: int,
    mover: chess.Color,
    *,
    played_move: chess.Move | None = None,
    best_move: chess.Move | None = None,
    best_san: str | None = None,
) -> MoveReview:
    """Clasifica una jugada comparando las evaluaciones antes y después.

    La pérdida siempre se calcula desde el bando que acaba de mover. Por eso,
    para las negras, que el marcador de blancas suba implica una pérdida.
    """
    is_best = played_move is not None and played_move == best_move
    directional_change = score_before_cp - score_after_cp
    loss = directional_change if mover == chess.WHITE else -directional_change
    centipawn_loss = max(0, loss)

    if is_best:
        quality = MoveQuality.BEST
        centipawn_loss = 0
        explanation = "Coincide con la mejor jugada del motor."
    elif centipawn_loss <= 50:
        quality = MoveQuality.GOOD
        explanation = "Es una jugada sólida; mantiene casi toda la evaluación."
    elif centipawn_loss <= 150:
        quality = MoveQuality.ERROR
        explanation = _loss_explanation("Pierde", centipawn_loss, best_san)
    else:
        quality = MoveQuality.BLUNDER
        explanation = _loss_explanation("Deja escapar", centipawn_loss, best_san)

    return MoveReview(
        ply=ply,
        san=san,
        quality=quality,
        centipawn_loss=centipawn_loss,
        explanation=explanation,
        best_san=best_san,
    )


def summarize_game(reviews: Iterable[MoveReview]) -> GameSummary:
    """Agrupa las revisiones por calidad para la pantalla de final de partida."""
    items = tuple(reviews)
    return GameSummary(
        reviews=items,
        best_moves=tuple(item for item in items if item.quality is MoveQuality.BEST),
        good_moves=tuple(item for item in items if item.quality is MoveQuality.GOOD),
        errors=tuple(item for item in items if item.quality is MoveQuality.ERROR),
        blunders=tuple(item for item in items if item.quality is MoveQuality.BLUNDER),
    )


def _loss_explanation(prefix: str, centipawn_loss: int, best_san: str | None) -> str:
    pawns = centipawn_loss / 100
    explanation = f"{prefix} {pawns:.1f} peones de evaluación."
    if best_san:
        explanation += f" La mejor alternativa era {best_san}."
    return explanation
