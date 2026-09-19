"""Reading the CSV archive LinkedIn produces under "Get a copy of your data"."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from linkedin_optimizer import analyze
from linkedin_optimizer.linkedin_export import load_export, parse_date
from linkedin_optimizer.models import ProfileError

PROFILE_CSV = (
    "First Name,Last Name,Maiden Name,Address,Birth Date,Headline,Summary,Industry,Geo Location\n"
    'Layla,Haddad,,,,"Senior Backend Engineer | Payments at scale | Python, Go",'
    '"I build payment systems that stay up on the busiest day of the year.\n\n'
    'Last year I cut the checkout error rate from 1.9% to 0.2%. Email me at layla@example.com.",'
    'Financial Services,"Amman, Jordan"\n'
)

POSITIONS_CSV = (
    "Company Name,Title,Description,Location,Started On,Finished On\n"
    'Northwind Pay,Senior Backend Engineer,"- Led the microservices migration, cutting p99 '
    'latency from 900ms to 210ms.\n- Designed the caching layer.","Amman, Jordan",Mar 2021,\n'
    'Cedar Labs,Backend Engineer,"- Built the SQL reporting service used by 40+ analysts.",'
    "Remote,Jun 2018,Feb 2021\n"
)

EDUCATION_CSV = (
    "School Name,Start Date,End Date,Notes,Degree Name,Activities\n"
    "University of Jordan,2014,2018,,BSc Computer Engineering,\n"
)

SKILLS_CSV = "Name\nPython\nGo\nMicroservices\nPostgreSQL\npython\n"
CERTIFICATIONS_CSV = (
    "Name,Url,Authority,Started On,Finished On,License Number\n"
    "AWS Certified Solutions Architect,,Amazon,Jan 2023,Jan 2026,ABC-1\n"
)
LANGUAGES_CSV = "Name,Proficiency\nArabic,NATIVE_OR_BILINGUAL\nEnglish,PROFESSIONAL_WORKING\n"

CONNECTIONS_CSV = (
    "Notes:\n"
    '"When exporting your connection data, you may notice that some of the email addresses are '
    'missing. You will only see email addresses for connections who have allowed this."\n'
    "\n"
    "First Name,Last Name,URL,Email Address,Company,Position,Connected On\n"
    "Omar,Nasser,https://www.linkedin.com/in/omar,,Acme,Engineer,05 Sep 2023\n"
    "Sara,Khalil,https://www.linkedin.com/in/sara,,Globex,Designer,11 Jan 2024\n"
    "Noor,Aziz,https://www.linkedin.com/in/noor,,Initech,Analyst,02 Feb 2024\n"
)

RECOMMENDATIONS_CSV = (
    "First Name,Last Name,Company,Job Title,Text,Creation Date,Status\n"
    "Omar,Nasser,Acme,Engineer,Great colleague.,Sep 2023,VISIBLE\n"
    "Sara,Khalil,Globex,Designer,Ships on time.,Jan 2024,VISIBLE\n"
    "Noor,Aziz,Initech,Analyst,Draft text.,Feb 2024,PENDING\n"
)

FULL_EXPORT = {
    "Profile.csv": PROFILE_CSV,
    "Positions.csv": POSITIONS_CSV,
    "Education.csv": EDUCATION_CSV,
    "Skills.csv": SKILLS_CSV,
    "Certifications.csv": CERTIFICATIONS_CSV,
    "Languages.csv": LANGUAGES_CSV,
    "Connections.csv": CONNECTIONS_CSV,
    "Recommendations_Received.csv": RECOMMENDATIONS_CSV,
}


def write_zip(path: Path, files: dict[str, str], prefix: str = "") -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(prefix + name, content)
    return path


@pytest.fixture
def export_zip(tmp_path: Path) -> Path:
    return write_zip(tmp_path / "Basic_LinkedInDataExport.zip", FULL_EXPORT)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Mar 2021", "2021-03"),
        ("March 2021", "2021-03"),
        ("Sep. 2019", "2019-09"),
        ("2021-03", "2021-03"),
        ("2021-3", "2021-03"),
        ("2018", "2018"),
        ("05 Sep 2023", "2023-09"),
        ("", ""),
        ("Present", ""),
        ("nonsense", ""),
    ],
)
def test_parse_date(raw: str, expected: str) -> None:
    assert parse_date(raw) == expected


class TestFullExport:
    def test_profile_fields(self, export_zip: Path) -> None:
        profile = load_export(export_zip).profile
        assert profile.full_name == "Layla Haddad"
        assert profile.headline.startswith("Senior Backend Engineer")
        assert "checkout error rate" in profile.about
        assert profile.location == "Amman, Jordan"
        assert profile.industry == "Financial Services"

    def test_positions_including_the_current_one(self, export_zip: Path) -> None:
        profile = load_export(export_zip).profile
        assert [experience.title for experience in profile.experiences] == [
            "Senior Backend Engineer",
            "Backend Engineer",
        ]
        current = profile.experiences[0]
        assert current.start_date == "2021-03"
        assert current.end_date == ""
        assert current.is_current is True
        assert len(current.bullets) == 2
        assert profile.experiences[1].end_date == "2021-02"

    def test_education_skills_certifications_languages(self, export_zip: Path) -> None:
        profile = load_export(export_zip).profile
        assert profile.educations[0].school == "University of Jordan"
        assert profile.educations[0].end_year == "2018"
        assert profile.skills == ["Python", "Go", "Microservices", "PostgreSQL"]  # duplicate dropped
        assert profile.certifications == ["AWS Certified Solutions Architect"]
        assert profile.languages == ["Arabic", "English"]

    def test_connections_are_counted_past_the_notes_preamble(self, export_zip: Path) -> None:
        assert load_export(export_zip).profile.connections_count == 3

    def test_only_visible_recommendations_are_counted(self, export_zip: Path) -> None:
        assert load_export(export_zip).profile.recommendations_count == 2

    def test_fields_the_export_cannot_supply_stay_unset(self, export_zip: Path) -> None:
        result = load_export(export_zip)
        assert result.profile.has_photo is False
        assert result.profile.custom_url == ""
        assert result.profile.target_keywords == []
        assert any("does not include the profile photo" in note for note in result.notes)

    def test_files_read_are_reported(self, export_zip: Path) -> None:
        assert set(load_export(export_zip).files_read) == set(FULL_EXPORT)

    def test_the_imported_profile_scores(self, export_zip: Path) -> None:
        report = analyze(load_export(export_zip).profile)
        assert 0 < report.score < 100
        assert report.category_scores["keywords"] is None  # no target set by the export

    def test_result_is_json_serialisable(self, export_zip: Path) -> None:
        payload = json.loads(json.dumps(load_export(export_zip).to_dict()))
        assert payload["profile"]["full_name"] == "Layla Haddad"
        assert payload["notes"]


class TestArchiveShapes:
    def test_a_folder_of_csvs_works_too(self, tmp_path: Path) -> None:
        folder = tmp_path / "export"
        folder.mkdir()
        for name, content in FULL_EXPORT.items():
            (folder / name).write_text(content, encoding="utf-8")
        assert load_export(folder).profile.full_name == "Layla Haddad"

    def test_files_nested_inside_a_folder_in_the_zip(self, tmp_path: Path) -> None:
        path = write_zip(tmp_path / "nested.zip", FULL_EXPORT, prefix="Basic_LinkedInDataExport/")
        assert load_export(path).profile.connections_count == 3

    def test_a_utf8_bom_is_stripped(self, tmp_path: Path) -> None:
        path = write_zip(tmp_path / "bom.zip", {"Profile.csv": "﻿" + PROFILE_CSV})
        assert load_export(path).profile.full_name == "Layla Haddad"

    def test_macos_resource_forks_are_ignored(self, tmp_path: Path) -> None:
        files = dict(FULL_EXPORT)
        files["__MACOSX/Profile.csv"] = "junk\n"
        path = tmp_path / "mac.zip"
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        assert load_export(path).profile.full_name == "Layla Haddad"

    def test_lowercase_filenames_and_headers(self, tmp_path: Path) -> None:
        path = write_zip(
            tmp_path / "lower.zip",
            {"profile.csv": "first name,last name,headline\nLayla,Haddad,Engineer\n"},
        )
        profile = load_export(path).profile
        assert profile.full_name == "Layla Haddad"
        assert profile.headline == "Engineer"


class TestPartialAndBrokenExports:
    def test_a_partial_export_reports_what_is_missing(self, tmp_path: Path) -> None:
        path = write_zip(tmp_path / "partial.zip", {"Skills.csv": SKILLS_CSV})
        result = load_export(path)
        assert result.profile.skills
        assert any("Profile.csv is missing" in note for note in result.notes)
        assert any("No positions found" in note for note in result.notes)

    def test_unknown_columns_are_ignored(self, tmp_path: Path) -> None:
        path = write_zip(
            tmp_path / "extra.zip",
            {"Profile.csv": "First Name,Headline,Some New Column\nLayla,Engineer,whatever\n"},
        )
        assert load_export(path).profile.headline == "Engineer"

    def test_empty_rows_are_dropped(self, tmp_path: Path) -> None:
        path = write_zip(
            tmp_path / "empty-rows.zip",
            {"Positions.csv": "Company Name,Title,Description\n,,\nAcme,Engineer,Built things.\n"},
        )
        assert len(load_export(path).profile.experiences) == 1

    def test_an_archive_with_no_linkedin_csvs_is_rejected(self, tmp_path: Path) -> None:
        path = write_zip(tmp_path / "other.zip", {"holiday-photos.csv": "a,b\n1,2\n"})
        with pytest.raises(ProfileError, match="No LinkedIn CSV files"):
            load_export(path)

    def test_a_file_that_is_not_a_zip_is_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.txt"
        path.write_text("hello", encoding="utf-8")
        with pytest.raises(ProfileError, match="not a ZIP archive"):
            load_export(path)

    def test_a_missing_path_is_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ProfileError, match="Export not found"):
            load_export(tmp_path / "nope.zip")

    def test_a_zip_bomb_style_nested_zip_is_not_followed(self, tmp_path: Path) -> None:
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, "w") as archive:
            archive.writestr("Profile.csv", PROFILE_CSV)
        outer = tmp_path / "outer.zip"
        with zipfile.ZipFile(outer, "w") as archive:
            archive.writestr("inner.zip", inner.getvalue())
        with pytest.raises(ProfileError, match="No LinkedIn CSV files"):
            load_export(outer)
