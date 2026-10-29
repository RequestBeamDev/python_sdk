"""Incremental SSE framing, shared by synchronous and asynchronous clients."""

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SSEEvent:
    data: str
    event: str = "message"
    id: str | None = None

    def json(self) -> Any:
        return json.loads(self.data)


class SSEParser:
    def __init__(self) -> None:
        self.data: list[str] = []
        self.event = "message"
        self.id: str | None = None
        self.first_line = True

    def feed(self, line: str) -> SSEEvent | None:
        if self.first_line:
            line = line.removeprefix("\ufeff")
            self.first_line = False
        if not line:
            event = SSEEvent("\n".join(self.data), self.event, self.id) if self.data else None
            self.data = []
            self.event = "message"
            return event
        if line.startswith(":"):
            return None
        field, _, value = line.partition(":")
        value = value.removeprefix(" ")
        if field == "data":
            self.data.append(value)
        elif field == "event":
            self.event = value or "message"
        elif field == "id" and "\x00" not in value:
            self.id = value
        return None
