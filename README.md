# research-agent

An agent that researches a startup (overview, funding rounds, recent news,
competitors, key people) and returns a structured report. Callable via CLI
or a deployable HTTP API.

## Architecture

- `src/research_agent/schema.py` — the `CompanyReport` Pydantic model. This
  is the contract: the agent must submit a payload matching this schema.
- `src/research_agent/agent.py` — the orchestrator. Runs a Claude Agent SDK
  loop with the built-in `WebSearch`/`WebFetch` tools plus one custom tool,
  `submit_report`, which the agent calls exactly once at the end with the
  full report. `run_research(company_name)` is the single entry point used
  by both the CLI and the API.
- `src/research_agent/render.py` — renders a `CompanyReport` to Markdown or
  HTML (all agent/web-sourced text is HTML-escaped). JSON
  (`report.model_dump_json()`) is the canonical form.
- `src/research_agent/pdf.py` — renders a `CompanyReport` to PDF bytes by
  running the HTML template through WeasyPrint. Optional dependency, see below.
- `src/research_agent/cli.py` — Typer CLI: `research-agent "Company"`.
- `src/research_agent/api.py` — FastAPI app: `POST /research`.
- `eval/` — a promptfoo eval suite (see below).

## Local setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then fill in ANTHROPIC_API_KEY
export $(grep -v '^#' .env | xargs)   # or use direnv/etc.
```

Run the tests:

```bash
pytest
```

## Run it

CLI:

```bash
research-agent "Anthropic"                                  # markdown to stdout
research-agent "Anthropic" --format json --out anthropic.json
research-agent "Anthropic" --format html --open              # writes anthropic.html and opens it
research-agent "Anthropic" --format pdf --open                # writes anthropic.pdf and opens it
```

`--format` is one of `markdown` (default), `json`, `html`, or `pdf`. `--open`
opens the resulting file in your default viewer after writing it; if you use
`--open` (or `--format pdf`) without `--out`, a filename is auto-generated
from the company name in the current directory.

PDF output needs the optional `pdf` extra, which pulls in
[WeasyPrint](https://weasyprint.org/):

```bash
pip install -e ".[pdf]"
```

WeasyPrint also needs a few native libraries (Pango, Cairo, GDK-Pixbuf) —
on macOS: `brew install pango`; on Debian/Ubuntu (also what to add to the
Dockerfile if you want PDF support in the deployed API):
`apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev`.

### Calling a deployed instance from the CLI

By default the CLI runs the agent locally (needs `ANTHROPIC_API_KEY`). Set
`RESEARCH_AGENT_API_URL` (or pass `--api-url`) to instead call a deployed
instance's `/research` endpoint over HTTP and render the result locally —
no Anthropic key needed on the calling machine, just the deployment's
`RESEARCH_AGENT_API_KEY`:

```bash
export RESEARCH_AGENT_API_URL=https://research-agent-xxxxx.us-central1.run.app
export RESEARCH_AGENT_API_KEY=...   # the deployment's shared secret
research-agent "Anthropic" --format html --open
```
If these aren't installed, `--format pdf` fails with a clear error rather
than a stack trace.

API (local):

```bash
uvicorn research_agent.api:app --reload --port 8080
curl -X POST localhost:8080/research \
  -H 'Content-Type: application/json' \
  -d '{"company_name": "Anthropic"}'
```

If `RESEARCH_AGENT_API_KEY` is set, add `-H "X-API-Key: <value>"` to the curl call.

## Evals

Uses [promptfoo](https://www.promptfoo.dev/) — a `npm`/`npx` tool, no separate
install needed:

```bash
npx promptfoo@latest eval -c eval/promptfooconfig.yaml
npx promptfoo@latest view   # opens a local dashboard of results
```

`eval/promptfooconfig.yaml` is the starting golden set: a few companies with
hand-verified stable facts (founding year) checked deterministically, one
LLM-as-judge ("llm-rubric") check for overall report quality, and one check
that a nonsense company name doesn't produce a hallucinated report. Re-run
this after any change to the system prompt, tools, or model — a score drop
is a regression. Grow the golden set as you find real failure cases.

## Deploying

Live deployment: GCP project `research-agent-nk`, Cloud Run service
`research-agent` in `us-central1`. **Deploys automatically on every push to
`main`** via [.github/workflows/deploy.yml](.github/workflows/deploy.yml):
tests run first, then Cloud Build builds the image and Cloud Run is updated.
Auth from GitHub Actions to GCP uses Workload Identity Federation (no
service account key stored anywhere) — the workflow can impersonate the
`github-deployer` service account only when running as this exact repo
(`nadeemk/research-agent`).

### GCP Cloud Run (manual / one-time setup)

```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/<PROJECT_ID>/research-agent/research-agent
gcloud run deploy research-agent \
  --image us-central1-docker.pkg.dev/<PROJECT_ID>/research-agent/research-agent \
  --region us-central1 \
  --set-secrets ANTHROPIC_API_KEY=research-agent-anthropic-key:latest,RESEARCH_AGENT_API_KEY=research-agent-api-key:latest \
  --allow-unauthenticated
```

(Create the two secrets in Secret Manager first: `gcloud secrets create ...`,
and grant the Cloud Run service account `roles/secretmanager.secretAccessor`.)
Cloud Run scales to zero, so idle cost is ~$0 — good fit for low, bursty
personal usage. This manual path is what CI now runs automatically; use it
directly only for one-off testing or if you're setting up a second environment.

### AWS (Fargate/App Runner equivalent)

- Push the image to ECR: `aws ecr ...` + `docker push`.
- Deploy via App Runner (simplest, closest analog to Cloud Run) or Fargate
  behind an ALB if you need more control.
- Store `ANTHROPIC_API_KEY` / `RESEARCH_AGENT_API_KEY` in AWS Secrets Manager
  and reference them in the task definition's `secrets` block — do not put
  them in plain env vars in the task definition.

### Testing a deployment end-to-end

1. Local: `docker build -t research-agent . && docker run -p 8080:8080 --env-file .env research-agent`, then curl `/health` and `/research`.
2. Staging: deploy to a separate service name (e.g. `research-agent-staging`), point `eval/promptfooconfig.yaml`'s provider at the HTTP endpoint instead of the local Python function (swap `providers:` to an `http` provider pointing at the staging URL), and run the eval suite against it.
3. Prod: deploy, then smoke-test with 2-3 real company lookups via the CLI (pointed at the prod URL) before considering it live.

## Notes / things to revisit

- Fine-tuning is deliberately out of scope for v1 — this is a retrieval +
  tool-use task, not a knowledge-memorization one. Revisit only as a
  cost/latency optimization once you have real traffic volume (distill a
  cheaper model on (input, report) pairs from this agent).
- `WebSearch`/`WebFetch` are Claude's built-in tools (bundled via the Claude
  Agent SDK's Claude Code CLI) — no separate search API key needed. If you
  later want more structured/reliable funding data, swap in a paid source
  (e.g. Crunchbase API) as an additional custom tool in `agent.py`.
