from pathlib import Path


def test_android_build_profile_uses_kivy_and_keeps_core_play_offline():
    spec = Path("mobile/buildozer.spec").read_text(encoding="utf-8")

    assert "requirements = python3,kivy,python-chess" in spec
    assert "android.permissions =" in spec
    assert "android.permissions = INTERNET" not in spec
    assert "orientation = portrait" in spec


def test_github_workflow_builds_and_retains_the_android_apk():
    workflow = Path(".github/workflows/android-apk.yml").read_text(encoding="utf-8")

    assert "buildozer -v android debug" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "mobile/bin/*.apk" in workflow
    assert "--licenses" in workflow
