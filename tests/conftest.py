"""Shared fixtures: the two reference profiles used across the test suite."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from linkedin_optimizer import Profile

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def strong_profile_data() -> dict:
    return json.loads((EXAMPLES / "strong_profile.json").read_text(encoding="utf-8"))


@pytest.fixture
def weak_profile_data() -> dict:
    return json.loads((EXAMPLES / "weak_profile.json").read_text(encoding="utf-8"))


@pytest.fixture
def strong_profile(strong_profile_data: dict) -> Profile:
    return Profile.from_dict(strong_profile_data)


@pytest.fixture
def weak_profile(weak_profile_data: dict) -> Profile:
    return Profile.from_dict(weak_profile_data)
