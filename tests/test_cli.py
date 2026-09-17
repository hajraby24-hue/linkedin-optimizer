from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from linkedin_optimizer.cli import EXIT_BAD_INPUT, EXIT_BELOW_THRESHOLD, EXIT_OK, main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
STRONG = str(EXAMPLES / "strong_profile.json")
WEAK = str(EXAMPLES / "weak_profile.json")


def run(*argv: str, stdin: str = "") -> tuple[int, str]:
    out = io.StringIO()
    status = main(list(argv), stdout=out, stdin=io.StringIO(stdin))
    return status, out.getvalue()


def test_analyze_prints_a_text_report() -> None:
    status, output = run("analyze", STRONG)
    assert status == EXIT_OK
    assert "Overall score" in output
    assert "Layla Haddad" in output


def test_analyze_json_output_is_parsable() -> None:
    status, output = run("analyze", WEAK, "--format", "json")
    payload = json.loads(output)
    assert status == EXIT_OK
    assert payload["grade"] == "F"
    assert payload["actions"]


def test_analyze_markdown_output() -> None:
    _, output = run("analyze", STRONG, "--format", "markdown")
    assert output.startswith("# Layla Haddad")


def test_analyze_reads_stdin() -> None:
    status, output = run("analyze", "-", "--format", "json", stdin='{"headline": "Engineer at Acme"}')
    assert status == EXIT_OK
    assert json.loads(output)["score"] < 30


def test_analyze_writes_to_a_file(tmp_path: Path) -> None:
    destination = tmp_path / "report.md"
    status, output = run("analyze", STRONG, "--format", "markdown", "-o", str(destination))
    assert status == EXIT_OK
    assert "Report written to" in output
    assert destination.read_text(encoding="utf-8").startswith("# Layla Haddad")


def test_target_overrides_from_the_command_line() -> None:
    _, output = run(
        "analyze", WEAK, "--format", "json", "--target-keyword", "kubernetes", "--target-keyword", "terraform"
    )
    findings = json.dumps(json.loads(output)["results"])
    assert "kubernetes" in findings and "terraform" in findings


def test_max_actions_limits_the_list() -> None:
    _, output = run("analyze", WEAK, "--format", "json", "--max-actions", "2")
    assert len(json.loads(output)["actions"]) == 2


def test_fail_under_sets_the_exit_status() -> None:
    assert run("analyze", WEAK, "--format", "json", "--fail-under", "70")[0] == EXIT_BELOW_THRESHOLD
    assert run("analyze", STRONG, "--format", "json", "--fail-under", "70")[0] == EXIT_OK


def test_missing_file_is_a_clean_error() -> None:
    assert run("analyze", "does-not-exist.json")[0] == EXIT_BAD_INPUT


def test_invalid_json_is_a_clean_error() -> None:
    assert run("analyze", "-", stdin="{oops}")[0] == EXIT_BAD_INPUT


def test_init_writes_a_template_and_refuses_to_overwrite(tmp_path: Path) -> None:
    destination = tmp_path / "profile.json"
    status, output = run("init", str(destination))
    assert status == EXIT_OK
    assert "Created" in output
    assert "headline" in json.loads(destination.read_text(encoding="utf-8"))

    assert run("init", str(destination))[0] == EXIT_BAD_INPUT
    assert run("init", str(destination), "--force")[0] == EXIT_OK


def test_the_generated_template_analyzes_without_crashing(tmp_path: Path) -> None:
    destination = tmp_path / "profile.json"
    run("init", str(destination))
    status, output = run("analyze", str(destination), "--format", "json")
    assert status == EXIT_OK
    assert json.loads(output)["score"] == 0.0


def test_rules_lists_every_rule_with_its_weight() -> None:
    status, output = run("rules")
    assert status == EXIT_OK
    assert "headline" in output and "completeness" in output
    assert "100" in output


def test_a_missing_subcommand_is_rejected() -> None:
    with pytest.raises(SystemExit):
        run()
