"""Headline checks: the 220 characters recruiters see in every search result."""

from __future__ import annotations

from ..models import Profile
from ..text import contains_phrase, find_filler_phrases, tokenize
from .base import Finding, Rule, RuleResult

MAX_LENGTH = 220
MIN_USEFUL_LENGTH = 40
RECOMMENDED_LENGTH = 70
VALUE_SEPARATORS = ("|", "•", "·", "—", "–", "»")


class HeadlineRule(Rule):
    id = "headline"
    category = "headline"
    title = "Headline"
    weight = 18.0

    def evaluate(self, profile: Profile) -> RuleResult:
        headline = profile.headline.strip()
        findings: list[Finding] = []

        if not headline:
            return self._result(
                0.0,
                [
                    self._finding(
                        "critical",
                        "The headline is empty.",
                        "Write a headline in the form: Role | what you do | who you do it for. "
                        "It is indexed by search and shown next to every comment you post.",
                    )
                ],
            )

        score = 1.0
        length = len(headline)

        if length > MAX_LENGTH:
            score -= 0.25
            findings.append(
                self._finding(
                    "critical",
                    f"The headline is {length} characters; LinkedIn cuts it off at {MAX_LENGTH}.",
                    f"Trim at least {length - MAX_LENGTH} characters so nothing is lost.",
                )
            )
        elif length < MIN_USEFUL_LENGTH:
            score -= 0.3
            findings.append(
                self._finding(
                    "warning",
                    f"The headline is only {length} characters and leaves {MAX_LENGTH - length} unused.",
                    "Add your specialty and the outcome you deliver, not just the job title.",
                )
            )
        elif length < RECOMMENDED_LENGTH:
            score -= 0.1
            findings.append(
                self._finding(
                    "info",
                    f"The headline uses {length} of {MAX_LENGTH} characters.",
                    "There is room for one more keyword or a concrete result.",
                )
            )

        if not any(separator in headline for separator in VALUE_SEPARATORS):
            score -= 0.15
            findings.append(
                self._finding(
                    "info",
                    "The headline is a single block of text.",
                    "Separate two or three claims with '|' so it stays scannable.",
                )
            )

        job_title_only = len(tokenize(headline)) <= 4 and " at " in f" {headline.lower()} "
        if job_title_only:
            score -= 0.2
            findings.append(
                self._finding(
                    "warning",
                    "The headline repeats your job title and employer only.",
                    "That is already shown under your current role. Use the space for your specialty instead.",
                )
            )

        filler = find_filler_phrases(headline)
        if filler:
            score -= 0.15
            findings.append(
                self._finding(
                    "warning",
                    f"The headline contains filler wording: {', '.join(filler)}.",
                    "Replace it with something measurable, e.g. a domain, a technology, or a result.",
                )
            )

        # The role itself counts as a keyword: "Senior Backend Engineer | ..." is already searchable.
        target_terms = [term for term in ([profile.target_role] + profile.target_keywords) if term]
        missing = [term for term in target_terms if not contains_phrase(headline, term)]
        if target_terms and len(missing) == len(target_terms):
            score -= 0.2
            findings.append(
                self._finding(
                    "warning",
                    "No target keyword appears in the headline.",
                    f"Work at least one of these into it: {', '.join(target_terms[:5])}.",
                )
            )

        if not findings:
            findings.append(
                self._finding("success", "The headline is specific, keyword-rich and within the length limit.")
            )

        return self._result(score, findings)
