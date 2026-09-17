from __future__ import annotations

import json

import pytest

from linkedin_optimizer import Experience, Profile, ProfileError


def test_from_dict_reads_every_section(strong_profile: Profile) -> None:
    assert strong_profile.full_name == "Layla Haddad"
    assert len(strong_profile.experiences) == 2
    assert strong_profile.educations[0].field_of_study == "Computer Engineering"
    assert "Kubernetes" in strong_profile.skills
    assert strong_profile.has_photo is True


def test_missing_fields_fall_back_to_empty_defaults() -> None:
    profile = Profile.from_dict({})
    assert profile.headline == ""
    assert profile.skills == []
    assert profile.connections_count == 0
    assert profile.current_experience is None


def test_skills_accept_a_comma_separated_string() -> None:
    profile = Profile.from_dict({"skills": "Python, SQL , , Go"})
    assert profile.skills == ["Python", "SQL", "Go"]


@pytest.mark.parametrize(
    "payload",
    [
        {"headline": ["not", "a", "string"]},
        {"skills": {"not": "a list"}},
        {"experiences": ["not an object"]},
        {"connections_count": "many"},
    ],
)
def test_bad_types_raise_profile_error(payload: dict) -> None:
    with pytest.raises(ProfileError):
        Profile.from_dict(payload)


def test_from_json_reports_invalid_json() -> None:
    with pytest.raises(ProfileError, match="Invalid JSON"):
        Profile.from_json("{not json}")


def test_from_file_reports_a_missing_path(tmp_path) -> None:
    with pytest.raises(ProfileError, match="not found"):
        Profile.from_file(tmp_path / "nope.json")


def test_round_trip_through_dict(strong_profile: Profile) -> None:
    restored = Profile.from_dict(json.loads(json.dumps(strong_profile.to_dict())))
    assert restored == strong_profile


def test_current_experience_prefers_the_open_ended_role() -> None:
    profile = Profile.from_dict(
        {
            "experiences": [
                {"title": "Old", "start_date": "2015-01", "end_date": "2018-01"},
                {"title": "Now", "start_date": "2018-02", "end_date": ""},
            ]
        }
    )
    assert profile.current_experience is not None
    assert profile.current_experience.title == "Now"


def test_experience_bullets_strip_markers() -> None:
    experience = Experience(description="- Led a team\n• Shipped v2\n\n  Cut costs  ")
    assert experience.bullets == ["Led a team", "Shipped v2", "Cut costs"]


def test_searchable_text_covers_all_sections(strong_profile: Profile) -> None:
    text = strong_profile.searchable_text()
    assert "kubernetes" in text
    assert "northwind pay" in text
    assert "computer engineering" in text
