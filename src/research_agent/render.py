"""Render a CompanyReport as Markdown. JSON (model_dump) is the canonical form."""

from __future__ import annotations

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
