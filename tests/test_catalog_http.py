"""HTTP catalog loading."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from uvdrop.catalog import check_app_path, is_catalog_url, load_all_catalogs, load_catalog_url
from uvdrop.i18n import set_language


@pytest.fixture()
def catalog_http_server(tmp_path: Path):
    app_dir = tmp_path / "apps" / "demo"
    app_dir.mkdir(parents=True)
    (app_dir / "main.py").write_text("print(1)\n", encoding="utf-8")
    payload = {
        "version": 1,
        "catalog": "HTTP Team",
        "base": str(tmp_path),
        "apps": [
            {
                "id": "demo",
                "name": "Demo",
                "summary": "from http",
                "path": "apps/demo",
                "command": "main.py",
            }
        ],
    }
    body = json.dumps(payload).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path.rstrip("/") != "/catalog.json":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    url = f"http://{host}:{port}/catalog.json"
    yield url
    server.shutdown()


def test_is_catalog_url() -> None:
    assert is_catalog_url("https://example.com/c.json")
    assert is_catalog_url("http://127.0.0.1:9/x")
    assert not is_catalog_url(r"\\server\share\c.json")
    assert not is_catalog_url("C:/cats/c.json")


def test_load_catalog_url(catalog_http_server: str) -> None:
    set_language("en")
    result = load_catalog_url(catalog_http_server)
    assert not result.errors
    assert len(result.apps) == 1
    assert result.apps[0].name == "Demo"
    assert result.title == "HTTP Team"
    resolved = check_app_path(result.apps[0])
    assert resolved.is_dir()


def test_load_all_mixes_file_and_url(tmp_path: Path, catalog_http_server: str) -> None:
    local = tmp_path / "local.json"
    local.write_text(
        json.dumps({"catalog": "Local", "apps": [{"name": "L", "path": "x"}]}),
        encoding="utf-8",
    )
    merged = load_all_catalogs([str(local), catalog_http_server])
    assert [a.name for a in merged.apps] == ["L", "Demo"]


def test_http_relative_without_base_errors() -> None:
    set_language("en")
    from uvdrop.catalog import CatalogApp

    app = CatalogApp(
        name="X",
        path="relative/app",
        catalog_path="https://example.com/catalog.json",
        path_base="",
    )
    with pytest.raises(ValueError, match="base"):
        check_app_path(app)
