# Bildx AI Image-Ad Generator

A full-stack creative studio that turns a public product image and factual brief into grounded ad copy and a downloadable 1080×1350 PNG. FastAPI runs asynchronous jobs; React provides the marketer workflow; Pillow composes the final ad while preserving the supplied product image.

## Quick start

Requirements: Docker Desktop with Docker Compose.

```bash
cp .env.example .env       # optional; fake provider works without this
docker compose up --build
```

Open <http://localhost:3000>. API documentation is proxied from the backend at <http://localhost:3000/api/health>; direct Swagger docs are available when running the backend locally at <http://localhost:8000/docs>.

The default `fake` provider is deterministic, offline-safe, and consumes no credits. Use any direct, publicly reachable image URL. Choose one of the sample briefs or enter product facts manually.

## Local development

Backend (Python 3.11+):

```bash
py -m pip install -r backend/requirements.txt
py -m uvicorn app.main:app --app-dir backend --reload
```

Frontend (Node 20+), in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to port 8000.

## Verification

```bash
py -m pytest
py scripts/load_demo.py
cd frontend
npm run lint
npm run build
```

`load_demo.py` submits 10 API requests concurrently using an in-process ASGI transport, fake provider, and mocked image bytes. It verifies unique IDs, a three-job concurrency ceiling, nine successful jobs, one isolated permanent failure, and idempotency-key duplicate prevention. It uses no network or paid model.

## Provider configuration

Copy `.env.example` to `.env`, set `AI_PROVIDER` to `fake`, `gemini`, or `openai`, and provide only the matching key. Credentials are read from environment variables and never returned by the API.

The prompt asks the model for JSON copy only. Pillow then renders the original product pixels and copy deterministically. This is less visually generative than diffusion-based image synthesis, but it offers stronger product fidelity, reliably legible typography, predictable cost, and reproducible output. Provider implementations share `BaseAIProvider`, so another model can be added without changing routes or orchestration.

## API workflow

1. `POST /api/generations` with the product brief and optional `Idempotency-Key`.
2. Poll `GET /api/generations/{id}` until `completed` or `failed`.
3. Download `GET /api/generations/{id}/image`.

Statuses are `pending`, `processing`, `retrying`, `completed`, and `failed`. The queue is bounded, work is isolated in retained background tasks, provider work is semaphore-limited, transient failures use bounded exponential backoff, and permanent failures are not retried.

## Security and limitations

- URL validation blocks non-HTTP protocols, localhost, private/link-local/reserved address ranges, and private DNS results.
- Downloads have strict timeouts, declared and actual size checks, content-type checks, and image decoding validation.
- Remote URL fetching still has residual DNS-rebinding and redirect risks. Production should use an egress proxy, validate every redirect hop at connection time, stream into a hard byte-limited buffer, and pin resolved public addresses.
- State and idempotency records are process-local and are lost on restart. A production/multi-worker deployment should use Redis/Postgres plus a durable worker queue.
- Grounding combines strict prompt rules, schema word limits, and high-risk claim detection; it is not a formal semantic proof that every phrase is sourced.
- CORS is intentionally permissive for this self-contained demo and should be restricted to known origins in production.

See `ARCHITECTURE.md`, `PROMPT_NOTES.md`, and `AI_USAGE.md` for design details.

## Time spent and next steps

Approximate implementation time: 5.5 hours, including backend completion, UI, tests, load demonstration, Docker, and documentation.

Next: durable storage/queue, an egress-isolated downloader, semantic grounding against source spans, authentication and rate limiting, richer layout templates, accessibility testing, and browser end-to-end tests.

## Demo video checklist

The repository cannot embed a human-recorded walkthrough automatically. A submission recording (maximum five minutes) should show:

1. `docker compose up --build`
2. Successful generation and PNG download
3. Invalid/failing image behavior and retry UI
4. `py -m pytest`
5. `py scripts/load_demo.py`
