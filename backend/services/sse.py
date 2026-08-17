"""Server-sent event formatting for HackerGPT streaming protocol."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


def sse_event(event: str, data: BaseModel | dict[str, Any]) -> bytes:
    payload = data.model_dump(mode="json") if isinstance(data, BaseModel) else data
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {encoded}\n\n".encode()
