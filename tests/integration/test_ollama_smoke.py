from __future__ import annotations

import os

import httpx
import pytest


@pytest.mark.skipif(
    os.getenv("HACKERGPT_RUN_OLLAMA_INTEGRATION") != "1",
    reason="real Ollama smoke test is opt-in",
)
async def test_real_ollama_smoke() -> None:
    async with httpx.AsyncClient(base_url="http://127.0.0.1:11434", timeout=15) as client:
        version = await client.get("/api/version")
        version.raise_for_status()
        tags = await client.get("/api/tags")
        tags.raise_for_status()
        models = tags.json().get("models", [])
        names = [item.get("name") for item in models if isinstance(item, dict)]
        if "qwen3:8b" not in names:
            pytest.skip("qwen3:8b is not installed; no model download was attempted")
        generated = await client.post(
            "/api/generate",
            json={"model": "qwen3:8b", "prompt": "Reply with one short word.", "stream": False},
        )
        generated.raise_for_status()
        assert isinstance(generated.json().get("response"), str)
