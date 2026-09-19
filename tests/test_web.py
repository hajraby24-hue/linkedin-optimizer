"""The static web UI: served correctly and wired to the API it calls."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="the API extra is not installed")
from fastapi.testclient import TestClient  # noqa: E402

from linkedin_optimizer.api import STATIC_DIR, app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_index_serves_the_form(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<form class="panel" id="profile-form"' in response.text


def test_index_is_not_in_the_openapi_schema(client: TestClient) -> None:
    assert "/" not in client.get("/openapi.json").json()["paths"]


@pytest.mark.parametrize(
    "name,content_type",
    [("styles.css", "text/css"), ("app.js", "text/javascript"), ("favicon.svg", "image/svg+xml")],
)
def test_static_assets_are_served(client: TestClient, name: str, content_type: str) -> None:
    response = client.get(f"/static/{name}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_type)


def test_every_asset_the_page_references_exists(client: TestClient) -> None:
    page = client.get("/").text
    for asset in ("/static/styles.css", "/static/app.js", "/static/favicon.svg"):
        assert asset in page
        assert client.get(asset).status_code == 200


def test_the_page_is_arabic_and_right_to_left(client: TestClient) -> None:
    assert '<html lang="ar" dir="rtl">' in client.get("/").text


def test_the_script_posts_to_the_analyze_endpoint() -> None:
    script = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert 'fetch("/analyze"' in script
    assert '"content-type": "application/json"' in script


def test_static_directory_ships_with_the_package() -> None:
    assert STATIC_DIR.is_dir()
    assert {path.name for path in STATIC_DIR.iterdir()} >= {"index.html", "app.js", "styles.css"}


def test_the_form_field_names_match_the_api_schema(client: TestClient) -> None:
    """Every name= in the form must be a field the ProfileIn model accepts."""
    import re

    page = client.get("/").text
    schema = client.get("/openapi.json").json()["components"]["schemas"]["ProfileIn"]["properties"]
    form_fields = set(re.findall(r'<(?:input|textarea)[^>]*\bname="([a-z_]+)"', page))
    assert form_fields <= set(schema), form_fields - set(schema)
    assert {"headline", "about", "skills", "target_role"} <= form_fields


def test_a_traversal_attempt_does_not_escape_the_static_directory(client: TestClient) -> None:
    assert client.get("/static/../api.py").status_code == 404


def test_the_bundled_files_are_plain_local_assets() -> None:
    """The tool runs offline: nothing may be pulled from a CDN."""
    page = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert "http://" not in page
    assert "https://" not in page


def test_no_unexpected_files_in_the_static_directory() -> None:
    assert all(path.suffix in {".html", ".css", ".js", ".svg"} for path in Path(STATIC_DIR).iterdir())


def test_the_page_offers_the_export_upload(client: TestClient) -> None:
    page = client.get("/").text
    assert 'id="export-file"' in page
    assert 'accept=".zip,application/zip"' in page


def test_the_script_posts_the_archive_to_the_import_endpoint() -> None:
    script = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert 'fetch("/import"' in script
    assert "FormData" in script
