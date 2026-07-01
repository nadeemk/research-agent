"""promptfoo custom Python provider: runs the real agent against a company name.

promptfoo calls call_api(prompt, options, context) and expects a dict with
an "output" key. `prompt` here is just the rendered company_name (see the
`prompts:` template in promptfooconfig.yaml).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from research_agent.agent import run_research  # noqa: E402


def call_api(prompt, options, context):
    company_name = context["vars"]["company_name"]
    report = asyncio.run(run_research(company_name))
    return {"output": report.model_dump_json()}
