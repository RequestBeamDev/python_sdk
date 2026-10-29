# SDK Scope and Decisions

Date: 2026-10-29.

## Scope

This repository provides a Python 3.10+ package named `requestbeam`, using HTTPX for synchronous and asynchronous HTTP. It covers the public RequestBeam text, image, video, job, Similarweb, and Twitter contracts. It is an independent SDK repository, not a modification to the gateway, billing database, deployed model catalog, or production services.

The contract snapshot was checked against the RequestBeam application repository's `wiki/public-api-catalog.json`, `wiki/en/api-reference/jobs.mdx`, its public routes, and `packages/shared/src/public-api/public-locales.json`. These source files are evidence for the contract at the date above, not a promise that every upstream provider is currently available.

## API Design

- Preserve server-native JSON and IDs. Do not create a universal response wrapper or turn large decimal IDs into floating-point numbers.
- Keep separate methods for chat, Responses, Messages, images, and videos because their routes and terminal behavior differ.
- Image results are direct JSON/SSE, while video submission returns `data.jobId` for Jobs polling. Submission success is not generation completion.
- Use HTTPX for HTTP transport, timeouts, connection ownership, and line iteration. Parse SSE framing without assuming every event is a text delta.
- Require finite polling budgets and bounded Twitter page iteration. No automatic billing-sensitive retries, even for GET.
- Stop locally on timeout, early stream exit, or async cancellation without claiming upstream cancellation or a refund.
- Preserve Similarweb endpoint-specific data. Only worldwide `country=999` is supported; do not advertise country data or interpret empty records as zero.
- Keep API keys on the configured trusted HTTPS origin, reject cross-origin/unsafe request paths, and do not follow redirects. Asset downloads are deliberately left to a separate client without the API key.

Synchronous polling cannot forcibly cancel an in-flight response: remaining time is applied to HTTP phase timeouts and the deadline is checked between requests. This limitation is documented rather than presented as a strict total wall-clock guarantee. Async polling additionally bounds the whole in-flight request with an asynchronous deadline.

## Language Policy

All 12 public project languages have complete getting-started READMEs and translated SDK-generated errors: English, German, Turkish, Italian, Spanish, French, Brazilian Portuguese, Japanese, Korean, Simplified Chinese, Traditional Chinese, and Russian. Canonical codes match the application source. Public URL aliases (`pt`, `cn`, `tw`), `zh`, script aliases, underscores, and case are normalized explicitly. Unknown locale values fail instead of silently selecting another language.

Localization does not translate API field names, model IDs, request prompts, service error messages, response data, or protocol values. Detailed API reference and design notes are maintained in English; localized READMEs link to them. Adding a public language requires both a translated README and complete local-message coverage.

## Verification Boundary

Automated tests use synthetic fixtures and HTTPX mock transports. They make no paid API calls and do not establish real upstream availability, billing accuracy, successful live generation, production acceptance, deployment, or publication to PyPI. README model examples come from the public contract; applications must inspect current model availability and per-model limits before execution.

This version is installable from a local checkout. No PyPI release is asserted. Git commit identity, remote repository publication, and package publication are separate actions and must be reported separately by the release operator.

## Maintenance

Update the route mapping, Similarweb allowlist, terminal-status/stream rules, and targeted mock tests when the public contract changes. Preserve the no-retry default unless a future API provides a documented idempotency contract. Keep new examples free of real credentials and label recorded fixtures as synthetic. Review locale coverage against the application's public language registry rather than maintaining a smaller independent list.
