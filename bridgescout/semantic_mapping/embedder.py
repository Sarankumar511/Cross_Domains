from __future__ import annotations

import numpy as np

from bridgescout.config import EMBEDDING_MODEL_NAME

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)


def embed_text(text: str) -> np.ndarray:
    return embed_texts([text])[0]
