"""Small text helpers shared by the rules.

Deliberately dependency-free: the analysis engine runs anywhere Python does,
with no NLP model to download.
"""

from __future__ import annotations

import re
from collections import Counter

WORD_RE = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")
QUANTIFIER_RE = re.compile(
    r"(\d+(?:[.,]\d+)?\s*(?:%|percent|k\b|m\b|bn\b|x\b))|([$€£]\s*\d)|(\b\d{2,}\b)",
    re.IGNORECASE,
)

STOPWORDS = frozenset(
    """
    a an and are as at be been but by for from had has have how i in is it its
    me my of on or our that the their them they this to was we were what when
    which who will with you your about into over more most very can also just
    """.split()
)

# Verbs that make an experience bullet read as an accomplishment.
ACTION_VERBS = frozenset(
    """
    achieved analyzed architected automated built championed coached created cut
    delivered deployed designed developed directed drove eliminated engineered
    established expanded generated grew implemented improved increased initiated
    introduced launched led managed migrated modernized negotiated optimized
    orchestrated overhauled owned pioneered planned produced reduced refactored
    rebuilt scaled shipped simplified spearheaded standardized streamlined
    supervised trained transformed unified
    """.split()
)

# Phrases that take up space without telling a recruiter anything.
FILLER_PHRASES = (
    "hard worker",
    "hard working",
    "hardworking",
    "team player",
    "results-driven",
    "results driven",
    "detail-oriented",
    "detail oriented",
    "self-starter",
    "self starter",
    "go-getter",
    "think outside the box",
    "passionate about",
    "guru",
    "ninja",
    "rockstar",
    "rock star",
    "synergy",
    "world-class",
    "seeking opportunities",
    "looking for opportunities",
)

# Starting points when the profile names a target role but no keywords.
ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "software engineer": ("python", "api", "testing", "code review", "ci/cd", "system design"),
    "backend engineer": ("api", "database", "microservices", "scalability", "sql", "caching"),
    "frontend engineer": ("react", "typescript", "accessibility", "performance", "css", "ui"),
    "data scientist": ("python", "machine learning", "statistics", "sql", "experimentation", "modeling"),
    "data analyst": ("sql", "dashboards", "reporting", "excel", "visualization", "kpi"),
    "data engineer": ("etl", "pipelines", "sql", "airflow", "warehouse", "streaming"),
    "product manager": ("roadmap", "discovery", "stakeholders", "metrics", "user research", "prioritization"),
    "project manager": ("planning", "budget", "stakeholders", "delivery", "risk", "agile"),
    "designer": ("figma", "user research", "prototyping", "design system", "usability", "wireframes"),
    "marketing": ("seo", "campaigns", "content", "analytics", "conversion", "brand"),
    "sales": ("pipeline", "quota", "crm", "negotiation", "prospecting", "revenue"),
    "devops engineer": ("kubernetes", "terraform", "ci/cd", "monitoring", "aws", "automation"),
    "security engineer": ("threat modeling", "incident response", "siem", "vulnerability", "compliance", "iam"),
}


def tokenize(text: str) -> list[str]:
    """Lowercased word tokens, stopwords removed."""
    return [word for word in WORD_RE.findall(text.lower()) if word not in STOPWORDS]


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text.lower()))


def top_terms(text: str, limit: int = 10, min_length: int = 3) -> list[tuple[str, int]]:
    """Most frequent meaningful terms, highest count first."""
    counts = Counter(word for word in tokenize(text) if len(word) >= min_length)
    return counts.most_common(limit)


def contains_phrase(text: str, phrase: str) -> bool:
    """Whole-phrase match that ignores case and surrounding punctuation."""
    pattern = r"(?<![a-z0-9])" + re.escape(phrase.lower()) + r"(?![a-z0-9])"
    return re.search(pattern, text.lower()) is not None


def find_filler_phrases(text: str) -> list[str]:
    return [phrase for phrase in FILLER_PHRASES if contains_phrase(text, phrase)]


def has_quantified_result(text: str) -> bool:
    """True when the text carries a number a recruiter can weigh."""
    return QUANTIFIER_RE.search(text) is not None


def starts_with_action_verb(sentence: str) -> bool:
    words = WORD_RE.findall(sentence.lower())
    if not words:
        return False
    first = words[0]
    return first in ACTION_VERBS or (first.endswith("ed") and first[:-1] in ACTION_VERBS)


def keywords_for_role(role: str) -> list[str]:
    """Suggested keywords for a role name, matched loosely."""
    normalized = role.strip().lower()
    if not normalized:
        return []
    if normalized in ROLE_KEYWORDS:
        return list(ROLE_KEYWORDS[normalized])
    for known, keywords in ROLE_KEYWORDS.items():
        if known in normalized or normalized in known:
            return list(keywords)
    # Fall back to a shared word, e.g. "senior data scientist" -> "data scientist".
    role_words = set(tokenize(normalized))
    for known, keywords in ROLE_KEYWORDS.items():
        if role_words & set(tokenize(known)):
            return list(keywords)
    return []
