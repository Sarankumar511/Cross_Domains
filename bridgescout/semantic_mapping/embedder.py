"""Text embeddings for the cross-domain search index.

Uses ``sentence-transformers`` (MiniLM) when it is installed — the full-quality
path for local development. When it is not (e.g. the slim Cloud Foundry droplet,
which omits torch), it falls back to a deterministic scikit-learn
``HashingVectorizer``: lower quality, but no model download and a ~10 MB
footprint, so the pipeline still runs end to end.

Both paths return L2-normalised float32 vectors, so cosine similarity is just a
dot product and FAISS ``IndexFlatIP`` works unchanged. The index is rebuilt in
the same process that queries it, so the two encoders never mix.
"""

from __future__ import annotations

import numpy as np

from bridgescout.config import EMBEDDING_MODEL_NAME

_HASHING_DIM = 512

_encoder: tuple[str, object] | None = None


def _load_encoder() -> tuple[str, object]:
    global _encoder
    if _encoder is not None:
        return _encoder
    try:
        from sentence_transformers import SentenceTransformer

        _encoder = ("st", SentenceTransformer(EMBEDDING_MODEL_NAME))
    except Exception:  # ImportError, or torch/backend load failure
        from sklearn.feature_extraction.text import HashingVectorizer

        _encoder = (
            "hashing",
            HashingVectorizer(n_features=_HASHING_DIM, alternate_sign=False, norm="l2"),
        )
    return _encoder


def embedding_backend() -> str:
    """'st' (sentence-transformers) or 'hashing' (sklearn fallback)."""
    return _load_encoder()[0]


def embed_texts(texts: list[str]) -> np.ndarray:
    kind, encoder = _load_encoder()
    if kind == "st":
        return encoder.encode(texts, normalize_embeddings=True, convert_to_numpy=True)

    matrix = encoder.transform(texts).toarray().astype("float32")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def embed_text(text: str) -> np.ndarray:
    return embed_texts([text])[0]
