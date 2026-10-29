import json

import httpx
import pytest

from requestbeam import (
    SIMILARWEB_OPERATIONS,
    APIError,
    AsyncRequestBeam,
    JobFailedError,
    PollingTimeoutError,
    ProtocolError,
    RequestBeam,
    TransportError,
)


def client_for(handler, **kwargs):
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, follow_redirects=True)
    return RequestBeam("secret-test-key", http_client=http, **kwargs), http


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("chat_completions", "/v1/chat-completions"),
        ("responses", "/openai/responses"),
        ("messages", "/anthropic/v1/messages"),
        ("generate_image", "/openai/v1/images/generations"),
        ("generate_video", "/v1/video/seedance"),
    ],
)
def test_payload_and_routes(method, path):
    observed = []

    def handler(request):
        observed.append(request)
        return httpx.Response(200, json={"native": [1, 2], "future_field": "preserved"})

    client, http = client_for(handler)
    with http, client:
        result = getattr(client, method)(model="actual-model", prompt="你好", unknown={"a": 1})
        assert result == {"native": [1, 2], "future_field": "preserved"}
    assert len(observed) == 1
    assert observed[0].url.path == path
    assert observed[0].headers["authorization"] == "Bearer secret-test-key"
    assert json.loads(observed[0].content)["prompt"] == "你好"


@pytest.mark.parametrize(
    "path",
    [
        "https://evil.example/a",
        "//evil.example/a",
        "/x/../a",
        "/x/%2e%2e/a",
        "/x/%252e%252e/a",
        "/x\\evil",
        "/x?q=secret",
        "/x#fragment",
        "/x//y",
        "/x\na",
    ],
)
def test_untrusted_paths_rejected(path):
    client, http = client_for(lambda r: pytest.fail("must not send"))
    with http, client, pytest.raises(ValueError):
        client.request("GET", path)


@pytest.mark.parametrize(
    "base",
    [
        "http://api.requestbeam.com",
        "https://user:password@api.requestbeam.com",
        "https://api.requestbeam.com/v1",
        "https://api.requestbeam.com?key=secret",
        "https://api.requestbeam.com#fragment",
    ],
)
def test_base_url_validation(base):
    with pytest.raises(ValueError):
        RequestBeam("key", base_url=base)


def test_redirect_is_not_followed_with_injected_client():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "https://evil.example/"})

    client, http = client_for(handler)
    with http, client, pytest.raises(APIError) as caught:
        client.list_models()
    assert caught.value.status_code == 302
    assert len(requests) == 1


def test_error_metadata_and_no_retry():
    requests = []
    body = {"success": False, "error": {"code": 30000, "message": "original"}, "requestId": "req-1"}

    def handler(request):
        requests.append(request)
        return httpx.Response(429, json=body, headers={"Retry-After": "10"})

    client, http = client_for(handler)
    with http, client, pytest.raises(APIError) as caught:
        client.generate_video(prompt="hello")
    error = caught.value
    assert (error.status_code, error.code, error.request_id, error.retry_after) == (
        429,
        30000,
        "req-1",
        "10",
    )
    assert error.body == body and str(error) == "original"
    assert len(requests) == 1


def test_flat_error_and_invalid_json():
    client, http = client_for(
        lambda r: httpx.Response(400, json={"code": "bad", "message": "native"})
    )
    with http, client, pytest.raises(APIError) as caught:
        client.list_models()
    assert caught.value.code == "bad" and str(caught.value) == "native"
    client, http = client_for(lambda r: httpx.Response(200, text="not json"))
    with http, client, pytest.raises(ProtocolError):
        client.list_models()


def test_transport_error_does_not_include_key():
    def handler(request):
        raise httpx.ConnectError("secret-test-key", request=request)

    client, http = client_for(handler)
    with http, client, pytest.raises(TransportError) as caught:
        client.list_models()
    assert "secret-test-key" not in str(caught.value)
    assert caught.value.__suppress_context__


def test_external_client_stays_open():
    client, http = client_for(lambda r: httpx.Response(200, json={}))
    with client:
        client.list_models()
    assert not http.is_closed
    http.close()


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True])
def test_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        RequestBeam("key", timeout=timeout)


def test_200_platform_error_remains_error():
    client, http = client_for(
        lambda r: httpx.Response(
            200, json={"success": False, "error": {"code": 20001, "message": "denied"}}
        )
    )
    with http, client, pytest.raises(APIError) as caught:
        client.list_models()
    assert caught.value.status_code == 200 and caught.value.code == 20001


