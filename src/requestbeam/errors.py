"""Stable exception types; service messages and bodies remain untranslated."""

from typing import Any


class RequestBeamError(Exception):
    """Base class for SDK errors."""


class APIError(RequestBeamError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        code: Any = None,
        request_id: str | None = None,
        body: Any = None,
        retry_after: str | None = None,
        error_type: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.request_id = request_id
        self.body = body
        self.retry_after = retry_after
        self.error_type = error_type


class TransportError(RequestBeamError):
    """Network failure; requests are never automatically retried."""


class ProtocolError(RequestBeamError):
    """An unexpected response cannot be interpreted safely."""


class JobFailedError(RequestBeamError):
    def __init__(self, message: str, *, job: dict[str, Any]):
        super().__init__(message)
        self.job = job


class PollingTimeoutError(RequestBeamError):
    def __init__(self, message: str, *, job_id: str):
        super().__init__(message)
        self.job_id = job_id
