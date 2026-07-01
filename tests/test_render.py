from research_agent.render import report_to_html
from research_agent.schema import CompanyReport

FULL_PAYLOAD = {
    "company_name": "Acme Inc",
    "overview": {
        "website": "https://acme.example",
        "founded_year": 2015,
        "headquarters": "Springfield",
        "industry": "Industrial equipment",
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


def test_html_contains_expected_content():
    report = CompanyReport.model_validate(FULL_PAYLOAD)
    out = report_to_html(report)
    assert out.startswith("<!DOCTYPE html>")
    assert "Acme Inc" in out
    assert "Seed" in out
    assert "Globex" in out
    assert 'href="https://acme.example"' in out


def test_html_escapes_untrusted_agent_sourced_text():
    """Web-sourced text (headlines, descriptions, names) must never be
    injected into the HTML unescaped — the agent fetches arbitrary pages,
    so this is the difference between a report and a stored-XSS vector."""
    payload = {
        "company_name": "Acme Inc",
        "overview": {"description": "<script>alert(1)</script>"},
        "recent_news": [
            {
                "headline": '"><img src=x onerror=alert(2)>',
                "summary": "<b>bold</b> claim",
                "source_url": "https://example.com/article",
            }
        ],
        "key_people": [{"name": "<script>evil()</script>", "role": "CEO"}],
    }
    report = CompanyReport.model_validate(payload)
    out = report_to_html(report)

    assert "<script>" not in out
    assert "<img" not in out
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out
    assert "&lt;script&gt;evil()&lt;/script&gt;" in out
    assert "&lt;img src=x onerror=alert(2)&gt;" in out
