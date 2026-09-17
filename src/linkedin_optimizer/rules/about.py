"""About-section checks: the hook, the substance and the call to action."""

from __future__ import annotations

import re

from ..models import Profile
from ..text import find_filler_phrases, has_quantified_result, word_count
from .base import Finding, Rule, RuleResult

MAX_LENGTH = 2600
#: Characters visible before LinkedIn collapses the section behind "see more".
PREVIEW_LENGTH = 265
MIN_WORDS = 60
RECOMMENDED_WORDS = 150

CONTACT_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|https?://|dm me|message me|get in touch|reach out|contact me", re.I)
FIRST_PERSON_RE = re.compile(r"\b(i|i'm|i've|my|me)\b", re.I)


class AboutRule(Rule):
    id = "about"
    category = "about"
    title = "About section"
    weight = 20.0

    def evaluate(self, profile: Profile) -> RuleResult:
        about = profile.about.strip()
        findings: list[Finding] = []

        if not about:
            return self._result(
                0.0,
                [
                    self._finding(
                        "critical",
                        "The About section is empty.",
                        "Write 3-5 short paragraphs: what you do, proof you can do it, "
                        "what you are looking for, and how to reach you.",
                    )
                ],
            )

        score = 1.0
        words = word_count(about)

        if len(about) > MAX_LENGTH:
            score -= 0.2
            findings.append(
                self._finding(
                    "critical",
                    f"The About section is {len(about)} characters; the limit is {MAX_LENGTH}.",
                    f"Cut about {len(about) - MAX_LENGTH} characters or the end will be rejected.",
                )
            )
        elif words < MIN_WORDS:
            score -= 0.35
            findings.append(
                self._finding(
                    "warning",
                    f"The About section is only {words} words.",
                    f"Aim for {RECOMMENDED_WORDS}+ words: it is the section recruiters read after the headline.",
                )
            )
        elif words < RECOMMENDED_WORDS:
            score -= 0.1
            findings.append(
                self._finding(
                    "info",
                    f"The About section is {words} words.",
                    "One more paragraph of concrete results would strengthen it.",
                )
            )

        preview = about[:PREVIEW_LENGTH]
        if not has_quantified_result(preview) and words >= MIN_WORDS:
            score -= 0.1
            findings.append(
                self._finding(
                    "info",
                    f"The first {PREVIEW_LENGTH} characters (all that is shown before 'see more') carry no number.",
                    "Open with a concrete result so the preview earns the click.",
                )
            )

        if not has_quantified_result(about):
            score -= 0.2
            findings.append(
                self._finding(
                    "warning",
                    "The About section contains no measurable result.",
                    "Add at least one number: team size, growth, latency, revenue, users.",
                )
            )

        if not FIRST_PERSON_RE.search(about):
            score -= 0.1
            findings.append(
                self._finding(
                    "info",
                    "The About section is written in the third person.",
                    "First person reads as a conversation and performs better on LinkedIn.",
                )
            )

        if not CONTACT_RE.search(about):
            score -= 0.15
            findings.append(
                self._finding(
                    "warning",
                    "The About section ends without a call to action.",
                    "Close with how to reach you: an email, a link, or an invitation to message you.",
                )
            )

        filler = find_filler_phrases(about)
        if filler:
            score -= min(0.2, 0.05 * len(filler))
            findings.append(
                self._finding(
                    "warning",
                    f"Filler wording found: {', '.join(filler)}.",
                    "Replace each with a specific example of the same claim.",
                )
            )

        if not findings:
            findings.append(
                self._finding("success", "The About section is substantial, concrete and ends with a call to action.")
            )

        return self._result(score, findings)
