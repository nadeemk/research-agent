"""Render a CompanyReport as Markdown or HTML. JSON (model_dump) is the canonical form."""

from __future__ import annotations

import html as html_lib

from research_agent.schema import CompanyReport, FundingRound, NewsItem


def _fmt_amount(amount_usd: float | None) -> str:
    if amount_usd is None:
        return "undisclosed"
    if amount_usd >= 1_000_000_000:
        return f"${amount_usd / 1_000_000_000:.2f}B"
    if amount_usd >= 1_000_000:
        return f"${amount_usd / 1_000_000:.1f}M"
    return f"${amount_usd:,.0f}"


def _render_funding_round(r: FundingRound) -> str:
    date_str = r.announced_date.isoformat() if r.announced_date else "date unknown"
    lead = ", ".join(r.lead_investors) or "unknown lead"
    lines = [f"- **{r.round_type}** ({date_str}) — {_fmt_amount(r.amount_usd)}, led by {lead}"]
    if r.other_investors:
        lines.append(f"  - Other investors: {', '.join(r.other_investors)}")
    if r.valuation_usd:
        lines.append(f"  - Valuation: {_fmt_amount(r.valuation_usd)}")
    if r.source_urls:
        lines.append(f"  - Sources: {', '.join(r.source_urls)}")
    return "\n".join(lines)


def _render_news_item(n: NewsItem) -> str:
    date_str = n.published_date.isoformat() if n.published_date else "date unknown"
    return f"- **{n.headline}** ({date_str}) — {n.summary} [source]({n.source_url})"


def report_to_markdown(report: CompanyReport) -> str:
    o = report.overview
    lines: list[str] = []

    lines.append(f"# {report.company_name}")
    lines.append(f"_Generated {report.generated_at.isoformat()}_")
    lines.append("")

    lines.append("## Overview")
    lines.append(o.description)
    lines.append("")
    lines.append(f"- Website: {o.website or 'unknown'}")
    lines.append(f"- Founded: {o.founded_year or 'unknown'}")
    lines.append(f"- Headquarters: {o.headquarters or 'unknown'}")
    lines.append(f"- Industry: {o.industry or 'unknown'}")
    lines.append(f"- Employees (est.): {o.employee_count_estimate or 'unknown'}")
    lines.append("")

    lines.append("## Funding Rounds")
    if report.funding_rounds:
        lines.extend(_render_funding_round(r) for r in report.funding_rounds)
    else:
        lines.append("_No funding rounds found._")
    lines.append("")

    lines.append("## Recent News")
    if report.recent_news:
        lines.extend(_render_news_item(n) for n in report.recent_news)
    else:
        lines.append("_No recent news found._")
    lines.append("")

    lines.append("## Competitors")
    lines.append(", ".join(report.competitors) if report.competitors else "_None found._")
    lines.append("")

    lines.append("## Key People")
    if report.key_people:
        lines.extend(f"- {p.name} — {p.role}" for p in report.key_people)
    else:
        lines.append("_None found._")
    lines.append("")

    if report.confidence_notes:
        lines.append("## Confidence Notes")
        lines.append(report.confidence_notes)
        lines.append("")

    lines.append("## Sources")
    if report.sources:
        lines.extend(f"- [{s.title or s.url}]({s.url})" for s in report.sources)
    else:
        lines.append("_None recorded._")

    return "\n".join(lines)


_HTML_STYLE = """\
<style>
  :root { color-scheme: light; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    max-width: 760px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; line-height: 1.5;
  }
  h1 { font-size: 28px; margin-bottom: 4px; }
  .generated-at { color: #666; font-size: 13px; margin-bottom: 24px; }
  h2 { font-size: 18px; margin-top: 32px; border-bottom: 1px solid #e2e2e2; padding-bottom: 4px; }
  table { width: 100%; border-collapse: collapse; margin-top: 8px; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #eee; font-size: 14px; vertical-align: top; }
  th { color: #666; font-weight: 600; font-size: 12px; text-transform: uppercase; }
  ul { padding-left: 20px; }
  li { margin-bottom: 10px; font-size: 14px; }
  .meta-list { list-style: none; padding: 0; font-size: 14px; }
  .meta-list li { margin-bottom: 4px; }
  .empty { color: #888; font-style: italic; }
  .notes { background: #fff8e6; border: 1px solid #f0dca0; padding: 10px 14px; border-radius: 6px; font-size: 14px; }
  a { color: #2563eb; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .sources { font-size: 12px; color: #555; }
</style>\
"""


def _esc(value: object) -> str:
    return html_lib.escape(str(value)) if value not in (None, "") else ""


def _or_unknown(value: object) -> str:
    return _esc(value) if value not in (None, "") else '<span class="empty">unknown</span>'


