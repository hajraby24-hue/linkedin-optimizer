"""PDF export: structure, content and the graceful path when ReportLab is absent."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from linkedin_optimizer import Profile, analyze
from linkedin_optimizer.pdf import (
    INSTALL_HINT,
    STATUS,
    TRACK,
    PdfUnavailable,
    _band,
    render_pdf,
    shape,
    write_pdf,
)

pytest.importorskip("reportlab", reason="the pdf extra is not installed")


def extract_text(payload: bytes) -> str:
    reader = pytest.importorskip("pypdf").PdfReader(io.BytesIO(payload))
    return "\n".join(page.extract_text() for page in reader.pages)


@pytest.fixture
def weak_pdf(weak_profile: Profile) -> bytes:
    return render_pdf(analyze(weak_profile))


def test_output_is_a_pdf(weak_pdf: bytes) -> None:
    assert weak_pdf.startswith(b"%PDF-")
    assert weak_pdf.rstrip().endswith(b"%%EOF")
    assert len(weak_pdf) > 2000


def test_the_score_and_grade_are_on_the_page(weak_pdf: bytes) -> None:
    text = extract_text(weak_pdf)
    assert "16.4" in text
    assert "/ 100" in text
    assert "Omar Nasser" in text


def test_every_section_is_listed(weak_profile: Profile) -> None:
    report = analyze(weak_profile)
    text = extract_text(render_pdf(report))
    for result in report.results:
        assert result.title in text


def test_actions_and_findings_are_included(weak_profile: Profile) -> None:
    report = analyze(weak_profile)
    text = extract_text(render_pdf(report)).replace("\n", " ")
    assert "Do these first" in text
    assert "All findings" in text
    assert report.actions[0].message.split(".")[0][:40] in text


def test_a_not_scored_section_says_so() -> None:
    profile = Profile.from_dict({"headline": "Engineer at Acme"})  # no target role
    assert "not scored" in extract_text(render_pdf(analyze(profile)))


def test_the_footer_carries_the_version_and_page_number(weak_pdf: bytes) -> None:
    text = extract_text(weak_pdf)
    assert "linkedin-optimizer" in text
    assert "page 1" in text


def test_an_empty_profile_still_renders() -> None:
    payload = render_pdf(analyze(Profile.from_dict({})))
    assert payload.startswith(b"%PDF-")
    assert "LinkedIn profile" in extract_text(payload)


def test_write_pdf_to_a_path(tmp_path: Path, weak_profile: Profile) -> None:
    destination = tmp_path / "report.pdf"
    write_pdf(analyze(weak_profile), destination)
    assert destination.read_bytes().startswith(b"%PDF-")


def test_write_pdf_to_an_open_file(tmp_path: Path, weak_profile: Profile) -> None:
    destination = tmp_path / "report.pdf"
    with destination.open("wb") as handle:
        write_pdf(analyze(weak_profile), handle)
    assert destination.read_bytes().startswith(b"%PDF-")


def test_markup_characters_in_a_profile_do_not_break_rendering() -> None:
    """ReportLab reads <b> as markup; profile text must be escaped, not parsed."""
    profile = Profile.from_dict({"full_name": "A <b>& B</b>", "headline": "R&D <lead>"})
    text = extract_text(render_pdf(analyze(profile)))
    assert "<b>" in text


def test_unbalanced_markup_in_a_profile_does_not_raise() -> None:
    """A stray "<" is not valid markup; escaping must keep ReportLab from parsing it."""
    profile = Profile.from_dict({"full_name": "A < B", "headline": "1 < 2 & 3 > 2"})
    assert render_pdf(analyze(profile)).startswith(b"%PDF-")


@pytest.mark.parametrize(
    "percent,band",
    [(100, "good"), (80, "good"), (79, "warning"), (50, "warning"), (49, "critical"), (0, "critical")],
)
def test_meter_bands(percent: float, band: str) -> None:
    assert _band(percent) == band


def test_every_band_has_a_fill_and_a_lighter_track() -> None:
    assert set(STATUS) == set(TRACK)
    for band, fill in STATUS.items():
        assert fill != TRACK[band]
        assert fill.startswith("#") and TRACK[band].startswith("#")


class TestRightToLeftText:
    def test_latin_text_is_untouched(self) -> None:
        assert shape("Layla Haddad") == "Layla Haddad"

    def test_arabic_text_is_reshaped(self) -> None:
        pytest.importorskip("arabic_reshaper")
        assert shape("ليلى حداد") != "ليلى حداد"

    def test_an_arabic_name_renders(self) -> None:
        payload = render_pdf(analyze(Profile.from_dict({"full_name": "ليلى حداد"})))
        assert payload.startswith(b"%PDF-")


def test_a_clear_error_when_reportlab_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fail_on_reportlab(name: str, *args: object, **kwargs: object) -> object:
        if name == "reportlab":
            raise ImportError("No module named 'reportlab'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_on_reportlab)
    with pytest.raises(PdfUnavailable, match="linkedin-optimizer\\[pdf\\]"):
        render_pdf(analyze(Profile.from_dict({})))
    assert "pip install" in INSTALL_HINT
