"""PDF rendering of a report, for sharing or filing alongside a CV.

Needs the optional `pdf` extra (ReportLab); `render_pdf` raises `PdfUnavailable`
with the install command when it is missing, so the rest of the tool keeps
working without it.

Layout follows the same reading order as the terminal report: the score as a
single hero figure, one meter per section, the ranked actions, then every
finding. Each meter carries its percentage as text, so severity is never
colour-alone.
"""

from __future__ import annotations

import datetime as dt
import io
from pathlib import Path
from typing import Any, BinaryIO

from . import __version__
from .engine import Report

#: Fixed status palette: fill colour carries severity, always beside a label.
STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "critical": "#d03b3b",
}
#: The unfilled part of a meter is a light step of the fill's own hue.
TRACK = {
    "good": "#dbf0db",
    "warning": "#fdefd1",
    "critical": "#f6d8d8",
}
SEVERITY_COLOR = {
    "critical": STATUS["critical"],
    "warning": STATUS["warning"],
    "info": "#4a5a6a",
    "success": STATUS["good"],
}
SEVERITY_LABEL = {
    "critical": "CRITICAL",
    "warning": "WARNING",
    "info": "NOTE",
    "success": "OK",
}

INK = "#1a1d21"
MUTED = "#5d6874"
RULE = "#d9dee3"
NEUTRAL_TRACK = "#e7eaee"