def test_user_lookup_routes_and_query():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"data": {"id": "123"}})

    client, http = client_for(handler)
    with http, client:
        client.twitter_user_by_username("@alice", **{"user.fields": "public_metrics"})
        client.twitter_user("123")
    assert requests[0].url.path == "/v1/twitter/users"
    assert requests[0].url.params["username"] == "@alice"
    assert requests[0].url.params["user.fields"] == "public_metrics"
    assert requests[1].url.path == "/v1/twitter/users/123"


def test_polling_statuses_and_bigint(monkeypatch):
    monkeypatch.setattr("requestbeam.client.time.sleep", lambda n: None)
    statuses = iter(["PENDING", "CONNECT", "PROCESSING", "COMPLETED"])
    paths = []

    def handler(request):
        paths.append(request.url.path)
        return httpx.Response(
            200,
            json={"success": True, "data": {"id": "999999999999999999", "status": next(statuses)}},
        )

    client, http = client_for(handler)
    with http, client:
        assert client.wait_for_job("999999999999999999")["data"]["status"] == "COMPLETED"
        with pytest.raises(ValueError):
            client.get_job(999999999999999999)
    assert paths == ["/v1/jobs/999999999999999999"] * 4


@pytest.mark.parametrize("status", ["FAILED", "CANCELLED", "UNKNOWN"])
def test_polling_failure(status):
    client, http = client_for(lambda r: httpx.Response(200, json={"data": {"status": status}}))
    error = ProtocolError if status == "UNKNOWN" else JobFailedError
    with http, client, pytest.raises(error):
        client.wait_for_job("123")


def test_polling_timeout_bounds_request(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("requestbeam.client.time.monotonic", lambda: clock[0])
    monkeypatch.setattr(
        "requestbeam.client.time.sleep", lambda n: clock.__setitem__(0, clock[0] + n)
    )
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"data": {"status": "PENDING"}})

    client, http = client_for(handler)
    with http, client, pytest.raises(PollingTimeoutError):
        client.wait_for_job("123", timeout=2, poll_interval=5)
    assert len(calls) == 1
    assert calls[0].extensions["timeout"]["read"] == 2


def test_similarweb_preserves_case_dates_and_native_body():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"Records": [], "TotalCount": 0})

    client, http = client_for(handler)
    with http, client:
        result = client.similarweb(
            "websites/backlinks",
            keys="example.com",
            Page=2,
            country=999,
            **{"from": "2026-01-01", "to": "2026-03-01"},
        )
        assert result == {"Records": [], "TotalCount": 0}
        with pytest.raises(ValueError):
            client.similarweb("../../evil")
    assert requests[0].url.params["Page"] == "2"
    assert requests[0].url.params["from"] == "2026-01-01"
    assert "latest" not in requests[0].url.params
    assert len(SIMILARWEB_OPERATIONS) == 27


def test_twitter_pagination_bound_and_token():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"data": [], "meta": {"next_token": f"t{len(calls)}"}})

    client, http = client_for(handler)
    with http, client:
        pages = list(client.iter_twitter_user_tweets("123", max_pages=2, max_results=5))
    assert len(pages) == len(calls) == 2
    assert calls[1].url.params["pagination_token"] == "t1"


def test_twitter_repeated_token_rejected():
    client, http = client_for(lambda r: httpx.Response(200, json={"meta": {"next_token": "same"}}))
    with http, client, pytest.raises(ProtocolError):
        list(client.iter_twitter_user_tweets("123", max_pages=10))


def test_sse_multiline_bom_comments_and_done():
    content = '\ufeff: keepalive\r\nid: evt1\r\nevent: chunk\r\ndata: {"a":\r\ndata: 1}\r\n\r\ndata: [DONE]\r\n\r\n'
    response = httpx.Response(200, text=content, headers={"Content-Type": "text/event-stream"})
    client, http = client_for(lambda r: response)
    with http, client, client.stream_chat_completions(model="test") as events:
        result = list(events)
    assert len(result) == 1
    assert (result[0].event, result[0].id, result[0].json()) == ("chunk", "evt1", {"a": 1})
    assert response.is_closed


@pytest.mark.parametrize(
    ("method", "content"),
    [
        ("stream_responses", 'event: response.completed\ndata: {"type":"response.completed"}\n\n'),
        ("stream_messages", 'event: message_stop\ndata: {"type":"message_stop"}\n\n'),
        (
            "stream_image",
            'event: image_generation.completed\ndata: {"type":"image_generation.completed"}\n\ndata: [DONE]\n\n',
        ),
    ],
)
def test_protocol_specific_stream_end(method, content):
    client, http = client_for(
        lambda r: httpx.Response(200, text=content, headers={"content-type": "text/event-stream"})
    )
    with http, client, getattr(client, method)() as events:
        assert len(list(events)) == 1


