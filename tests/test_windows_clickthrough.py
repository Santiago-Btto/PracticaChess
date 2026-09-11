from src.windows_clickthrough import MA_ACTIVATE, WM_MOUSEACTIVATE, WindowsMouseActivateHandler


class _WindowApiStub:
    def __init__(self):
        self.forwarded = []

    def call_window_proc(self, proc, hwnd, message, wparam, lparam):
        self.forwarded.append((proc, hwnd, message, wparam, lparam))
        return 73

    def set_window_proc(self, hwnd, proc):
        self.restored = (hwnd, proc)


def test_mouse_activate_keeps_the_click_for_the_game_window():
    api = _WindowApiStub()
    handler = WindowsMouseActivateHandler(api, previous_proc=99)

    result = handler.window_proc(hwnd=10, message=WM_MOUSEACTIVATE, wparam=2, lparam=3)

    assert result == MA_ACTIVATE
    assert api.forwarded == []


def test_other_window_messages_continue_to_the_original_proc():
    api = _WindowApiStub()
    handler = WindowsMouseActivateHandler(api, previous_proc=99)

    result = handler.window_proc(hwnd=10, message=0x0010, wparam=2, lparam=3)

    assert result == 73
    assert api.forwarded == [(99, 10, 0x0010, 2, 3)]


def test_uninstall_restores_the_sdl_window_proc():
    api = _WindowApiStub()
    handler = WindowsMouseActivateHandler(api, previous_proc=99)
    handler.hwnd = 10
    handler._callback = object()
    handler._installed = True

    handler.uninstall()

    assert api.restored == (10, 99)
    assert handler._installed is False
    assert handler._callback is None
