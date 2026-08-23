import os
import uuid
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from backend.config import Config
from backend.services.document_service import DocumentProcessor
from backend.services.rag_service import RAGManager

api_bp = Blueprint("api", __name__)
doc_processor = DocumentProcessor()
rag_manager = RAGManager()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@api_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "DocMind AI RAG Engine",
        "documents_indexed": len(rag_manager.documents)
    })

@api_bp.route("/documents", methods=["GET"])
def get_documents():
    return jsonify({"documents": rag_manager.list_documents()})

@api_bp.route("/documents", methods=["POST"])
def upload_document():
    if "file" not in request.files:
        return jsonify({"error": "No file parameter in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not supported. Allowed: {', '.join(Config.ALLOWED_EXTENSIONS)}"}), 400

    doc_id = str(uuid.uuid4())[:8]
    raw_name = request.form.get("name", file.filename)
    clean_name = os.path.splitext(raw_name)[0]

    filename = secure_filename(file.filename)
    filepath = os.path.join(Config.UPLOAD_FOLDER, f"{doc_id}_{filename}")
    file.save(filepath)

    try:
        pages_count, chunks = doc_processor.process_file(filepath, doc_id, clean_name)
        rag_manager.add_document(doc_id, clean_name, pages_count, chunks, filepath)
        
        return jsonify({
            "doc_id": doc_id,
            "name": clean_name,
            "pages": pages_count,
            "chunks": len(chunks)
        }), 201
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": str(e)}), 500

@api_bp.route("/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    rag_manager.delete_document(doc_id)
    return jsonify({"message": f"Successfully deleted document {doc_id}"})

@api_bp.route("/documents/<doc_id>/summary", methods=["GET"])
def get_document_summary(doc_id):
    summary = rag_manager.generate_summary(doc_id)
    return jsonify({"doc_id": doc_id, "summary": summary})

@api_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    question = data.get("question")
    if not question or not question.strip():
        return jsonify({"error": "Question is required"}), 400

    doc_id = data.get("doc_id")
    top_k = data.get("top_k", 4)

    answer, sources = rag_manager.answer_question(question, doc_id=doc_id, top_k=top_k)
    return jsonify({
        "answer": answer,
        "sources": sources
    })

@api_bp.route("/compare", methods=["POST"])
def compare():
    data = request.get_json() or {}
    question = data.get("question")
    doc_id_1 = data.get("doc_id_1")
    doc_id_2 = data.get("doc_id_2")

    if not question or not doc_id_1 or not doc_id_2:
        return jsonify({"error": "question, doc_id_1, and doc_id_2 are required fields"}), 400

    comparison = rag_manager.compare_documents(question, doc_id_1, doc_id_2)
    return jsonify({"comparison": comparison})

@api_bp.route("/reset", methods=["POST"])
def reset():
    data = request.get_json() or {}
    doc_id = data.get("doc_id")
    rag_manager.reset_history(doc_id)
    return jsonify({"message": "Chat history reset successfully"})
