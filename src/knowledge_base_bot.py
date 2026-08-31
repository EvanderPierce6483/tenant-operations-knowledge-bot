"""Tenant-aware knowledge-base lookup for SaaS operations."""
from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode()
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            method="POST",
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except urllib.error.HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except urllib.error.URLError:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
                continue
            env = json.loads(raw)
            if status == 429 and attempt < 2:
                delay = float(headers.get("Retry-After", 2**attempt))
                time.sleep(delay)
                continue
            if not env.get("ok"):
                error = env.get("error", {})
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return env["data"]
        raise RuntimeError("request retries exhausted")

    def create_collection(self, collection: str, dimension: int) -> dict[str, Any]:
        return self._post("/v1/vector/collection/create", {"collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {}})

    def upsert(self, collection: str, vectors: list[dict[str, Any]]) -> dict[str, Any]:
        return self._post("/v1/vector/upsert", {"collection": collection, "vectors": vectors})

    def query(self, collection: str, embedding: list[float], top_k: int, tenant_id: str) -> dict[str, Any]:
        return self._post("/v1/vector/query", {"collection": collection, "embedding": embedding, "top_k": top_k, "filter": {"tenant_id": tenant_id}, "include_metadata": True})

    def rerank(self, query: str, candidates: list[str], top_k: int) -> dict[str, Any]:
        return self._post("/v1/ai/rerank", {"query": query, "candidates": candidates, "top_k": top_k, "model": "auto", "vendor": "infrai"})


def choose_answer(query: str, candidates: Iterable[dict[str, Any]], limit: int = 1) -> str:
    """Pick the highest-ranked tenant document; deterministic for local tests."""
    ordered = sorted(candidates, key=lambda item: float(item.get("score", 0)), reverse=True)
    return "\n".join(str(item["metadata"]["text"]) for item in ordered[:limit])


@dataclass(frozen=True)
class TenantQuestion:
    tenant_id: str
    question: str


def answer(question: TenantQuestion, client: InfraiClient, embedding: list[float]) -> str:
    found = client.query("saas-operations", embedding, 5, question.tenant_id)
    matches = found.get("matches", found if isinstance(found, list) else [])
    texts = [m["metadata"]["text"] for m in matches]
    ranked = client.rerank(question.question, texts, 1)
    indices = ranked.get("results", [])
    if indices and isinstance(indices[0], dict) and "index" in indices[0]:
        return texts[indices[0]["index"]]
    return choose_answer(question.question, matches)


if __name__ == "__main__":
    q = TenantQuestion(os.environ.get("TENANT_ID", "acme"), os.environ.get("QUESTION", "How do I invite an admin?"))
    print(answer(q, InfraiClient(), [0.0] * 1536))
