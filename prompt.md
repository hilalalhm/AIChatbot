# Telegram AI Chat V2

## 1. Project Objective

Build a production-ready **AI Chat application using Telegram as the UI**.

The application must support:

* Telegram Bot
* FastAPI backend
* Persistent conversations
* Persistent context/memory
* Multiple AI providers
* Automatic AI provider fallback
* Context preservation during fallback
* Safe retry handling
* Ambiguous timeout handling
* Provider health monitoring
* Circuit breaker
* Conversation locking
* Per-user rate limiting
* Token-aware context management
* Automatic conversation summarization
* Multi-user isolation
* Multiple conversations per user
* GitHub repository
* Automated tests
* GitHub Actions CI/CD
* Deployment to Jagoan Hosting
* cPanel `Setup Python App`
* Passenger-compatible deployment
* Easy addition of new AI providers

The most important requirement is:

> **Changing AI providers must NEVER cause the conversation context to be lost.**

The database is the source of truth for conversation history.

AI providers are only execution backends.

---

# 2. Important Instructions

Before writing code:

1. Inspect the existing repository.
2. Inspect all existing files that are relevant.
3. Determine whether the repository is empty or already contains an application.
4. Reuse existing code when appropriate.
5. Do not unnecessarily delete existing functionality.
6. Do not invent APIs, endpoints, models, credentials, or hosting commands.
7. Do not hardcode secrets.
8. Do not commit `.env`.
9. Do not log API keys or tokens.
10. Implement real working code, not pseudocode.
11. Add tests for important functionality.
12. Run the tests after implementation.
13. Fix errors found during testing.
14. Verify imports and application startup.
15. Verify `/health`.
16. Verify database initialization/migrations.
17. Verify fallback behavior using mocked providers.
18. Verify GitHub Actions configuration.
19. Verify deployment configuration.
20. Document anything that cannot be automatically verified.

Do not claim that deployment works unless it has actually been tested.

If a Jagoan Hosting-specific command cannot be verified, make it configurable instead of inventing a command.

---

# 3. Core Architecture

Use this architecture:

```text
Telegram User
      |
      v
Telegram Bot
      |
      v
FastAPI Webhook
      |
      v
Telegram Handler
      |
      v
Chat Service
      |
      +----------------+
      |                |
      v                v
Conversation       Rate Limiter
Manager
      |
      v
Database
      |
      v
Context Manager
      |
      +----------------------+
      |                      |
      v                      v
Conversation Summary    Recent Messages
      |
      v
Context Snapshot
      |
      v
AI Router
      |
      +----------+----------+
      |          |          |
      v          v          v
 Provider A  Provider B  Provider C
      |          |          |
      +----------+----------+
                 |
                 v
          Final AI Response
                 |
                 v
              Database
                 |
                 v
              Telegram
```

The fundamental design must be:

```text
Database
   |
   v
Context Manager
   |
   v
Immutable Context Snapshot
   |
   v
AI Router
   |
   +---- Provider A
   |
   +---- Provider B
   |
   +---- Provider C
```

---

# 4. Core Principle

The AI provider must NOT own the conversation.

The database owns the conversation.

For example:

```text
User
  |
  +-- Conversation A
  |      |
  |      +-- Message 1
  |      +-- Message 2
  |      +-- Message 3
  |
  +-- Conversation B
         |
         +-- Message 1
         +-- Message 2
```

If Provider A fails:

```text
Provider A
    |
    X FAILED
    |
    v
Provider B
```

Provider B must receive the same conversation context.

---

# 5. Technology Stack

Use:

* Python 3.x
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic
* SQLite for development
* MySQL/MariaDB compatibility for production
* httpx
* python-dotenv
* A stable Telegram Bot library with webhook support
* pytest
* pytest-asyncio
* Git
* GitHub
* GitHub Actions

Avoid unnecessary infrastructure for V1.

Do NOT introduce:

* Redis
* Kafka
* Celery
* Kubernetes
* Docker

unless there is a strong technical reason.

The application should remain simple and suitable for affordable/shared hosting.

---

# 6. Project Structure

Use this structure:

