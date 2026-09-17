from __future__ import annotations

import pytest

from linkedin_optimizer import Profile
from linkedin_optimizer.rules import (
    DEFAULT_RULES,
    AboutRule,
    CompletenessRule,
    ExperienceRule,
    Finding,
    HeadlineRule,
    KeywordRule,
    SkillsRule,
)


def messages(result) -> str:
    return " ".join(finding.message for finding in result.findings)


def rule_ids(result) -> set[str]:
    return {finding.severity for finding in result.findings}


def test_default_rule_weights_sum_to_100() -> None:
    assert sum(rule.weight for rule in DEFAULT_RULES) == pytest.approx(100.0)


def test_rule_ids_are_unique() -> None:
    ids = [rule.id for rule in DEFAULT_RULES]
    assert len(ids) == len(set(ids))


def test_finding_rejects_an_unknown_severity() -> None:
    with pytest.raises(ValueError, match="Unknown severity"):
        Finding(rule_id="x", category="x", severity="disaster", message="x")


def test_scores_are_clamped_to_the_unit_interval() -> None:
    result = HeadlineRule().evaluate(Profile.from_dict({"headline": "!" * 400}))
    assert 0.0 <= result.score <= 1.0


class TestHeadlineRule:
    def test_empty_headline_scores_zero(self) -> None:
        result = HeadlineRule().evaluate(Profile.from_dict({}))
        assert result.score == 0.0
        assert "empty" in messages(result)

    def test_overlong_headline_is_critical(self) -> None:
        result = HeadlineRule().evaluate(Profile.from_dict({"headline": "Engineer | " * 30}))
        assert "critical" in rule_ids(result)
        assert "220" in messages(result)

    def test_job_title_only_headline_is_flagged(self) -> None:
        result = HeadlineRule().evaluate(Profile.from_dict({"headline": "Engineer at Acme"}))
        assert "job title" in messages(result)

    def test_target_role_in_the_headline_counts_as_a_keyword(self) -> None:
        profile = Profile.from_dict(
            {
                "headline": "Senior Backend Engineer | Payments at scale | Python, Go, Kubernetes",
                "target_role": "backend engineer",
                "target_keywords": ["api", "caching"],
            }
        )
        assert "No target keyword" not in messages(HeadlineRule().evaluate(profile))

    def test_a_strong_headline_scores_full_marks(self, strong_profile: Profile) -> None:
        result = HeadlineRule().evaluate(strong_profile)
        assert result.score == pytest.approx(1.0)


class TestAboutRule:
    def test_empty_about_scores_zero(self) -> None:
        assert AboutRule().evaluate(Profile.from_dict({})).score == 0.0

    def test_short_filler_about_is_penalised(self, weak_profile: Profile) -> None:
        result = AboutRule().evaluate(weak_profile)
        assert result.score < 0.4
        assert "team player" in messages(result)

    def test_missing_call_to_action_is_reported(self) -> None:
        about = "I lead payments teams. " * 20 + "I cut latency by 40% last year."
        result = AboutRule().evaluate(Profile.from_dict({"about": about}))
        assert "call to action" in messages(result)

    def test_a_strong_about_keeps_most_of_its_points(self, strong_profile: Profile) -> None:
        assert AboutRule().evaluate(strong_profile).score >= 0.9


class TestExperienceRule:
    def test_no_experience_scores_zero(self) -> None:
        assert ExperienceRule().evaluate(Profile.from_dict({})).score == 0.0

    def test_duty_style_description_is_flagged(self, weak_profile: Profile) -> None:
        result = ExperienceRule().evaluate(weak_profile)
        assert result.score < 0.5
        assert "description" in messages(result)

    def test_missing_start_date_is_flagged(self) -> None:
        profile = Profile.from_dict(
            {
                "experiences": [
                    {
                        "title": "Engineer",
                        "company": "Acme",
                        "description": "- Led the migration that cut p99 latency from 900ms to 210ms "
                        "across every checkout service in production.",
                    }
                ]
            }
        )
        assert "no start date" in messages(ExperienceRule().evaluate(profile))

    def test_a_strong_experience_section_scores_full_marks(self, strong_profile: Profile) -> None:
        assert ExperienceRule().evaluate(strong_profile).score == pytest.approx(1.0)


class TestSkillsRule:
    def test_no_skills_scores_zero(self) -> None:
        assert SkillsRule().evaluate(Profile.from_dict({})).score == 0.0

    def test_duplicates_are_reported(self) -> None:
        profile = Profile.from_dict({"skills": ["Python", "python", "SQL"]})
        assert "Duplicate" in messages(SkillsRule().evaluate(profile))

    def test_target_keywords_missing_from_the_list_are_named(self) -> None:
        profile = Profile.from_dict({"skills": ["Python"], "target_keywords": ["sql", "airflow"]})
        result = SkillsRule().evaluate(profile)
        assert "sql" in messages(result) and "airflow" in messages(result)

    def test_keywords_are_derived_from_the_target_role(self) -> None:
        profile = Profile.from_dict({"skills": ["Python"] * 20, "target_role": "data analyst"})
        assert "dashboards" in messages(SkillsRule().evaluate(profile))


class TestKeywordRule:
    def test_coverage_is_the_score(self) -> None:
        profile = Profile.from_dict(
            {"headline": "SQL and Python", "target_keywords": ["sql", "python", "airflow", "dbt"]}
        )
        result = KeywordRule().evaluate(profile)
        assert result.score == pytest.approx(0.5)
        assert "airflow" in messages(result)

    def test_no_target_means_no_penalty(self) -> None:
        result = KeywordRule().evaluate(Profile.from_dict({"headline": "Engineer"}))
        assert result.score == pytest.approx(1.0)
        assert "not scored" in messages(result)

    def test_keyword_stuffing_is_flagged(self) -> None:
        profile = Profile.from_dict({"about": "python " * 30, "target_keywords": ["python"]})
        result = KeywordRule().evaluate(profile)
        assert "appears 30 times" in messages(result)
        assert result.score < 1.0

    def test_keywords_buried_outside_the_headline_are_reported(self) -> None:
        profile = Profile.from_dict({"skills": ["Airflow"], "target_keywords": ["airflow"]})
        assert "deep in the profile" in messages(KeywordRule().evaluate(profile))


class TestCompletenessRule:
    def test_empty_profile_scores_zero(self) -> None:
        assert CompletenessRule().evaluate(Profile.from_dict({})).score == 0.0

    def test_fully_filled_profile_scores_one(self, strong_profile: Profile) -> None:
        assert CompletenessRule().evaluate(strong_profile).score == pytest.approx(1.0)

    def test_a_missing_photo_is_critical(self, strong_profile: Profile) -> None:
        strong_profile.has_photo = False
        result = CompletenessRule().evaluate(strong_profile)
        assert "critical" in rule_ids(result)
        assert result.score < 1.0
