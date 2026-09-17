"""Command line interface: `linkedin-optimizer analyze profile.json`."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from . import __version__
from .engine import analyze
from .models import Profile, ProfileError
from .report import render_json, render_markdown, render_text
from .templates import BLANK_PROFILE

EXIT_OK = 0
EXIT_BELOW_THRESHOLD = 1
EXIT_BAD_INPUT = 2

RENDERERS = {
    "text": lambda report, color: render_text(report, color=color),
    "json": lambda report, color: render_json(report),
    "markdown": lambda report, color: render_markdown(report),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linkedin-optimizer",
        description="Score a LinkedIn profile and list what to fix first.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="analyze a profile JSON file")
    analyze_parser.add_argument(
        "profile",
        help="path to the profile JSON file, or '-' to read it from stdin",
    )
    analyze_parser.add_argument(
        "-f", "--format", choices=sorted(RENDERERS), default="text", help="output format (default: text)"
    )
    analyze_parser.add_argument("-o", "--output", help="write the report to this file instead of stdout")
    analyze_parser.add_argument("--target-role", help="override the target role from the file")
    analyze_parser.add_argument(
        "--target-keyword",
        action="append",
        dest="target_keywords",
        metavar="KEYWORD",
        help="add a target keyword (repeatable); overrides the file when given",
    )
    analyze_parser.add_argument(
        "--max-actions", type=int, default=5, help="how many next steps to rank (default: 5)"
    )
    analyze_parser.add_argument(
        "--fail-under",
        type=float,
        metavar="SCORE",
        help=f"exit with status {EXIT_BELOW_THRESHOLD} when the score is below SCORE",
    )
    analyze_parser.add_argument("--no-color", action="store_true", help="disable ANSI colors")

    init_parser = subparsers.add_parser("init", help="write a blank profile template")
    init_parser.add_argument(
        "path", nargs="?", default="profile.json", help="file to create (default: profile.json)"
    )
    init_parser.add_argument("--force", action="store_true", help="overwrite the file if it exists")

    subparsers.add_parser("rules", help="list the rules and their weights")
    return parser


def _load_profile(source: str, stdin: TextIO) -> Profile:
    if source == "-":
        return Profile.from_json(stdin.read())
    return Profile.from_file(source)


def _command_analyze(args: argparse.Namespace, stdout: TextIO, stdin: TextIO) -> int:
    profile = _load_profile(args.profile, stdin)
    if args.target_role:
        profile.target_role = args.target_role
    if args.target_keywords:
        profile.target_keywords = args.target_keywords

    report = analyze(profile, max_actions=args.max_actions)
    color = not args.no_color and getattr(stdout, "isatty", lambda: False)()
    rendered = RENDERERS[args.format](report, color)

    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(f"Report written to {args.output} (score {report.score:.1f}/100)", file=stdout)
    else:
        print(rendered, file=stdout)

    if args.fail_under is not None and report.score < args.fail_under:
        print(
            f"Score {report.score:.1f} is below the required {args.fail_under:.1f}.",
            file=sys.stderr,
        )
        return EXIT_BELOW_THRESHOLD
    return EXIT_OK


def _command_init(args: argparse.Namespace, stdout: TextIO) -> int:
    path = Path(args.path)
    if path.exists() and not args.force:
        print(f"{path} already exists; pass --force to overwrite it.", file=sys.stderr)
        return EXIT_BAD_INPUT
    path.write_text(json.dumps(BLANK_PROFILE, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Created {path}. Fill it in, then run: linkedin-optimizer analyze {path}", file=stdout)
    return EXIT_OK


def _command_rules(stdout: TextIO) -> int:
    from .rules import DEFAULT_RULES

    print(f"{'ID':<14}{'CATEGORY':<16}{'WEIGHT':>7}  TITLE", file=stdout)
    for rule in DEFAULT_RULES:
        print(f"{rule.id:<14}{rule.category:<16}{rule.weight:>7.0f}  {rule.title}", file=stdout)
    print(f"{'total':<14}{'':<16}{sum(rule.weight for rule in DEFAULT_RULES):>7.0f}", file=stdout)
    return EXIT_OK


def main(
    argv: Sequence[str] | None = None,
    stdout: TextIO | None = None,
    stdin: TextIO | None = None,
) -> int:
    """Entry point. Returns the process exit status instead of raising."""
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    inp = stdin or sys.stdin

    try:
        if args.command == "analyze":
            return _command_analyze(args, out, inp)
        if args.command == "init":
            return _command_init(args, out)
        if args.command == "rules":
            return _command_rules(out)
    except ProfileError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT

    parser.error(f"unknown command {args.command!r}")
    return EXIT_BAD_INPUT  # pragma: no cover - argparse exits first


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