```text
telegram-ai-chat/
|
+-- app/
|   |
|   +-- __init__.py
|   +-- main.py
|   +-- config.py
|   |
|   +-- api/
|   |   +-- __init__.py
|   |   +-- health.py
|   |
|   +-- telegram/
|   |   +-- __init__.py
|   |   +-- bot.py
|   |   +-- handlers.py
|   |   +-- webhook.py
|   |
|   +-- ai/
|   |   +-- __init__.py
|   |   +-- base.py
|   |   +-- router.py
|   |   +-- registry.py
|   |   +-- exceptions.py
|   |   +-- health.py
|   |   |
|   |   +-- providers/
|   |       +-- __init__.py
|   |       +-- openai_compatible.py
|   |       +-- kimi.py
|   |       +-- qwen.py
|   |       +-- opencode.py
|   |
|   +-- context/
|   |   +-- __init__.py
|   |   +-- manager.py
|   |   +-- memory.py
|   |   +-- summarizer.py
|   |
|   +-- database/
|   |   +-- __init__.py
|   |   +-- database.py
|   |   +-- models.py
|   |   +-- repository.py
|   |
|   +-- services/
|   |   +-- __init__.py
|   |   +-- chat_service.py
|   |   +-- conversation_service.py
|   |   +-- message_service.py
|   |
|   +-- reliability/
|   |   +-- __init__.py
|   |   +-- circuit_breaker.py
|   |   +-- lock.py
|   |   +-- rate_limiter.py
|   |
|   +-- utils/
|       +-- __init__.py
|       +-- ids.py
|       +-- logging.py
|
+-- tests/
|   +-- test_health.py
|   +-- test_ai_router.py
|   +-- test_fallback.py
|   +-- test_context.py
|   +-- test_summary.py
|   +-- test_database.py
|   +-- test_locking.py
|   +-- test_rate_limit.py
|   +-- test_telegram.py
|
+-- scripts/
|   +-- setup_webhook.py
|   +-- deploy.sh
|
+-- .github/
|   +-- workflows/
|       +-- test.yml
|       +-- deploy.yml
|
+-- .env.example
+-- .gitignore
+-- requirements.txt
+-- requirements-dev.txt
+-- passenger_wsgi.py
+-- README.md
+-- LICENSE
```

You may modify the structure if a better architecture is justified.

Keep separation of concerns.

---

# 7. Configuration

Use environment variables.

Create `.env.example`.

Example:

```env
APP_ENV=development
DEBUG=true

DATABASE_URL=sqlite:///./data/app.db

TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_URL=
TELEGRAM_WEBHOOK_SECRET=

AI_PROVIDER_ORDER=kimi,qwen,opencode

AI_TIMEOUT_SECONDS=60
AI_MAX_RETRIES=1

CONTEXT_MAX_TOKENS=12000
RECENT_MESSAGE_LIMIT=30
SUMMARY_TRIGGER_TOKENS=8000

RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW_SECONDS=60

CIRCUIT_BREAKER_FAILURE_THRESHOLD=3
CIRCUIT_BREAKER_COOLDOWN_SECONDS=60

LOG_LEVEL=INFO
```

Provider-specific configuration should also be environment-based.

Example:

```env
KIMI_API_KEY=
KIMI_BASE_URL=
KIMI_MODEL=

QWEN_API_KEY=
QWEN_BASE_URL=
QWEN_MODEL=

OPENCODE_API_KEY=
OPENCODE_BASE_URL=
OPENCODE_MODEL=
```

Do not assume these provider values are valid.

Use the actual provider configuration only when confirmed.

---

# 8. Secrets

Never hardcode:

* AI API keys
* Telegram bot token
* Database password
* Webhook secret
* SSH private key
* Hosting credentials

Never commit:

```text
.env
```

to Git.

Production secrets belong in the hosting environment.

GitHub Actions secrets should only contain deployment credentials or other values genuinely required by CI/CD.

---

# 9. Database

Use SQLAlchemy.

Development:

```text
SQLite
```

Production:

```text
MySQL / MariaDB
```

The business logic must not depend directly on SQLite.

Use repositories.

Architecture:

```text
ChatService
    |
    +-- UserRepository
    +-- ConversationRepository
    +-- MessageRepository
    |
    v
SQLAlchemy
    |
    v
Database
```

---

# 10. Users Table

Create:

```text
users
```

Fields:

```text
id
telegram_id
username
first_name
created_at
updated_at
```

Requirements:

* `telegram_id` must be unique.
* User lookup must use Telegram identity.
* Never expose another user's data.

---

# 11. Conversations Table

Create:

```text
conversations
```

Fields:

```text
id
user_id
title
summary
created_at
updated_at
```

One user may have multiple conversations.

