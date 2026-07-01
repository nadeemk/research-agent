"""FastAPI wrapper: POST /research {"company_name": "..."} -> CompanyReport.

If RESEARCH_AGENT_API_KEY is set in the environment, requests must include a
matching `X-API-Key` header. Since this can be deployed to a public Cloud Run
/ Fargate URL, set this before deploying — otherwise anyone with the URL can
burn your Anthropic quota. Left unset, auth is skipped (fine for local dev).
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from research_agent.agent import run_research
from research_agent.schema import CompanyReport

logger = logging.getLogger(__name__)

app = FastAPI(title="Startup Research Agent", version="0.1.0")

API_KEY = os.environ.get("RESEARCH_AGENT_API_KEY")

if not API_KEY:
    logger.warning(
        "RESEARCH_AGENT_API_KEY is not set — the /research endpoint is unauthenticated. "
        "Set this env var before deploying publicly."
    )


class ResearchRequest(BaseModel):
    company_name: str


def _check_api_key(x_api_key: str | None) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header.")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/research", response_model=CompanyReport)
async def research(
    req: ResearchRequest, x_api_key: str | None = Header(default=None)
) -> CompanyReport:
    _check_api_key(x_api_key)
    try:
        return await run_research(req.company_name)
    except Exception as exc:
        logger.exception("research failed for %r", req.company_name)
        raise HTTPException(status_code=502, detail=f"Research failed: {exc}") from exc
