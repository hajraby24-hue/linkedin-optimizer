"""linkedin-optimizer — score a LinkedIn profile and say what to fix first.

The whole analysis is local, deterministic and dependency-free:

    from linkedin_optimizer import Profile, analyze

    report = Profile.from_file("profile.json")
    print(analyze(report).score)
"""

from __future__ import annotations

from .engine import Action, Report, analyze, grade_for
from .models import Education, Experience, Profile, ProfileError
from .report import render_json, render_markdown, render_text
from .rules import DEFAULT_RULES, Finding, Rule, RuleResult

__version__ = "0.1.0"

__all__ = [
    "Action",
    "DEFAULT_RULES",
    "Education",
    "Experience",
    "Finding",
    "Profile",
    "ProfileError",
    "Report",
    "Rule",
    "RuleResult",
    "__version__",
    "analyze",
    "grade_for",
    "render_json",
    "render_markdown",
    "render_text",
]
