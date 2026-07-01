"""CLI entry point: `research-agent lookup "Company Name"`."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer

from research_agent.agent import run_research
from research_agent.render import report_to_markdown

app = typer.Typer(add_completion=False)


@app.command()
def lookup(
    company_name: str = typer.Argument(..., help="Name of the company to research."),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown or json."),
    out: Path | None = typer.Option(None, "--out", "-o", help="Write output to this file instead of stdout."),
) -> None:
    """Research a company and print (or save) the report."""
    if fmt not in ("markdown", "json"):
        typer.secho(f"Unknown format: {fmt!r} (use 'markdown' or 'json')", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    typer.secho(f"Researching {company_name}...", fg=typer.colors.CYAN, err=True)
    try:
        report = asyncio.run(run_research(company_name))
    except Exception as exc:  # surface agent/schema failures clearly to the CLI user
        typer.secho(f"Research failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    output = (
        report.model_dump_json(indent=2) if fmt == "json" else report_to_markdown(report)
    )

    if out:
        out.write_text(output)
        typer.secho(f"Wrote report to {out}", fg=typer.colors.GREEN, err=True)
    else:
        sys.stdout.write(output + "\n")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