Conversation ownership must always be checked.

---

# 12. Messages Table

Create:

```text
messages
```

Fields:

```text
id
conversation_id
role
content
status
provider
model
request_id
attempt_id
created_at
updated_at
```

Roles:

```text
system
user
assistant
```

Statuses:

```text
pending
processing
completed
failed
unknown
```

`unknown` is mandatory for ambiguous provider outcomes.

---

# 13. Provider Attempts

Create a provider attempt record if useful:

```text
provider_attempts
```

Fields:

```text
id
message_id
request_id
attempt_id
provider
model
status
error_type
latency_ms
created_at
completed_at
```

This is used to track fallback attempts.

Example:

```text
Request:
req_123

Attempt 1:
kimi
timeout
UNKNOWN

Attempt 2:
qwen
success
```

---

# 14. Database Migrations

Use Alembic.

Create an initial migration.

README must explain:

```bash
alembic upgrade head
```

Do not perform destructive database operations automatically.

Never delete production data during migration.

---

# 15. Telegram

Use Telegram webhook for production.

Endpoint:

```text
POST /telegram/webhook
```

Health endpoint:

```text
GET /health
```

Commands:

```text
/start
/help
/new
/reset
/history
/models
/status
```

---

# 16. Telegram /start

When `/start` is received:

1. Find user.
2. Create user if necessary.
3. Create default conversation if necessary.
4. Return a concise welcome message.

---

# 17. New Conversation

Implement:

```text
/new
```

It creates a new conversation.

Old conversations must remain available.

Example:

```text
Conversation A
- AI Project

Conversation B
- Job Application
```

Context must remain isolated.

---

# 18. Conversation History

Implement:

```text
/history
```

It should show only conversations owned by the current Telegram user.

---

# 19. Reset

Implement:

```text
/reset
```

Reset the active conversation context without accidentally deleting unrelated conversations.

If an operation is destructive, require confirmation.

---

# 20. Models

Implement:

```text
/models
```

Show configured providers/models.

Example:

```text
AI Providers

Kimi: Available
Qwen: Available
OpenCode: Disabled
```

Never expose API keys.

---

# 21. Status

Implement:

```text
/status
```

Show safe system status.

Example:

```text
Bot: Online
Database: OK

AI Providers:
Kimi: Healthy
Qwen: Degraded
OpenCode: Disabled
```

Do not expose internal credentials.

---

# 22. Context Management

Create:

```text
ContextManager
```

Primary method:

```python
build_context(
    conversation_id,
    current_message
)
```

It should produce a `ContextSnapshot`.

Context should contain:

```text
System Instructions
Conversation Summary
Important Memory
Recent Messages
Current User Message
```

---

# 23. Context Snapshot

Once created, the context snapshot must not change during fallback.

Example:

```text
context_snapshot = build_context()

Provider A(context_snapshot)
Provider B(context_snapshot)
Provider C(context_snapshot)
```

Do NOT rebuild the context after Provider A fails.

This is mandatory.

---

# 24. Context Priority

When context exceeds the available budget, prioritize:

```text
1. System instructions
2. Conversation summary
3. Important memory
4. Recent messages
5. Current user message
```

Use:

```env
CONTEXT_MAX_TOKENS=12000
```

Do not rely only on a fixed number of messages.

---

# 25. Token-Aware Context

Context management must consider token size.

Do not simply do:

```text
last 30 messages
```

without checking context size.

The system should:

1. Calculate/estimate context size.
2. Reserve room for the current user message.
3. Include summary.
4. Include important memory.
5. Include as many recent messages as fit.
6. Avoid exceeding the configured context budget.

---

# 26. Conversation Summary

When conversation becomes large, summarize older messages.

Trigger:

```env
SUMMARY_TRIGGER_TOKENS=8000
```

Do not summarize on every request.

The summary should preserve:

* User goals
* Project state
* Decisions
* Important configurations
* Preferences
* Constraints
* Unresolved problems
* Important facts
* Current task

The summary must not randomly remove important information.

---

# 27. Important Memory

Separate:

```text
Conversation Summary
```

from:

```text
Important Memory
```

Important memory stores facts that should remain available for the conversation.

Example:

```text
The backend uses FastAPI.
Deployment target is Jagoan Hosting.
Telegram is the primary UI.
```

Do not store unnecessary sensitive information.

---

# 28. AI Provider Abstraction

Create a common provider interface.

Concept:

