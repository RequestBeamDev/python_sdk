import math
import os
from typing import Any
from urllib.parse import unquote, urlsplit

import httpx

from ._sse import SSEEvent
from .errors import APIError, JobFailedError, ProtocolError
from .i18n import normalize_locale, translate

SIMILARWEB_OPERATIONS = frozenset(
    {
        "keywords/suggestions",
        "websites/backlinks",
        "websites/keywords",
        "keywords/websites",
        "websites/traffic-sources",
        "websites/outgoing-traffic",
        "websites/incoming-referrals",
        "websites/branded-keywords",
        "websites/geography",
        "websites/devices",
        "websites/search-performance",
        "websites/social-traffic",
        "websites/engagement",
        "websites/visits",
        "websites/visits/table",
        "websites/visits/trend",
        "websites/ranks",
        "websites/ranks/country",
        "websites/ranks/global",
        "websites/ranks/category",
        "websites/channels",
        "websites/similar-sites",
        "websites/similar-sites/suggestions",
        "websites/history/visits",
        "websites/history/bounce-rate",
        "websites/history/visit-duration",
        "websites/history/pages-per-visit",
    }
)


class BaseClient:
    def __init__(self, api_key: str | None, base_url: str, timeout: float, locale: str):
        self.locale = normalize_locale(locale)
        key = api_key if api_key is not None else os.environ.get("REQUESTBEAM_API_KEY", "")
        if not isinstance(key, str) or not key.strip() or any(c in key for c in "\r\n"):
            raise ValueError(self._message("missing_api_key"))
        parsed = urlsplit(base_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError(self._message("invalid_base_url"))
        self.base_url = base_url.rstrip("/")
        self.timeout = self._positive(timeout, "invalid_timeout")
        self._headers = {"Authorization": f"Bearer {key}", "User-Agent": "requestbeam-python/0.1.0"}

    def _message(self, key: str) -> str:
        return translate(self.locale, key)

    def _positive(self, value: float, key: str) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(self._message(key))
        return float(value)

    def _url(self, path: str) -> str:
        if not isinstance(path, str):
            raise ValueError(self._message("invalid_path"))
        decoded = path
        for _ in range(4):
            expanded = unquote(decoded)
            if expanded == decoded:
                break
            decoded = expanded
        parsed = urlsplit(decoded)
        if (
            not decoded.startswith("/")
            or "//" in decoded
            or "\\" in decoded
            or parsed.scheme
            or parsed.netloc
            or parsed.query
            or parsed.fragment
            or any(segment in (".", "..") for segment in decoded.split("/"))
            or any(ord(c) <= 32 or ord(c) == 127 for c in decoded)
            or "%" in decoded
        ):
            raise ValueError(self._message("invalid_path"))
        return self.base_url + path

    def _identifier(self, value: str) -> str:
        if not isinstance(value, str) or not value or not value.isascii() or not value.isdigit():
            raise ValueError(self._message("invalid_job_id"))
        return value

    def _similarweb_path(self, operation: str) -> str:
        prefix = "/v1/similarweb/"
        if isinstance(operation, str):
            operation = operation.removeprefix(prefix)
        if operation not in SIMILARWEB_OPERATIONS:
            raise ValueError(self._message("invalid_path"))
        return prefix + operation

    def _body(self, response: httpx.Response) -> Any:
        try:
            body = response.json()
        except ValueError:
            if response.is_success:
                raise ProtocolError(self._message("invalid_response")) from None
            body = None
        if not response.is_success or (
            isinstance(body, dict)
            and (body.get("success") is False or body.get("error") is not None)
        ):
            self._api_error(response, body)
        return body

    def _api_error(self, response: httpx.Response, body: Any) -> None:
        error = body.get("error") if isinstance(body, dict) else None
        if error is None and isinstance(body, dict) and isinstance(body.get("response"), dict):
            error = body["response"].get("error")
        if error is None and isinstance(body, dict):
            error = body
        code = error.get("code") if isinstance(error, dict) else None
        error_type = error.get("type") if isinstance(error, dict) else None
        message = error.get("message") if isinstance(error, dict) else None
        request_id = (
            (body.get("requestId") or body.get("request_id")) if isinstance(body, dict) else None
        )
        raise APIError(
            message if isinstance(message, str) else self._message("invalid_response"),
            status_code=response.status_code,
            code=code,
            request_id=request_id or response.headers.get("x-request-id"),
            body=body,
            retry_after=response.headers.get("retry-after"),
            error_type=error_type,
        )

    def _stream_event(self, event: SSEEvent, response: httpx.Response, kind: str) -> bool:
        if event.data == "[DONE]":
            return kind in ("chat", "image")
        try:
            body = event.json()
        except ValueError:
            raise ProtocolError(self._message("invalid_response")) from None
        if event.event in ("error", "response.error") or (
            isinstance(body, dict)
            and (body.get("error") is not None or body.get("type") in ("error", "response.error"))
        ):
            self._api_error(response, body)
        event_type = body.get("type", event.event) if isinstance(body, dict) else event.event
        if kind == "responses":
            if event_type == "response.failed":
                self._api_error(response, body)
            return event_type in ("response.completed", "response.incomplete")
        if kind == "messages":
            return event_type == "message_stop"
        return kind == "image" and event_type == "image_generation.completed"

    def _non_stream(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("stream"):
            raise ValueError(self._message("invalid_stream"))
        return payload

    def _job_state(self, body: Any) -> bool:
        job = body.get("data") if isinstance(body, dict) else None
        if not isinstance(job, dict):
            raise ProtocolError(self._message("invalid_response"))
        status = job.get("status")
        if status == "COMPLETED":
            return True
        if status in ("FAILED", "CANCELLED"):
            raise JobFailedError(self._message("job_failed"), job=job)
        if status not in ("PENDING", "CONNECT", "PROCESSING"):
            raise ProtocolError(self._message("invalid_response"))
        return False

    def _pages(self, max_pages: int) -> None:
        if isinstance(max_pages, bool) or not isinstance(max_pages, int) or max_pages < 1:
            raise ValueError(self._message("invalid_pagination"))

    def _next_token(self, body: Any, seen: set[str]) -> str | None:
        if not isinstance(body, dict) or not isinstance(body.get("meta", {}), dict):
            raise ProtocolError(self._message("invalid_response"))
        token = body.get("meta", {}).get("next_token")
        if token is None or token == "":
            return None
        if not isinstance(token, str) or token in seen:
            raise ProtocolError(self._message("invalid_pagination"))
        seen.add(token)
        return token
