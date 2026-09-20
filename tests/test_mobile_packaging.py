import configparser
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
    assert "--sdk_root=" in workflow


def test_android_build_is_pinned_to_the_stable_python_311_toolchain():
    parser = configparser.ConfigParser()
    parser.read("mobile/buildozer.spec", encoding="utf-8")
    app = parser["app"]
    workflow = Path(".github/workflows/android-apk.yml").read_text(encoding="utf-8")

    assert app["p4a.branch"] == "master"
    assert app["p4a.commit"] == "957a3e5f8c270f7aa648ba185e5a68c1077a798d"
    assert app["android.ndk"] == "25b"
    assert '"buildozer==1.5.0"' in workflow
    assert '"cython==0.29.34"' in workflow
