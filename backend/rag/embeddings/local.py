"""Deterministic local embedding provider.

This is a dependency-light local default for development and tests. It is not a
large semantic model, but it preserves the provider abstraction and never sends
document text off-machine.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

from backend.rag.checksums import sha256_text
from backend.rag.models import EmbeddedText


class LocalHashEmbeddingProvider:
    provider_id = "local"
    model_id = "hash-embedding-v1"
    dimension = 128
    local = True

    async def embed_texts(self, texts: list[str]) -> list[EmbeddedText]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> EmbeddedText:
        vector = [0.0] * self.dimension
        tokens = tokenize(text)
        for token, count in Counter(tokens).items():
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        normalized = [round(value / norm, 8) for value in vector]
        return EmbeddedText(
            text=text,
            checksum=sha256_text(text),
            vector=normalized,
            provider=self.provider_id,
            model=self.model_id,
            dimension=self.dimension,
        )


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]{2,}", text.lower())
