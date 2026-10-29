# RequestBeam Python SDK

[English](README.md) | [Deutsch](docs/README.de.md) | [Türkçe](docs/README.tr.md) | [Italiano](docs/README.it.md) | [Español](docs/README.es.md) | [Français](docs/README.fr.md) | [Português](docs/README.pt-BR.md) | [日本語](docs/README.ja.md) | [한국어](docs/README.ko.md) | [简体中文](docs/README.zh-CN.md) | [繁體中文](docs/README.zh-TW.md) | [Русский](docs/README.ru.md)

A synchronous and asynchronous Python client for RequestBeam text, image, video, Similarweb, and Twitter APIs. It preserves native response objects and provides bounded job polling, SSE events, typed errors, and local messages in all 12 public project languages.

## Installation

Install from this repository with Python 3.10 or newer. This version has not been published to PyPI; do not assume that a package with the same name there is this SDK.

```bash
git clone https://github.com/RequestBeamDev/python_sdk.git
cd python_sdk
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## Authentication and language

Keep the API key in your local or server environment. The default API root is `https://api.requestbeam.com`; do not append `/v1`. `locale` changes SDK-generated errors only. It never translates prompts, API fields, model IDs, or the server's original error message. Codes and aliases include `en`, `de`, `tr`, `it`, `es`, `fr`, `pt-BR` / `pt`, `ja`, `ko`, `zh-CN` / `cn` / `zh`, `zh-TW` / `tw`, and `ru`; underscores and case are normalized. Unsupported languages raise `ValueError`.

Custom `base_url` values must be HTTPS origins with no credentials, path, query, or fragment. Job and Twitter user IDs must be nonempty strings of ASCII digits.

```bash
export REQUESTBEAM_API_KEY="YOUR_API_KEY"
export REQUESTBEAM_TEXT_MODEL="YOUR_TEXT_MODEL_ID"
```

## Text and async

Use `list_models()` to inspect the current model catalog, then set `REQUESTBEAM_TEXT_MODEL` to an appropriate model ID. Catalog presence alone does not guarantee live provider availability. Responses are ordinary dictionaries. Context managers close SDK-owned connections; caller-supplied HTTP clients remain caller-owned.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="en") as client:
    models = client.list_models()
    result = client.chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    )
    print(result)
```

```python
import asyncio
import os
from requestbeam import AsyncRequestBeam

async def main():
    async with AsyncRequestBeam(locale="en") as client:
        result = await client.chat_completions(
            model=os.environ["REQUESTBEAM_TEXT_MODEL"],
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(result)

asyncio.run(main())
```

## Streaming

Use the stream context manager even if you stop reading early. Each `SSEEvent` exposes `event`, `data`, `id`, and `json()`. Event payloads differ by protocol; do not assume that every event contains text. The iterator consumes the `[DONE]` sentinel. Stream failures raise an SDK exception.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="en") as client:
    with client.stream_chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    ) as events:
        for event in events:
            print(event.event, event.data)
```

## Images and video

Image generation returns a result directly as JSON or SSE; it does not use Jobs. Video submission returns `data.jobId`, which is a string. `wait_for_job()` returns the complete job response after `COMPLETED`, and raises `JobFailedError` for `FAILED` or `CANCELLED`. A wait timeout stops local waiting only; it does not cancel the upstream job or its charges.

Synchronous polling applies the remaining budget to each HTTP timeout phase and checks the deadline between requests. It cannot forcibly interrupt an in-flight synchronous response, so total wall time can exceed the polling budget. Async polling also enforces the remaining request budget with an asynchronous deadline. Use `stream_*` methods for streams; non-stream methods reject `stream=True` before sending.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="en") as client:
    image = client.generate_image(
        model="gpt-image-2", prompt="A red bicycle beside a white wall"
    )
    submission = client.generate_video(
        model="seedance-2.0",
        prompt="A quiet city street at dawn, slow forward camera movement.",
        duration=5,
        resolution="720p",
        aspectRatio="16:9",
        generateAudio=False,
    )
    job = client.wait_for_job(
        submission["data"]["jobId"], timeout=600, poll_interval=5
    )
    print(job["data"]["outputResult"])
```

## Similarweb and Twitter

Similarweb has 27 allowed operations and preserves each endpoint's native response fields. Only worldwide data (`country=999`) is supported. Other valid country values are normalized by the service to worldwide data, not country-specific results. Supply an explicit `from` / `to` pair with `**{"from": ..., "to": ...}` when needed; these values are not rewritten by the SDK. Empty results do not mean zero traffic.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="en") as client:
    traffic = client.similarweb(
        "websites/visits", keys="example.com", country=999
    )
    print(traffic)
```

Twitter helpers cover username lookup, ID lookup, and user timelines. The page iterator yields complete native pages, follows `meta.next_token`, has an explicit page cap, and rejects repeated cursors. It does not merge pages or promise to retrieve an entire timeline. Data GET requests can be billed; each fetched page is a separate request.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="en") as client:
    user = client.twitter_user_by_username("TwitterDev")
    user_id = user["data"]["id"]
    for page in client.iter_twitter_user_tweets(
        user_id, max_pages=3, max_results=10
    ):
        print(page)
```

## Errors and local files

`APIError` preserves the HTTP status, service code, original message, request ID, and response body. `TransportError`, `ProtocolError`, `PollingTimeoutError`, and `JobFailedError` distinguish connection, protocol, wait, and job failures. Do not publish raw responses or exception bodies without checking them for private data. Keep keys out of source control, browser code, screenshots, and logs.

```python
from requestbeam import APIError, RequestBeam

try:
    with RequestBeam(locale="en") as client:
        client.get_job("123456789012345678")
except APIError as exc:
    print(exc.status_code, exc.code, exc.request_id)
```

Save results locally only after checking the returned structure. The SDK does not automatically download remote assets. Output URLs may expire; retrieve trusted results promptly with a separate, unauthenticated HTTP client so the RequestBeam key is never sent to an asset host.

```python
import json
from pathlib import Path

# result: a response obtained from one of the calls above.
Path("result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

## Verification and limits

The automated suite uses mock transports and makes no paid API calls. As of 2026-10-29, this repository has not been validated by live paid generation, deployed, or published to PyPI. No request is automatically retried, including billed GET requests and generation submissions. Unknown parameters and server response shapes are not silently normalized. Check model-specific limits in the RequestBeam documentation before running examples.

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m build
```

See [API reference](docs/api-reference.md) for method signatures and protocol differences, and [design notes](docs/design.md) for scope and verification boundaries.

[RequestBeam](https://requestbeam.com/en) · [API](https://requestbeam.com/en/docs/api-reference/models)
