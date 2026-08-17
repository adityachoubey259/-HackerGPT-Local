"""Ollama embedding adapter."""

from __future__ import annotations

import httpx

from backend.rag.checksums import sha256_text
from backend.rag.embeddings.base import EmbeddingProviderError
from backend.rag.models import EmbeddedText


class OllamaEmbeddingProvider:
    provider_id = "ollama"
    local = True

    def __init__(self, base_url: str, model_id: str, *, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.dimension = 0
        self._timeout = timeout

    async def embed_texts(self, texts: list[str]) -> list[EmbeddedText]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            embedded: list[EmbeddedText] = []
            for text in texts:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model_id, "prompt": text},
                )
                if response.status_code >= 400:
                    raise EmbeddingProviderError("Ollama embedding request failed.")
                vector = response.json().get("embedding")
                if not isinstance(vector, list) or not vector:
                    raise EmbeddingProviderError("Ollama returned no embedding vector.")
                float_vector = [float(value) for value in vector]
                self.dimension = len(float_vector)
                embedded.append(
                    EmbeddedText(
                        text=text,
                        checksum=sha256_text(text),
                        vector=float_vector,
                        provider=self.provider_id,
                        model=self.model_id,
                        dimension=len(float_vector),
                    )
                )
            return embedded
