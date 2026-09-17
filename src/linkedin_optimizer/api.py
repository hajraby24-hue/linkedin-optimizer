"""HTTP API and web UI around the analysis engine.

Run it with:  uvicorn linkedin_optimizer.api:app --reload
The form is then served at / and the OpenAPI docs at /docs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .engine import analyze
from .models import Profile, ProfileError
from .report import render_markdown
from .rules import DEFAULT_RULES

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="LinkedIn Optimizer",
    version=__version__,
    summary="Score a LinkedIn profile and return ranked, concrete fixes.",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """The web UI: a form that posts to /analyze and renders the report."""
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


class ExperienceIn(BaseModel):
    title: str = ""
    company: str = ""
    start_date: str = ""
    end_date: str = ""
    location: str = ""
    description: str = ""


class EducationIn(BaseModel):
    school: str = ""
    degree: str = ""
    field_of_study: str = ""
    start_year: str = ""
    end_year: str = ""


class ProfileIn(BaseModel):
    """Request body. Every field is optional; missing ones simply score as absent."""

    full_name: str = ""
    headline: str = ""
    about: str = ""
    location: str = ""
    industry: str = ""
    experiences: list[ExperienceIn] = Field(default_factory=list)
    educations: list[EducationIn] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    featured_count: int = 0
    recommendations_count: int = 0
    connections_count: int = 0
    has_photo: bool = False
    has_banner: bool = False
    custom_url: str = ""
    target_role: str = ""
    target_keywords: list[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    profile: ProfileIn
    max_actions: int = Field(default=5, ge=1, le=50)
    include_markdown: bool = False


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/rules", tags=["meta"])
def list_rules() -> dict[str, Any]:
    return {
        "total_weight": sum(rule.weight for rule in DEFAULT_RULES),
        "rules": [
            {"id": rule.id, "category": rule.category, "title": rule.title, "weight": rule.weight}
            for rule in DEFAULT_RULES
        ],
    }


@app.post("/analyze", tags=["analysis"])
def analyze_profile(request: AnalyzeRequest) -> dict[str, Any]:
    try:
        profile = Profile.from_dict(request.profile.model_dump())
    except ProfileError as error:  # pragma: no cover - pydantic catches most of these first
        raise HTTPException(status_code=422, detail=str(error)) from error

    report = analyze(profile, max_actions=request.max_actions)
    payload = report.to_dict()
    if request.include_markdown:
        payload["markdown"] = render_markdown(report)
    return payload
