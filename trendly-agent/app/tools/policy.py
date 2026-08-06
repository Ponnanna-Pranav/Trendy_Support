"""
Policy grounding tool.

Chunks trendly_policy.md by section (## headers) and does semantic
retrieval with a small local sentence-transformer model (free, no API
cost, runs on CPU). This is the ONLY source of truth the agent is allowed
to use for policy questions — the system prompt forbids answering policy
questions from general knowledge, and every policy claim must trace back
to a chunk returned here.
"""
from __future__ import annotations
import os
import re
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache

import numpy as np

POLICY_PATH = Path(__file__).parent.parent / "data" / "trendly_policy.md"

_MODEL_NAME = "all-MiniLM-L6-v2"


@dataclass
class Chunk:
    id: str
    title: str
    text: str


def _load_chunks() -> list[Chunk]:
    raw = POLICY_PATH.read_text(encoding="utf-8")
    # Split on markdown ## headers, keep the header with its body
    parts = re.split(r"\n(?=## )", raw)
    chunks: list[Chunk] = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part or part.startswith("#") and not part.startswith("##"):
            # top-level title / preamble block — skip if it's just the H1 + notes
            if not part.startswith("##"):
                continue
        title_match = re.match(r"##\s+(.*)", part)
        title = title_match.group(1).strip() if title_match else f"Section {i}"
        chunks.append(Chunk(id=f"policy-{i}", title=title, text=part))
    return chunks


class PolicyIndex:
    """Semantic search via sentence-transformers when the model is
    reachable, falling back to a dependency-light keyword-overlap scorer
    if it can't be downloaded (e.g. no internet to huggingface.co in a
    sandboxed CI env). The fallback is intentionally simple and logged
    loudly rather than silently degrading grounding quality — see README."""

    def __init__(self):
        self.chunks = _load_chunks()
        self.model = None
        self.embeddings = None
        if os.environ.get("POLICY_SEARCH_MODE", "semantic") == "keyword":
            print("[policy] POLICY_SEARCH_MODE=keyword — skipping embedding model load")
            return
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(_MODEL_NAME)
            texts = [c.title + "\n" + c.text for c in self.chunks]
            self.embeddings = self.model.encode(texts, normalize_embeddings=True)
        except Exception as e:  # noqa: BLE001
            print(f"[policy] semantic model unavailable ({e}); using keyword fallback")
            self.model = None      # ensure both are None so search() falls back cleanly
            self.embeddings = None

    def _keyword_search(self, query: str, k: int) -> list[dict]:
        q_terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        scored = []
        for c in self.chunks:
            c_terms = re.findall(r"[a-z0-9]+", (c.title + " " + c.text).lower())
            overlap = sum(1 for t in c_terms if t in q_terms)
            scored.append((overlap, c))
        scored.sort(key=lambda x: -x[0])
        return [
            {"section_id": c.id, "title": c.title, "text": c.text,
             "relevance_score": round(score / max(len(q_terms), 1), 3)}
            for score, c in scored[:k]
        ]

    def search(self, query: str, k: int = 3) -> list[dict]:
        if self.model is None or self.embeddings is None:
            return self._keyword_search(query, k)
        q_emb = self.model.encode([query], normalize_embeddings=True)[0]
        sims = self.embeddings @ q_emb
        top_idx = np.argsort(-sims)[:k]
        results = []
        for idx in top_idx:
            c = self.chunks[idx]
            results.append({
                "section_id": c.id,
                "title": c.title,
                "text": c.text,
                "relevance_score": round(float(sims[idx]), 3),
            })
        return results

    def get_all_titles(self) -> list[str]:
        return [c.title for c in self.chunks]


@lru_cache(maxsize=1)
def get_policy_index() -> PolicyIndex:
    return PolicyIndex()


def search_policy(query: str, k: int = 3) -> dict:
    """Tool entrypoint. Returns grounded policy chunks for a query."""
    index = get_policy_index()
    results = index.search(query, k=k)
    return {
        "query": query,
        "results": results,
        "instructions": (
            "Only use the 'text' fields above to answer policy questions. "
            "If none of these chunks actually answer the question, say you "
            "don't have that policy information rather than guessing."
        ),
    }
