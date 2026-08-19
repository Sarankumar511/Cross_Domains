from __future__ import annotations

import json

import numpy as np

from bridgescout.config import FAISS_INDEX_PATH, INDEX_DIR, INDEX_METADATA_PATH
from bridgescout.ingestion.preprocessing import Paper
from bridgescout.semantic_mapping.embedder import embed_texts


class VectorStore:
    def __init__(self) -> None:
        self.index = None
        self.metadata: list[dict] = []

    def build(self, papers: list[Paper]) -> None:
        import faiss

        candidates = [p for p in papers if p.method_text]
        texts = [p.method_text for p in candidates]
        embeddings = embed_texts(texts).astype("float32")
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)
        self.metadata = [
            {
                "paper_id": p.id,
                "title": p.title,
                "domain": p.domain,
                "method_text": p.method_text,
            }
            for p in candidates
        ]

    def save(self) -> None:
        import faiss

        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(FAISS_INDEX_PATH))
        with open(INDEX_METADATA_PATH, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

    def load(self) -> None:
        import faiss

        self.index = faiss.read_index(str(FAISS_INDEX_PATH))
        with open(INDEX_METADATA_PATH, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

    def search(self, query_embedding: np.ndarray, top_k: int) -> list[tuple[dict, float]]:
        query = query_embedding.astype("float32").reshape(1, -1)
        k = min(top_k, len(self.metadata))
        if k == 0:
            return []
        scores, indices = self.index.search(query, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append((self.metadata[idx], float(score)))
        return results
