"""Orchestrator: runs the research agent loop and returns a validated CompanyReport.

Both the CLI and the API call `run_research()` — it is the single entry point
so there is no divergence between the two surfaces.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query, tool

from research_agent.schema import CompanyReport

logger = logging.getLogger(__name__)

# Left unset, the SDK falls back to its own default model, which is not
# necessarily the cheapest — pin explicitly. haiku is cheaper but was
# observed leaking raw tool-call syntax into text fields on this
# multi-step tool-use + large structured-output task; sonnet is the
# reliability/cost tradeoff. Override with RESEARCH_AGENT_MODEL as needed.
MODEL = os.environ.get("RESEARCH_AGENT_MODEL", "sonnet")

SYSTEM_PROMPT = """\
You are a startup research analyst. Given a company name, research it using
web search and produce a single structured report.

Process:
1. Search for the company's official site, "about" info, and industry/founding details.
2. Search specifically for its funding history (rounds, amounts, investors, valuation).
   Try queries like "<company> funding round", "<company> raises Series", \
"<company> valuation".
3. Search for recent news (last ~12 months): product launches, leadership changes, \
partnerships, controversies. Prefer primary sources (company blog, press releases, \
reputable outlets) over aggregators.
4. Note competitors and key people (founders/executives) if findable.
5. For every factual claim, keep track of the source URL you got it from.
6. If you cannot find something, leave the field empty/null rather than guessing —
   do not fabricate numbers, dates, or names. Use `confidence_notes` to flag gaps
   or conflicting information between sources.
7. When you are done gathering evidence, call the `submit_report` tool exactly
   once with the complete report. This is your final action — do not produce a
   text summary instead of calling the tool.

If the company name is ambiguous (e.g. common word, multiple companies with the
same name), do your best to identify the most likely startup/tech company match,
and note the ambiguity in confidence_notes.
"""

MAX_TURNS = 40


def _build_report_tool(collector: dict[str, Any]):
    """Build a fresh submit_report tool bound to this request's collector dict.

    Built per-call (not module-level) so concurrent requests in the same
    process never share state.
    """
    report_schema = CompanyReport.model_json_schema()

    @tool(
        "submit_report",
        "Submit the final, complete structured company research report. "
        "Call this exactly once, as your last action.",
        report_schema,
    )
    async def submit_report(args: dict[str, Any]) -> dict[str, Any]:
        collector["report"] = args
        return {"content": [{"type": "text", "text": "Report received."}]}

    return submit_report


async def run_research(company_name: str) -> CompanyReport:
    """Research `company_name` and return a validated CompanyReport.

    Raises RuntimeError if the agent never called submit_report, and
    pydantic.ValidationError if it submitted a payload that doesn't match
    the schema.
    """
    collector: dict[str, Any] = {}
    submit_report = _build_report_tool(collector)
    report_server = create_sdk_mcp_server(
        name="report", version="1.0.0", tools=[submit_report]
    )

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"report": report_server},
        allowed_tools=["WebSearch", "WebFetch", "mcp__report__submit_report"],
        permission_mode="bypassPermissions",
        max_turns=MAX_TURNS,
        model=MODEL,
    )

    prompt = (
        f'Research the company "{company_name}" and submit a complete report '
        "using the submit_report tool."
    )

    async for message in query(prompt=prompt, options=options):
        logger.debug("agent message: %r", message)

    if "report" not in collector:
        raise RuntimeError(
            f"Agent finished without calling submit_report for {company_name!r}"
        )

    return CompanyReport.model_validate(collector["report"])
