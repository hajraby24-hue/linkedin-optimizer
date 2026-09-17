"""Rule protocol and the value objects rules produce."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..models import Profile

#: Ordered from most to least urgent; the report sorts findings by this.
SEVERITIES = ("critical", "warning", "info", "success")
SEVERITY_ORDER = {severity: index for index, severity in enumerate(SEVERITIES)}


@dataclass(frozen=True)
class Finding:
    """One observation about a profile, with the fix attached."""

    rule_id: str
    category: str
    severity: str
    message: str
    suggestion: str = ""

    def __post_init__(self) -> None:
        if self.severity not in SEVERITY_ORDER:
            raise ValueError(f"Unknown severity {self.severity!r}, expected one of {SEVERITIES}")

    @property
    def is_actionable(self) -> bool:
        return self.severity != "success"

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class RuleResult:
    """A rule's verdict: a 0..1 score plus the findings that explain it."""

    rule_id: str
    category: str
    title: str
    weight: float
    score: float
    findings: list[Finding] = field(default_factory=list)
    #: False when the rule had nothing to judge (e.g. no target role was set).
    #: The engine then drops it from the total instead of awarding free points.
    applicable: bool = True

    def __post_init__(self) -> None:
        self.score = max(0.0, min(1.0, self.score))

    @property
    def weighted_points(self) -> float:
        """Points this rule contributes to the overall score."""
        return self.score * self.weight

    @property
    def points_lost(self) -> float:
        return self.weight - self.weighted_points

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "title": self.title,
            "weight": self.weight,
            "score": round(self.score, 4),
            "points": round(self.weighted_points, 2),
            "applicable": self.applicable,
            "findings": [finding.to_dict() for finding in self.findings],
        }


class Rule(ABC):
    """Base class for every check the engine runs.

    Subclasses declare `id`, `category`, `title` and `weight`, then implement
    `evaluate`. `weight` is expressed in points of the final 0-100 score.
    """

    id: str = ""
    category: str = ""
    title: str = ""
    weight: float = 0.0

    @abstractmethod
    def evaluate(self, profile: Profile) -> RuleResult:  # pragma: no cover - interface
        ...

    def _result(self, score: float, findings: list[Finding], applicable: bool = True) -> RuleResult:
        return RuleResult(
            rule_id=self.id,
            category=self.category,
            title=self.title,
            weight=self.weight,
            score=score,
            findings=findings,
            applicable=applicable,
        )

    def _finding(self, severity: str, message: str, suggestion: str = "") -> Finding:
        return Finding(
            rule_id=self.id,
            category=self.category,
            severity=severity,
            message=message,
            suggestion=suggestion,
        )
