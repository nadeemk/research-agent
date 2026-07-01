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
- `src/research_agent/render.py` — renders a `CompanyReport` to Markdown.
  JSON (`report.model_dump_json()`) is the canonical form.
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
research-agent "Anthropic"
research-agent "Anthropic" --format json --out anthropic.json
```

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

### GCP Cloud Run

```bash
gcloud builds submit --tag gcr.io/<PROJECT_ID>/research-agent
gcloud run deploy research-agent \
  --image gcr.io/<PROJECT_ID>/research-agent \
  --region us-central1 \
  --set-secrets ANTHROPIC_API_KEY=research-agent-anthropic-key:latest,RESEARCH_AGENT_API_KEY=research-agent-api-key:latest \
  --allow-unauthenticated
```

(Create the two secrets in Secret Manager first: `gcloud secrets create ...`.)
Cloud Run scales to zero, so idle cost is ~$0 — good fit for low, bursty
personal usage.

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
