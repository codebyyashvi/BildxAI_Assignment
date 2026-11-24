# AI Usage

Cursor’s coding agent was used to inspect the assignment, identify missing deliverables, implement the React interface and project infrastructure, and suggest reliability tests and documentation.

No generated change was accepted solely on model confidence. Verification included:

- Reading every changed source file against the assignment requirements.
- Running the full Python test suite with fake/mocked providers.
- Building and linting the TypeScript frontend.
- Running a repeatable 10-request concurrency demonstration.
- Reviewing the Dockerfiles and Compose wiring. Docker was unavailable on the
  development machine, so container startup must be re-run on a Docker host.
- Reviewing `git diff` for secrets, generated caches, and unintended files.

The AI did not supply production credentials, invoke paid model calls, or fabricate the submitted sample image. `sample-output.png` is rendered by this application’s deterministic Pillow composer. The candidate remains responsible for understanding and modifying all submitted code.
