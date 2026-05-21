from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import settings

_COLLECTION = "irs_pubs"


@dataclass
class RetrievedChunk:
    text: str
    pub_number: str
    section: str
    revision_date: str
    source_url: str
    score: float


def _client():
    import chromadb

    return chromadb.PersistentClient(path=str(settings.chroma_dir))


def _embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def get_collection():
    return _client().get_or_create_collection(_COLLECTION)


def add_chunks(chunks: list[dict[str, Any]]) -> None:
    """`chunks`: list of {id, text, metadata{pub_number, section, revision_date, source_url}}."""
    if not chunks:
        return
    col = get_collection()
    embedder = _embedder()
    texts = [c["text"] for c in chunks]
    embs = embedder.encode(texts, normalize_embeddings=True).tolist()
    col.add(
        ids=[c["id"] for c in chunks],
        embeddings=embs,
        documents=texts,
        metadatas=[c["metadata"] for c in chunks],
    )


def query(question: str, *, k: int = 6) -> list[RetrievedChunk]:
    embedder = _embedder()
    q_emb = embedder.encode([question], normalize_embeddings=True).tolist()[0]
    res = get_collection().query(query_embeddings=[q_emb], n_results=k)
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    out: list[RetrievedChunk] = []
    for text, meta, dist in zip(docs, metas, dists):
        # Chroma returns cosine *distance* with normalized embeddings; similarity = 1 - distance.
        score = max(0.0, min(1.0, 1.0 - float(dist)))
        out.append(
            RetrievedChunk(
                text=text,
                pub_number=str(meta.get("pub_number", "")),
                section=str(meta.get("section", "")),
                revision_date=str(meta.get("revision_date", "")),
                source_url=str(meta.get("source_url", "")),
                score=score,
            )
        )
    return out
