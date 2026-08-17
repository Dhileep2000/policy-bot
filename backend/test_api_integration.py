"""ASGI integration tests for the frontend-facing API contract.

External Supabase and Gemini calls are replaced so the complete HTTP contract can
be verified safely in any development environment.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from config import settings


class ApiIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.patches = [
            patch.object(main, "init_db"),
            patch.object(main, "gemini_is_configured", return_value=True),
            patch.object(settings, "DOCUMENTS_DIR", self.temp_dir.name),
        ]
        for patcher in self.patches:
            patcher.start()
        self.client = TestClient(main.app)

    def tearDown(self) -> None:
        for patcher in reversed(self.patches):
            patcher.stop()
        self.temp_dir.cleanup()

    def test_chat_documents_upload_and_delete_contract(self) -> None:
        document = {
            "id": 7,
            "filename": "remote-work.txt",
            "stored_filename": "stored-remote-work.txt",
            "status": "Indexed",
            "storage_size": "1.0 KB",
            "last_updated": "2026-08-17T00:00:00Z",
            "tag": "HR-POL-01",
            "description": "Remote-work policy.",
        }
        answer = {"answer": "Remote work is permitted.", "sources": [], "index_names": [], "response_type": "general_knowledge"}

        with (
            patch.object(main, "get_all_documents", return_value=[document]),
            patch.object(main.rag_pipeline, "query", return_value=answer),
            patch.object(main, "add_document", return_value=8) as add_document,
            patch.object(main, "process_and_index_document") as process_document,
            patch.object(main, "get_document_by_id", return_value=document),
            patch.object(main, "delete_document") as delete_document,
        ):
            documents_response = self.client.get("/api/documents")
            self.assertEqual(documents_response.status_code, 200)
            self.assertEqual(documents_response.json(), [document])

            chat_response = self.client.post("/api/chat", json={"message": "Can I work remotely?"})
            self.assertEqual(chat_response.status_code, 200)
            self.assertEqual(chat_response.json(), answer)

            upload_response = self.client.post(
                "/api/documents/upload",
                files={"files": ("remote-work.txt", b"Remote work policy content", "text/plain")},
            )
            self.assertEqual(upload_response.status_code, 200)
            self.assertEqual(upload_response.json()["document"]["id"], 8)
            self.assertTrue(add_document.called)
            self.assertTrue(process_document.called)

            stored_file = Path(settings.DOCUMENTS_DIR, document["stored_filename"])
            stored_file.write_text("test document", encoding="utf-8")
            delete_response = self.client.delete("/api/documents/7")
            self.assertEqual(delete_response.status_code, 200)
            self.assertFalse(stored_file.exists())
            delete_document.assert_called_once_with(7)

    def test_database_outage_is_reported_as_service_unavailable(self) -> None:
        with patch.object(main, "init_db", side_effect=main.DatabaseError("Could not connect to Supabase.")):
            response = self.client.get("/api/documents")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Could not connect to Supabase.")

    def test_chat_falls_back_to_gemini_when_document_retrieval_is_unavailable(self) -> None:
        fallback_answer = {
            "answer": "General guidance.",
            "sources": [],
            "index_names": [],
            "companies": [],
            "response_type": "general_knowledge",
        }
        with (
            patch.object(main.vector_store, "similarity_search", side_effect=main.DatabaseError("Could not connect to Supabase.")),
            patch.object(main.rag_pipeline, "_answer_from_general_knowledge", return_value=fallback_answer),
        ):
            response = self.client.post("/api/chat", json={"message": "What is remote work?"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), fallback_answer)


if __name__ == "__main__":
    unittest.main()