@pytest.mark.parametrize("content", ["", 'data: {"partial":true}\n\n'])
def test_stream_truncation_raises(content):
    client, http = client_for(
        lambda r: httpx.Response(200, text=content, headers={"content-type": "text/event-stream"})
    )
    with http, client, client.stream_chat_completions() as events, pytest.raises(ProtocolError):
        list(events)


def test_stream_error_preserves_body():
    body = {"error": {"message": "upstream failed", "code": "failed"}, "request_id": "r1"}
    client, http = client_for(
        lambda r: httpx.Response(
            200,
            text=f"event: error\ndata: {json.dumps(body)}\n\n",
            headers={"content-type": "text/event-stream"},
        )
    )
    with http, client, client.stream_messages() as events, pytest.raises(APIError) as caught:
        list(events)
    assert caught.value.body == body and caught.value.request_id == "r1"


@pytest.mark.parametrize(
    "content",
    [
        "data: [DONE]\n\n",
        'event: image_generation.completed\ndata: {"type":"image_generation.completed"}\n\n',
    ],
)
def test_image_requires_completed_and_done(content):
    client, http = client_for(
        lambda r: httpx.Response(200, text=content, headers={"content-type": "text/event-stream"})
    )
    with http, client, client.stream_image() as events, pytest.raises(ProtocolError):
        list(events)


def test_nested_response_error_and_claude_type():
    body = {
        "type": "response.failed",
        "response": {"error": {"code": "failed", "message": "original"}},
    }
    client, http = client_for(
        lambda r: httpx.Response(
            200, text=f"data: {json.dumps(body)}\n\n", headers={"content-type": "text/event-stream"}
        )
    )
    with http, client, client.stream_responses() as events, pytest.raises(APIError) as caught:
        list(events)
    assert caught.value.code == "failed" and str(caught.value) == "original"
    client, http = client_for(
        lambda r: httpx.Response(
            400, json={"error": {"type": "invalid_request_error", "message": "original"}}
        )
    )
    with http, client, pytest.raises(APIError) as caught:
        client.messages()
    assert caught.value.code is None and caught.value.error_type == "invalid_request_error"


def test_non_stream_rejects_stream_before_sending():
    client, http = client_for(lambda r: pytest.fail("must not make a paid request"))
    with http, client, pytest.raises(ValueError):
        client.chat_completions(stream=True)


async def test_async_calls_pagination_and_ownership():
    calls = []

    async def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"data": [], "meta": {}})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as http:
        async with AsyncRequestBeam("key", http_client=http) as client:
            assert await client.list_models() == {"data": [], "meta": {}}
            assert len([p async for p in client.iter_twitter_user_tweets("123")]) == 1
        assert not http.is_closed
    assert len(calls) == 2


async def test_async_poll_and_stream():
    async def handler(request):
        if request.url.path.startswith("/v1/jobs/"):
            return httpx.Response(200, json={"data": {"status": "COMPLETED"}})
        return httpx.Response(
            200,
            text='data: {"ok":true}\n\ndata: [DONE]\n\n',
            headers={"content-type": "text/event-stream"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with AsyncRequestBeam("key", http_client=http) as client:
            assert (await client.wait_for_job("123"))["data"]["status"] == "COMPLETED"
            async with client.stream_chat_completions() as events:
                assert [e.json() async for e in events] == [{"ok": True}]


async def test_async_poll_deadline():
    import asyncio

    async def handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json={"data": {"status": "COMPLETED"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with AsyncRequestBeam("key", http_client=http) as client:
            with pytest.raises(PollingTimeoutError):
                await client.wait_for_job("123", timeout=0.01)


async def test_async_redirect_and_stream_failures():
    requests = []

    async def handler(request):
        requests.append(request)
        if request.url.path == "/v1/models":
            return httpx.Response(307, headers={"Location": "https://evil.example/"})
        return httpx.Response(
            200,
            text='data: {"partial":true}\n\n',
            headers={"content-type": "text/event-stream"},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as http:
        async with AsyncRequestBeam("key", http_client=http) as client:
            with pytest.raises(APIError):
                await client.list_models()
            async with client.stream_chat_completions() as events:
                with pytest.raises(ProtocolError):
                    _ = [event async for event in events]
            with pytest.raises(ValueError):
                await client.chat_completions(stream=True)
    assert len(requests) == 2


def test_stream_early_exit_closes_response():
    response = httpx.Response(
        200,
        text='data: {"partial":true}\n\ndata: [DONE]\n\n',
        headers={"content-type": "text/event-stream"},
    )
    client, http = client_for(lambda r: response)
    with http, client:
        with client.stream_chat_completions() as events:
            assert next(events).json() == {"partial": True}
        assert response.is_closed
