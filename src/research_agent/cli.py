"""CLI entry point: `research-agent "Company Name"`.

Note: Typer collapses a single-command app so the subcommand name (`lookup`)
is not part of the invocation — see the README for the actual usage.

By default this runs the agent locally (needs ANTHROPIC_API_KEY). If
RESEARCH_AGENT_API_URL is set (or --api-url is passed), it instead calls a
deployed instance's /research endpoint over HTTP and renders the result
locally — so the CLI can act as a thin client against a Cloud Run/Fargate
deployment without needing an Anthropic key on the calling machine.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

import typer

from research_agent.agent import run_research
from research_agent.render import report_to_html, report_to_markdown
from research_agent.schema import CompanyReport

app = typer.Typer(add_completion=False)

VALID_FORMATS = ("markdown", "json", "html", "pdf")
EXTENSIONS = {"markdown": "md", "json": "json", "html": "html", "pdf": "pdf"}
REMOTE_TIMEOUT_SECONDS = 280


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "report"


def _open_file(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    elif sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", str(path)], check=False)
    else:
        webbrowser.open(path.resolve().as_uri())


def _fetch_remote(api_url: str, company_name: str) -> CompanyReport:
    """POST to a deployed instance's /research endpoint and return the parsed report."""
    url = api_url.rstrip("/") + "/research"
    body = json.dumps({"company_name": company_name}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("RESEARCH_AGENT_API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key

    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=REMOTE_TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Remote request failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc

    return CompanyReport.model_validate(payload)


@app.command()
def lookup(
    company_name: str = typer.Argument(..., help="Name of the company to research."),
    fmt: str = typer.Option(
        "markdown", "--format", "-f", help=f"Output format: {', '.join(VALID_FORMATS)}."
    ),
    out: Path | None = typer.Option(
        None, "--out", "-o", help="Write output to this file instead of stdout."
    ),
    open_after: bool = typer.Option(
        False,
        "--open",
        help="Open the output file after writing (auto-names the file if --out wasn't given).",
    ),
    api_url: str | None = typer.Option(
        None,
        "--api-url",
        envvar="RESEARCH_AGENT_API_URL",
        help=(
            "Call a deployed instance's /research endpoint instead of running the agent "
            "locally. Defaults to $RESEARCH_AGENT_API_URL if set. Uses $RESEARCH_AGENT_API_KEY "
            "as the X-API-Key header if set."
        ),
    ),
) -> None:
    """Research a company and print (or save) the report."""
    if fmt not in VALID_FORMATS:
        typer.secho(
            f"Unknown format: {fmt!r} (use one of {', '.join(VALID_FORMATS)})",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)

    typer.secho(f"Researching {company_name}...", fg=typer.colors.CYAN, err=True)
    try:
        if api_url:
            typer.secho(f"(via {api_url})", fg=typer.colors.CYAN, err=True)
            report = _fetch_remote(api_url, company_name)
        else:
            report = asyncio.run(run_research(company_name))
    except Exception as exc:  # surface agent/schema/network failures clearly to the CLI user
        typer.secho(f"Research failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    content: str | bytes
    if fmt == "pdf":
        from research_agent.pdf import report_to_pdf  # lazy: optional dependency

        try:
            content = report_to_pdf(report)
        except RuntimeError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc
    elif fmt == "html":
        content = report_to_html(report)
    elif fmt == "json":
        content = report.model_dump_json(indent=2)
    else:
        content = report_to_markdown(report)

    # PDF is binary and --open needs a real file, so auto-name one if the
    # user didn't give us a path with --out.
    if out is None and (fmt == "pdf" or open_after):
        out = Path(f"{_slugify(company_name)}.{EXTENSIONS[fmt]}")

    if out:
        if isinstance(content, bytes):
            out.write_bytes(content)
        else:
            out.write_text(content)
        typer.secho(f"Wrote report to {out}", fg=typer.colors.GREEN, err=True)
        if open_after:
            _open_file(out)
    else:
        sys.stdout.write(content + "\n")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
