"""Lectura periódica y local de una región elegida del escritorio."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import ImageGrab

from src.position_import import PositionImportError, detect_position_from_image, orient_placement
from src.screenshot_tracking import ScreenshotTracker, TrackingResult


DesktopBox = tuple[int, int, int, int]


def selection_to_desktop_bbox(
    selection: tuple[int, int, int, int],
    preview_rect: tuple[int, int, int, int],
    desktop_size: tuple[int, int],
) -> DesktopBox:
    """Convierte una selección sobre la vista previa a píxeles del escritorio."""
    sx, sy, ex, ey = selection
    px, py, pw, ph = preview_rect
    desktop_w, desktop_h = desktop_size
    left, right = sorted((sx, ex))
    top, bottom = sorted((sy, ey))
    return (
        int((left - px) * desktop_w / pw),
        int((top - py) * desktop_h / ph),
        int((right - px) * desktop_w / pw),
        int((bottom - py) * desktop_h / ph),
    )


@dataclass(frozen=True)
class MonitorResult:
    accepted: bool
    message: str


class ScreenRegionMonitor:
    """Nunca controla otra app: solo captura el rectángulo configurado y lee piezas."""

    def __init__(
        self,
        tracker: ScreenshotTracker,
        assets_dir: Path | None,
        white_bottom: bool,
        capture: Callable[..., object] = ImageGrab.grab,
        detect_placement: Callable[[object, Path | None], str] = detect_position_from_image,
    ):
        self.tracker = tracker
        self.assets_dir = assets_dir
        self.white_bottom = white_bottom
        self._capture = capture
        self._detect_placement = detect_placement
        self.region: DesktopBox | None = None
        self.active = False

    def set_region(self, region: DesktopBox) -> None:
        left, top, right, bottom = region
        if right <= left or bottom <= top:
            raise ValueError("La zona elegida debe tener ancho y alto positivos.")
        self.region = region
        self.active = False

    def start(self) -> None:
        if self.region is None:
            raise ValueError("Primero selecciona la zona del tablero en pantalla.")
        self.active = True

    def stop(self) -> None:
        self.active = False

    def read_current_placement(self) -> str:
        """Lee la región una vez; se usa para fijar la posición inicial."""
        if self.region is None:
            raise ValueError("Primero selecciona la zona del tablero en pantalla.")
        image = self._capture(bbox=self.region)
        placement = self._detect_placement(image, self.assets_dir)
        return orient_placement(placement, white_bottom=self.white_bottom)

    def poll(self) -> MonitorResult:
        if not self.active:
            return MonitorResult(False, "El monitor está detenido.")
        assert self.region is not None
        try:
            placement = self.read_current_placement()
            result: TrackingResult = self.tracker.observe(placement)
            return MonitorResult(result.accepted, result.message)
        except PositionImportError as exc:
            return MonitorResult(False, str(exc))
        except Exception:
            return MonitorResult(
                False,
                "No se pudo leer la zona del tablero. Verifica que siga visible y completa.",
            )
