"""Evita que Windows consuma el primer clic al reactivar la ventana Pygame."""

from __future__ import annotations

import ctypes
import logging
import sys
from typing import Any

import pygame


log = logging.getLogger(__name__)

WM_MOUSEACTIVATE = 0x0021
MA_ACTIVATE = 1
GWLP_WNDPROC = -4


class WindowsMouseActivateHandler:
    """Subclase el procedimiento de ventana y conserva el clic de activación."""

    def __init__(self, api: Any, previous_proc: int):
        self._api = api
        self.previous_proc = previous_proc
        self.hwnd: int | None = None
        self._callback: Any = None
        self._installed = False

    def window_proc(self, hwnd: int, message: int, wparam: int, lparam: int) -> int:
        if message == WM_MOUSEACTIVATE:
            return MA_ACTIVATE
        return self._api.call_window_proc(self.previous_proc, hwnd, message, wparam, lparam)

    def uninstall(self) -> None:
        """Restaura el procedimiento SDL original antes de cerrar la aplicación."""
        if not self._installed or self.hwnd is None:
            return
        try:
            self._api.set_window_proc(self.hwnd, self.previous_proc)
        except OSError as exc:
            log.warning("No se pudo restaurar el procedimiento de ventana: %s", exc)
        finally:
            self._installed = False
            self._callback = None


class _WindowsUser32Api:
    def __init__(self):
        from ctypes import wintypes

        self._set_window_long = ctypes.WinDLL("user32", use_last_error=True).SetWindowLongPtrW
        self._set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        self._set_window_long.restype = ctypes.c_ssize_t

        self._call_window_proc = ctypes.WinDLL("user32", use_last_error=True).CallWindowProcW
        self._call_window_proc.argtypes = [
            ctypes.c_void_p,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        self._call_window_proc.restype = ctypes.c_ssize_t

    def set_window_proc(self, hwnd: int, proc: Any) -> int:
        proc_value = ctypes.cast(proc, ctypes.c_void_p).value if not isinstance(proc, int) else proc
        ctypes.set_last_error(0)
        previous = self._set_window_long(hwnd, GWLP_WNDPROC, proc_value)
        if previous == 0:
            error = ctypes.get_last_error()
            if error:
                raise ctypes.WinError(error)
        return previous

    def call_window_proc(self, proc: int, hwnd: int, message: int, wparam: int, lparam: int) -> int:
        return self._call_window_proc(proc, hwnd, message, wparam, lparam)


def install_windows_clickthrough() -> WindowsMouseActivateHandler | None:
    """Instala el arreglo nativo en Windows; en otros sistemas no hace nada."""
    if sys.platform != "win32":
        return None

    hwnd = pygame.display.get_wm_info().get("window")
    if not hwnd:
        log.warning("No se encontró la ventana nativa de Pygame para conservar el primer clic.")
        return None

    api = _WindowsUser32Api()
    handler = WindowsMouseActivateHandler(api, previous_proc=0)
    window_proc_type = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_size_t,
        ctypes.c_ssize_t,
    )
    callback = window_proc_type(handler.window_proc)

    try:
        handler.previous_proc = api.set_window_proc(hwnd, callback)
    except OSError as exc:
        log.warning("No se pudo conservar el primer clic al recuperar foco: %s", exc)
        return None

    handler.hwnd = hwnd
    handler._callback = callback  # Mantener viva la función C durante toda la partida.
    handler._installed = True
    log.info("Primer clic al recuperar foco habilitado mediante la ventana nativa de Windows.")
    return handler
