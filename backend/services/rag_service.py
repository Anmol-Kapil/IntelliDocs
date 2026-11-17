import os
import ssl
import truststore
from datetime import datetime
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq, DefaultHttpxClient, APIConnectionError, AuthenticationError, RateLimitError, NotFoundError, PermissionDeniedError
from werkzeug.exceptions import ServiceUnavailable, BadGateway
from backend.config import Config

def groq_failure(error):
    if isinstance(error, APIConnectionError):
        message = "Cannot securely connect to Groq. Check your network, proxy, and trusted certificates."
    elif isinstance(error, AuthenticationError):
        message = "Groq rejected the API key. Update GROQ_API_KEY in backend/.env and restart the backend."
    elif isinstance(error, NotFoundError):
        message = "The configured Groq model is unavailable. Update GROQ_MODEL in backend/.env and restart the backend."
    elif isinstance(error, PermissionDeniedError):
        message = "Your Groq account does not have permission to use this model. Check your Groq project settings."
    elif isinstance(error, RateLimitError):
        message = "Groq rate or usage limit reached. Wait and retry, or check your Groq account limits."
    else:
        message = "Groq could not generate a response. Try again or check the service status."
    return BadGateway(message)

class RAGManager:
    def __init__(self):
        os.makedirs(Config.CHROMA_DB_DIR, exist_ok=True)
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        self.embedder = SentenceTransformer(Config.EMBEDDING_MODEL)
        self.chroma_client = chromadb.PersistentClient(path=Config.CHROMA_DB_DIR)
        
        try:
            self.collection = self.chroma_client.get_collection("docmind_documents")
        except Exception:
            self.collection = self.chroma_client.create_collection("docmind_documents")
            
        self.groq_key = Config.GROQ_API_KEY
        self.groq_client = Groq(
            api_key=self.groq_key,
            http_client=DefaultHttpxClient(verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)),
        ) if self.groq_key else None
        
        self.documents = {}
        self.chat_histories = {}
        self.global_history = []
        
        self._recover_persisted_documents()

    def _recover_persisted_documents(self):
        """Recover document catalog metadata from ChromaDB on startup if available."""
        try:
            results = self.collection.get(include=["metadatas"])
            if results and results.get("metadatas"):
                for meta in results["metadatas"]:
                    doc_id = meta.get("doc_id")
                    doc_name = meta.get("doc_name")
                    if doc_id and doc_id not in self.documents:
                        self.documents[doc_id] = {
                            "name": doc_name,
                            "pages": meta.get("page", 1),
                            "chunks": 1,
                            "uploaded": datetime.now().strftime("%H:%M")
                        }
                        # Resolve only files inside the configured upload directory.
                        matches = [entry.path for entry in os.scandir(Config.UPLOAD_FOLDER)
                                   if entry.is_file() and entry.name.startswith(f"{doc_id}_")]
                        if len(matches) == 1:
                            self.documents[doc_id]["filepath"] = matches[0]
                        self.chat_histories[doc_id] = []
                    elif doc_id in self.documents:
                        self.documents[doc_id]["chunks"] += 1
                        if meta.get("page", 1) > self.documents[doc_id]["pages"]:
                            self.documents[doc_id]["pages"] = meta.get("page", 1)
        except Exception as e:
            print(f"[RAGManager] Warning during index recovery: {e}")

    def add_document(self, doc_id, doc_name, pages_count, chunks, filepath):
        texts = [c["text"] for c in chunks]
        embeddings = self.embedder.encode(texts).tolist()
        metadatas = [c["metadata"] for c in chunks]
        ids = [c["id"] for c in chunks]

        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        self.documents[doc_id] = {
            "name": doc_name,
            "pages": pages_count,
            "chunks": len(chunks),
            "filepath": filepath,
            "uploaded": datetime.now().strftime("%H:%M")
        }
        self.chat_histories[doc_id] = []

    def list_documents(self):
        return [
            {"doc_id": k, **{f: v for f, v in info.items() if f != "filepath"}}
            for k, info in self.documents.items()
        ]

    def delete_document(self, doc_id):
        records = self.collection.get(where={"doc_id": doc_id})
        if records and records.get("ids"):
            self.collection.delete(ids=records["ids"])

        if doc_id in self.documents:
            filepath = self.documents[doc_id].get("filepath")
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            del self.documents[doc_id]

        if doc_id in self.chat_histories:
            del self.chat_histories[doc_id]
        # Global answers may refer to the deleted document.
        self.global_history = []

    def retrieve(self, question, doc_id=None, top_k=3):
        count = self.documents.get(doc_id, {}).get("chunks", 0) if doc_id else self.collection.count()
        if not count:
            return []
        args = {
            "query_embeddings": self.embedder.encode([question]).tolist(),
            "n_results": min(top_k, count),
            "include": ["documents", "metadatas", "distances"]
        }
        if doc_id:
            args["where"] = {"doc_id": doc_id}

        results = self.collection.query(**args)
        
        retrieved_chunks = []
        if results and results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0]

            for i in range(len(docs)):
                dist = float(dists[i])
                # Calculate normalized similarity score (supports both cosine and L2 distances)
                relevance = round(max(0.15, min(0.99, 1.0 - (dist / 2.0))), 2)
                retrieved_chunks.append({
                    "text": docs[i],
                    "page": metas[i].get("page", 1),
                    "doc_name": metas[i].get("doc_name", "Document"),
                    "relevance": relevance
                })
        return retrieved_chunks

    def answer_question(self, question, doc_id=None, top_k=4):
        if not self.groq_client:
            raise ServiceUnavailable("Set GROQ_API_KEY in backend/.env to enable AI features.")

        history = self.chat_histories.get(doc_id, []) if doc_id else self.global_history
        scope = f"'{self.documents[doc_id]['name']}'" if doc_id and doc_id in self.documents else "all documents"
        chunks = self.retrieve(question, doc_id=doc_id, top_k=top_k)

        if not chunks:
            return "No relevant context found in the uploaded documents.", []

        context_str = "\n\n".join(
            f"[{c['doc_name']} — Page {c['page']}]: {c['text']}" for c in chunks
        )

        messages = [
            {
                "role": "system",
                "content": f"You are DocMind AI, an intelligent RAG context assistant. Answer the user question using ONLY the provided context from {scope}.\n"
                           f"Cite the relevant page numbers inline (e.g. [Page X]). If the information is not present in the context, explicitly state: 'I could not find information about that in the provided documents.'\n\n"
                           f"CONTEXT:\n{context_str}"
            }
        ] + history + [{"role": "user", "content": question}]

        try:
            completion = self.groq_client.chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=messages,
                max_tokens=600,
                temperature=0.2
            )
            response_text = completion.choices[0].message.content

            updated_history = (history + [
                {"role": "user", "content": question},
                {"role": "assistant", "content": response_text}
            ])[-10:]

            if doc_id:
                self.chat_histories[doc_id] = updated_history
            else:
                self.global_history = updated_history

            sources = [
                {"doc": c["doc_name"], "page": c["page"], "relevance": c["relevance"]}
                for c in chunks
            ]
            return response_text, sources
        except Exception as e:
            raise groq_failure(e) from e

    def compare_documents(self, question, doc_id_1, doc_id_2):
        if not self.groq_client:
            raise ServiceUnavailable("Set GROQ_API_KEY in backend/.env to enable AI features.")

        name1 = self.documents.get(doc_id_1, {}).get("name", "Doc 1")
        name2 = self.documents.get(doc_id_2, {}).get("name", "Doc 2")

        c1 = self.retrieve(question, doc_id=doc_id_1, top_k=3)
        c2 = self.retrieve(question, doc_id=doc_id_2, top_k=3)

        txt1 = "\n".join(c["text"] for c in c1) if c1 else "No text retrieved."
        txt2 = "\n".join(c["text"] for c in c2) if c2 else "No text retrieved."

        prompt = f"""Compare what these two documents state about: "{question}"

--- Document 1: {name1} ---
{txt1}

--- Document 2: {name2} ---
{txt2}

Format your comparison with clear headers:
### 1. Key Insights from {name1}
### 2. Key Insights from {name2}
### 3. Shared Points / Similarities
### 4. Key Differences / Contrasts"""

        try:
            completion = self.groq_client.chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=700,
                temperature=0.2
            )
            return completion.choices[0].message.content
        except Exception as e:
            raise groq_failure(e) from e

    def generate_summary(self, doc_id):
        if not self.groq_client:
            raise ServiceUnavailable("Set GROQ_API_KEY in backend/.env to enable AI features.")

        if doc_id not in self.documents:
            return "Document not found."

        doc_name = self.documents[doc_id]["name"]
        sample_chunks = self.retrieve("overview main topics summary key points", doc_id=doc_id, top_k=5)
        combined_text = "\n\n".join(c["text"] for c in sample_chunks)

        prompt = f"""Provide an executive summary of the document titled "{doc_name}".

Extract key topics, overall scope, and important takeaways based on the following excerpts:

{combined_text}

Format as markdown with:
- **Executive Overview**
- **Core Topics Covered**
- **Key Takeaways**"""

        try:
            completion = self.groq_client.chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.3
            )
            return completion.choices[0].message.content
        except Exception as e:
            raise groq_failure(e) from e

    def reset_history(self, doc_id=None):
        if doc_id:
            self.chat_histories[doc_id] = []
        else:
            self.global_history = []
