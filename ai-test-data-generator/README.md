# AI Test Data Generator

Turn a **user story**, an **API specification**, and **validation rules** into
comprehensive, ready-to-use test data — powered by the Anthropic Claude API
with a deterministic rule-based fallback.

For any endpoint you describe, it generates:

1. **Positive test data** — records satisfying every constraint.
2. **Negative test data** — records each violating exactly one rule, with the
   violated field and expected error.
3. **Boundary values** — at/just-below/just-above every numeric and length edge.
4. **Equivalence partitions** — valid and invalid classes per field, with a
   representative value for each.
5. **API request payloads** — concrete, ready-to-send requests (method, path,
   headers, body, expected status).
6. **Database seed data** — rows plus generated `INSERT` statements.

…and **export formats** so the data drops straight into whichever stack you use —
each a complete, runnable file built from the payloads:

- **Robot Framework** suite (`RequestsLibrary`, data-driven with status assertions),
- **pytest** module (`requests` + `@pytest.mark.parametrize`),
- **Playwright** spec (`@playwright/test`, `request.*` per payload), and
- **plain Python** script (`requests`, no test framework — exits non-zero on failure).

---

## Tech stack

Python 3.11 · FastAPI · Pydantic · Anthropic Claude (`claude-opus-4-8`) ·
**Robot Framework** (project test suite + export target) · **Playwright**
(export target) · Docker.

---

## Architecture

The design follows **SOLID**: every layer depends on abstractions
(`TestDataGenerator`, `ResultStore`), the orchestration `GenerationService` has a
single responsibility, and new generators/stores can be added without modifying
existing code.

```
                    ┌──────────────────────────────────────────┐
  HTTP request ───▶ │ api/routes.py   (FastAPI endpoints)        │
                    │ api/dependencies.py (composition root, DI) │
                    └───────────────┬──────────────────────────┘
                                    ▼
                    ┌──────────────────────────────────────────┐
                    │ services/generation_service.py            │
                    │   validate → generate → store             │
                    └───────┬───────────────────────┬──────────┘
                            ▼                        ▼
        ┌───────────────────────────────┐   ┌──────────────────────┐
        │ services/generator_agent.py    │   │ services/storage.py  │
        │  TestDataGenerator (interface) │   │  ResultStore (iface) │
        │  ├─ ClaudeTestDataGenerator    │   │  └─ InMemoryStore    │
        │  └─ RuleBasedTestDataGenerator │   └──────────────────────┘
        └──────┬─────────────────────────┘
               ▼ (offline engine)
        ┌───────────────────────────────┐
        │ services/rule_based.py         │  deterministic 6-artifact engine
        │ utils/values.py · utils/sql.py │  value derivation · INSERT builder
        └───────────────────────────────┘
```

```
app/
  api/         FastAPI routes + dependency injection
  core/        domain exceptions + handlers
  models/      Pydantic input + output models (single source of truth)
  services/    generator agents (Claude + rule-based), orchestration, storage
  utils/       deterministic value generation + SQL seed builder
  config.py    env-driven settings
  main.py      app factory
sample_data/   sample generation request
tests/         offline Robot Framework suites + TestClient keyword library
```

### Graceful degradation

Without `ANTHROPIC_API_KEY`, the service uses the deterministic **rule-based
engine** (`generated_by_ai: false`) — so it is always functional, reproducible,
and testable offline. Set the key to switch to **Claude** for story-aware,
domain-realistic data (`generated_by_ai: true`).

> The Claude path intentionally does **not** use JSON-schema structured outputs:
> the generated payloads (`data`, `body`, seed `rows`) are free-form objects, and
> structured outputs require `additionalProperties: false` on every object. The
> agent constrains shape via a strict prompt and validates the parsed JSON against
> the same Pydantic models; seed `INSERT`s are always rebuilt server-side so they
> are syntactically correct regardless of model output.

---

## Quick start (local)

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Unix:     source .venv/bin/activate

pip install -r requirements-dev.txt

# Optional: enable live Claude generation
cp .env.example .env        # then set ANTHROPIC_API_KEY

