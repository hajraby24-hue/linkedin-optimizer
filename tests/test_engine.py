from __future__ import annotations

import pytest

from linkedin_optimizer import Profile, analyze
from linkedin_optimizer.engine import grade_for
from linkedin_optimizer.rules import Finding, Rule, RuleResult


class StubRule(Rule):
    id = "stub"
    category = "stub"
    title = "Stub"
    weight = 10.0

    def __init__(self, score: float) -> None:
        self._score = score

    def evaluate(self, profile: Profile) -> RuleResult:
        return self._result(
            self._score,
            [Finding(rule_id=self.id, category=self.category, severity="warning", message="stub finding")],
        )


@pytest.mark.parametrize(
    "score,grade", [(100.0, "A"), (90.0, "A"), (85.0, "B"), (72.0, "C"), (60.0, "D"), (10.0, "F")]
)
def test_grade_for(score: float, grade: str) -> None:
    assert grade_for(score) == grade


def test_empty_profile_scores_near_zero() -> None:
    report = analyze(Profile.from_dict({}))
    assert report.score < 10.0
    assert report.grade == "F"


def test_strong_profile_outscores_weak_profile(strong_profile: Profile, weak_profile: Profile) -> None:
    assert analyze(strong_profile).score > analyze(weak_profile).score + 40


def test_score_is_the_weighted_average_of_rule_scores() -> None:
    report = analyze(Profile.from_dict({}), rules=[StubRule(0.5), StubRule(1.0)])
    assert report.score == pytest.approx(75.0)


def test_findings_are_sorted_by_severity(weak_profile: Profile) -> None:
    severities = [finding.severity for finding in analyze(weak_profile).findings]
    assert severities == sorted(severities, key=["critical", "warning", "info", "success"].index)


def test_actions_are_capped_and_ranked_by_impact(weak_profile: Profile) -> None:
    report = analyze(weak_profile, max_actions=3)
    impacts = [action.impact for action in report.actions]
    assert len(report.actions) == 3
    assert impacts == sorted(impacts, reverse=True)


def test_successful_findings_never_become_actions(strong_profile: Profile) -> None:
    report = analyze(strong_profile)
    assert all(action.severity != "success" for action in report.actions)


def test_category_scores_cover_every_rule(strong_profile: Profile) -> None:
    report = analyze(strong_profile)
    assert set(report.category_scores) == {result.category for result in report.results}
    assert all(value is None or 0 <= value <= 100 for value in report.category_scores.values())


def test_a_rule_without_input_is_excluded_from_the_total() -> None:
    profile = Profile.from_dict({"headline": "Engineer at Acme"})  # no target role or keywords
    report = analyze(profile)
    keyword_result = next(result for result in report.results if result.rule_id == "keywords")
    assert keyword_result.applicable is False
    assert report.category_scores["keywords"] is None
    assert all(action.category != "keywords" for action in report.actions)


def test_setting_a_target_makes_keyword_coverage_count() -> None:
    profile = Profile.from_dict({"headline": "Engineer at Acme", "target_role": "data scientist"})
    keyword_result = next(r for r in analyze(profile).results if r.rule_id == "keywords")
    assert keyword_result.applicable is True
    assert keyword_result.score < 0.5


def test_to_dict_is_json_serialisable(weak_profile: Profile) -> None:
    import json

    payload = json.loads(json.dumps(analyze(weak_profile).to_dict()))
    assert payload["grade"] == "F"
    assert payload["summary"]["critical"] >= 1
    assert payload["results"][0]["rule_id"] == "headline"


def test_fixing_the_about_section_raises_the_score(weak_profile: Profile) -> None:
    before = analyze(weak_profile).score
    weak_profile.about = (
        "I build data products. Last year I shipped a churn model that cut cancellations by 18% "
        "and saved $1.2m. I work in Python and SQL, and I care most about experiments that change "
        "a decision rather than dashboards nobody opens. Reach out at omar@example.com."
    )
    assert analyze(weak_profile).score > before