```python
class AIProvider:
    async def chat(
        self,
        messages,
        model=None,
        request_id=None,
        attempt_id=None,
    ):
        ...
```

Every provider must implement the same interface.

Telegram and ChatService must not know provider-specific implementation details.

---

# 29. Unified AI Response

Create a unified response object.

It should contain information such as:

```text
content
provider
model
request_id
attempt_id
usage
latency_ms
status
```

The rest of the application must use this unified object.

---

# 30. Provider Registry

Do not scatter:

```python
if provider == "kimi":
    ...
elif provider == "qwen":
    ...
```

throughout the codebase.

Use:

```text
ProviderRegistry
```

Example:

```text
ProviderRegistry
|
+-- kimi
+-- qwen
+-- opencode
```

Provider priority comes from:

```env
AI_PROVIDER_ORDER=kimi,qwen,opencode
```

---

# 31. OpenAI-Compatible Provider

If multiple providers use an OpenAI-compatible API, create a reusable adapter:

```text
OpenAICompatibleProvider
```

Configuration:

```text
name
base_url
api_key
model
timeout
```

This makes adding providers easier.

Do not assume a provider is OpenAI-compatible unless its API actually supports it.

---

# 32. Provider Availability

Before making a request, check:

```text
Provider configured?
        |
        v
Circuit breaker open?
        |
        v
Provider available?
        |
        v
Make request
```

Disabled providers should be skipped.

---

# 33. AI Router

Create:

```text
AIRouter
```

Concept:

```python
await ai_router.chat(
    context=context_snapshot,
    request_id=request_id,
)
```

The router controls:

* Provider selection
* Retry
* Fallback
* Error classification
* Circuit breaker
* Provider attempt tracking

Telegram must not handle fallback logic.

---

# 34. Fallback

Example:

```text
Provider A
    |
    X
    |
Provider B
    |
    X
    |
Provider C
    |
    v
SUCCESS
```

The user should receive the successful response normally.

---

# 35. Fallback Context Preservation

This is one of the highest-priority requirements.

Example:

```text
context_snapshot = {
    summary: "...",
    memory: "...",
    recent_messages: [...],
    current_message: "..."
}
```

Provider A receives:

```text
context_snapshot
```

Provider A fails.

Provider B receives the exact same:

```text
context_snapshot
```

Do not mutate it between attempts.

---

# 36. Error Classification

Classify errors.

Retry/fallback candidates include:

```text
timeout
network error
408
429
500
502
503
temporary unavailable
quota exhausted
```

Configuration/authentication errors:

```text
401
403
invalid API key
invalid configuration
```

Do not retry authentication failures indefinitely.

---

# 37. Retry

Retries must be limited.

Configuration:

```env
AI_MAX_RETRIES=1
```

Use exponential backoff where appropriate.

Never implement infinite retries.

---

# 38. Ambiguous Timeout

This is critical.

Never assume:

```text
timeout = provider did not process request
```

A provider may have accepted the request and generated a response while the client timed out.

Therefore:

```text
REQUEST
   |
   v
Provider
   |
   +-- request accepted
   |
   +-- response generated
   |
   X network timeout
```

The final state may be unknown.

Use:

```text
UNKNOWN
```

when the result cannot be determined.

---

# 39. Request ID

Every logical user request must have:

```text
request_id
```

Example:

```text
req_01ABC123
```

Every provider attempt must have:

```text
attempt_id
```

Example:

```text
attempt_01
attempt_02
```

Use them in logs and database records.

---

# 40. Idempotency / Duplicate Protection

One logical user request must not result in multiple final assistant messages.

Structure:

```text
Request
|
+-- Attempt 1
|
+-- Attempt 2
|
+-- Attempt 3
```

Only one attempt can become the final successful response.

If a provider timeout is ambiguous:

```text
attempt = UNKNOWN
```

Do not blindly assume it is safe to retry.

If the provider supports idempotency or status lookup, use it.

If it does not:

1. Record the attempt as UNKNOWN.
2. Apply the configured fallback policy.
3. Prevent duplicate final assistant messages.
4. Preserve database consistency.
5. Log the ambiguity.

---

# 41. Message State Machine

Use:

```text
PENDING
   |
   v
PROCESSING
   |
   +----> COMPLETED
   |
   +----> FAILED
   |
   +----> UNKNOWN
```

Do not perform invalid state transitions.

---

# 42. Conversation Lock

