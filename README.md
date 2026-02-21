# Hermes: AI-Powered Operating System for Disaster Response

## The Problem: The Distribution Void
In the wake of natural and manmade disasters such as blizzards, tsunamis, or wildfires, critical infrastructure is often the first thing to fail. When the internet goes dark, communities are left isolated. While traditional emergency services (911/112) exist, they are frequently overwhelmed or physically unable to reach victims, leaving a massive gap in immediate, life-saving resource distribution.

## The Solution: AI-Orchestrated Resilience
We are developing a decentralized **Operating System for Disaster Response** that transforms a chaotic crisis into a coordinated ecosystem of resilience. By leveraging the only surviving communication channels like **SMS and Voice**, our platform uses **Ethical AI agents** to orchestrate a peer-to-peer support network, autonomously matching urgent requests for medicine, fuel, or shelter with people who have available resources.

## project structure
Monorepo: **FastAPI** backend (`api/`) and **React + Vite** frontend (`ui/`), with type-safe API client generation (Orval).

## Prerequisites

- **Node.js** (for the UI and root scripts)
- **Python 3** (for the API; recommend 3.11+)
- A **Supabase** project (for `SUPABASE_URL` and `SUPABASE_POSTGRES_URL`)

## Setup

### 1. Install dependencies

From the repo root:

```bash
npm install
cd ui && npm install && cd ..
```

### 2. Environment

Create a `.env` file at the **project root** (e.g. `cp .env.example .env`) and set the required variables (get these from your [Supabase](https://supabase.com) project settings):

```bash
# .env (at project root)
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_POSTGRES_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres

# Twilio (required for SMS webhook + outbound send API)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=...

# Workflow bridge base URL (inbound SMS forwards to /sms)
WORKFLOW_WEBHOOK_URL=https://your-workflow-domain.example/twilio/webhooks
```

- **SUPABASE_URL** — Project URL (API URL).
- **SUPABASE_POSTGRES_URL** — Direct Postgres connection string (e.g. from Supabase → Settings → Database → Connection string, “URI” / “Transaction” pooler).
- **TWILIO_ACCOUNT_SID**, **TWILIO_AUTH_TOKEN**, **TWILIO_FROM_NUMBER** — required for SMS webhook verification and outbound delivery.
- **WORKFLOW_WEBHOOK_URL** — workflow base URL; inbound SMS events are forwarded to `${WORKFLOW_WEBHOOK_URL}/sms`.

The API and the migration script (`npm run migrate`) both read from this file. If either variable is missing, the API will fail on startup with a clear error.

### 3. API Python environment

Create a venv and install dependencies:

```bash
cd api
python -m venv venv
# macOS/Linux:
source venv/bin/activate
# Windows:
# .\venv\Scripts\activate

pip install -r requirements.txt
cd ..
```

If you prefer not to activate the venv, use `api/venv/bin/python` and `api/venv/bin/pip` (or `api\venv\Scripts\python.exe` on Windows) when running API commands.

### 4. Generate the API client (frontend)

The UI uses a generated, type-safe client from the OpenAPI spec. After changing the API or cloning the repo, regenerate it:

```bash
npm run api:gen
```

This (1) exports `api/openapi.json` from the FastAPI app and (2) runs Orval in `ui/` to update `ui/src/api/generated/`. If `python` is not on your PATH, run the export step with the API venv:

```bash
cd api && ./venv/bin/python export_openapi.py && cd .. && npm run api:gen --prefix ui
```

### 5. Database migrations

Migrations are raw SQL in `api/migrations/*.sql`. From the repo root (with root `.env` set):

```bash
npm run migrate
```

The script uses `SUPABASE_POSTGRES_URL` from the root `.env`, applies any new `.sql` files in order, and records them in the `_migrations` table.

## Running the project

- **API and UI together** (from repo root):

  ```bash
  npm run dev
  ```

  - UI: http://localhost:5173 (Vite dev server; proxies `/api` to the backend)
  - API: http://localhost:8000

- **API only**: `npm run dev:api` (or `cd api && uvicorn index:app --reload --host 0.0.0.0`)
- **UI only**: `npm run dev:ui` (or `cd ui && npm run dev`)

## Twilio SMS API contracts

### Inbound webhook (Twilio -> API)

- `POST /twilio/webhooks/sms`
- Content type: `application/x-www-form-urlencoded`
- Expected Twilio fields: `From`, `To`, `Body`, `MessageSid`
- Behavior:
  - validates `X-Twilio-Signature` when `TWILIO_AUTH_TOKEN` is set
  - stores message in `text_message` (`source=SMS`, `direction=Inbound`)
  - triggers workflow handoff stub (`api/workflow_bridge.py`)
  - returns TwiML success response

#### Inspect inbound webhook logs

- Run `npm run dev` and watch the API terminal output.
- The webhook logs:
  - request metadata (`method`, `url`)
  - inbound headers and payload body
  - signature validation failures
  - persistence and workflow forwarding outcomes

### Outbound send (App -> Twilio)

- `POST /messages/send`
- Content type: `application/json`
- Request body:

  ```json
  {
    "to": "+15551234567",
    "body": "Fuel assistance requested nearby. Can you help?",
    "context": {
      "case_id": "optional-case-uuid"
    }
  }
  ```

- Response body:
  - `success`, `message_sid`, `status`, `to`, `from_number`, `workflow`
  - `persistence_error` is populated only if SMS sends but DB logging fails

### AI-agent handoff contract

- Inbound webhook normalizes message data and calls `handle_inbound_message(...)` in `api/workflow_bridge.py`.
- This is intentionally a no-op contract placeholder so your AI teammate can plug in classification + broadcast logic without changing public API shape.
- **API in Docker** (uses `.env` at project root for `SUPABASE_URL` and `SUPABASE_POSTGRES_URL`):

  ```bash
  npm run docker:build
  npm run docker:run
  ```

  Then open http://localhost:8000 (e.g. `curl http://localhost:8000/health`).

## Project layout

| Path                    | Description                                                                                                                  |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `api/`                  | FastAPI app. Env is loaded from `api/env.py`; import `SUPABASE_URL` / `SUPABASE_POSTGRES_URL` from `env` there.              |
| `.env`                  | Env vars at project root (not committed). Required: `SUPABASE_URL`, `SUPABASE_POSTGRES_URL`. Used by API and migrate script. |
| `api/migrations/`       | Raw SQL migrations; run with `npm run migrate` (TypeScript runner in `scripts/migrate.ts`).                                  |
| `api/openapi.json`      | OpenAPI spec, generated by `api/export_openapi.py`.                                                                          |
| `ui/`                   | React + Vite app. Tailwind + shadcn/ui.                                                                                      |
| `ui/src/api/generated/` | Orval-generated API client and schemas; do not edit by hand.                                                                 |
| `ui/src/components/ui/` | shadcn components. Use `@/components/ui` for imports.                                                                        |

## Imports

- **API (Python)**

  - Env: `from env import SUPABASE_URL, SUPABASE_POSTGRES_URL`
  - App lives in `api/index.py`; run with `uvicorn index:app` from `api/`.

- **UI (TypeScript)**
  - Path alias: `@/` → `ui/src/` (e.g. `import { Button } from "@/components/ui/button"`).
  - API hooks and types: `@/api/generated/endpoints`, `@/api/generated/schemas`.

For adding new API endpoints and regenerating the client, see [AGENTS.md](./AGENTS.md).