uvicorn app.main:app --reload
```

Open <http://localhost:8000/docs> for interactive API docs.

> Without `ANTHROPIC_API_KEY`, generation is produced by the rule-based engine
> (`generated_by_ai: false`). Set the key to use Claude.

---

## API

Base path: `/api`

| Method | Path                  | Description                                          |
| ------ | --------------------- | ---------------------------------------------------- |
| POST   | `/generate`           | Generate all six artifact categories. Returns `generation_id`. |
| GET    | `/result/{id}`        | Fetch a previously generated result.                 |
| GET    | `/health`             | Liveness + whether a live AI provider is active.     |

### Example

```bash
curl -s -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d @sample_data/sample_request.json
```

### Request shape

```jsonc
{
  "user_story": "As a new user, I want to register ...",
  "api_spec": {
    "method": "POST",
    "path": "/api/v1/users",
    "success_status": 201,
    "error_status": 400,
    "headers": {
      "Content-Type": "application/json",
      "X-API-KEY": "%{MY_API_KEY}"
    },
    "fields": [
      { "name": "email", "type": "email", "required": true },
      { "name": "username", "type": "string", "min_length": 3, "max_length": 20 },
      { "name": "age", "type": "integer", "minimum": 18, "maximum": 120 },
      { "name": "role", "type": "enum", "required": false, "enum": ["user", "admin"] }
    ]
  },
  "validation_rules": [
    { "rule": "Password must contain a digit and a letter.", "fields": ["password"] }
  ],
  "table_name": "users",
  "count": 3
}
```

Supported field `type` values: `string`, `integer`, `number`, `boolean`,
`email`, `date`, `datetime`, `uuid`, `enum`. Constraints: `required`,
`minimum`/`maximum` (numeric), `min_length`/`max_length` (string), `enum`,
`pattern`, `example`.

**`api_spec.headers`** (optional) are applied to every generated payload and
emitted into all four exports — use them for gateway auth. **Don't hard-code
secrets**: reference an environment variable with `%{ENV_VAR}`. The Robot export
emits headers via `Create Dictionary`, so Robot resolves `%{ENV_VAR}` (and
`${VAR}`) at run time — set the variable in your shell or `-v VAR:value`, and the
real key never lives in the generated file. (The pytest/Playwright/Python exports
embed the header value as written, so use literal values or edit them there.)

### Response shape

`generated` contains `positive`, `negative`, `boundary_values`,
`equivalence_partitions`, `api_payloads`, `seed_data`, and `exports`. The
`exports` object carries four ready-to-run files:

| Field                      | Save as                     | Run with                                   |
| -------------------------- | --------------------------- | ------------------------------------------ |
| `exports.robot_framework`  | `generated_api_tests.robot` | `robot` (needs `robotframework-requests`)  |
| `exports.pytest`           | `generated_api_test.py`     | `pytest` (needs `pytest requests`)         |
| `exports.playwright`       | `generated_api.spec.ts`     | `npx playwright test`                      |
| `exports.python`           | `generated_api_checks.py`   | `python` (needs `requests`)                |

Each targets `${BASE_URL}` / `BASE_URL` (default `http://localhost:8000`) so you
point it at your own API under test.

---

## Configuration

All settings are environment variables (see `.env.example`):

| Variable                 | Default            | Purpose                                   |
| ------------------------ | ------------------ | ----------------------------------------- |
| `ANTHROPIC_API_KEY`      | _(empty)_          | Enables live Claude generation.           |
| `CLAUDE_MODEL`           | `claude-opus-4-8`  | Model id.                                 |
| `CLAUDE_MAX_TOKENS`      | `8000`             | Max output tokens.                        |
| `CLAUDE_EFFORT`          | `high`             | Reasoning effort (`low`…`max`).           |
| `CLAUDE_TIMEOUT_SECONDS` | `120`              | Anthropic client timeout.                 |
| `DEFAULT_RECORD_COUNT`   | `3`                | Positive records when `count` is omitted. |
| `MAX_RECORD_COUNT`       | `50`               | Hard cap on requested `count`.            |

The Claude agent uses **adaptive thinking** and the **effort** parameter.

---

## Tests

The project's own test suite is **Robot Framework** (no pytest). It runs fully
offline against the app via Starlette's `TestClient` — no live server, no API
key (it exercises the rule-based engine).

```bash
pip install -r requirements-dev.txt
robot --outputdir results tests/      # run from the project root so `app` imports
```

`tests/libraries/GeneratorClient.py` exposes the API as Robot keywords; the
suites cover health, generation of all six artifact categories, the export
formats, result fetch/round-trip, validation errors, and 404s.

> **Run from the project root** so `from app.main import create_app` resolves.
> If your editor's Robot Framework Language Server reports "import errors",
> point it at this project's `.venv` interpreter and add the project root to its
> Python path — those are static-analysis warnings, not runtime failures.

---

## Run with Docker

```bash
docker compose up --build
# or
docker build -t ai-test-data-generator .
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-... ai-test-data-generator
```

---

## How it works

1. `POST /generate` → `GenerationService.generate` validates the request and
   clamps `count` to `MAX_RECORD_COUNT`.
2. The configured `TestDataGenerator` produces all six artifact categories:
   - **Claude** (`ClaudeTestDataGenerator`) when an API key is set — story-aware,
     domain-realistic values.
   - **Rule-based** (`RuleBasedTestDataGenerator`) otherwise — deterministic data
     derived from the field constraints (`utils/values.py`), with `INSERT`s built
     by `utils/sql.py`.
3. The service builds the **Robot Framework**, **pytest**, **Playwright**, and
   **plain-Python** exports deterministically from the API payloads (so every
   engine emits correct, runnable files), then stores the result and returns it
   with a `generation_id`; fetch it again via `GET /result/{id}`.
