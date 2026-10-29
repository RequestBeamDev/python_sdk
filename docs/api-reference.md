# Python SDK API Reference

Contract snapshot: 2026-10-29. See the [English README](../README.md) for runnable examples and links to all 12 translations. The SDK forwards native API parameters and response bodies rather than inventing a shared response envelope. Consult the [RequestBeam API documentation](https://requestbeam.com/en/docs/api-reference/models) for model-specific fields, limits, availability, and billing.

## Clients and Ownership

```python
RequestBeam(
    api_key=None,
    *,
    base_url="https://api.requestbeam.com",
    timeout=60.0,
    locale="en",
    http_client=None,
)
AsyncRequestBeam(
    api_key=None,
    *,
    base_url="https://api.requestbeam.com",
    timeout=60.0,
    locale="en",
    http_client=None,
)
```

- `api_key`: explicit key, or `REQUESTBEAM_API_KEY` when omitted. All calls use `Authorization: Bearer ...`.
- `base_url`: an HTTPS origin, optionally with a port and trailing slash. Paths, credentials, query strings, and fragments are rejected. It must be a trusted server: this is the destination of your key. Do not append `/v1`.
- `timeout`: positive finite number in seconds, passed to HTTPX as a per-phase timeout. This is not a universal end-to-end wall-clock limit.
- `locale`: `en`, `de`, `tr`, `it`, `es`, `fr`, `pt-BR`, `ja`, `ko`, `zh-CN`, `zh-TW`, or `ru`. URL aliases `pt`, `cn`, `tw`, and `zh` are accepted; case and underscores are normalized. `zh-Hans` and `zh-Hant` are also accepted. Unsupported codes raise `ValueError` in English because no target translation exists.
- `http_client`: optionally supply `httpx.Client` or `httpx.AsyncClient`, respectively. SDK-owned clients close on `close()` / `aclose()` or context exit; injected clients remain caller-owned. Custom transports, authentication, hooks, or logging on injected clients are your responsibility.

Use `with RequestBeam(...)` or `async with AsyncRequestBeam(...)`. Async request methods are awaited. Async stream methods are used with `async with`, and stream/page iterators with `async for`.

## Request Methods

| Method | HTTP route | Result |
| --- | --- | --- |
| `list_models()` | `GET /v1/models` | Native model catalog; presence does not prove live provider health |
| `chat_completions(**payload)` | `POST /v1/chat-completions` | Native chat-completions JSON |
| `responses(**payload)` | `POST /openai/responses` | Native Responses JSON |
| `messages(**payload)` | `POST /anthropic/v1/messages` | Native Messages JSON |
| `generate_image(**payload)` | `POST /openai/v1/images/generations` | Direct image result JSON; no Jobs polling |
| `generate_video(**payload)` | `POST /v1/video/seedance` | Submission envelope with `data.jobId` |
| `get_job(job_id)` | `GET /v1/jobs/{id}` | Complete job envelope |
| `similarweb(operation, **params)` | `GET /v1/similarweb/{operation}` | Endpoint-specific native JSON |
| `twitter_user_by_username(username, **params)` | `GET /v1/twitter/users?username=...` | Native Twitter response |
| `twitter_user(user_id, **params)` | `GET /v1/twitter/users/{id}` | Native Twitter response |
| `twitter_user_tweets(user_id, **params)` | `GET /v1/twitter/users/{id}/tweets` | One native page, including `data/includes/meta` when present |

`payload` is forwarded as JSON. Query parameters go through HTTPX encoding. No model is chosen for you, and unknown fields are not silently removed or translated. Non-stream text and image methods reject `stream=True` before making a request. RequestBeam routes differ from the default routes in third-party OpenAI or Anthropic SDKs; use the routes above.

`job_id` and Twitter `user_id` must be nonempty strings of ASCII digits. Never convert Snowflake IDs to floating-point values. Jobs must belong to the same account as the key used to query them.

The low-level method is:

```python
client.request("GET", "/v1/models", json=None, params=None)
```

It accepts an absolute-path reference beginning with one `/`, on the configured origin only. Full URLs, `//`, traversal segments, backslashes, embedded query strings, fragments, and unsafe encoded paths are rejected. Put query data in `params`. Redirects are not followed. The response must be valid JSON on success; a successful non-JSON body raises `ProtocolError`. The generic method does not add endpoint-specific validation or a streaming parser.

## Streams

| Method | Protocol |
| --- | --- |
| `stream_chat_completions(**payload)` | Chat-completions SSE |
| `stream_responses(**payload)` | Responses SSE |
| `stream_messages(**payload)` | Messages SSE |
| `stream_image(**payload)` | Image generation SSE |

These methods set `stream=True` and request `text/event-stream`. Use their context managers to close responses, including when exiting early. Each yielded immutable `SSEEvent` has `data: str`, `event: str = "message"`, and `id: str | None`. `event.json()` parses its JSON value. The parser joins multiline `data:` fields, accepts comment lines, preserves event IDs, and handles chunk boundaries through HTTPX line iteration.

Protocol terminal events are checked. Chat ends at `[DONE]`; Responses completes at `response.completed`; Messages at `message_stop`; images require a completion event followed by `[DONE]`. The `[DONE]` sentinel itself is not yielded. An unexpected end-of-stream raises `ProtocolError`; explicit service errors raise `APIError`, including error events after an HTTP 200 response. Do not treat HTTP 200 or a partial stream as completed output. Stopping your iterator early closes local resources but does not establish upstream cancellation or a refund.

```python
import asyncio
import os
from requestbeam import AsyncRequestBeam

async def main():
    async with AsyncRequestBeam() as client:
        async with client.stream_chat_completions(
            model=os.environ["REQUESTBEAM_TEXT_MODEL"],
            messages=[{"role": "user", "content": "Hello"}],
        ) as events:
            async for event in events:
                print(event.event, event.data)

asyncio.run(main())
```

## Job Polling

```python
client.wait_for_job(job_id, timeout=600, poll_interval=5)
```

Both timing arguments must be positive and finite. The helper waits through `PENDING`, `CONNECT`, and `PROCESSING`; returns the complete original job response at `COMPLETED`; and raises `JobFailedError` at `FAILED` or `CANCELLED`. Unknown states or malformed job responses raise `ProtocolError`. Use `job["data"]["outputResult"]` only after successful completion; its shape depends on the model.

The synchronous helper checks a monotonic deadline between requests and caps each HTTP phase timeout by the remaining budget. It cannot forcibly interrupt an in-flight synchronous response. A response delivering data continuously can exceed the nominal polling budget, so this is not a strict wall-clock ceiling. The async helper additionally limits the in-flight request to the remaining asynchronous deadline. A network error is not automatically retried. `PollingTimeoutError.job_id` identifies the job you can check later. Neither timeout nor local cancellation cancels upstream work or billing.

## Similarweb Operations

Pass a suffix such as `"websites/visits"` or its full local path `"/v1/similarweb/websites/visits"`. `SIMILARWEB_OPERATIONS` exports the immutable allowlist:

```text
keywords/suggestions
keywords/websites
websites/backlinks
websites/branded-keywords
websites/channels
websites/devices
websites/engagement
websites/geography
websites/history/bounce-rate
websites/history/pages-per-visit
websites/history/visit-duration
websites/history/visits
websites/incoming-referrals
websites/keywords
websites/outgoing-traffic
websites/ranks
websites/ranks/category
websites/ranks/country
websites/ranks/global
websites/search-performance
websites/similar-sites
websites/similar-sites/suggestions
websites/social-traffic
websites/traffic-sources
websites/visits
websites/visits/table
websites/visits/trend
```

Use `keys` for endpoints that require a website or keyword value. Other parameters vary by endpoint; retain their exact spelling, including provider-specific capitalization. The SDK does not impose a shared schema or infer pagination from `Records`, `Data`, or another field. Check the endpoint documentation before constructing subsequent pages.

Only worldwide data is supported: send `country=999`. Other valid country values are rewritten to worldwide at the service's upstream boundary; they do not enable country-specific data. Explicit paired dates can be passed as `**{"from": "2026-08-01", "to": "2026-08-31"}`. The SDK preserves date input and does not invent historical range support. An empty or missing result must not be interpreted as zero traffic.

## Twitter Pagination

```python
client.iter_twitter_user_tweets(user_id, max_pages=10, **params)
```

This lazy iterator makes one request per yielded page. `max_pages` must be a positive integer, not a boolean. It follows `meta.next_token` as the next `pagination_token`, stops when no token remains or the page cap is reached, and rejects repeated/invalid cursors. Reaching the cap is a deliberate partial result, not evidence of complete history. `max_results` is a service parameter (1 through 100), distinct from the SDK page cap. Each call can be billed, including GET requests. No background prefetch is performed.

```python
import asyncio
import os
from requestbeam import AsyncRequestBeam

async def main():
    async with AsyncRequestBeam() as client:
        async for page in client.iter_twitter_user_tweets(
            os.environ["TWITTER_USER_ID"], max_pages=3, max_results=10
        ):
            print(page)

asyncio.run(main())
```

## Errors and Billing Boundaries

All runtime SDK exceptions derive from `RequestBeamError`; invalid local inputs use `ValueError`.

| Exception | Useful attributes / meaning |
| --- | --- |
| `APIError` | `status_code`, `code`, `message`, `request_id`, `body`, `retry_after`, `error_type`; service fields remain unchanged |
| `TransportError` | Network failure; the server may already have executed the request |
| `ProtocolError` | Malformed JSON, stream framing/termination, job status, or pagination data |
| `JobFailedError` | `job` retains the full failed/cancelled job response |
| `PollingTimeoutError` | `job_id` can be checked later |

There are no automatic retries, including for HTTP 429/5xx, read timeouts, billed GET endpoints, or generation submissions. `retry_after` is retained for callers to assess; it does not trigger a retry. Inspect account/request status before repeating an operation that may already have been accepted. Server error messages and bodies can contain sensitive input; avoid logging them without review. The SDK does not create, cancel, retry, refund, or download anything beyond the API call explicitly requested by your code.

## Local Verification

Install the development extra and run `python -m pytest`, `python -m ruff check .`, and `python -m build`. The tests use HTTPX mock transports and do not require API keys for real services. They exercise request contracts, authentication boundaries, errors, sync/async lifecycle, SSE, job polling, pagination, and localization. See [design notes](design.md) for the live-verification boundary.
