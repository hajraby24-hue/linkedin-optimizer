"""Skills checks: coverage, focus and alignment with the target role."""

from __future__ import annotations

from ..models import Profile
from ..text import contains_phrase, keywords_for_role
from .base import Finding, Rule, RuleResult

MIN_SKILLS = 5
RECOMMENDED_SKILLS = 15
MAX_SKILLS = 50
#: LinkedIn shows the first three skills on the profile card.
PINNED_SKILLS = 3


class SkillsRule(Rule):
    id = "skills"
    category = "skills"
    title = "Skills"
    weight = 12.0

    def evaluate(self, profile: Profile) -> RuleResult:
        skills = profile.skills
        findings: list[Finding] = []

        if not skills:
            return self._result(
                0.0,
                [
                    self._finding(
                        "critical",
                        "No skills listed.",
                        f"Add {RECOMMENDED_SKILLS}+ skills; recruiter search filters read this section directly.",
                    )
                ],
            )

        score = 1.0

        if len(skills) < MIN_SKILLS:
            score -= 0.4
            findings.append(
                self._finding(
                    "warning",
                    f"Only {len(skills)} skills listed.",
                    f"Add at least {RECOMMENDED_SKILLS}; LinkedIn allows up to {MAX_SKILLS}.",
                )
            )
        elif len(skills) < RECOMMENDED_SKILLS:
            score -= 0.15
            findings.append(
                self._finding(
                    "info",
                    f"{len(skills)} skills listed.",
                    f"{RECOMMENDED_SKILLS}+ widens the searches you appear in.",
                )
            )
        elif len(skills) > MAX_SKILLS:
            score -= 0.1
            findings.append(
                self._finding(
                    "warning",
                    f"{len(skills)} skills listed; LinkedIn keeps only {MAX_SKILLS}.",
                    "Drop the weakest ones yourself instead of letting the list be truncated.",
                )
            )

        seen: dict[str, str] = {}
        duplicates = []
        for skill in skills:
            key = skill.lower()
            if key in seen:
                duplicates.append(skill)
            seen[key] = skill
        if duplicates:
            score -= 0.1
            findings.append(
                self._finding(
                    "info",
                    f"Duplicate skills: {', '.join(duplicates[:5])}.",
                    "Each duplicate wastes one of your slots.",
                )
            )

        target_terms = profile.target_keywords or keywords_for_role(profile.target_role)
        if target_terms:
            skills_text = " \n ".join(skills)
            missing = [term for term in target_terms if not contains_phrase(skills_text, term)]
            if missing:
                score -= min(0.3, 0.1 * len(missing))
                findings.append(
                    self._finding(
                        "warning" if len(missing) > len(target_terms) / 2 else "info",
                        f"Target skills missing from the list: {', '.join(missing[:6])}.",
                        "Add the ones you genuinely have, then ask colleagues to endorse them.",
                    )
                )
            pinned = " \n ".join(skills[:PINNED_SKILLS])
            if not any(contains_phrase(pinned, term) for term in target_terms):
                score -= 0.1
                findings.append(
                    self._finding(
                        "info",
                        f"None of your first {PINNED_SKILLS} skills matches the target role.",
                        f"LinkedIn shows the first {PINNED_SKILLS} on the profile card — reorder them.",
                    )
                )

        if not findings:
            findings.append(self._finding("success", "The skills list is complete and aligned with the target role."))

        return self._result(score, findings)