Messages from the same conversation must be processed sequentially.

Example:

```text
User sends:

Message A
Message B
Message C
```

The system must avoid:

```text
A
C
B
```

Use:

```text
ConversationLock
```

Flow:

```text
Acquire lock
    |
Process request
    |
Save result
    |
Release lock
```

V1 may use an in-process lock.

However, design it as an abstraction so it can later be replaced by a distributed locking mechanism.

---

# 43. Rate Limiting

Implement per-user rate limiting.

Configuration:

```env
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW_SECONDS=60
```

Rate limiting must happen before the AI provider is called.

If limit is exceeded:

```text
Too many requests.
Please try again shortly.
```

Do not consume AI provider quota for rejected requests.

---

# 44. Circuit Breaker

Each provider should have:

```text
HEALTHY
DEGRADED
OPEN
HALF_OPEN
```

Example:

```text
Provider A
   |
failure
   |
failure
   |
failure
   |
OPEN
```

While OPEN:

```text
Provider A is skipped.
```

After cooldown:

```text
OPEN
  |
  v
HALF_OPEN
  |
  v
test request
  |
  +-- success --> HEALTHY
  |
  +-- failure --> OPEN
```

Configuration:

```env
CIRCUIT_BREAKER_FAILURE_THRESHOLD=3
CIRCUIT_BREAKER_COOLDOWN_SECONDS=60
```

---

# 45. Provider Health

Provider failure must not crash the entire application.

Example:

```text
Kimi = down
Qwen = healthy
```

The application should continue using Qwen.

---

# 46. Chat Service

Create:

```text
ChatService
```

Main flow:

```text
Telegram message
       |
       v
Rate limit
       |
       v
Acquire conversation lock
       |
       v
Create user message
       |
       v
PENDING
       |
       v
PROCESSING
       |
       v
Load conversation
       |
       v
Build context snapshot
       |
       v
AI Router
       |
       v
Provider attempts
       |
       v
Save final response
       |
       v
COMPLETED
       |
       v
Send Telegram response
       |
       v
Release lock
```

If AI fails:

```text
User message remains stored.
```

Never delete the user's message because an AI provider failed.

---

# 47. All Providers Failed

If all providers fail:

```text
User message = saved
Assistant final response = not created
```

Telegram should receive:

```text
Maaf, semua AI provider sedang tidak tersedia.
Pesan Anda sudah tersimpan. Silakan coba lagi nanti.
```

Never expose:

* stack trace
* API key
* internal exception
* database credentials
* provider credentials

---

# 48. Telegram Response Chunking

Telegram responses may be too long.

Implement a response chunker.

Priority:

```text
1. Paragraph
2. Newline
3. Whitespace
4. Hard split
```

Do not arbitrarily cut words if avoidable.

---

# 49. Webhook Security

Use:

```env
TELEGRAM_WEBHOOK_SECRET=
```

Validate the webhook secret when configured.

Production webhook must use HTTPS.

---

# 50. Logging

Use structured logging where practical.

Include:

```text
timestamp
level
request_id
conversation_id
message_id
attempt_id
provider
model
status
latency
error_type
```

Example:

```text
request=req_123
conversation=45
provider=kimi
attempt=1
status=timeout
latency=60000
```

Never log:

```text
API keys
Telegram token
Authorization headers
Passwords
Database passwords
SSH keys
```

---

# 51. Multi-User Isolation

User A must never access User B's conversations.

Every conversation query must validate ownership.

Concept:

```text
Telegram ID
    |
    v
User
    |
    v
Conversation
    |
    v
Messages
```

Do not trust a raw conversation ID supplied by a user without checking ownership.

---

# 52. Input Validation

Validate Telegram input.

Implement reasonable message length limits.

Do not allow unlimited input.

If necessary:

```text
Pesan terlalu panjang.
Silakan pecah menjadi beberapa pesan.
```

---

# 53. Error Handling

Create custom exceptions where useful:

```text
ProviderError
ProviderTimeoutError
ProviderRateLimitError
ProviderAuthenticationError
ProviderUnavailableError
ContextError
DatabaseError
TelegramError
```

Use clear error classification.

---

# 54. Restart Safety

Conversation history must survive application restart.

Never store the main conversation state only in:

```text
RAM
```

or:

```text
global Python variables
```

The database must contain the persistent state.

---

# 55. Stale Processing Recovery

If the server crashes while a message is:

```text
PROCESSING
```

the application should detect stale processing records.

