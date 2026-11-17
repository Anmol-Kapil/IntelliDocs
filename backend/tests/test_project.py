"""Integration regressions with real loaders/Chroma and offline model doubles.

Run from the repository root: python -m unittest discover -s backend/tests -v
"""
import importlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace

import numpy as np

from backend.config import Config
from backend.services.rag_service import RAGManager, groq_failure


class OfflineEmbedder:
    """Deterministic vectors; these tests do not assess semantic model quality."""
    def encode(self, texts):
        return np.array([[len(text), text.lower().count("solar"), 1.0] for text in texts], dtype=float)


class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory()
        cls.patches = [
            patch.object(Config, "UPLOAD_FOLDER", os.path.join(cls.storage.name, "uploads")),
            patch.object(Config, "CHROMA_DB_DIR", os.path.join(cls.storage.name, "chroma")),
            patch.object(Config, "GROQ_API_KEY", ""),
        ]
        if os.environ.get("INTELLIDOCS_LIVE_EMBEDDINGS") != "1":
            cls.patches.append(patch("backend.services.rag_service.SentenceTransformer", return_value=OfflineEmbedder()))
        for item in cls.patches:
            item.start()
        cls.api = importlib.import_module("backend.routes.api")
        cls.app = importlib.import_module("backend.app").create_app()
        cls.app.config["TESTING"] = True

    @classmethod
    def tearDownClass(cls):
        cls.api.rag_manager.chroma_client._system.stop()
        for item in reversed(cls.patches):
            item.stop()
        # Chroma may keep SQLite handles open on Windows until process exit.
        try:
            cls.storage.cleanup()
        except OSError:
            pass

    def setUp(self):
        self.manager = self.api.rag_manager
        records = self.manager.collection.get()
        if records["ids"]:
            self.manager.collection.delete(ids=records["ids"])
        self.manager.documents.clear()
        self.manager.chat_histories.clear()
        self.manager.global_history.clear()
        self.manager.groq_client = None
        self.client = self.app.test_client()

    def upload(self, text=b"Solar energy reduces fuel costs.", filename="report.txt"):
        return self.client.post("/api/documents", data={"file": (io.BytesIO(text), filename)},
                                content_type="multipart/form-data")

    def test_health_and_catalog(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        self.assertEqual(self.client.get("/api/documents").json, {"documents": []})

    def test_upload_retrieve_restart_delete(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.json)
        doc_id = response.json["doc_id"]
        filepath = self.manager.documents[doc_id]["filepath"]
        chunks = self.manager.retrieve("solar", doc_id, top_k=20)
        self.assertEqual(len(chunks), 1)
        self.assertIn("Solar energy", chunks[0]["text"])
        self.assertEqual(chunks[0]["page"], 1)
        recovered = RAGManager()
        self.assertEqual(recovered.documents[doc_id]["filepath"], filepath)
        with patch.object(self.api, "rag_manager", recovered):
            self.assertEqual(self.client.delete(f"/api/documents/{doc_id}").status_code, 200)
        self.assertFalse(Path(filepath).exists())
        self.assertEqual(recovered.collection.count(), 0)

    def test_markdown_upload(self):
        self.assertEqual(self.upload(b"# Solar\nUseful information", "notes.md").status_code, 201)

    def test_pdf_upload(self):
        from pypdf import PdfWriter
        # A blank PDF must be rejected rather than inserted as an empty document.
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        content = io.BytesIO()
        writer.write(content)
        response = self.upload(content.getvalue(), "scan.pdf")
        self.assertEqual(response.status_code, 400, response.json)
        self.assertIn("no extractable text", response.json["error"])

    def test_text_pdf_upload(self):
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        writer = PdfWriter()
        page = writer.add_blank_page(width=200, height=200)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 20 100 Td (Solar energy report.) Tj ET")
        page[NameObject("/Contents")] = stream
        content = io.BytesIO()
        writer.write(content)
        response = self.upload(content.getvalue(), "report.pdf")
        self.assertEqual(response.status_code, 201, response.json)
        self.assertEqual(response.json["pages"], 1)

    def test_ai_flows_with_offline_completion(self):
        first = self.upload().json["doc_id"]
        second = self.upload(b"Wind energy needs no fuel.", "wind.md").json["doc_id"]
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Solar reduces fuel costs. [Page 1]"))])
        self.manager.groq_client = client
        answer = self.client.post("/api/chat", json={"question": "solar", "doc_id": first})
        self.assertEqual(answer.status_code, 200, answer.json)
        self.assertEqual(answer.json["sources"][0]["doc"], "report")
        self.assertEqual(len(self.manager.chat_histories[first]), 2)
        summary = self.client.get(f"/api/documents/{first}/summary")
        self.assertEqual(summary.status_code, 200)
        compare = self.client.post("/api/compare", json={"question": "costs", "doc_id_1": first, "doc_id_2": second})
        self.assertEqual(compare.status_code, 200)
        self.assertEqual(client.chat.completions.create.call_count, 3)

    def test_provider_failure_is_bad_gateway(self):
        self.upload()
        client = Mock()
        client.chat.completions.create.side_effect = RuntimeError("provider unavailable")
        self.manager.groq_client = client
        response = self.client.post("/api/chat", json={"question": "solar"})
        self.assertEqual(response.status_code, 502)
        self.assertIn("error", response.json)

    def test_provider_errors_have_actionable_messages(self):
        import httpx
        from groq import APIConnectionError, AuthenticationError, NotFoundError, RateLimitError
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        errors = [
            (APIConnectionError(request=request), "trusted certificates"),
            (AuthenticationError("unauthorized", response=httpx.Response(401, request=request), body={}), "API key"),
            (NotFoundError("missing model", response=httpx.Response(404, request=request), body={}), "GROQ_MODEL"),
            (RateLimitError("limit", response=httpx.Response(429, request=request), body={}), "limit"),
        ]
        for error, expected in errors:
            with self.subTest(error=type(error).__name__):
                result = groq_failure(error)
                self.assertEqual(result.code, 502)
                self.assertIn(expected, result.description)

    def test_empty_upload(self):
        response = self.upload(b" \n\t")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.manager.collection.count(), 0)

    def test_invalid_upload_type_and_missing_file(self):
        self.assertEqual(self.upload(b"x", "report.exe").status_code, 400)
        self.assertEqual(self.client.post("/api/documents").status_code, 400)

    def test_oversized_upload_returns_json(self):
        with patch.dict(self.app.config, {"MAX_CONTENT_LENGTH": 100}):
            response = self.upload(b"x" * 200)
        self.assertEqual(response.status_code, 413)
        self.assertIn("error", response.json)

    def test_invalid_json_bodies(self):
        for endpoint in ["chat", "compare", "reset"]:
            for body in [[], "text", 12, None]:
                with self.subTest(endpoint=endpoint, body=body):
                    response = self.client.post(f"/api/{endpoint}", json=body)
                    self.assertEqual(response.status_code, 400)
                    self.assertIn("error", response.json)

    def test_invalid_question_types(self):
        for value in [None, 12, [], {}, "  "]:
            response = self.client.post("/api/chat", json={"question": value})
            self.assertEqual(response.status_code, 400)

    def test_invalid_retrieval_depth(self):
        for value in [0, -1, 21, True, 1.5, "4", []]:
            response = self.client.post("/api/chat", json={"question": "solar", "top_k": value})
            self.assertEqual(response.status_code, 400)

    def test_unknown_document(self):
        self.assertEqual(self.client.delete("/api/documents/missing").status_code, 404)
        self.assertEqual(self.client.get("/api/documents/missing/summary").status_code, 404)
        self.assertEqual(self.client.post("/api/chat", json={"question": "q", "doc_id": "missing"}).status_code, 404)
        self.assertEqual(self.client.post("/api/reset", json={"doc_id": []}).status_code, 400)

    def test_compare_same_document(self):
        doc_id = self.upload().json["doc_id"]
        response = self.client.post("/api/compare", json={"question": "q", "doc_id_1": doc_id, "doc_id_2": doc_id})
        self.assertEqual(response.status_code, 400)

    def test_missing_key_is_service_error(self):
        doc_id = self.upload().json["doc_id"]
        self.assertEqual(self.client.post("/api/chat", json={"question": "q"}).status_code, 503)
        self.assertEqual(self.client.get(f"/api/documents/{doc_id}/summary").status_code, 503)

    def test_empty_index_retrieval(self):
        self.assertEqual(self.manager.retrieve("anything"), [])

    def test_delete_failure_preserves_catalog(self):
        doc_id = self.upload().json["doc_id"]
        with patch.object(self.manager.collection, "delete", side_effect=RuntimeError("disk error")):
            response = self.client.delete(f"/api/documents/{doc_id}")
        self.assertEqual(response.status_code, 500)
        self.assertIn(doc_id, self.manager.documents)

    def test_reset_and_delete_clear_history(self):
        doc_id = self.upload().json["doc_id"]
        self.manager.chat_histories[doc_id] = [{"role": "user", "content": "q"}]
        self.manager.global_history = [{"role": "user", "content": "q"}]
        self.assertEqual(self.client.post("/api/reset", json={"doc_id": doc_id}).status_code, 200)
        self.assertEqual(self.manager.chat_histories[doc_id], [])
        self.client.delete(f"/api/documents/{doc_id}")
        self.assertEqual(self.manager.global_history, [])


if __name__ == "__main__":
    unittest.main()
