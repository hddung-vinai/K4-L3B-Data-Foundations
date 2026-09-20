from __future__ import annotations

from typing import Any, Callable

from .chunking import compute_similarity
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    An in-memory vector store for text chunks.

    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._store: list[dict[str, Any]] = []
        self._next_index = 0

    @staticmethod
    def _base_doc_id(doc: Document) -> str:
        """
        Trace a chunk back to its source document.

        Chunk ids look like "file#0", "file#1" — doc_id must be "file" so that
        delete_document removes every chunk of that file, not just one.
        """
        existing = (doc.metadata or {}).get("doc_id")
        if existing:
            return str(existing)
        return doc.id.split("#", 1)[0]

    def _make_record(self, doc: Document) -> dict[str, Any]:
        """Normalize one Document into the dict shape used everywhere downstream."""
        # Copy metadata: store không được sửa dict của người gọi.
        metadata = dict(doc.metadata or {})
        doc_id = self._base_doc_id(doc)
        metadata["doc_id"] = doc_id

        record = {
            "id": doc.id,
            "doc_id": doc_id,
            "index": self._next_index,  # thứ tự nạp, dùng để phá hòa khi score bằng nhau
            "content": doc.content,
            "metadata": metadata,
            "embedding": self._embedding_fn(doc.content),
        }
        self._next_index += 1
        return record

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        """Cosine-similarity search restricted to the records passed in."""
        if not records or top_k <= 0:
            return []

        query_embedding = self._embedding_fn(query)
        scored = [
            {
                "id": record["id"],
                "content": record["content"],
                "metadata": record["metadata"],
                "index": record["index"],
                # Cố tình không trả "embedding": vector hàng trăm chiều làm bẩn output.
                "score": compute_similarity(query_embedding, record["embedding"]),
            }
            for record in records
        ]
        # -index: score bằng nhau thì bản ghi nạp trước đứng trước, kết quả tất định.
        scored.sort(key=lambda item: (item["score"], -item["index"]), reverse=True)
        for item in scored:
            del item["index"]
        return scored[:top_k]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and append it to self._store.
        """
        if not docs:
            return

        self._store.extend(self._make_record(doc) for doc in docs)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        Embeds the query once, then scores it against every stored embedding.
        """
        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if not metadata_filter:
            return self._search_records(query, self._store, top_k)

        candidates = [
            record
            for record in self._store
            if all(record["metadata"].get(key) == value for key, value in metadata_filter.items())
        ]
        return self._search_records(query, candidates, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        # Lọc ra list mới thay vì remove() trong vòng lặp — không sửa list đang duyệt.
        remaining = [record for record in self._store if record["metadata"].get("doc_id") != doc_id]
        if len(remaining) == len(self._store):
            return False

        self._store = remaining
        return True
