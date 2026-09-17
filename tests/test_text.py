from __future__ import annotations

import pytest

from linkedin_optimizer.text import (
    contains_phrase,
    find_filler_phrases,
    has_quantified_result,
    keywords_for_role,
    starts_with_action_verb,
    tokenize,
    top_terms,
    word_count,
)


def test_tokenize_drops_stopwords_and_keeps_tech_tokens() -> None:
    assert tokenize("We use C# and node.js in the API") == ["use", "c#", "node.js", "api"]


def test_word_count_counts_every_word() -> None:
    assert word_count("We use C# and node.js in the API") == 8


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Cut latency by 40%", True),
        ("Saved $2.5m a year", True),
        ("Managed a team of 12", True),
        ("Improved things a lot", False),
        ("Worked on 3 things", False),
    ],
)
def test_has_quantified_result(text: str, expected: bool) -> None:
    assert has_quantified_result(text) is expected


def test_contains_phrase_matches_whole_words_only() -> None:
    assert contains_phrase("I work on APIs daily", "api") is False
    assert contains_phrase("I design the API layer", "api") is True
    assert contains_phrase("Built an ML pipeline", "machine learning") is False


@pytest.mark.parametrize(
    "sentence,expected",
    [
        ("Led the migration", True),
        ("Reduced churn", True),
        ("Responsible for the backlog", False),
        ("", False),
    ],
)
def test_starts_with_action_verb(sentence: str, expected: bool) -> None:
    assert starts_with_action_verb(sentence) is expected


def test_find_filler_phrases() -> None:
    found = find_filler_phrases("A hardworking team player and self-starter")
    assert set(found) == {"hardworking", "team player", "self-starter"}


def test_keywords_for_role_matches_loosely() -> None:
    assert keywords_for_role("Senior Data Scientist") == keywords_for_role("data scientist")
    assert keywords_for_role("") == []
    assert keywords_for_role("underwater basket weaver") == []


def test_top_terms_ranks_by_frequency() -> None:
    assert top_terms("python python sql", limit=2) == [("python", 2), ("sql", 1)]
