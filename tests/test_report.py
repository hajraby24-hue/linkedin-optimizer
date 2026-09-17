from __future__ import annotations

import json

from linkedin_optimizer import Profile, analyze, render_json, render_markdown, render_text


def test_render_text_without_color_has_no_escape_codes(weak_profile: Profile) -> None:
    output = render_text(analyze(weak_profile), color=False, width=80)
    assert "\033[" not in output
    assert "Overall score" in output
    assert "Do these first" in output


def test_render_text_with_color_emits_escape_codes(weak_profile: Profile) -> None:
    assert "\033[" in render_text(analyze(weak_profile), color=True, width=80)


def test_render_text_lists_every_section(strong_profile: Profile) -> None:
    report = analyze(strong_profile)
    output = render_text(report, color=False, width=90)
    for result in report.results:
        assert result.title in output


def test_render_json_matches_to_dict(weak_profile: Profile) -> None:
    report = analyze(weak_profile)
    assert json.loads(render_json(report)) == json.loads(json.dumps(report.to_dict()))


def test_render_markdown_has_a_table_and_findings(weak_profile: Profile) -> None:
    output = render_markdown(analyze(weak_profile))
    assert output.startswith("# ")
    assert "| Section | Score | Points |" in output
    assert "## All findings" in output


def test_report_title_falls_back_when_the_name_is_missing() -> None:
    output = render_text(analyze(Profile.from_dict({})), color=False, width=80)
    assert output.startswith("LinkedIn profile")


def test_a_not_scored_section_is_marked_as_such() -> None:
    report = analyze(Profile.from_dict({"headline": "Engineer at Acme"}))
    assert "not scored" in render_text(report, color=False, width=90)
    assert "not scored" in render_markdown(report)
