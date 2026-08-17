"""Supabase PostgreSQL persistence for policy metadata and embeddings."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from config import settings, supabase_is_configured


class DatabaseError(RuntimeError):
    """Raised when Supabase rejects a database operation."""


class SupabaseDatabase:
    def __init__(self) -> None:
        self.base_url = settings.SUPABASE_URL.rstrip("/")
        self.key = settings.SUPABASE_SECRET_KEY

    def _headers(self, *, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def request(self, method: str, table: str, *, params: dict[str, str] | None = None,
                json: Any = None, prefer: str | None = None) -> Any:
        if not supabase_is_configured():
            raise DatabaseError("Supabase is not configured. Set real SUPABASE_URL and SUPABASE_SECRET_KEY values in backend/.env.")
        try:
            response = httpx.request(
                method,
                f"{self.base_url}/rest/v1/{table}",
                params=params,
                json=json,
                headers=self._headers(prefer=prefer),
                timeout=settings.REQUEST_TIMEOUT,
            )
        except httpx.HTTPError as exc:
            raise DatabaseError("Could not connect to Supabase.") from exc

        if response.is_error:
            message = response.json().get("message", response.text) if response.content else "Unknown Supabase error"
            raise DatabaseError(f"Supabase {table} request failed ({response.status_code}): {message}")
        return response.json() if response.content else None


db = SupabaseDatabase()


def init_db() -> None:
    """Verify that the migration has been applied without mutating production data."""
    db.request("GET", "documents", params={"select": "id", "limit": "1"})


def add_document(filename: str, storage_size: str, status: str = "Processing", company: str | None = None,
                 tag: str | None = None, description: str | None = None, stored_filename: str | None = None) -> int:
    rows = db.request(
        "POST", "documents",
        json={
            "filename": filename,
            "stored_filename": stored_filename,
            "company": company,
            "tag": tag,
            "status": status,
            "storage_size": storage_size,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "description": description,
        },
        prefer="return=representation",
    )
    return int(rows[0]["id"])


def update_document_status(doc_id: int, status: str, company: str | None = None,
                           tag: str | None = None, description: str | None = None) -> None:
    payload: dict[str, Any] = {"status": status, "last_updated": datetime.now(timezone.utc).isoformat()}
    if company is not None:
        payload["company"] = company
    if tag is not None:
        payload["tag"] = tag
    if description is not None:
        payload["description"] = description
    db.request("PATCH", "documents", params={"id": f"eq.{doc_id}"}, json=payload)


def get_all_documents() -> list[dict[str, Any]]:
    return db.request("GET", "documents", params={"select": "*", "order": "id.desc"})


def get_document_by_id(doc_id: int) -> dict[str, Any] | None:
    rows = db.request("GET", "documents", params={"select": "*", "id": f"eq.{doc_id}", "limit": "1"})
    return rows[0] if rows else None


def delete_document(doc_id: int) -> None:
    db.request("DELETE", "document_chunks", params={"document_id": f"eq.{doc_id}"})
    db.request("DELETE", "documents", params={"id": f"eq.{doc_id}"})
