"""CLI entry point: `research-agent "Company Name"`.

Note: Typer collapses a single-command app so the subcommand name (`lookup`)
is not part of the invocation — see the README for the actual usage.
"""

from __future__ import annotations

import asyncio
import re
import subprocess
import sys
import webbrowser
from pathlib import Path

import typer

from research_agent.agent import run_research
from research_agent.render import report_to_html, report_to_markdown

app = typer.Typer(add_completion=False)

VALID_FORMATS = ("markdown", "json", "html", "pdf")
EXTENSIONS = {"markdown": "md", "json": "json", "html": "html", "pdf": "pdf"}


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
        report = asyncio.run(run_research(company_name))
    except Exception as exc:  # surface agent/schema failures clearly to the CLI user
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
