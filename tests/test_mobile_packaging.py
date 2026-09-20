from pathlib import Path


def test_android_build_profile_uses_kivy_and_keeps_core_play_offline():
    spec = Path("mobile/buildozer.spec").read_text(encoding="utf-8")

    assert "requirements = python3,kivy,python-chess" in spec
    assert "android.permissions =" in spec
    assert "android.permissions = INTERNET" not in spec
    assert "orientation = portrait" in spec
