from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()


def _require_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set (check your .env or export it)")
    return api_key


def _to_float_list(vec: Any) -> list[float]:
    """
    Normalize embedding outputs to a JSON-serializable flat list[float].

    Handles:
      - numpy arrays (1D or 2D like (1,dim))
      - lists/tuples
      - nested single-item wrappers ([[...]] or [array([...])])
    """
    # Unwrap single-item list/tuple wrappers repeatedly
    while isinstance(vec, (list, tuple)) and len(vec) == 1:
        vec = vec[0]

    # numpy / array-like -> python
    if hasattr(vec, "tolist"):
        vec = vec.tolist()

    # After tolist(), we may have [[...]] -> unwrap once
    if isinstance(vec, list) and len(vec) == 1 and isinstance(vec[0], list):
        vec = vec[0]

    # Ensure it's a flat list
    if not isinstance(vec, list):
        try:
            vec = list(vec)  # type: ignore[arg-type]
        except TypeError as e:
            raise TypeError(f"Unsupported embedding type for serialization: {type(vec)}") from e

    if vec and isinstance(vec[0], list):
        raise TypeError(
            f"Embedding still nested after normalization (example inner type={type(vec[0])})."
        )

    return [float(x) for x in vec]


def get_embedding_function(*, embedding_model: str = "text-embedding-3-small") -> OpenAIEmbeddingFunction:
    """
    Public factory for the embedding function (stable API surface for the rest of the codebase).
    """
    api_key = _require_api_key()
    return OpenAIEmbeddingFunction(api_key=api_key, model_name=embedding_model)


def embed_texts(
    texts: list[str],
    *,
    embedding_model: str = "text-embedding-3-small",
) -> list[list[float]]:
    """
    Returns embeddings for a batch of texts as list[list[float]].

    This avoids relying on Chroma internal/private members.
    """
    if not texts:
        return []

    ef = get_embedding_function(embedding_model=embedding_model)

    # OpenAIEmbeddingFunction is callable; it returns embeddings for input batch.
    raw = ef(texts)

    # Normalize each embedding to list[float]
    return [_to_float_list(e) for e in raw]


def embed_query(
    query: str,
    *,
    embedding_model: str = "text-embedding-3-small",
) -> list[float]:
    """
    Convenience wrapper for single query embedding.
    """
    embs = embed_texts([query], embedding_model=embedding_model)
    return embs[0]


def get_collection(
    *,
    persist_dir: Path,
    name: str = "funding_docs",
    embedding_model: str = "text-embedding-3-small",
):
    client = chromadb.PersistentClient(path=str(persist_dir))
    embedding_fn = get_embedding_function(embedding_model=embedding_model)

    return client.get_or_create_collection(
        name=name,
        embedding_function=embedding_fn,
    )