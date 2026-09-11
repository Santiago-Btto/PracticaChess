from pathlib import Path


def _launcher_text() -> str:
    return Path("ejecutar_windows.bat").read_text(encoding="utf-8")


def test_launcher_explains_a_game_startup_failure_before_waiting():
    launcher = _launcher_text()

    assert "[ERROR] AI Ajedrez no pudo iniciarse" in launcher
    assert "Codigo de salida: !APP_EXIT!" in launcher
    assert launcher.index("[ERROR] AI Ajedrez no pudo iniciarse") < launcher.rindex("pause")


def test_launcher_keeps_successful_and_failed_startup_exit_codes():
    launcher = _launcher_text()

    assert 'set "APP_EXIT=!errorlevel!"' in launcher
    assert 'exit /b !APP_EXIT!' in launcher


def test_launcher_version_probes_are_safe_inside_batch_blocks():
    launcher = _launcher_text()
    version_probes = [line for line in launcher.splitlines() if ' -c "import sys;' in line]

    assert version_probes
    assert all("(" not in probe and ")" not in probe for probe in version_probes)
    assert all("sys.version_info[1] in [10, 11, 12, 13]" in probe for probe in version_probes)


def test_launcher_error_text_does_not_close_its_enclosing_batch_block():
    launcher = _launcher_text()

    assert "Python 3.10 a 3.13" in launcher
    assert "Python (3.10 a 3.13)" not in launcher
