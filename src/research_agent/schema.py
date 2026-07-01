"""Structured output schema for a company research report.

This is the contract between the agent and everything downstream (renderer,
API response, eval assertions). The agent submits a payload matching
CompanyReport via the `submit_report` tool; anything that doesn't validate
is rejected and the agent must retry.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import BaseModel, Field


class Source(BaseModel):
    url: str
    title: str | None = None


class FundingRound(BaseModel):
    round_type: str = Field(..., description='e.g. "Seed", "Series A", "Series B"')
    announced_date: date | None = None
    amount_usd: float | None = Field(
        None, description="Total raised in this round, in USD. Null if undisclosed."
    )
    lead_investors: list[str] = Field(default_factory=list)
    other_investors: list[str] = Field(default_factory=list)
    valuation_usd: float | None = None
    source_urls: list[str] = Field(default_factory=list)


class NewsItem(BaseModel):
    headline: str
    published_date: date | None = None
    summary: str = Field(..., description="1-3 sentence summary of the article.")
    source_url: str


class Person(BaseModel):
    name: str
    role: str


class CompanyOverview(BaseModel):
    legal_name: str | None = None
    website: str | None = None
    founded_year: int | None = None
    headquarters: str | None = None
    industry: str | None = None
    employee_count_estimate: str | None = Field(
        None, description='Free-text estimate, e.g. "50-100" if no exact figure found.'
    )
    description: str = Field(..., description="2-4 sentence description of what the company does.")


class CompanyReport(BaseModel):
    company_name: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    overview: CompanyOverview
    funding_rounds: list[FundingRound] = Field(default_factory=list)
    recent_news: list[NewsItem] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)
    key_people: list[Person] = Field(default_factory=list)
    confidence_notes: str | None = Field(
        None,
        description=(
            "Caveats about data quality/gaps, e.g. 'no funding data found, "
            "company may be bootstrapped' or 'conflicting valuation figures found'."
        ),
    )
    sources: list[Source] = Field(
        default_factory=list, description="All distinct sources consulted, deduplicated."
    )
