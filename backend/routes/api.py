import os
import uuid
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest, NotFound, HTTPException
from backend.config import Config
from backend.services.document_service import DocumentProcessor
from backend.services.rag_service import RAGManager

api_bp = Blueprint("api", __name__)
doc_processor = DocumentProcessor()
rag_manager = RAGManager()

def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequest("A JSON object is required")
    return data

def require_document(doc_id, optional=False):
    if optional and doc_id is None:
        return
    if not isinstance(doc_id, str) or not doc_id.strip():
        raise BadRequest("Document ID must be a non-empty string")
    if doc_id not in rag_manager.documents:
        raise NotFound("Document not found")

def require_question(data):
    question = data.get("question")
    if not isinstance(question, str) or not question.strip():
        raise BadRequest("Question must be a non-empty string")
    return question.strip()

@api_bp.errorhandler(HTTPException)
def handle_http_error(error):
    return jsonify({"error": error.description}), error.code

@api_bp.errorhandler(Exception)
def handle_service_error(error):
    from flask import current_app
    current_app.logger.exception("API request failed")
    return jsonify({"error": "The request could not be completed. Check the backend logs and service configuration."}), 500

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

    doc_id = str(uuid.uuid4())
    raw_name = request.form.get("name", file.filename)
    clean_name = os.path.splitext(raw_name)[0]

    filename = secure_filename(file.filename)
    filepath = os.path.join(Config.UPLOAD_FOLDER, f"{doc_id}_{filename}")
    try:
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        file.save(filepath)
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
        if isinstance(e, ValueError):
            return jsonify({"error": str(e)}), 400
        raise

@api_bp.route("/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    require_document(doc_id)
    rag_manager.delete_document(doc_id)
    return jsonify({"message": f"Successfully deleted document {doc_id}"})

@api_bp.route("/documents/<doc_id>/summary", methods=["GET"])
def get_document_summary(doc_id):
    require_document(doc_id)
    summary = rag_manager.generate_summary(doc_id)
    return jsonify({"doc_id": doc_id, "summary": summary})

@api_bp.route("/chat", methods=["POST"])
def chat():
    data = json_body()
    question = require_question(data)

    doc_id = data.get("doc_id")
    top_k = data.get("top_k", 4)
    require_document(doc_id, optional=True)
    if type(top_k) is not int or not 1 <= top_k <= 20:
        raise BadRequest("top_k must be an integer between 1 and 20")

    answer, sources = rag_manager.answer_question(question, doc_id=doc_id, top_k=top_k)
    return jsonify({
        "answer": answer,
        "sources": sources
    })

@api_bp.route("/compare", methods=["POST"])
def compare():
    data = json_body()
    question = require_question(data)
    doc_id_1 = data.get("doc_id_1")
    doc_id_2 = data.get("doc_id_2")

    require_document(doc_id_1)
    require_document(doc_id_2)
    if doc_id_1 == doc_id_2:
        raise BadRequest("Select two different documents to compare")

    comparison = rag_manager.compare_documents(question, doc_id_1, doc_id_2)
    return jsonify({"comparison": comparison})

@api_bp.route("/reset", methods=["POST"])
def reset():
    data = json_body()
    doc_id = data.get("doc_id")
    require_document(doc_id, optional=True)
    rag_manager.reset_history(doc_id)
    return jsonify({"message": "Chat history reset successfully"})
