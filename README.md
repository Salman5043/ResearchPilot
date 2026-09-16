# AI Research Assistant

A LangGraph-powered, evidence-grounded research assistant that decomposes a topic, searches the web, builds an evidence map, writes a cited report, fact-checks the draft, and performs one controlled revision when needed.

## Architecture

```text
User Topic
    ↓
Planner
    ↓
Web Research + URL Deduplication
    ↓
Evidence Map
    ↓
Cited Draft Report
    ↓
Fact-Checking Critic
    ↓
  ┌───────────────┐
  │ Major issues? │
  └───────┬───────┘
      YES │       │ NO
          ↓       └──────→ Finish
      Revision
          ↓
       Critic
          ↓
        Finish
```

## Stack

- Python 3.12
- FastAPI
- LangGraph / LangChain
- Groq
- Tavily
- Docker
- GitHub Actions
- Render Free Web Service

## Local setup

```powershell
uv sync
Copy-Item .env.example .env
```

Add your keys to `.env`:

```env
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
```

Run:

```powershell
uv run uvicorn app:app --reload
```

Open `http://127.0.0.1:8000/`.

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `GROQ_API_KEY` | Groq authentication | required |
| `TAVILY_API_KEY` | Tavily authentication | required |
| `GROQ_MODEL` | Groq model | `openai/gpt-oss-safeguard-20b` |
| `GROQ_MAX_TOKENS` | Default LLM output budget | `1400` |
| `GROQ_MIN_REQUEST_INTERVAL` | Minimum gap between local LLM calls | `0.5` |
| `TAVILY_SEARCH_DEPTH` | Tavily search depth | `basic` |
| `MAX_REVISIONS` | Maximum critic-driven revisions | `1` |
| `APP_ENV` | Environment label | `development` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `*` |
| `AUTO_OPEN_BROWSER` | Local browser auto-open | `false` |

## API

### Health

`GET /api/health`

### Standard research

`POST /api/research`

```json
{
  "topic": "The impact of AI agents on enterprise software development"
}
```

### Streaming research

`POST /api/research/stream`

Returns Server-Sent Events for progressive UI updates.

## Citations and evidence

Research sources receive stable IDs such as `[S1]` and `[S2]`. The evidence map, report and review use these IDs to keep claims traceable to retrieved sources. Important decisions should still be independently verified because web search and LLM synthesis are not guaranteed to be error-free.

## Free deployment with Render

This repository includes `Dockerfile` and `render.yaml` for a Render free web service.

1. Push the repository to GitHub.
2. In Render, create a **New Blueprint** and select the GitHub repository.
3. Render reads `render.yaml` and creates the web service.
4. Set `GROQ_API_KEY` and `TAVILY_API_KEY` as secret environment variables in Render.
5. Deploy.
6. Verify `https://YOUR-SERVICE.onrender.com/api/health`.

The frontend uses `window.location.origin`, so the same build works locally and on the deployed Render URL.

### Free-tier note

Free hosting may sleep after inactivity and can have cold-start latency. This deployment is best treated as a portfolio/demo environment rather than a latency-sensitive production service.

## CI/CD

GitHub Actions runs on pull requests and pushes to `main`:

```text
Checkout
  ↓
uv sync
  ↓
Python compile check
  ↓
Unit tests
  ↓
Docker build
```

Connect the repository to Render and enable automatic deploys from `main` for continuous deployment.

## Security

Never commit `.env`, API keys, `.venv`, `__pycache__`, or compiled Python files. Use `.env.example` for configuration templates and store production secrets in Render environment variables.

## Project structure

```text
research_assistant/
├── .github/workflows/ci.yml
├── api/
│   └── routes.py
├── graph/
│   ├── graph_builder.py
│   ├── nodes.py
│   └── state.py
├── static/
│   └── index.html
├── tests/
│   └── test_app.py
├── utils/
│   ├── llm.py
│   └── search_tool.py
├── .env.example
├── .gitignore
├── Dockerfile
├── render.yaml
├── app.py
├── pyproject.toml
└── uv.lock
```
