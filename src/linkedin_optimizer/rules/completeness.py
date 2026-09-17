"""Profile completeness: the one-off settings that gate reach."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..models import Profile
from .base import Finding, Rule, RuleResult

#: Below this, LinkedIn shows "500+" instead of a number and second-degree reach suffers.
HEALTHY_CONNECTIONS = 500
RECOMMENDED_RECOMMENDATIONS = 2


@dataclass(frozen=True)
class Item:
    """One completeness checkbox, with the message used when it is unchecked."""

    key: str
    points: float
    severity: str
    check: Callable[[Profile], bool]
    message: str
    suggestion: str


ITEMS: tuple[Item, ...] = (
    Item(
        "photo", 2.0, "critical", lambda p: p.has_photo,
        "No profile photo.",
        "A profile with a photo gets far more profile views; use a plain background and a clear face.",
    ),
    Item(
        "banner", 1.0, "info", lambda p: p.has_banner,
        "No background banner.",
        "The banner is free space for your specialty, your employer, or a link.",
    ),
    Item(
        "name", 1.0, "critical", lambda p: bool(p.full_name),
        "No full name set.",
        "Use the name colleagues would search for, with no emoji or job title attached.",
    ),
    Item(
        "location", 1.0, "warning", lambda p: bool(p.location),
        "No location set.",
        "Location is one of the most used recruiter filters.",
    ),
    Item(
        "industry", 1.0, "warning", lambda p: bool(p.industry),
        "No industry set.",
        "Industry decides which searches and feeds you surface in.",
    ),
    Item(
        "custom_url", 1.0, "info", lambda p: bool(p.custom_url),
        "The profile URL still has the default random suffix.",
        "Claim linkedin.com/in/your-name; it is what you put on a CV.",
    ),
    Item(
        "education", 1.0, "info", lambda p: bool(p.educations),
        "No education entries.",
        "Add school and field of study even for an unfinished degree.",
    ),
    Item(
        "certifications", 1.0, "info", lambda p: bool(p.certifications),
        "No certifications listed.",
        "Certifications are indexed and add credibility to the skills you claim.",
    ),
    Item(
        "languages", 1.0, "info", lambda p: bool(p.languages),
        "No languages listed.",
        "Languages matter for regional and remote roles.",
    ),
    Item(
        "featured", 1.0, "info", lambda p: p.featured_count > 0,
        "The Featured section is empty.",
        "Pin a project, an article, or a talk — it is the only section that shows your work directly.",
    ),
    Item(
        "recommendations", 2.0, "warning",
        lambda p: p.recommendations_count >= RECOMMENDED_RECOMMENDATIONS,
        f"Fewer than {RECOMMENDED_RECOMMENDATIONS} recommendations.",
        "Ask two people you worked closely with; offer to write theirs first.",
    ),
    Item(
        "connections", 2.0, "info",
        lambda p: p.connections_count >= HEALTHY_CONNECTIONS,
        f"Fewer than {HEALTHY_CONNECTIONS} connections.",
        f"Past {HEALTHY_CONNECTIONS} your posts reach a materially wider second-degree network.",
    ),
)


class CompletenessRule(Rule):
    id = "completeness"
    category = "completeness"
    title = "Profile completeness"
    weight = 12.0

    def evaluate(self, profile: Profile) -> RuleResult:
        findings: list[Finding] = []
        earned = 0.0
        available = sum(item.points for item in ITEMS)
        missing = []

        for item in ITEMS:
            if item.check(profile):
                earned += item.points
            else:
                missing.append(item)
                findings.append(self._finding(item.severity, item.message, item.suggestion))

        if not missing:
            findings.append(self._finding("success", "Every completeness item is filled in."))
        else:
            findings.insert(
                0,
                self._finding(
                    "info",
                    f"{len(ITEMS) - len(missing)} of {len(ITEMS)} completeness items are done.",
                ),
            )

        return self._result(earned / available, findings)