def _link(url: str | None, text: str | None = None) -> str:
    if not url:
        return '<span class="empty">unknown</span>'
    safe_url = _esc(url)
    label = _esc(text) if text else safe_url
    return f'<a href="{safe_url}" target="_blank" rel="noopener">{label}</a>'


def _html_funding_row(r: FundingRound) -> str:
    date_str = r.announced_date.isoformat() if r.announced_date else None
    lead = ", ".join(r.lead_investors) or None
    sources = " ".join(_link(u, "source") for u in r.source_urls) or '<span class="empty">—</span>'
    return (
        "<tr>"
        f"<td>{_esc(r.round_type)}</td>"
        f"<td>{_or_unknown(date_str)}</td>"
        f"<td>{_esc(_fmt_amount(r.amount_usd))}</td>"
        f"<td>{_or_unknown(lead)}</td>"
        f"<td>{_esc(_fmt_amount(r.valuation_usd)) if r.valuation_usd else '<span class=\"empty\">—</span>'}</td>"
        f"<td>{sources}</td>"
        "</tr>"
    )


def _html_news_item(n: NewsItem) -> str:
    date_str = n.published_date.isoformat() if n.published_date else "date unknown"
    return (
        f"<li><strong>{_esc(n.headline)}</strong> "
        f'<span class="empty">({_esc(date_str)})</span><br>'
        f"{_esc(n.summary)} {_link(n.source_url, 'source')}</li>"
    )


def report_to_html(report: CompanyReport) -> str:
    """Render a CompanyReport as a standalone HTML document.

    All agent/web-sourced text is HTML-escaped before insertion, since it
    ultimately comes from arbitrary fetched web pages and must not be
    trusted as safe markup.
    """
    o = report.overview
    body: list[str] = []

    body.append(f"<h1>{_esc(report.company_name)}</h1>")
    body.append(f'<p class="generated-at">Generated {_esc(report.generated_at.isoformat())}</p>')

    body.append("<h2>Overview</h2>")
    body.append(f"<p>{_esc(o.description)}</p>")
    body.append('<ul class="meta-list">')
    body.append(f"<li><strong>Website:</strong> {_link(o.website)}</li>")
    body.append(f"<li><strong>Founded:</strong> {_or_unknown(o.founded_year)}</li>")
    body.append(f"<li><strong>Headquarters:</strong> {_or_unknown(o.headquarters)}</li>")
    body.append(f"<li><strong>Industry:</strong> {_or_unknown(o.industry)}</li>")
    body.append(f"<li><strong>Employees (est.):</strong> {_or_unknown(o.employee_count_estimate)}</li>")
    body.append("</ul>")

    body.append("<h2>Funding Rounds</h2>")
    if report.funding_rounds:
        body.append(
            "<table><thead><tr>"
            "<th>Round</th><th>Date</th><th>Amount</th><th>Lead Investor(s)</th>"
            "<th>Valuation</th><th>Sources</th>"
            "</tr></thead><tbody>"
        )
        body.extend(_html_funding_row(r) for r in report.funding_rounds)
        body.append("</tbody></table>")
    else:
        body.append('<p class="empty">No funding rounds found.</p>')

    body.append("<h2>Recent News</h2>")
    if report.recent_news:
        body.append("<ul>")
        body.extend(_html_news_item(n) for n in report.recent_news)
        body.append("</ul>")
    else:
        body.append('<p class="empty">No recent news found.</p>')

    body.append("<h2>Competitors</h2>")
    body.append(
        f"<p>{_esc(', '.join(report.competitors))}</p>"
        if report.competitors
        else '<p class="empty">None found.</p>'
    )

    body.append("<h2>Key People</h2>")
    if report.key_people:
        body.append(
            "<ul>" + "".join(f"<li>{_esc(p.name)} — {_esc(p.role)}</li>" for p in report.key_people) + "</ul>"
        )
    else:
        body.append('<p class="empty">None found.</p>')

    if report.confidence_notes:
        body.append("<h2>Confidence Notes</h2>")
        body.append(f'<p class="notes">{_esc(report.confidence_notes)}</p>')

    body.append("<h2>Sources</h2>")
    if report.sources:
        body.append(
            '<ul class="sources">'
            + "".join(f"<li>{_link(s.url, s.title or s.url)}</li>" for s in report.sources)
            + "</ul>"
        )
    else:
        body.append('<p class="empty">None recorded.</p>')

    body_html = "\n".join(body)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{_esc(report.company_name)} — Research Report</title>\n"
        f"{_HTML_STYLE}\n</head>\n<body>\n{body_html}\n</body>\n</html>\n"
    )
