"""
src/asset_loader.py
Descarga los sets de piezas Neo (Chess.com) y Cburnett (Lichess) y los carga
en Pygame. Solo necesita internet la primera vez; luego funciona 100 % offline.
"""
import logging
from pathlib import Path

import requests
import pygame
import chess

log = logging.getLogger(__name__)

# Mapa nombre ↔ código de assets
_COLOR_MAP  = {chess.WHITE: "w", chess.BLACK: "b"}
_PIECE_MAP  = {
    chess.PAWN:   "P",
    chess.KNIGHT: "N",
    chess.BISHOP: "B",
    chess.ROOK:   "R",
    chess.QUEEN:  "Q",
    chess.KING:   "K",
}

PIECE_THEME = "neo"
LICHESS_PIECE_THEME = "lichess-cburnett"
_THEME_MARKER = ".piece-theme"
_CHESS_COM_NEO_BASE = "https://www.chess.com/chess-themes/pieces/neo/300"
_LICHESS_CBURNETT_BASE = "https://lichess1.org/assets/piece/cburnett"

_THEME_ALIASES = {
    "neo": PIECE_THEME,
    "chesscom": PIECE_THEME,
    "chess.com": PIECE_THEME,
    "chess-com": PIECE_THEME,
    "lichess": LICHESS_PIECE_THEME,
    "lichess-cburnett": LICHESS_PIECE_THEME,
}


def normalize_theme(theme: str | None = None) -> str:
    """Normaliza los nombres que expone la interfaz de temas."""
    normalized = _THEME_ALIASES.get((theme or PIECE_THEME).lower())
    if normalized is None:
        raise ValueError(f"Tema de piezas no compatible: {theme}")
    return normalized


def piece_assets_dir(assets_dir: Path, theme: str | None = None) -> Path:
    """Devuelve la carpeta de caché propia de cada tema.

    Neo conserva la ruta histórica para no obligar a redescargar los assets
    existentes. Cburnett se mantiene aislado para que sus PNG no reemplacen
    las plantillas Neo que usa el importador de Chess.com.
    """
    return assets_dir if normalize_theme(theme) == PIECE_THEME else assets_dir / LICHESS_PIECE_THEME


def piece_url(color: str, piece: str, *, theme: str | None = None) -> str:
    """Devuelve la URL pública oficial de una pieza del tema elegido."""
    normalized = normalize_theme(theme)
    if normalized == LICHESS_PIECE_THEME:
        return f"{_LICHESS_CBURNETT_BASE}/{color}{piece.upper()}.svg"
    return f"{_CHESS_COM_NEO_BASE}/{color}{piece.lower()}.png"

# ── Descarga ───────────────────────────────────────────────────────────────

def download_pieces(
    assets_dir: Path, size: int = 80, *, theme: str | None = None,
) -> bool:
    """
    Descarga las 12 piezas del tema solicitado desde su origen público.
    Devuelve True si todas las piezas están disponibles.
    """
    normalized = normalize_theme(theme)
    target_dir = piece_assets_dir(assets_dir, normalized)
    target_dir.mkdir(parents=True, exist_ok=True)
    all_names = [
        f"{c}{p}"
        for c in ("w", "b")
        for p in ("P", "N", "B", "R", "Q", "K")
    ]
    marker = target_dir / _THEME_MARKER
    theme_is_current = marker.exists() and marker.read_text(encoding="utf-8").strip() == normalized
    missing = [n for n in all_names if not (target_dir / f"{n}.png").exists()]

    if theme_is_current and not missing:
        return True

    # Un caché previo podía contener Cburnett con los mismos nombres; el
    # marcador evita conservarlo por error después de cambiar al set Neo.
    to_download = all_names if not theme_is_current else missing
    log.info("Descargando set de piezas %s (%d piezas)…", normalized, len(to_download))
    ok = True
    for name in to_download:
        try:
            resp = requests.get(piece_url(name[0], name[1], theme=normalized), timeout=15)
            resp.raise_for_status()
            if normalized == LICHESS_PIECE_THEME:
                (target_dir / f"{name}.svg").write_bytes(resp.content)
                _render_svg_to_png(resp.content, target_dir / f"{name}.png")
            else:
                (target_dir / f"{name}.png").write_bytes(resp.content)
            log.debug("  ✓ %s", name)
        except Exception as exc:
            log.error("  ✗ No se pudo descargar %s: %s", name, exc)
            ok = False

    if ok:
        marker.write_text(normalized, encoding="utf-8")
        log.info("Piezas descargadas correctamente.")
    return ok


# ── Carga en Pygame ────────────────────────────────────────────────────────

def load_piece_images(
    assets_dir: Path, size: int = 80, *, theme: str | None = None,
) -> dict:
    """
    Devuelve un dict { chess.Piece → pygame.Surface }.
    Si no existe el PNG de alguna pieza devuelve superficie vacía (fallback).
    """
    images: dict[chess.Piece, pygame.Surface] = {}
    target_dir = piece_assets_dir(assets_dir, theme)

    for color in (chess.WHITE, chess.BLACK):
        for piece_type in (
            chess.PAWN, chess.KNIGHT, chess.BISHOP,
            chess.ROOK,  chess.QUEEN,  chess.KING,
        ):
            name = f"{_COLOR_MAP[color]}{_PIECE_MAP[piece_type]}"
            path = target_dir / f"{name}.png"
            piece = chess.Piece(piece_type, color)

            if path.exists():
                surf = pygame.image.load(str(path)).convert_alpha()
                surf = pygame.transform.smoothscale(surf, (size, size))
                images[piece] = surf
            else:
                log.warning("Pieza no encontrada: %s — usando fallback Unicode", name)
                images[piece] = _make_unicode_surface(piece, size)

    return images


def _render_svg_to_png(svg: bytes, destination: Path) -> None:
    """Rasteriza el SVG oficial para Pygame y el reconocedor local."""
    try:
        import cairosvg
    except ImportError as exc:
        raise RuntimeError("Falta CairoSVG para preparar las piezas de Lichess.") from exc
    cairosvg.svg2png(bytestring=svg, write_to=str(destination), output_width=300, output_height=300)


def _make_unicode_surface(piece: chess.Piece, size: int) -> pygame.Surface:
    """Fallback: renderiza el símbolo Unicode de la pieza en una superficie."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.font.init()
    font = pygame.font.SysFont("segoeuisymbol,symbola,unifont", int(size * 0.85))
    symbol = piece.unicode_symbol()
    color = (255, 255, 255) if piece.color == chess.WHITE else (30, 30, 30)
    outline_color = (30, 30, 30) if piece.color == chess.WHITE else (220, 220, 220)
    # outline
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        t = font.render(symbol, True, outline_color)
        r = t.get_rect(center=(size // 2 + dx, size // 2 + dy))
        surf.blit(t, r)
    text = font.render(symbol, True, color)
    rect = text.get_rect(center=(size // 2, size // 2))
    surf.blit(text, rect)
    return surf