Do not blindly regenerate the request.

Possible recovery:

```text
PROCESSING
    |
    v
stale
    |
    v
UNKNOWN
```

The recovery policy must prevent duplicate AI generation.

---

# 56. Health Endpoint

Implement:

```text
GET /health
```

Minimum response:

```json
{
  "status": "ok"
}
```

It may also include:

```text
database
telegram
providers
```

Do not expose secrets.

One failed AI provider should not automatically make the whole application unhealthy.

---

# 57. Provider Metrics

Track basic provider metrics.

At minimum:

```text
success count
failure count
timeout count
rate limit count
average latency
```

For V1, in-memory metrics are acceptable.

Do not build an unnecessarily complex monitoring system.

---

# 58. Development

README must include:

```bash
python -m venv .venv
```

Install:

```bash
pip install -r requirements.txt
```

Development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run:

```bash
uvicorn app.main:app --reload
```

Test:

```bash
pytest
```

---

# 59. Telegram Webhook Setup

Create:

```text
scripts/setup_webhook.py
```

Use:

```env
TELEGRAM_WEBHOOK_URL=
TELEGRAM_WEBHOOK_SECRET=
```

Do not hardcode the webhook URL.

---

# 60. Passenger / cPanel

Create:

```text
passenger_wsgi.py
```

The entrypoint should expose the FastAPI application in a way compatible with the actual hosting environment.

Example concept:

```python
from app.main import app

application = app
```

If an adapter is necessary, implement it based on the actual runtime.

Do not assume unsupported Passenger configuration.

---

# 61. Jagoan Hosting

Production target:

```text
Jagoan Hosting Cloud Hosting
```

The application should be deployable using:

```text
cPanel
Setup Python App
```

The deployment mechanism must be configurable.

Do not invent unsupported hosting commands.

---

# 62. Deployment Architecture

Target:

```text
Local Development
       |
       v
Git Commit
       |
       v
Git Push
       |
       v
GitHub
       |
       v
GitHub Actions
       |
       v
Run Tests
       |
       +---- FAIL ----> STOP
       |
       v
Deploy
       |
       v
Jagoan Hosting
       |
       v
Python App
       |
       v
Health Check
```

---

# 63. GitHub Actions Test Workflow

Create:

```text
.github/workflows/test.yml
```

It should:

1. Checkout repository.
2. Setup Python.
3. Install dependencies.
4. Run tests.
5. Fail if tests fail.

---

# 64. GitHub Actions Deployment Workflow

Create:

```text
.github/workflows/deploy.yml
```

Expected flow:

```text
Push to main
     |
     v
Checkout
     |
     v
Setup Python
     |
     v
Install dependencies
     |
     v
Run tests
     |
     +---- FAIL ----> STOP
     |
     v
Deploy to Jagoan Hosting
```

Never deploy a failed build.

---

# 65. Deployment Credentials

Use GitHub Secrets for deployment credentials.

Possible variables:

```text
HOST
PORT
USERNAME
SSH_PRIVATE_KEY
DEPLOY_PATH
```

Names may be changed if necessary.

Never put SSH private keys into the repository.

---

# 66. Production Environment

Production environment variables must be configured on Jagoan Hosting.

Do not upload `.env` to GitHub.

Separate:

```text
Local environment
Production environment
GitHub Actions secrets
```

---

# 67. Deployment Script

Create:

```text
scripts/deploy.sh
```

if required.

It should perform:

```text
1. Enter project directory
2. Update code
3. Install dependencies
4. Run migrations if required
5. Reload/restart Python application
6. Fail immediately if a critical step fails
```

Use:

```bash
set -e
```

or equivalent.

Do not invent an unsupported restart command.

Make the restart command configurable.

---

# 68. Rollback

Document rollback.

Example:

```bash
git revert <commit>
```

or deploy a known-good previous commit.

Do not create dangerous automatic rollback behavior.

---

# 69. Testing Strategy

Tests must not depend on real AI API credentials.

Use mocked/fake providers.

Create:

```text
SuccessfulProvider
FailingProvider
TimeoutProvider
RateLimitedProvider
AuthenticationErrorProvider
```

---

# 70. Required Tests

## Test: Provider Success

```text
A = SUCCESS
```

Expected:

```text
A response
```

---

## Test: Provider Fallback

```text
A = FAILURE
B = SUCCESS
```

Expected:

```text
B response
```

---

## Test: Multiple Fallback

