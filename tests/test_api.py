from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi", reason="the API extra is not installed")
from fastapi.testclient import TestClient  # noqa: E402

from linkedin_optimizer import __version__  # noqa: E402
from linkedin_optimizer.api import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_rules_endpoint_lists_the_rule_set(client: TestClient) -> None:
    payload = client.get("/rules").json()
    assert payload["total_weight"] == 100.0
    assert {rule["id"] for rule in payload["rules"]} >= {"headline", "about", "experience"}


def test_analyze_scores_a_strong_profile(client: TestClient, strong_profile_data: dict) -> None:
    response = client.post("/analyze", json={"profile": strong_profile_data})
    assert response.status_code == 200
    payload = response.json()
    assert payload["score"] > 85
    assert payload["grade"] in {"A", "B"}
    assert payload["profile_name"] == "Layla Haddad"


def test_analyze_scores_a_weak_profile(client: TestClient, weak_profile_data: dict) -> None:
    payload = client.post("/analyze", json={"profile": weak_profile_data}).json()
    assert payload["grade"] == "F"
    assert payload["summary"]["critical"] >= 1
    assert payload["actions"][0]["suggestion"]


def test_analyze_accepts_an_empty_profile(client: TestClient) -> None:
    response = client.post("/analyze", json={"profile": {}})
    assert response.status_code == 200
    assert response.json()["score"] < 10


def test_max_actions_is_honoured(client: TestClient, weak_profile_data: dict) -> None:
    payload = client.post("/analyze", json={"profile": weak_profile_data, "max_actions": 2}).json()
    assert len(payload["actions"]) == 2


def test_markdown_is_opt_in(client: TestClient, weak_profile_data: dict) -> None:
    body = {"profile": weak_profile_data}
    assert "markdown" not in client.post("/analyze", json=body).json()
    with_markdown = client.post("/analyze", json={**body, "include_markdown": True}).json()
    assert with_markdown["markdown"].startswith("# Omar Nasser")


@pytest.mark.parametrize(
    "body",
    [
        {"profile": {"skills": "not a list"}},
        {"profile": {"experiences": [{"title": 5.5, "company": []}]}},
        {"max_actions": 3},
        {"profile": {}, "max_actions": 0},
    ],
)
def test_malformed_requests_are_rejected(client: TestClient, body: dict) -> None:
    assert client.post("/analyze", json=body).status_code == 422


class TestImportEndpoint:
    """POST /import: the browser hands up the archive, gets a profile back."""

    @staticmethod
    def _zip_bytes() -> bytes:
        import io
        import zipfile

        from test_linkedin_export import FULL_EXPORT

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, content in FULL_EXPORT.items():
                archive.writestr(name, content)
        return buffer.getvalue()

    def test_an_export_becomes_a_profile(self, client: TestClient) -> None:
        response = client.post(
            "/import", files={"file": ("export.zip", self._zip_bytes(), "application/zip")}
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["profile"]["full_name"] == "Layla Haddad"
        assert payload["profile"]["connections_count"] == 3
        assert payload["notes"]
        assert "Profile.csv" in payload["files_read"]

    def test_the_result_feeds_straight_into_analyze(self, client: TestClient) -> None:
        profile = client.post(
            "/import", files={"file": ("export.zip", self._zip_bytes(), "application/zip")}
        ).json()["profile"]
        response = client.post("/analyze", json={"profile": profile})
        assert response.status_code == 200
        assert response.json()["profile_name"] == "Layla Haddad"

    def test_a_file_that_is_not_a_zip_is_rejected(self, client: TestClient) -> None:
        response = client.post("/import", files={"file": ("notes.txt", b"hello", "text/plain")})
        assert response.status_code == 422
        assert "ZIP" in response.json()["detail"]

    def test_the_error_names_the_upload_not_a_server_path(self, client: TestClient) -> None:
        """A server-side temp path must never reach the browser."""
        detail = client.post(
            "/import", files={"file": ("notes.txt", b"hello", "text/plain")}
        ).json()["detail"]
        assert "notes.txt" in detail
        assert "/tmp" not in detail and "export.zip" not in detail

    def test_an_empty_upload_is_rejected(self, client: TestClient) -> None:
        response = client.post("/import", files={"file": ("empty.zip", b"", "application/zip")})
        assert response.status_code == 422

    def test_a_missing_file_field_is_rejected(self, client: TestClient) -> None:
        assert client.post("/import").status_code == 422


class TestPdfEndpoint:
    def test_a_pdf_is_returned_as_an_attachment(self, client: TestClient, weak_profile_data: dict) -> None:
        pytest.importorskip("reportlab")
        response = client.post("/report.pdf", json={"profile": weak_profile_data})
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.headers["content-disposition"] == 'attachment; filename="omar-nasser-report.pdf"'
        assert response.content.startswith(b"%PDF-")

    def test_a_nameless_profile_gets_a_default_filename(self, client: TestClient) -> None:
        pytest.importorskip("reportlab")
        response = client.post("/report.pdf", json={"profile": {}})
        assert response.headers["content-disposition"] == 'attachment; filename="linkedin-profile-report.pdf"'

    def test_the_filename_strips_characters_that_do_not_belong_in_one(self, client: TestClient) -> None:
        pytest.importorskip("reportlab")
        response = client.post("/report.pdf", json={"profile": {"full_name": 'A/B "C" <d>'}})
        disposition = response.headers["content-disposition"]
        assert "/" not in disposition.split("filename=")[1]
        assert '"' not in disposition.split("filename=")[1].strip('"')
