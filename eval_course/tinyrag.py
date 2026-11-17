"""Mounted documents → chunks → TinyRAG VectorStore → attributed retrieval.

The local TF-IDF adapter supplies real corpus-based vectors without an API key.
It is a lexical baseline, not a pretrained semantic embedding model.
"""

import hashlib
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer

from vendor.tinyrag.embeddings import BaseEmbeddings
from vendor.tinyrag.VectorBase import VectorStore

from .knowledge import catalog, terms


class CorpusEmbeddings(BaseEmbeddings):
    def __init__(self, texts):
        super().__init__(path="local-tfidf", is_api=False)
        self.vectorizer = TfidfVectorizer(analyzer=lambda text: sorted(terms(text)))
        self.vectorizer.fit(texts)

    def get_embedding(self, text, model=None):
        return self.vectorizer.transform([text]).toarray()[0].tolist()


def chunks(documents, size=1200, overlap=150):
    """Preserve exact text and character offsets; source identity survives splitting."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("Chunk size must be positive and overlap smaller than size")
    output = []
    for doc in documents:
        for start in range(0, len(doc["text"]), size - overlap):
            text = doc["text"][start : start + size]
            output.append(
                {
                    "path": doc["path"],
                    "chunk_id": f"{doc['path']}#{start}",
                    "text": text,
                    "sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "source_sha256": doc["sha256"],
                    "start": start,
                    "end": start + len(text),
                }
            )
            if start + size >= len(doc["text"]):
                break
    return output


def retrieve(query: str, limit: int = 3, root: Path | None = None) -> list[dict]:
    if not isinstance(query, str) or not query.strip() or not 1 <= limit <= 10:
        raise ValueError("请输入查询内容，limit 必须在 1–10 之间。")
    parts = [part for part in chunks(catalog(root)) if terms(part["text"])]
    if not parts:
        return []
    # Prefixes distinguish identical passages from different source documents.
    entries = {f"[{p['chunk_id']}]\n{p['text']}": p for p in parts}
    embedding = CorpusEmbeddings(list(entries))
    store = VectorStore(list(entries))
    store.get_vector(embedding)
    ranked = store.query(query, embedding, k=min(limit, len(entries)))
    query_vector = embedding.get_embedding(query)
    vectors = dict(zip(store.document, store.vectors))
    hits = []
    for text in ranked:
        similarity = float(store.get_similarity(query_vector, vectors[text]))
        if similarity <= 0:
            continue
        part = entries[text]
        hits.append(
            {
                **part,
                "similarity": similarity,
                "matches": len(terms(query) & terms(part["text"])),
                "retriever": "TinyRAG.VectorStore",
                "embedding": "local-tfidf",
            }
        )
    return hits
