"""Render a CompanyReport to PDF bytes, via HTML + WeasyPrint.

WeasyPrint is an optional dependency (`pip install -e ".[pdf]"`) since it
pulls in native libs (Pango/Cairo/GDK-Pixbuf) that plain markdown/json/html
output doesn't need. Imported lazily so the base install stays light.
"""

from __future__ import annotations

from research_agent.render import report_to_html
from research_agent.schema import CompanyReport


def report_to_pdf(report: CompanyReport) -> bytes:
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError(
            'PDF output requires the "pdf" extra: pip install -e ".[pdf]" '
            "(also needs system libs — see README)."
        ) from exc

    return HTML(string=report_to_html(report)).write_pdf()
