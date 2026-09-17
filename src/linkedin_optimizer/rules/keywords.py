"""Keyword coverage: does the profile contain the terms recruiters search for?"""

from __future__ import annotations

from ..models import Profile
from ..text import contains_phrase, keywords_for_role, top_terms
from .base import Finding, Rule, RuleResult

#: A keyword repeated this often reads as stuffing rather than emphasis.
STUFFING_THRESHOLD = 12


class KeywordRule(Rule):
    id = "keywords"
    category = "keywords"
    title = "Keyword coverage"
    weight = 16.0

    def evaluate(self, profile: Profile) -> RuleResult:
        findings: list[Finding] = []
        text = profile.searchable_text()

        if not text.strip():
            return self._result(
                0.0,
                [
                    self._finding(
                        "critical",
                        "The profile has no text to index.",
                        "Fill in the headline and About first.",
                    )
                ],
            )

        targets = profile.target_keywords or keywords_for_role(profile.target_role)
        if not targets:
            findings.append(
                self._finding(
                    "info",
                    "No target role or keywords set, so keyword coverage was not scored.",
                    "Set 'target_role' or 'target_keywords' to check the profile against a real job description.",
                )
            )
            observed = ", ".join(term for term, _ in top_terms(text, limit=8))
            if observed:
                findings.append(
                    self._finding("info", f"The profile currently reads strongest on: {observed}.")
                )
            return self._result(1.0, findings, applicable=False)

        present = [term for term in targets if contains_phrase(text, term)]
        missing = [term for term in targets if term not in present]
        coverage = len(present) / len(targets)

        if missing:
            severity = "critical" if coverage < 0.4 else "warning" if coverage < 0.75 else "info"
            findings.append(
                self._finding(
                    severity,
                    f"Keyword coverage is {coverage:.0%} ({len(present)}/{len(targets)}). "
                    f"Missing: {', '.join(missing)}.",
                    "Place each missing keyword where it is true: headline, About, a role description, or skills.",
                )
            )

        headline_and_about = f"{profile.headline}\n{profile.about}"
        buried = [term for term in present if not contains_phrase(headline_and_about, term)]
        if buried:
            findings.append(
                self._finding(
                    "info",
                    f"Present but only deep in the profile: {', '.join(buried[:6])}.",
                    "Terms in the headline and About carry the most weight in search ranking.",
                )
            )

        words = text.split()
        for term, count in top_terms(text, limit=5):
            if count >= STUFFING_THRESHOLD and count / max(len(words), 1) > 0.03:
                findings.append(
                    self._finding(
                        "warning",
                        f"'{term}' appears {count} times.",
                        "Repetition past a handful of mentions reads as keyword stuffing to a human reader.",
                    )
                )
                coverage -= 0.05
                break

        if not missing and not buried:
            findings.append(
                self._finding("success", f"All {len(targets)} target keywords appear in the profile.")
            )

        return self._result(coverage, findings)
