# Telegram AI Chat V2

A production-ready **AI Chat application using Telegram as the UI** with a
FastAPI backend, persistent conversations, multiple AI providers, automatic
fallback, and context preservation across provider switches.

## Core Principle

```
DATABASE = SOURCE OF TRUTH
AI PROVIDER = EXECUTION BACKEND
```

The AI provider never owns the conversation. Conversation history lives in the
database. If a provider fails, the next provider receives the **exact same
immutable context snapshot**. Changing providers never loses conversation
context.

## Architecture

```
                    TELEGRAM
                       |
                       v
                 FASTAPI WEBHOOK
                       |
                       v
                  CHAT SERVICE
                       |
                       v
                    DATABASE
                       |
             +---------+---------+
             |                   |
             v                   v
       CONVERSATION          MESSAGES
         SUMMARY
             |
             v
       CONTEXT MANAGER
             |
             v
     IMMUTABLE CONTEXT
        SNAPSHOT
             |
             v
          AI ROUTER
             |
       +-----+-----+
       |     |     |
       v     v     v
       A     B     C
       |     |     |
       +-----+-----+
             |
             v
       FINAL RESPONSE
             |
             v
          DATABASE
             |
             v
          TELEGRAM
```

The flow per user request:

1. Telegram message arrives at `POST /telegram/webhook`.
2. Rate limiter checks the user (per-user sliding window).
3. Conversation lock serializes messages in the same conversation.
4. User message is persisted immediately (`PENDING`).
5. Context snapshot is built from the database (summary + memory + recent
   messages + current message), token-aware.
6. AI Router selects providers in priority order, with retries and fallback.
7. Each provider attempt is tracked (`provider_attempts`), with `request_id`
   and `attempt_id`.
8. Final assistant response is persisted once (`COMPLETED`).
9. Response is chunked and sent back to Telegram.

## Features

- Telegram bot + FastAPI webhook
- Persistent conversations (multiple per user)
- Persistent context / summary / important memory
- Multiple AI providers (Kimi, Qwen, Gemini, OpenCode) via a reusable
  OpenAI-compatible adapter
- Automatic fallback with **context preservation**
- Ambiguous timeout handling (`UNKNOWN` status)
- Provider health monitoring, metrics and circuit breaker
  (`HEALTHY` / `DEGRADED` / `OPEN` / `HALF_OPEN`)
- Per-user rate limiting
- Token-aware context management with automatic summarization
- Multi-user isolation
- Conversation locking
- Request/attempt IDs, duplicate-response prevention
- Stale-processing recovery (`PROCESSING` → `UNKNOWN`)
- GitHub Actions CI/CD
- Passenger / cPanel (`Setup Python App`) compatible deployment

## Requirements

- Python 3.11 or 3.12
- SQLite (development) or MySQL/MariaDB (production)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- API keys for the AI providers you want to use

## Installation

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

- Windows: `.venv\Scripts\Activate.ps1`
- Linux/macOS: `source .venv/bin/activate`

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Development dependencies:

```bash
pip install -r requirements-dev.txt
```

### 3. Create `.env`

```bash
cp .env.example .env
```

Fill in at least `TELEGRAM_BOT_TOKEN` and one provider API key.

## Environment Variables

See `.env.example` for the full reference.

