"""Experience checks: is each role explained in terms of outcomes?"""

from __future__ import annotations

from ..models import Profile
from ..text import has_quantified_result, starts_with_action_verb, word_count
from .base import Finding, Rule, RuleResult

MIN_DESCRIPTION_WORDS = 25
RECOMMENDED_BULLETS = 3


class ExperienceRule(Rule):
    id = "experience"
    category = "experience"
    title = "Experience"
    weight = 22.0

    def evaluate(self, profile: Profile) -> RuleResult:
        findings: list[Finding] = []

        if not profile.experiences:
            return self._result(
                0.0,
                [
                    self._finding(
                        "critical",
                        "No experience entries.",
                        "Add at least your current role: title, company, dates and what you achieved there.",
                    )
                ],
            )

        score = 1.0

        if not any(experience.is_current for experience in profile.experiences):
            score -= 0.1
            findings.append(
                self._finding(
                    "info",
                    "No position is marked as current.",
                    "Leave the end date empty on your current role, or LinkedIn treats the profile as inactive.",
                )
            )

        undescribed = [exp for exp in profile.experiences if word_count(exp.description) < MIN_DESCRIPTION_WORDS]
        if undescribed:
            score -= min(0.4, 0.2 * len(undescribed))
            labels = ", ".join(f"{exp.title or 'untitled'} @ {exp.company or 'unknown'}" for exp in undescribed[:3])
            findings.append(
                self._finding(
                    "warning" if len(undescribed) < len(profile.experiences) else "critical",
                    f"{len(undescribed)} position(s) have little or no description: {labels}.",
                    f"Give each role {RECOMMENDED_BULLETS} bullets that start with an action verb "
                    "and end with a result.",
                )
            )

        described = [exp for exp in profile.experiences if exp.bullets]
        quantified = [exp for exp in described if has_quantified_result(exp.description)]
        if described and not quantified:
            score -= 0.25
            findings.append(
                self._finding(
                    "warning",
                    "No position describes a measurable outcome.",
                    "Turn duties into results: 'Cut build time from 20 to 6 minutes' beats "
                    "'Responsible for the build system'.",
                )
            )
        elif described and len(quantified) < len(described):
            score -= 0.1
            findings.append(
                self._finding(
                    "info",
                    f"{len(described) - len(quantified)} of {len(described)} described positions carry no numbers.",
                    "Add one measurable result per role.",
                )
            )

        all_bullets = [bullet for exp in profile.experiences for bullet in exp.bullets]
        weak_bullets = [bullet for bullet in all_bullets if not starts_with_action_verb(bullet)]
        if all_bullets and len(weak_bullets) > len(all_bullets) / 2:
            score -= 0.15
            findings.append(
                self._finding(
                    "warning",
                    f"{len(weak_bullets)} of {len(all_bullets)} bullets do not start with an action verb.",
                    "Start with Led, Built, Reduced, Launched, Migrated — not 'Responsible for'.",
                )
            )

        missing_dates = [exp for exp in profile.experiences if not exp.start_date]
        if missing_dates:
            score -= 0.1
            findings.append(
                self._finding(
                    "warning",
                    f"{len(missing_dates)} position(s) have no start date.",
                    "Dates drive the seniority filters recruiters search with.",
                )
            )

        if not findings:
            findings.append(
                self._finding("success", "Every position is described with action verbs and measurable results.")
            )

        return self._result(score, findings)
