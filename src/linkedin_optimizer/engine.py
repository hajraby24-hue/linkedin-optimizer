"""Runs the rule set over a profile and aggregates the result."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from .models import Profile
from .rules import DEFAULT_RULES, SEVERITY_ORDER, Finding, Rule, RuleResult

GRADE_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (90.0, "A"),
    (80.0, "B"),
    (70.0, "C"),
    (55.0, "D"),
    (0.0, "F"),
)

#: How much weight a finding of each severity carries when ranking next actions.
SEVERITY_IMPACT = {"critical": 3.0, "warning": 2.0, "info": 1.0, "success": 0.0}


def grade_for(score: float) -> str:
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


@dataclass
class Action:
    """A single recommended next step, ranked by expected score impact."""

    rule_id: str
    category: str
    severity: str
    message: str
    suggestion: str
    impact: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion,
            "impact": round(self.impact, 2),
        }


@dataclass
class Report:
    """The full analysis of one profile."""

    score: float
    grade: str
    results: list[RuleResult] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    profile_name: str = ""

    @property
    def findings(self) -> list[Finding]:
        """Every finding from every rule, most urgent first."""
        return sorted(
            (finding for result in self.results for finding in result.findings),
            key=lambda finding: SEVERITY_ORDER[finding.severity],
        )

    def findings_by_severity(self, severity: str) -> list[Finding]:
        return [finding for finding in self.findings if finding.severity == severity]

    @property
    def category_scores(self) -> dict[str, float | None]:
        """Percentage per category; None where the rule did not apply."""
        return {
            result.category: round(result.score * 100, 1) if result.applicable else None
            for result in self.results
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "score": self.score,
            "grade": self.grade,
            "category_scores": self.category_scores,
            "results": [result.to_dict() for result in self.results],
            "actions": [action.to_dict() for action in self.actions],
            "summary": {
                "critical": len(self.findings_by_severity("critical")),
                "warning": len(self.findings_by_severity("warning")),
                "info": len(self.findings_by_severity("info")),
            },
        }


def _rank_actions(results: Iterable[RuleResult], limit: int) -> list[Action]:
    """Rank actionable findings by how many points their rule is losing.

    A warning inside a 22-point rule that is only half scored beats a critical
    inside a rule that is nearly full marks, because fixing it moves the needle.
    """
    actions: list[Action] = []
    for result in results:
        if not result.applicable:
            continue
        actionable = [finding for finding in result.findings if finding.is_actionable]
        if not actionable:
            continue
        total_impact = sum(SEVERITY_IMPACT[finding.severity] for finding in actionable)
        for finding in actionable:
            share = SEVERITY_IMPACT[finding.severity] / total_impact if total_impact else 0.0
            actions.append(
                Action(
                    rule_id=finding.rule_id,
                    category=finding.category,
                    severity=finding.severity,
                    message=finding.message,
                    suggestion=finding.suggestion,
                    impact=result.points_lost * share,
                )
            )
    actions.sort(key=lambda action: (-action.impact, SEVERITY_ORDER[action.severity]))
    return actions[:limit]


def analyze(
    profile: Profile,
    rules: Sequence[Rule] | None = None,
    max_actions: int = 5,
) -> Report:
    """Score `profile` against `rules` (the default rule set when omitted)."""
    active_rules = list(rules if rules is not None else DEFAULT_RULES)
    results = [rule.evaluate(profile) for rule in active_rules]

    scored = [result for result in results if result.applicable]
    total_weight = sum(result.weight for result in scored)
    earned = sum(result.weighted_points for result in scored)
    score = round(100 * earned / total_weight, 1) if total_weight else 0.0

    return Report(
        score=score,
        grade=grade_for(score),
        results=results,
        actions=_rank_actions(results, max_actions),
        profile_name=profile.full_name,
    )
