from typing import Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from config import gemini_is_configured, settings
from database import db


class SupabaseVectorStore:
    def __init__(self) -> None:
        self.embeddings: GoogleGenerativeAIEmbeddings | None = None

    def _get_embeddings(self) -> GoogleGenerativeAIEmbeddings:
        if not gemini_is_configured():
            raise RuntimeError("GEMINI_API_KEY is not configured. Add it to backend/.env before using chat or document indexing.")
        if self.embeddings is None:
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model=settings.EMBEDDING_MODEL,
                google_api_key=settings.GEMINI_API_KEY,
            )
        return self.embeddings

    def add_chunks(self, document_id: int, chunks: list[str], metadatas: list[dict[str, Any]]) -> None:
        if not chunks:
            return
        vectors = self._get_embeddings().embed_documents(chunks)
        db.request(
            "POST",
            "document_chunks",
            json=[
                {"document_id": document_id, "content": chunk, "metadata": metadata, "embedding": vector}
                for chunk, metadata, vector in zip(chunks, metadatas, vectors)
            ],
        )

    def similarity_search(self, query: str, k: int = 16, per_doc_k: int = 4, document_id: int | None = None) -> list[dict[str, Any]]:
        query_vector = self._get_embeddings().embed_query(query)
        rows = db.request(
            "POST",
            "rpc/match_document_chunks",
            json={
                "query_embedding": query_vector,
                "match_count": max(k, per_doc_k),
                "filter_document_id": document_id
            },
        )
        if not rows:
            return []

        candidates: list[dict[str, Any]] = []
        for row in rows:
            metadata = row.get("metadata") or {}
            candidates.append({
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "filename": row["filename"],
                "company": row.get("company") or metadata.get("company") or "Corporate Policy",
                "tag": row.get("tag") or "GEN-POL",
                "content": row["content"],
                "metadata": metadata,
                "score": float(row["score"]),
            })

        by_document: dict[int, list[dict[str, Any]]] = {}
        for candidate in candidates:
            by_document.setdefault(candidate["document_id"], []).append(candidate)
        selected: list[dict[str, Any]] = []
        selected_ids: set[int] = set()
        for items in by_document.values():
            for item in sorted(items, key=lambda value: value["score"], reverse=True)[:per_doc_k]:
                selected.append(item)
                selected_ids.add(item["chunk_id"])
        for item in sorted(candidates, key=lambda value: value["score"], reverse=True):
            if len(selected) >= k:
                break
            if item["chunk_id"] not in selected_ids:
                selected.append(item)
                selected_ids.add(item["chunk_id"])
        return sorted(selected, key=lambda value: value["score"], reverse=True)[:k]


vector_store = SupabaseVectorStore()
