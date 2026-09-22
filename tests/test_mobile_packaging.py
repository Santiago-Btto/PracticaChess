import configparser
import ast
from pathlib import Path


def test_android_build_profile_uses_kivy_and_keeps_core_play_offline():
    spec = Path("mobile/buildozer.spec").read_text(encoding="utf-8")

    assert "requirements = python3,kivy,chess" in spec
    assert "android.permissions =" in spec
    assert "android.permissions = INTERNET" not in spec
    assert "orientation = portrait" in spec


def test_android_build_profile_packages_the_importable_chess_module_directly():
    """python-for-android debe recibir el paquete que expone ``import chess``."""
    parser = configparser.ConfigParser()
    parser.read("mobile/buildozer.spec", encoding="utf-8")

    requirements = {
        requirement.strip()
        for requirement in parser["app"]["requirements"].split(",")
    }

    assert "chess" in requirements
    assert "python-chess" not in requirements


def test_github_workflow_builds_and_retains_the_android_apk():
    workflow = Path(".github/workflows/android-apk.yml").read_text(encoding="utf-8")

    assert "buildozer -v android debug" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "mobile/bin/*.apk" in workflow
    assert "--licenses" in workflow
    assert "--sdk_root=" in workflow


def test_github_workflow_selects_java_17_for_android_gradle():
    workflow = Path(".github/workflows/android-apk.yml").read_text(encoding="utf-8")

    assert "actions/setup-java@v4" in workflow
    assert "java-version: '17'" in workflow
    assert "distribution: temurin" in workflow


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


def test_mobile_entrypoint_uses_package_relative_imports():
    """El APK debe poder cargar los módulos incluso cuando se ejecutan como paquete."""
    app_tree = ast.parse(Path("mobile/app.py").read_text(encoding="utf-8"))
    main_tree = ast.parse(Path("mobile/main.py").read_text(encoding="utf-8"))

    app_imports = [node for node in ast.walk(app_tree) if isinstance(node, ast.ImportFrom)]
    main_imports = [node for node in ast.walk(main_tree) if isinstance(node, ast.ImportFrom)]

    assert any(node.module == "controller" and node.level == 1 for node in app_imports)
    assert any(node.module == "app" and node.level == 1 for node in main_imports)


def test_mobile_ui_uses_drawn_piece_assets_and_only_the_requested_controls():
    """Android no debe depender de los glifos de ajedrez de la fuente del sistema."""
    app_source = Path("mobile/app.py").read_text(encoding="utf-8")

    assert "class PieceWidget" in app_source
    assert "PIECE_SYMBOLS" not in app_source
    assert "♔" not in app_source
    assert "class EvaluationCurve" in app_source
    assert "class MoveArrow" in app_source
    for label in ("Voltear", "Deshacer", "Reiniciar", "Análisis"):
        assert f'"{label}"' in app_source


def test_mobile_ui_packages_a_complete_local_chess_piece_set():
    """Las piezas de Android deben ser assets locales, no glifos del sistema."""
    asset_dir = Path("mobile/assets/pieces")
    expected_names = {
        f"{color}{piece}.png"
        for color in ("w", "b")
        for piece in ("P", "N", "B", "R", "Q", "K")
    }

    assert asset_dir.is_dir()
    assert {path.name for path in asset_dir.glob("*.png")} == expected_names

    app_source = Path("mobile/app.py").read_text(encoding="utf-8")
    assert "assets/pieces" in app_source


def test_android_package_keeps_piece_sources_and_their_attribution():
    spec = Path("mobile/buildozer.spec").read_text(encoding="utf-8")
    license_text = Path("mobile/assets/pieces/LICENSE.md").read_text(encoding="utf-8")

    assert "svg" in spec
    assert "Cburnett" in license_text
    assert "CC BY-SA 3.0" in license_text
