# Architecture

## System design

The React/TypeScript single-page app submits a factual product brief to FastAPI and polls by generation ID. Nginx serves the compiled frontend and proxies `/api` to the backend. The backend has four layers:

1. **Routes and Pydantic schemas** validate transport data and expose create, poll, download, samples, and health endpoints.
2. **Generation orchestrator** owns lifecycle state, idempotency, queue admission, concurrency, retries, and failure isolation.
3. **Provider boundary** exposes one asynchronous `generate_ad_copy` contract, implemented by fake, Gemini, and OpenAI providers.
4. **Safety/composition** validates remote images and grounded copy, then uses Pillow to render a deterministic 1080×1350 PNG.

The prompt lives in `backend/app/services/prompt_engine.py`; model details do not leak into routes.

## Parallel behavior

`POST /api/generations` creates a UUID record and retained background task, then returns `202`. A configurable `asyncio.Semaphore` bounds simultaneously executing generation pipelines. Jobs waiting for a slot count toward `MAX_QUEUE_SIZE`; excess submissions receive `429`. Every record advances independently through pending, processing, retrying, and a terminal state.

This single-process design is intentionally easy to review and demonstrate. The semaphore currently covers download, provider call, and composition. That produces a conservative system-wide resource bound, although the health field `active_provider_calls` represents active pipelines rather than only time inside the remote model call.

## Failure handling

- Temporary provider/network failures retry at most `MAX_RETRIES` times with exponential backoff.
- Permanent input, grounding, authentication, and unsupported-content failures are not retried.
- Each job catches its own failures and records a safe message; unrelated jobs continue.
- Global exception handling masks stack traces and configuration.
- Strong task references prevent in-flight work from being garbage-collected.
- Idempotency keys map repeated submissions to the original generation.

## Capacity decisions

Defaults are three active pipelines and twenty waiting jobs. These are environment-configurable. The API rejects overload predictably instead of allowing unbounded memory growth. The demo uses in-memory records and local image files to avoid external infrastructure; production should move state and idempotency to a database, output to object storage, and jobs to a durable queue.

## Data and security boundaries

Product text is serialized inside explicit context delimiters and treated as passive data. URLs are restricted to HTTP(S), checked against private networks, downloaded with time/size/type limits, and decoded before use. Secrets enter only through environment variables. Output metadata includes model, prompt version, source URL, timestamps, retries, and duration.

The main residual risk is server-side URL fetching: application-level DNS checks alone cannot fully eliminate rebinding or malicious redirect behavior. Production should use a network-isolated fetch service with public-only egress and per-hop validation.