```text
A = FAILURE
B = FAILURE
C = SUCCESS
```

Expected:

```text
C response
```

---

## Test: All Providers Failed

Expected:

```text
User message = stored
Assistant final message = not created
Friendly error = sent
```

---

## Test: Context Preservation

Provider A fails.

Provider B must receive the exact same context snapshot.

---

## Test: Timeout

Provider A times out.

Expected:

```text
attempt = UNKNOWN
```

The system must not blindly assume that the request was never processed.

---

## Test: Rate Limit

User exceeds configured limit.

Expected:

```text
AI provider is not called
```

---

## Test: Circuit Breaker

After configured failures:

```text
provider = OPEN
```

Provider must be skipped while the circuit is open.

---

## Test: Authentication Error

Provider returns:

```text
401
```

Expected:

```text
provider skipped
no infinite retry
```

---

## Test: 429

Provider returns:

```text
429
```

Expected:

```text
retry/fallback according to policy
```

---

## Test: 500

Provider returns:

```text
500
```

Expected:

```text
fallback
```

---

## Test: Conversation Lock

Two messages sent nearly simultaneously must not corrupt conversation order.

---

## Test: User Isolation

User A cannot access User B's conversation.

---

## Test: Persistence

Restarting the application must not erase conversation history.

---

## Test: Long Conversation

Large conversation should use:

```text
summary
+
important memory
+
recent messages
```

within the configured context budget.

---

## Test: Telegram Chunking

Long AI response must be split into valid Telegram messages.

---

# 71. Acceptance Scenario

Use this scenario to verify the most important requirement.

Conversation:

```text
User:
Saya sedang membuat aplikasi Telegram AI.

Assistant:
Gunakan FastAPI sebagai backend.

User:
Bagaimana dengan database?

Assistant:
Gunakan PostgreSQL.
```

Next:

```text
User:
Sekarang buat struktur databasenya.
```

Provider A fails.

Provider B handles the request.

Provider B must still receive context containing:

```text
User is building a Telegram AI application.
Backend uses FastAPI.
Database choice is PostgreSQL.
```

The provider switch must be invisible to the conversation state.

---

# 72. Another Acceptance Scenario

Configure:

```text
AI_PROVIDER_ORDER=kimi,qwen,opencode
```

Simulate:

```text
Kimi = timeout
Qwen = 429
OpenCode = success
```

Expected:

```text
Kimi
  |
  v
UNKNOWN / timeout handling
  |
  v
Qwen
  |
  v
429
  |
  v
OpenCode
  |
  v
SUCCESS
```

Only one final assistant message may be stored.

---

# 73. Another Acceptance Scenario

Simulate:

```text
Kimi = 401
Qwen = success
```

Expected:

```text
Kimi skipped
Qwen called
Qwen response returned
```

Do not continuously retry Kimi.

---

# 74. Another Acceptance Scenario

Simulate:

```text
Kimi = 500
Qwen = 500
OpenCode = 500
```

Expected:

```text
User message saved
No duplicate assistant final message
Friendly Telegram error
```

---

# 75. Code Quality

Use:

* Type hints
* Clear naming
* Modular classes
* Dependency injection where useful
* Async network operations
* Proper exception handling
* Small focused functions
* Testable components

Avoid unnecessary abstraction.

The project should be understandable by another developer.

---

# 76. Telegram Handler Responsibility

Telegram handlers should only handle Telegram-specific operations.

Do not put all business logic into:

```text
handlers.py
```

The handler should roughly:

```text
Receive update
     |
Validate
     |
Call ChatService
     |
Send response
```

---

# 77. ChatService Responsibility

ChatService handles:

```text
User
Conversation
Message
Context
AI Router
Persistence
```

It should not contain Telegram-specific provider logic.

---

# 78. ContextManager Responsibility

ContextManager handles:

```text
Summary
Important Memory
Recent Messages
Token Budget
Context Snapshot
```

It should not know how Telegram sends messages.

---

# 79. AIRouter Responsibility

AIRouter handles:

```text
Provider selection
Provider priority
Retry
Fallback
Error classification
Circuit breaker
Provider attempts
```

It should not know Telegram-specific behavior.

---

# 80. Repository Responsibility

Repositories handle database operations.

Examples:

```text
UserRepository
ConversationRepository
MessageRepository
ProviderAttemptRepository
```

---

# 81. V1 Scope

V1 must focus on:

```text
Telegram
+
FastAPI
+
Database
+
Persistent conversations
+
Context manager
+
Summary
+
Multiple providers
+
Fallback
+
Timeout safety
+
Circuit breaker
+
Rate limiting
+
Conversation locking
+
Tests
+
GitHub Actions
+
Jagoan Hosting deployment
```

---

# 82. Do Not Overengineer V1

Do not add:

```text
Redis
Kafka
Celery
Kubernetes
Vector database
RAG
Voice
Image processing
PDF processing
Admin dashboard
```

unless required for the core system.

These can be added later.

---

# 83. Future V2/V3 Extensions

Design the architecture so it can later support:

```text
RAG
PDF
Images
Voice
Web Search
Admin Dashboard
Usage Analytics
Per-user model selection
Long-term memory
Vector database
Redis
Background jobs
```

But do not implement them now.

---

# 84. README Requirements

README must include:

```text
Project Overview
Architecture
Features
Requirements
Installation
Environment Variables
Database Setup
Telegram Setup
Webhook Setup
AI Provider Setup
Local Development
Testing
Deployment
Jagoan Hosting Setup
GitHub Actions
Rollback
Troubleshooting
Known Limitations
```

Include an architecture diagram.

---

# 85. .gitignore

Ensure the following are ignored:

```text
.env
.venv/
venv/
__pycache__/
*.pyc
.pytest_cache/
data/
*.db
```

Also ignore any generated secrets or private deployment files.

---

# 86. Requirements Files

Production dependencies:

```text
requirements.txt
```

Development dependencies:

```text
requirements-dev.txt
```

Do not include unused packages.

Pin versions when appropriate for deployment stability.

---

# 87. Final Verification

After implementation:

```text
1. Install dependencies
2. Run tests
3. Fix failures
4. Run tests again
5. Start FastAPI locally
6. Test /health
7. Test database
8. Test mocked providers
9. Test fallback
10. Test timeout
11. Test context preservation
12. Test locking
13. Test rate limiting
14. Test circuit breaker
15. Test Telegram chunking
16. Check .gitignore
17. Check GitHub Actions
18. Check Passenger entrypoint
19. Check deployment configuration
20. Review README
```

Do not stop after creating files.

---

# 88. Definition of Done

The project is considered complete only if:

* [ ] Telegram bot receives messages
* [ ] Telegram webhook works
* [ ] User persistence works
* [ ] Conversation persistence works
* [ ] Message persistence works
* [ ] Multiple conversations work
* [ ] User isolation works
* [ ] Context is generated from database
* [ ] Context summary works
* [ ] Important memory works
* [ ] Token-aware context works
* [ ] Multiple AI providers are supported
* [ ] Provider registry works
* [ ] Provider fallback works
* [ ] Context remains identical during fallback
* [ ] Retry policy works
* [ ] Timeout ambiguity is handled
* [ ] UNKNOWN status exists
* [ ] Request ID exists
* [ ] Attempt ID exists
* [ ] Duplicate final response is prevented
* [ ] Circuit breaker works
* [ ] Conversation locking works
* [ ] Rate limiting works
* [ ] Telegram response chunking works
* [ ] All-provider failure is handled gracefully
* [ ] Restart does not erase conversations
* [ ] Stale processing is handled
* [ ] Tests exist
* [ ] Tests pass
* [ ] No secrets are committed
* [ ] No secrets appear in logs
* [ ] GitHub Actions test workflow works
* [ ] Deployment workflow exists
* [ ] Jagoan Hosting deployment is documented
* [ ] `/health` works
* [ ] README is complete

---

# 89. Final Architecture Principle

Always preserve this architecture:

```text
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

The following rules are non-negotiable:

```text
DATABASE = SOURCE OF TRUTH

AI PROVIDER = EXECUTION BACKEND

CONTEXT MANAGER = CONTEXT BUILDER

AI ROUTER = PROVIDER SELECTOR

FALLBACK = MUST PRESERVE CONTEXT

TIMEOUT = MAY BE UNKNOWN

ONE USER REQUEST = ONE FINAL ASSISTANT RESPONSE

USER DATA = MUST BE ISOLATED

SECRETS = MUST NEVER BE COMMITTED

TEST FAILURE = MUST STOP DEPLOYMENT
```

Build the application according to this specification.

Do not merely describe the implementation.

**Inspect the repository, implement the code, run the tests, fix the errors, and leave the project in a working state.**