#: Fonts tried in order; the first one present is used so non-Latin names
#: (Arabic, for one) render as glyphs rather than boxes.
FONT_CANDIDATES = (
    ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("NotoSans", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
     "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
    ("LiberationSans", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
)

INSTALL_HINT = 'PDF output needs ReportLab. Install it with: pip install "linkedin-optimizer[pdf]"'


class PdfUnavailable(RuntimeError):
    """Raised when the optional PDF dependency is not installed."""


def _require_reportlab() -> Any:
    try:
        import reportlab  # noqa: F401
    except ImportError as error:  # pragma: no cover - exercised by a monkeypatched test
        raise PdfUnavailable(INSTALL_HINT) from error
    return reportlab


def _register_fonts() -> tuple[str, str]:
    """Return (regular, bold) font names, registering a Unicode TTF if there is one."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for name, regular, bold in FONT_CANDIDATES:
        if Path(regular).is_file() and Path(bold).is_file():
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, regular))
                pdfmetrics.registerFont(TTFont(f"{name}-Bold", bold))
            return name, f"{name}-Bold"
    return "Helvetica", "Helvetica-Bold"


def shape(text: str) -> str:
    """Shape and reorder right-to-left text when the optional libraries are present.

    Arabic letters are stored unjoined and logically ordered; without this a
    name like a profile owner's renders as disconnected, reversed glyphs.
    Latin text is returned untouched.
    """
    if not any("֐" <= char <= "ࣿ" for char in text):
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError:
        return text
    return get_display(arabic_reshaper.reshape(text))


def _band(percent: float) -> str:
    if percent >= 80:
        return "good"
    if percent >= 50:
        return "warning"
    return "critical"


def _build_meter(width: float, label: str, percent: float | None, font: str, bold: str) -> Any:
    """One section meter: label, track, fill, and the percentage as text."""
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.lib.colors import HexColor

    height = 26.0
    bar_height = 7.0
    bar_top = 0.0
    label_width = width * 0.40
    value_width = 58.0
    bar_width = width - label_width - value_width

    drawing = Drawing(width, height)
    drawing.add(String(0, height - 14, shape(label), fontName=bold, fontSize=9, fillColor=HexColor(INK)))

    if percent is None:
        drawing.add(
            String(
                label_width, height - 14, "not scored",
                fontName=font, fontSize=9, fillColor=HexColor(MUTED),
            )
        )
        return drawing

    band = _band(percent)
    drawing.add(
        Rect(
            label_width, bar_top + 2, bar_width, bar_height,
            rx=bar_height / 2, ry=bar_height / 2,
            fillColor=HexColor(TRACK[band]), strokeColor=None,
        )
    )
    if percent > 0:
        # A rounded cap cannot be narrower than the bar is tall, so a tiny score
        # still reads as a sliver — but a true zero draws nothing at all.
        filled = max(bar_height, bar_width * min(100.0, percent) / 100)
        drawing.add(
            Rect(
                label_width, bar_top + 2, filled, bar_height,
                rx=bar_height / 2, ry=bar_height / 2,
                fillColor=HexColor(STATUS[band]), strokeColor=None,
            )
        )
    drawing.add(
        String(
            label_width + bar_width + 8, bar_top + 2, f"{percent:.0f}%",
            fontName=bold, fontSize=9, fillColor=HexColor(INK),
        )
    )
    return drawing


def render_pdf(report: Report) -> bytes:
    """Render `report` as a PDF document and return its bytes."""
    _require_reportlab()

    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        PageBreak,  # noqa: F401 - kept available for future sectioning
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    font, bold = _register_fonts()
    buffer = io.BytesIO()
    margin = 18 * mm
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=18 * mm,
        title=f"{report.profile_name or 'LinkedIn profile'} — optimization report",
        author=f"linkedin-optimizer {__version__}",
    )
    width = document.width

    def style(name: str, **kwargs: Any) -> ParagraphStyle:
        base = {"fontName": font, "fontSize": 9.5, "leading": 13.5, "textColor": HexColor(INK)}
        base.update(kwargs)
        return ParagraphStyle(name, alignment=TA_LEFT, **base)

    title_style = style("title", fontName=bold, fontSize=17, leading=21)
    hero_style = style("hero", fontName=bold, fontSize=38, leading=42)
    muted_style = style("muted", textColor=HexColor(MUTED), fontSize=9)
    heading_style = style("heading", fontName=bold, fontSize=12, leading=16, spaceBefore=14)
    body_style = style("body")
    suggestion_style = style("suggestion", textColor=HexColor(MUTED), leftIndent=14, fontSize=9)

    story: list[Any] = []
    # Escaped, not just shaped: ReportLab parses a Paragraph as markup, so a name
    # containing "<" would be swallowed or raise.
    story.append(Paragraph(_escape(report.profile_name or "LinkedIn profile"), title_style))
    story.append(Paragraph("Profile optimization report", muted_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.7, color=HexColor(RULE)))
    story.append(Spacer(1, 12))

    band = _band(report.score)
    story.append(
        Paragraph(
            f'<font color="{STATUS[band]}">{report.score:.1f}</font>'
            f'<font size="14" color="{MUTED}"> / 100</font>'
            f'<font size="20"> &nbsp;{report.grade}</font>',
            hero_style,
        )
    )
    counts = report.to_dict()["summary"]
    story.append(
        Paragraph(
            f"{counts['critical']} critical · {counts['warning']} warnings · {counts['info']} notes",
            muted_style,
        )
    )
    story.append(Spacer(1, 16))

    story.append(Paragraph("Scores by section", heading_style))
    story.append(Spacer(1, 4))
    for result in report.results:
        percent = result.score * 100 if result.applicable else None
        story.append(_build_meter(width, result.title, percent, font, bold))

    if report.actions:
        story.append(Paragraph("Do these first", heading_style))
        for index, action in enumerate(report.actions, start=1):
            story.append(
                Paragraph(
                    f"<b>{index}. {_escape(action.message)}</b> "
                    f'<font color="{MUTED}">(+{action.impact:.1f} pts)</font>',
                    body_style,
                )
            )
            if action.suggestion:
                story.append(Paragraph(_escape(action.suggestion), suggestion_style))
            story.append(Spacer(1, 5))

    story.append(Paragraph("All findings", heading_style))
    for finding in report.findings:
        color = SEVERITY_COLOR[finding.severity]
        story.append(
            Paragraph(
                f'<font color="{color}"><b>{SEVERITY_LABEL[finding.severity]}</b></font> '
                f'<font color="{MUTED}">[{finding.category}]</font> {_escape(finding.message)}',
                body_style,
            )
        )
        if finding.suggestion:
            story.append(Paragraph(_escape(finding.suggestion), suggestion_style))
        story.append(Spacer(1, 4))

    generated = dt.date.today().isoformat()

    def decorate(canvas: Any, _document: Any) -> None:
        canvas.saveState()
        canvas.setFont(font, 7.5)
        canvas.setFillColor(HexColor(MUTED))
        canvas.drawString(
            margin, 12 * mm, f"linkedin-optimizer {__version__} · generated {generated}"
        )
        canvas.drawRightString(A4[0] - margin, 12 * mm, f"page {canvas.getPageNumber()}")
        canvas.restoreState()

    document.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return buffer.getvalue()


def _escape(text: str) -> str:
    """Escape the handful of characters ReportLab reads as markup."""
    return (
        shape(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def write_pdf(report: Report, target: str | Path | BinaryIO) -> None:
    """Render `report` and write it to a path or an open binary file."""
    payload = render_pdf(report)
    if isinstance(target, (str, Path)):
        Path(target).write_bytes(payload)
    else:
        target.write(payload)
