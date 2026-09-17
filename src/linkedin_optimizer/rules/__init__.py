"""The rule set applied to every profile."""

from __future__ import annotations

from .about import AboutRule
from .base import SEVERITIES, SEVERITY_ORDER, Finding, Rule, RuleResult
from .completeness import CompletenessRule
from .experience import ExperienceRule
from .headline import HeadlineRule
from .keywords import KeywordRule
from .skills import SkillsRule

#: Order matters only for presentation; weights sum to 100.
DEFAULT_RULES: tuple[Rule, ...] = (
    HeadlineRule(),
    AboutRule(),
    ExperienceRule(),
    SkillsRule(),
    KeywordRule(),
    CompletenessRule(),
)

__all__ = [
    "AboutRule",
    "CompletenessRule",
    "DEFAULT_RULES",
    "ExperienceRule",
    "Finding",
    "HeadlineRule",
    "KeywordRule",
    "Rule",
    "RuleResult",
    "SEVERITIES",
    "SEVERITY_ORDER",
    "SkillsRule",
]
