"""Asynchronous counterpart of RequestBeam, with the same native response shapes."""

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

import httpx

from ._common import BaseClient
from ._sse import SSEEvent, SSEParser
from .errors import PollingTimeoutError, ProtocolError, TransportError


class AsyncRequestBeam(BaseClient):
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.requestbeam.com",
        timeout: float = 60.0,
        locale: str = "en",
        http_client: httpx.AsyncClient | None = None,
    ):
        super().__init__(api_key, base_url, timeout, locale)
        self._owns_client = http_client is None
        self._client = http_client if http_client is not None else httpx.AsyncClient()

    async def __aenter__(self) -> "AsyncRequestBeam":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def request(self, method: str, path: str, *, json: Any = None, params: Any = None) -> Any:
        return await self._request(method, path, json=json, params=params, timeout=self.timeout)

    async def _request(
        self, method: str, path: str, *, json: Any = None, params: Any = None, timeout: float
    ) -> Any:
        url = self._url(path)
        try:
            response = await self._client.request(
                method,
                url,
                json=json,
                params=params,
                headers=self._headers,
                timeout=timeout,
                follow_redirects=False,
            )
        except httpx.RequestError:
            raise TransportError(self._message("transport_error")) from None
        try:
            return self._body(response)
        finally:
            await response.aclose()

    async def list_models(self) -> Any:
        return await self.request("GET", "/v1/models")

    async def chat_completions(self, **payload: Any) -> Any:
        return await self.request("POST", "/v1/chat-completions", json=self._non_stream(payload))

    async def responses(self, **payload: Any) -> Any:
        return await self.request("POST", "/openai/responses", json=self._non_stream(payload))

    async def messages(self, **payload: Any) -> Any:
        return await self.request("POST", "/anthropic/v1/messages", json=self._non_stream(payload))

    async def generate_image(self, **payload: Any) -> Any:
        return await self.request(
            "POST", "/openai/v1/images/generations", json=self._non_stream(payload)
        )

    async def generate_video(self, **payload: Any) -> Any:
        return await self.request("POST", "/v1/video/seedance", json=payload)

    async def get_job(self, job_id: str) -> Any:
        return await self.request("GET", "/v1/jobs/" + self._identifier(job_id))

    async def wait_for_job(
        self, job_id: str, *, timeout: float = 600, poll_interval: float = 5
    ) -> Any:
        job_id = self._identifier(job_id)
        timeout = self._positive(timeout, "invalid_timeout")
        poll_interval = self._positive(poll_interval, "invalid_poll_interval")
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise PollingTimeoutError(self._message("poll_timeout"), job_id=job_id)
            try:
                body = await asyncio.wait_for(
                    self._request(
                        "GET", "/v1/jobs/" + job_id, timeout=min(self.timeout, remaining)
                    ),
                    timeout=remaining,
                )
            except asyncio.TimeoutError:
                raise PollingTimeoutError(self._message("poll_timeout"), job_id=job_id) from None
            if time.monotonic() >= deadline:
                raise PollingTimeoutError(self._message("poll_timeout"), job_id=job_id)
            if self._job_state(body):
                return body
            await asyncio.sleep(min(poll_interval, max(0, deadline - time.monotonic())))

    async def similarweb(self, operation: str, **params: Any) -> Any:
        return await self.request("GET", self._similarweb_path(operation), params=params)

    async def twitter_user_by_username(self, username: str, **params: Any) -> Any:
        return await self.request(
            "GET", "/v1/twitter/users", params={**params, "username": username}
        )

    async def twitter_user(self, user_id: str, **params: Any) -> Any:
        return await self.request(
            "GET", "/v1/twitter/users/" + self._identifier(user_id), params=params
        )

    async def twitter_user_tweets(self, user_id: str, **params: Any) -> Any:
        return await self.request(
            "GET", "/v1/twitter/users/" + self._identifier(user_id) + "/tweets", params=params
        )

    async def iter_twitter_user_tweets(
        self, user_id: str, *, max_pages: int = 10, **params: Any
    ) -> AsyncIterator[Any]:
        self._pages(max_pages)
        seen = {params["pagination_token"]} if "pagination_token" in params else set()
        for _ in range(max_pages):
            page = await self.twitter_user_tweets(user_id, **params)
            yield page
            token = self._next_token(page, seen)
            if token is None:
                return
            params["pagination_token"] = token

    @asynccontextmanager
    async def _stream(
        self, path: str, kind: str, payload: dict[str, Any]
    ) -> AsyncIterator[AsyncIterator[SSEEvent]]:
        url = self._url(path)
        try:
            async with self._client.stream(
                "POST",
                url,
                json={**payload, "stream": True},
                headers={**self._headers, "Accept": "text/event-stream"},
                timeout=self.timeout,
                follow_redirects=False,
            ) as response:
                if not response.is_success:
                    await response.aread()
                    self._body(response)
                if "text/event-stream" not in response.headers.get("content-type", "").lower():
                    await response.aread()
                    self._body(response)
                    raise ProtocolError(self._message("invalid_response"))
                yield self._events(response, kind)
        except httpx.RequestError:
            raise TransportError(self._message("transport_error")) from None

    async def _events(self, response: httpx.Response, kind: str) -> AsyncIterator[SSEEvent]:
        parser = SSEParser()
        image_completed = False
        async for line in response.aiter_lines():
            event = parser.feed(line)
            if event is None:
                continue
            terminal = self._stream_event(event, response, kind)
            if kind == "image":
                if event.data == "[DONE]":
                    if not image_completed:
                        raise ProtocolError(self._message("stream_error"))
                else:
                    image_completed = image_completed or terminal
                    terminal = False
            if event.data != "[DONE]":
                yield event
            if terminal:
                return
        raise ProtocolError(self._message("stream_error"))

    def stream_chat_completions(
        self, **payload: Any
    ) -> AbstractAsyncContextManager[AsyncIterator[SSEEvent]]:
        return self._stream("/v1/chat-completions", "chat", payload)

    def stream_responses(self, **payload: Any) -> AbstractAsyncContextManager[AsyncIterator[SSEEvent]]:
        return self._stream("/openai/responses", "responses", payload)

    def stream_messages(self, **payload: Any) -> AbstractAsyncContextManager[AsyncIterator[SSEEvent]]:
        return self._stream("/anthropic/v1/messages", "messages", payload)

    def stream_image(self, **payload: Any) -> AbstractAsyncContextManager[AsyncIterator[SSEEvent]]:
        return self._stream("/openai/v1/images/generations", "image", payload)
