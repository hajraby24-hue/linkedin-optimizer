"""Read the CSV archive LinkedIn hands you under "Get a copy of your data".

The archive is a ZIP of CSV files (Profile.csv, Positions.csv, Skills.csv, …),
one row per item. Column names and the exact file set vary between archive
types and over time, so everything here is matched case-insensitively, every
file is optional, and an unrecognised column is ignored rather than fatal.

A few profile attributes are simply not in the export — the photo, the banner,
the Featured section, the vanity URL. `load_export` reports those as notes
instead of guessing, so the score is never inflated by an assumption.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import Education, Experience, Profile, ProfileError

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

#: Attributes the archive never carries; the caller has to fill them in.
NOT_IN_EXPORT = (
    "has_photo",
    "has_banner",
    "featured_count",
    "custom_url",
    "target_role",
    "target_keywords",
)


@dataclass
class ExportResult:
    """A profile read from an archive, plus what could not be read."""

    profile: Profile
    notes: list[str] = field(default_factory=list)
    files_read: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile.to_dict(),
            "notes": list(self.notes),
            "files_read": list(self.files_read),
        }


def parse_date(value: str) -> str:
    """Turn LinkedIn's date strings into "YYYY-MM", "YYYY", or "".

    Handles "Mar 2021", "March 2021", "2021-03", "2021", "05 Sep 2023" and the
    "Present"/"" forms that mark a current position.
    """
    text = (value or "").strip()
    if not text or text.lower() in {"present", "current", "-"}:
        return ""

    iso = re.match(r"^(\d{4})[-/](\d{1,2})", text)
    if iso:
        return f"{iso.group(1)}-{int(iso.group(2)):02d}"

    month_name = re.search(r"([a-z]{3})[a-z]*\.?\s+(\d{4})", text, re.IGNORECASE)
    if month_name:
        month = MONTHS.get(month_name.group(1).lower())
        if month:
            return f"{month_name.group(2)}-{month:02d}"

    year_only = re.search(r"\b(\d{4})\b", text)
    return year_only.group(1) if year_only else ""


class _Archive:
    """Uniform reader over a ZIP archive or an already-extracted folder."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._zip: zipfile.ZipFile | None = None
        if path.is_dir():
            self._names = {p.name.lower(): p for p in sorted(path.rglob("*.csv"))}
            return
        if not path.is_file():
            raise ProfileError(f"Export not found: {path}")
        try:
            self._zip = zipfile.ZipFile(path)
        except zipfile.BadZipFile as exc:
            raise ProfileError(f"{path} is not a ZIP archive or a folder of CSV files") from exc
        self._names = {
            Path(name).name.lower(): name
            for name in self._zip.namelist()
            if name.lower().endswith(".csv") and not name.startswith("__MACOSX/")
        }

    def close(self) -> None:
        if self._zip is not None:
            self._zip.close()

    def has(self, filename: str) -> bool:
        return filename.lower() in self._names

    def read_rows(self, filename: str) -> list[dict[str, str]]:
        """Rows of one CSV as dicts keyed by lowercased column name."""
        entry = self._names.get(filename.lower())
        if entry is None:
            return []
        if self._zip is not None:
            raw = self._zip.read(entry)
        else:
            raw = Path(entry).read_bytes()
        text = raw.decode("utf-8-sig", errors="replace")
        return list(_rows(text))


def _rows(text: str) -> Iterator[dict[str, str]]:
    """Parse CSV text, skipping the "Notes:" preamble some files carry.

    Connections.csv in particular starts with a few prose lines and a blank
    line before the real header row.
    """
    lines = text.splitlines()
    start = 0
    for index, line in enumerate(lines):
        if line.strip().lower().startswith("notes:"):
            start = index + 1
            while start < len(lines) and lines[start].strip():
                start += 1
            while start < len(lines) and not lines[start].strip():
                start += 1
            break

    reader = csv.DictReader(io.StringIO("\n".join(lines[start:])))
    for row in reader:
        yield {
            (key or "").strip().lower(): (value or "").strip()
            for key, value in row.items()
            if key is not None
        }


def _first(row: dict[str, str], *columns: str) -> str:
    """First non-empty value among the given column names."""
    for column in columns:
        value = row.get(column.lower(), "")
        if value:
            return value
    return ""


def _names_from(rows: list[dict[str, str]]) -> list[str]:
    seen: set[str] = set()
    names = []
    for row in rows:
        name = _first(row, "name", "skill name", "language")
        if name and name.lower() not in seen:
            seen.add(name.lower())
            names.append(name)
    return names


def load_export(path: str | Path) -> ExportResult:
    """Read a LinkedIn data export into a `Profile`.

    `path` is the downloaded ZIP or a folder containing the extracted CSVs.
    """
    archive = _Archive(Path(path))
    try:
        profile = Profile()
        notes: list[str] = []
        files_read: list[str] = []

        def rows(filename: str) -> list[dict[str, str]]:
            data = archive.read_rows(filename)
            if archive.has(filename):
                files_read.append(filename)
            return data

        profile_rows = rows("Profile.csv")
        if profile_rows:
            row = profile_rows[0]
            first_name = _first(row, "first name", "firstname")
            last_name = _first(row, "last name", "lastname")
            profile.full_name = " ".join(part for part in (first_name, last_name) if part)
            profile.headline = _first(row, "headline")
            profile.about = _first(row, "summary", "about")
            profile.location = _first(row, "geo location", "location", "address")
            profile.industry = _first(row, "industry")
        else:
            notes.append("Profile.csv is missing, so the headline, About and location are empty.")

        for row in rows("Positions.csv"):
            profile.experiences.append(
                Experience(
                    title=_first(row, "title", "position"),
                    company=_first(row, "company name", "company"),
                    start_date=parse_date(_first(row, "started on", "start date")),
                    end_date=parse_date(_first(row, "finished on", "end date")),
                    location=_first(row, "location"),
                    description=_first(row, "description"),
                )
            )
        if not profile.experiences:
            notes.append("No positions found (Positions.csv missing or empty).")

        for row in rows("Education.csv"):
            profile.educations.append(
                Education(
                    school=_first(row, "school name", "school"),
                    degree=_first(row, "degree name", "degree"),
                    field_of_study=_first(row, "field of study", "major"),
                    start_year=parse_date(_first(row, "start date"))[:4],
                    end_year=parse_date(_first(row, "end date"))[:4],
                )
            )

        profile.skills = _names_from(rows("Skills.csv"))
        profile.certifications = _names_from(rows("Certifications.csv"))
        profile.languages = _names_from(rows("Languages.csv"))

        connections = rows("Connections.csv")
        profile.connections_count = len(connections)

        recommendations = rows("Recommendations_Received.csv")
        visible = [row for row in recommendations if _first(row, "status").lower() in {"", "visible"}]
        profile.recommendations_count = len(visible)

        profile.experiences = [item for item in profile.experiences if not item.is_empty]
        profile.educations = [item for item in profile.educations if not item.is_empty]

        if not files_read:
            raise ProfileError(
                f"No LinkedIn CSV files found in {path}. Point this at the ZIP you downloaded "
                "from LinkedIn (Settings → Data privacy → Get a copy of your data)."
            )

        notes.append(
            "The export does not include the profile photo, banner, Featured section or vanity "
            "URL, so these are left unset: " + ", ".join(NOT_IN_EXPORT) + "."
        )
        if profile.educations and not any(item.field_of_study for item in profile.educations):
            notes.append("Education.csv has no field-of-study column; add it by hand if it matters.")

        return ExportResult(profile=profile, notes=notes, files_read=sorted(files_read))
    finally:
        archive.close()
