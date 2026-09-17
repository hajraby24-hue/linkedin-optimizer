"""Data model for a LinkedIn profile under analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ProfileError(ValueError):
    """Raised when raw profile data cannot be turned into a `Profile`."""


def _as_str(data: dict[str, Any], key: str, default: str = "") -> str:
    value = data.get(key, default)
    if value is None:
        return default
    if not isinstance(value, (str, int, float)):
        raise ProfileError(f"Field '{key}' must be a string, got {type(value).__name__}")
    return str(value).strip()


def _as_int(data: dict[str, Any], key: str, default: int = 0) -> int:
    value = data.get(key, default)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ProfileError(f"Field '{key}' must be a number, got {type(value).__name__}")
    try:
        return int(value)
    except ValueError as exc:
        raise ProfileError(f"Field '{key}' must be a number, got {value!r}") from exc


def _as_bool(data: dict[str, Any], key: str, default: bool = False) -> bool:
    value = data.get(key, default)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    raise ProfileError(f"Field '{key}' must be a boolean, got {type(value).__name__}")


def _as_str_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key) or []
    if isinstance(value, str):
        value = [part for part in value.split(",")]
    if not isinstance(value, list):
        raise ProfileError(f"Field '{key}' must be a list, got {type(value).__name__}")
    items = []
    for item in value:
        if not isinstance(item, (str, int, float)):
            raise ProfileError(f"Field '{key}' must contain strings, got {type(item).__name__}")
        text = str(item).strip()
        if text:
            items.append(text)
    return items


def _as_dict_list(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key) or []
    if not isinstance(value, list):
        raise ProfileError(f"Field '{key}' must be a list, got {type(value).__name__}")
    for item in value:
        if not isinstance(item, dict):
            raise ProfileError(f"Every entry of '{key}' must be an object, got {type(item).__name__}")
    return value


@dataclass
class Experience:
    """A single position in the experience section."""

    title: str = ""
    company: str = ""
    start_date: str = ""
    end_date: str = ""
    location: str = ""
    description: str = ""

    @property
    def is_current(self) -> bool:
        return self.end_date.strip().lower() in {"", "present", "current"}

    @property
    def is_empty(self) -> bool:
        """True when the entry carries no information (e.g. an untouched template row)."""
        return not any([self.title, self.company, self.location, self.bullets])

    @property
    def bullets(self) -> list[str]:
        """Description split into individual lines, bullet markers stripped."""
        lines = []
        for raw in self.description.splitlines():
            line = raw.strip().lstrip("-*•·–—").strip()
            if line:
                lines.append(line)
        return lines

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Experience:
        return cls(
            title=_as_str(data, "title"),
            company=_as_str(data, "company"),
            start_date=_as_str(data, "start_date"),
            end_date=_as_str(data, "end_date"),
            location=_as_str(data, "location"),
            description=_as_str(data, "description"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "company": self.company,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "location": self.location,
            "description": self.description,
        }


@dataclass
class Education:
    """A single entry in the education section."""

    school: str = ""
    degree: str = ""
    field_of_study: str = ""
    start_year: str = ""
    end_year: str = ""

    @property
    def is_empty(self) -> bool:
        return not any([self.school, self.degree, self.field_of_study])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Education:
        return cls(
            school=_as_str(data, "school"),
            degree=_as_str(data, "degree"),
            field_of_study=_as_str(data, "field_of_study"),
            start_year=_as_str(data, "start_year"),
            end_year=_as_str(data, "end_year"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "school": self.school,
            "degree": self.degree,
            "field_of_study": self.field_of_study,
            "start_year": self.start_year,
            "end_year": self.end_year,
        }


@dataclass
class Profile:
    """Everything the analyzer needs to know about a profile.

    Only `headline` and `about` carry weight on their own; the rest feeds
    completeness and keyword coverage checks.
    """

    full_name: str = ""
    headline: str = ""
    about: str = ""
    location: str = ""
    industry: str = ""
    experiences: list[Experience] = field(default_factory=list)
    educations: list[Education] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    featured_count: int = 0
    recommendations_count: int = 0
    connections_count: int = 0
    has_photo: bool = False
    has_banner: bool = False
    custom_url: str = ""
    target_role: str = ""
    target_keywords: list[str] = field(default_factory=list)

    @property
    def current_experience(self) -> Experience | None:
        for experience in self.experiences:
            if experience.is_current:
                return experience
        return self.experiences[0] if self.experiences else None

    def searchable_text(self) -> str:
        """All free text of the profile, joined and lowercased."""
        parts = [self.headline, self.about, self.industry, *self.skills, *self.certifications]
        for experience in self.experiences:
            parts.extend([experience.title, experience.company, experience.description])
        for education in self.educations:
            parts.extend([education.degree, education.field_of_study, education.school])
        return "\n".join(part for part in parts if part).lower()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Profile:
        if not isinstance(data, dict):
            raise ProfileError(f"Profile data must be an object, got {type(data).__name__}")
        return cls(
            full_name=_as_str(data, "full_name"),
            headline=_as_str(data, "headline"),
            about=_as_str(data, "about"),
            location=_as_str(data, "location"),
            industry=_as_str(data, "industry"),
            experiences=[
                entry
                for entry in (Experience.from_dict(item) for item in _as_dict_list(data, "experiences"))
                if not entry.is_empty
            ],
            educations=[
                entry
                for entry in (Education.from_dict(item) for item in _as_dict_list(data, "educations"))
                if not entry.is_empty
            ],
            skills=_as_str_list(data, "skills"),
            certifications=_as_str_list(data, "certifications"),
            languages=_as_str_list(data, "languages"),
            featured_count=_as_int(data, "featured_count"),
            recommendations_count=_as_int(data, "recommendations_count"),
            connections_count=_as_int(data, "connections_count"),
            has_photo=_as_bool(data, "has_photo"),
            has_banner=_as_bool(data, "has_banner"),
            custom_url=_as_str(data, "custom_url"),
            target_role=_as_str(data, "target_role"),
            target_keywords=_as_str_list(data, "target_keywords"),
        )

    @classmethod
    def from_json(cls, text: str) -> Profile:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProfileError(f"Invalid JSON: {exc}") from exc
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, path: str | Path) -> Profile:
        file_path = Path(path)
        if not file_path.is_file():
            raise ProfileError(f"Profile file not found: {file_path}")
        return cls.from_json(file_path.read_text(encoding="utf-8"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name,
            "headline": self.headline,
            "about": self.about,
            "location": self.location,
            "industry": self.industry,
            "experiences": [item.to_dict() for item in self.experiences],
            "educations": [item.to_dict() for item in self.educations],
            "skills": list(self.skills),
            "certifications": list(self.certifications),
            "languages": list(self.languages),
            "featured_count": self.featured_count,
            "recommendations_count": self.recommendations_count,
            "connections_count": self.connections_count,
            "has_photo": self.has_photo,
            "has_banner": self.has_banner,
            "custom_url": self.custom_url,
            "target_role": self.target_role,
            "target_keywords": list(self.target_keywords),
        }