| Variable | Description | Default |
| --- | --- | --- |
| `APP_ENV` | `development` / `production` | `development` |
| `DEBUG` | SQL echo etc. | `true` |
| `DATABASE_URL` | SQLAlchemy URL (SQLite dev / MySQL prod) | `sqlite:///./data/app.db` |
| `TELEGRAM_BOT_TOKEN` | Bot token | — |
| `TELEGRAM_WEBHOOK_URL` | Public HTTPS webhook URL | — |
| `TELEGRAM_WEBHOOK_SECRET` | Secret validated on webhook calls | — |
| `AI_PROVIDER_ORDER` | Provider priority, comma separated | `kimi,qwen,opencode` |
| `AI_TIMEOUT_SECONDS` | Per-request provider timeout | `60` |
| `AI_MAX_RETRIES` | Max retries per provider | `1` |
| `CONTEXT_MAX_TOKENS` | Context token budget | `12000` |
| `RECENT_MESSAGE_LIMIT` | Max recent messages to consider | `30` |
| `SUMMARY_TRIGGER_TOKENS` | Tokens above which summarization triggers | `8000` |
| `RATE_LIMIT_REQUESTS` | Requests per window per user | `10` |
| `RATE_LIMIT_WINDOW_SECONDS` | Rate limit window | `60` |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | Failures before circuit opens | `3` |
| `CIRCUIT_BREAKER_COOLDOWN_SECONDS` | Cooldown before HALF_OPEN | `60` |
| `LOG_LEVEL` | Logging level | `INFO` |

Provider-specific variables (`KIMI_API_KEY`, `KIMI_BASE_URL`, `KIMI_MODEL`,
`QWEN_API_KEY`, `QWEN_BASE_URL`, `QWEN_MODEL`, `OPENCODE_API_KEY`,
`OPENCODE_BASE_URL`, `OPENCODE_MODEL`, `GEMINI_API_KEY`, `GEMINI_BASE_URL`,
`GEMINI_MODEL`).

> **Secrets are never committed.** `.env` is git-ignored. Production secrets
> live in the hosting environment, CI credentials live in GitHub Secrets.

## Database Setup

### SQLite (development)

Tables are created automatically at startup via `init_db()`. For migrations:

```bash
alembic upgrade head
```

### MySQL/MariaDB (production)

Set `DATABASE_URL`:

```text
DATABASE_URL=mysql+aiomysql://user:password@host/dbname
```

Run migrations:

```bash
alembic upgrade head
```

> Note: the production driver `aiomysql` must be installed separately
> (`pip install aiomysql`). SQLite is used for development; business logic is
> driver-agnostic and goes through repositories.

## Telegram Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Set `TELEGRAM_BOT_TOKEN` in `.env`.
3. Set your public HTTPS webhook URL in `TELEGRAM_WEBHOOK_URL`.

### Webhook Setup

```bash
python scripts/setup_webhook.py
```

This calls `setWebhook` with `TELEGRAM_WEBHOOK_URL` and, if set,
`TELEGRAM_WEBHOOK_SECRET`.

### Commands

| Command | Description |
| --- | --- |
| `/start` | Create user + default conversation, show welcome |
| `/help` | Show help |
| `/new` | Create a new conversation |
| `/reset` | Reset the active conversation's context |
| `/history` | List conversations owned by the current user |
| `/models` | Show configured AI providers |
| `/status` | Show system/provider status |
| `/id` | Show your Telegram ID |

## AI Provider Setup

Providers use the OpenAI-compatible chat completions API
(`POST /chat/completions`) and are configured entirely via environment
variables. Add a new provider by:

1. Adding a subclass of `OpenAICompatibleProvider` (e.g. `app/ai/providers/xyz.py`).
2. Registering it in `app/ai/registry.py`.
3. Adding its config block in `app/config.py` and `.env.example`.
4. Adding its name to `AI_PROVIDER_ORDER`.

### Using the free Gemini tier

