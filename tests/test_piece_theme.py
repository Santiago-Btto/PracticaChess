import base64
from pathlib import Path

from src import asset_loader


_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADElEQVR42mNk+M/wHwAF/gL+7lP6NwAAAABJRU5ErkJggg=="
)


class _Response:
    content = _PNG

    def raise_for_status(self):
        return None


def test_uses_the_official_neo_piece_urls():
    assert asset_loader.PIECE_THEME == "neo"
    assert asset_loader.piece_url("w", "Q") == (
        "https://www.chess.com/chess-themes/pieces/neo/300/wq.png"
    )
    assert asset_loader.piece_url("b", "N").endswith("/bn.png")


def test_uses_lichess_cburnett_urls_and_a_separate_cache_folder():
    assert asset_loader.piece_url("w", "K", theme="lichess") == (
        "https://lichess1.org/assets/piece/cburnett/wK.svg"
    )
    assets = Path("assets/pieces")
    assert asset_loader.piece_assets_dir(assets, "lichess") == (
        assets / "lichess-cburnett"
    )


def test_downloads_and_marks_the_complete_neo_set(monkeypatch, tmp_path):
    calls = []

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return _Response()

    monkeypatch.setattr(asset_loader.requests, "get", fake_get)

    assert asset_loader.download_pieces(tmp_path)
    assert len(calls) == 12
    assert all("/pieces/neo/300/" in url for url, _ in calls)
    assert (tmp_path / ".piece-theme").read_text() == "neo"
    assert (tmp_path / "wQ.png").read_bytes() == _PNG


def test_downloads_lichess_as_svg_and_raster_templates(monkeypatch, tmp_path):
    calls = []

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return _Response()

    def fake_render(svg, destination):
        assert svg == _PNG
        destination.write_bytes(_PNG)

    monkeypatch.setattr(asset_loader.requests, "get", fake_get)
    monkeypatch.setattr(asset_loader, "_render_svg_to_png", fake_render)

    assert asset_loader.download_pieces(tmp_path, theme="lichess")
    target = tmp_path / "lichess-cburnett"
    assert len(calls) == 12
    assert all("lichess1.org/assets/piece/cburnett/" in url for url, _ in calls)
    assert (target / ".piece-theme").read_text() == "lichess-cburnett"
    assert (target / "wK.svg").read_bytes() == _PNG
    assert (target / "wK.png").read_bytes() == _PNG
