"""Rendering of a `Report` for the terminal and for machines."""

from __future__ import annotations

import json
import shutil

from .engine import Report

SEVERITY_LABEL = {
    "critical": "CRITICAL",
    "warning": "WARNING ",
    "info": "INFO    ",
    "success": "OK      ",
}

SEVERITY_COLOR = {
    "critical": "\033[31m",
    "warning": "\033[33m",
    "info": "\033[36m",
    "success": "\033[32m",
}
RESET = "\033[0m"
BOLD = "\033[1m"

BAR_WIDTH = 24


def _paint(text: str, code: str, color: bool) -> str:
    return f"{code}{text}{RESET}" if color else text


def _bar(percent: float, width: int = BAR_WIDTH) -> str:
    filled = int(round(width * max(0.0, min(100.0, percent)) / 100))
    return "█" * filled + "░" * (width - filled)


def _wrap(text: str, width: int, indent: str) -> str:
    """Wrap `text` under an arrow bullet; continuation lines align, without a second arrow."""
    import textwrap

    return textwrap.fill(
        text,
        width=max(width, 40),
        initial_indent=indent,
        subsequent_indent=" " * len(indent),
    )


def render_text(report: Report, color: bool = True, width: int | None = None) -> str:
    """Human-readable report for the terminal."""
    term_width = width or min(shutil.get_terminal_size((100, 24)).columns, 100)
    lines: list[str] = []

    title = report.profile_name or "LinkedIn profile"
    lines.append(_paint(f"{title} — optimization report", BOLD, color))
    lines.append("=" * term_width)

    grade_color = SEVERITY_COLOR["success" if report.score >= 80 else "warning" if report.score >= 55 else "critical"]
    lines.append(
        f"Overall score: {_paint(f'{report.score:.1f}/100  (grade {report.grade})', grade_color, color)}"
    )
    lines.append("")

    lines.append(_paint("Scores by section", BOLD, color))
    for result in report.results:
        if not result.applicable:
            lines.append(f"  {result.title:<22} {'not scored':^{BAR_WIDTH}}       —")
            continue
        percent = result.score * 100
        lines.append(
            f"  {result.title:<22} {_bar(percent)} {percent:5.1f}%"
            f"   {result.weighted_points:5.1f}/{result.weight:.0f} pts"
        )
    lines.append("")

    if report.actions:
        lines.append(_paint("Do these first", BOLD, color))
        for index, action in enumerate(report.actions, start=1):
            label = _paint(SEVERITY_LABEL[action.severity].strip(), SEVERITY_COLOR[action.severity], color)
            lines.append(f"  {index}. [{label}] {action.message}  (+{action.impact:.1f} pts)")
            if action.suggestion:
                lines.append(_wrap(action.suggestion, term_width - 6, "      → "))
        lines.append("")

    lines.append(_paint("All findings", BOLD, color))
    for finding in report.findings:
        label = _paint(SEVERITY_LABEL[finding.severity], SEVERITY_COLOR[finding.severity], color)
        lines.append(f"  {label} [{finding.category}] {finding.message}")
        if finding.suggestion:
            lines.append(_wrap(finding.suggestion, term_width - 6, "           → "))

    counts = report.to_dict()["summary"]
    lines.append("")
    lines.append(
        f"{counts['critical']} critical · {counts['warning']} warnings · {counts['info']} notes"
    )
    return "\n".join(lines)


def render_json(report: Report, indent: int = 2) -> str:
    """Machine-readable report, stable enough to diff between runs."""
    return json.dumps(report.to_dict(), indent=indent, ensure_ascii=False)


def render_markdown(report: Report) -> str:
    """Report as Markdown, for pasting into a document or a PR comment."""
    title = report.profile_name or "LinkedIn profile"
    lines = [
        f"# {title} — optimization report",
        "",
        f"**Score: {report.score:.1f}/100 (grade {report.grade})**",
        "",
        "| Section | Score | Points |",
        "| --- | --- | --- |",
    ]
    for result in report.results:
        if result.applicable:
            lines.append(
                f"| {result.title} | {result.score * 100:.0f}% | {result.weighted_points:.1f}/{result.weight:.0f} |"
            )
        else:
            lines.append(f"| {result.title} | not scored | — |")

    if report.actions:
        lines += ["", "## Do these first", ""]
        for index, action in enumerate(report.actions, start=1):
            lines.append(f"{index}. **{action.message}** _(+{action.impact:.1f} pts)_")
            if action.suggestion:
                lines.append(f"   - {action.suggestion}")

    lines += ["", "## All findings", ""]
    for finding in report.findings:
        lines.append(f"- `{finding.severity}` **[{finding.category}]** {finding.message}")
        if finding.suggestion:
            lines.append(f"  - {finding.suggestion}")
    return "\n".join(lines)