1. Get a free API key at [Google AI Studio](https://aistudio.google.com/apikey).
2. Configure `.env`:

```env
GEMINI_API_KEY=your_key_here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL=gemini-2.5-flash
```

The Gemini developer free tier applies rate limits but works without a credit
card. Other providers (Qwen/DashScope and Kimi/Moonshot) also offer free
trial quotas for new accounts — set their `*_API_KEY` in `.env` and they will
be used as fallbacks in the order set by `AI_PROVIDER_ORDER`.

Provider availability is checked before each request:

```
Provider configured? -> Circuit breaker open? -> Provider available? -> Request
```

## Local Development

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

```json
{
  "status": "ok",
  "database": "ok",
  "providers": { "kimi": "disabled", "qwen": "disabled", "opencode": "disabled" },
  "telegram": "not_configured"
}
```

## Testing

```bash
pytest
```

Tests use mocked / in-memory providers and do not require real AI credentials.

Fake providers include: `SuccessfulProvider`, `FailingProvider`,
`TimeoutProvider`, `RateLimitedProvider`, `AuthenticationErrorProvider`.

Key covered behaviors:

- Provider success / fallback / multiple fallback / all-failed
- **Context preservation during fallback**
- Timeout ambiguity (`UNKNOWN` outcome)
- Rate limiting (provider not called when limited)
- Circuit breaker (open provider skipped)
- Conversation locking (order preserved)
- User isolation (cross-user access rejected)
- Persistence (history survives "restart")
- Token-aware context budget
- Telegram response chunking
- Webhook security (secret validation)

## Deployment

### GitHub Actions

- `.github/workflows/test.yml` – checkouts, installs, runs tests on push/PR.
- `.github/workflows/deploy.yml` – runs tests, then deploys to Jagoan Hosting
  on push to `main`. **A failed build stops deployment.**

### Jagoan Hosting (cPanel "Setup Python App")

1. Create a Python App from cPanel pointing at the project directory.
2. The entrypoint is `passenger_wsgi.py` (exposes the FastAPI app as
   `application`).
3. Configure all environment variables in the hosting environment — **not**
   `.env` in Git.
4. Set `TELEGRAM_WEBHOOK_URL` to your HTTPS URL, then either run
   `scripts/setup_webhook.py` on the server or run it locally.

### Deployment Script

`scripts/deploy.sh` performs, with `set -e`:

1. Enter the project directory (`DEPLOY_PATH`)
2. Update code (`git pull --ff-only`)
3. Install dependencies
4. Run migrations when `alembic` is available
5. Restart via `RESTART_CMD` (configurable — no invented commands)

Configure the deployment via environment:

```bash
DEPLOY_PATH=/home/user/apps/telegram-ai-chat
RESTART_CMD="touch tmp/restart.txt"   # Passenger app restart
```

### GitHub Secrets

Set these GitHub Secrets for the deploy workflow:

| Secret | Description |
| --- | --- |
| `HOST` | SSH host |
| `PORT` | SSH port |
| `USERNAME` | SSH user |
| `SSH_PRIVATE_KEY` | SSH private key |
| `DEPLOY_PATH` | Remote project directory |
| `RESTART_CMD` | Restart/refresh command |

Never put SSH private keys into the repository.

## Rollback

Deploy a known-good previous commit:

```bash
git revert <commit>
```

or redeploy a previous tag/commit with the deploy workflow. There is no
automatic/risky rollback behavior.

SSH in, `git checkout <known-good-commit>`, then restart the app.

## Troubleshooting

- **Webhook returns 403** – the `X-Telegram-Bot-Api-Secret` header does not
  match `TELEGRAM_WEBHOOK_SECRET`.
- **Bot does not respond** – check webhook is set (`setWebhook` result) and
  that the URL is public HTTPS.
- **All providers fail** – check API keys/base URLs; check `/health` and
  `/status`; disable providers you won't use.
- **Deadlock / duplicate responses** – ensure `CONVERSATION_LOCK` is acquired
  per conversation; request/attempt IDs are logged in `provider_attempts`.
- **Migration differences** – run `alembic upgrade head` before starting.

## Known Limitations

- V1 uses an in-process conversation lock and in-memory rate limiting; for
  multiple app instances a distributed lock (e.g. Redis) is needed.
- V1 provider metrics are in-memory only.
- V1 does not include RAG, image/voice/PDF processing, or an admin dashboard
  (see project spec for V2/V3 roadmap).
- Byte-permitting hosting restrictions on Passenger are configuration-specific;
  `RESTART_CMD` is configurable rather than assumed.

## License

MIT – see [LICENSE](LICENSE).