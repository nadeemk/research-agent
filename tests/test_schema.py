import pytest
from pydantic import ValidationError

from research_agent.render import report_to_markdown
from research_agent.schema import CompanyReport

MINIMAL_VALID = {
    "company_name": "Acme Inc",
    "overview": {"description": "A test company that makes anvils."},
}


def test_minimal_report_validates():
    report = CompanyReport.model_validate(MINIMAL_VALID)
    assert report.company_name == "Acme Inc"
    assert report.funding_rounds == []
    assert report.sources == []


def test_missing_required_overview_description_rejected():
    payload = {"company_name": "Acme Inc", "overview": {}}
    with pytest.raises(ValidationError):
        CompanyReport.model_validate(payload)


def test_full_report_validates():
    payload = {
        "company_name": "Acme Inc",
        "overview": {
            "legal_name": "Acme Incorporated",
            "website": "https://acme.example",
            "founded_year": 2015,
            "headquarters": "Springfield",
            "industry": "Industrial equipment",
            "employee_count_estimate": "50-100",
            "description": "A test company that makes anvils.",
        },
        "funding_rounds": [
            {
                "round_type": "Seed",
                "announced_date": "2016-01-15",
                "amount_usd": 2_000_000,
                "lead_investors": ["Wile E. Ventures"],
                "source_urls": ["https://example.com/article"],
            }
        ],
        "recent_news": [
            {
                "headline": "Acme raises seed round",
                "published_date": "2016-01-15",
                "summary": "Acme announced a $2M seed round.",
                "source_url": "https://example.com/article",
            }
        ],
        "competitors": ["Globex"],
        "key_people": [{"name": "Wile E. Coyote", "role": "CEO"}],
        "sources": [{"url": "https://example.com/article", "title": "Acme raises seed"}],
    }
    report = CompanyReport.model_validate(payload)
    assert report.funding_rounds[0].amount_usd == 2_000_000

    md = report_to_markdown(report)
    assert "Acme Inc" in md
    assert "Seed" in md
    assert "Globex" in md
