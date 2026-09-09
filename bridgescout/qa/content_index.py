"""In-memory semantic index over library-paper passages.

Powers ``POST /api/ask``: an end user's question is embedded and matched against
paper passages, so an answer is only shown when it is actually grounded in an
uploaded / library paper. Rebuilt in the background whenever the library changes
(admin upload / delete), the same way the cross-domain method index is.

Granularity is per paper: papers whose id is passed in ``sentence_level_ids``
(the bundled samples + admin uploads) are split into sentences for precise
snippets; the rest (the large collected corpus, where all we hold is an abstract)
contribute a single passage each, which keeps the index a few thousand vectors
instead of tens of thousands.

Uses the shared embedder (MiniLM when available, hashing vectoriser otherwise) so
question and passage vectors always live in the same space, and an exact FAISS
inner-product index since the corpus is small.
"""

from __future__ import annotations

import json
from pathlib import Path

from bridgescout.ingestion.preprocessing import Paper, clean_text, split_sentences
from bridgescout.semantic_mapping.embedder import embed_text, embed_texts

# Fragments shorter than this are almost never a useful answer on their own.
_MIN_SNIPPET_CHARS = 25
_PASSAGE_CHARS = 700


class ContentIndex:
    def __init__(self) -> None:
        self.index = None
        self.metadata: list[dict] = []

    def build(self, papers: list[Paper], sentence_level_ids: set[str] | None = None) -> None:
        chunks: list[str] = []
        metadata: list[dict] = []
        for paper in papers:
            meta = {
                "paper_id": paper.id,
                "paper_title": paper.title,
                "domain": paper.domain,
            }
            sentence_level = sentence_level_ids is None or paper.id in sentence_level_ids

            if sentence_level:
                seen: set[str] = set()
                for section in (paper.abstract, paper.limitations_text, paper.method_text):
                    for sentence in split_sentences(section or ""):
                        key = sentence.lower()
                        if len(sentence) < _MIN_SNIPPET_CHARS or key in seen:
                            continue
                        seen.add(key)
                        chunks.append(sentence)
                        metadata.append({**meta, "snippet": sentence})
            else:
                passage = clean_text(paper.abstract or paper.limitations_text or paper.method_text)
                if len(passage) < _MIN_SNIPPET_CHARS:
                    continue
                chunks.append(passage[:_PASSAGE_CHARS])
                metadata.append({**meta, "snippet": passage[:_PASSAGE_CHARS]})

        self.metadata = metadata
        if not chunks:
            self.index = None
            return

        import faiss

        embeddings = embed_texts(chunks).astype("float32")
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)

    def add(self, papers: list[Paper], sentence_level_ids: set[str] | None = None) -> None:
        """Append papers to an already-built index (incremental admin upload)."""
        delta = ContentIndex()
        delta.build(papers, sentence_level_ids=sentence_level_ids)
        if delta.index is None:
            return
        if self.index is None:
            self.index = delta.index
            self.metadata = delta.metadata
            return
        vectors = delta.index.reconstruct_n(0, delta.index.ntotal)
        self.index.add(vectors)
        self.metadata.extend(delta.metadata)

    def size(self) -> int:
        return len(self.metadata)

    def save(self, index_path: Path, metadata_path: Path) -> None:
        import faiss

        index_path.parent.mkdir(parents=True, exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, str(index_path))
        metadata_path.write_text(json.dumps(self.metadata), encoding="utf-8")

    def load(self, index_path: Path, metadata_path: Path) -> None:
        import faiss

        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.index = faiss.read_index(str(index_path)) if index_path.exists() else None

    def search(self, question: str, top_k: int = 5) -> list[tuple[dict, float]]:
        if self.index is None or not self.metadata:
            return []
        query = embed_text(question).astype("float32").reshape(1, -1)
        k = min(top_k, len(self.metadata))
        scores, indices = self.index.search(query, k)
        results: list[tuple[dict, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append((self.metadata[idx], float(score)))
        return results
