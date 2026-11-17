import sys
import os

# Add parent directory to sys.path so 'backend.*' package imports work from any CWD
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge
from flask_cors import CORS
from backend.config import Config
from backend.routes.api import api_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.errorhandler(RequestEntityTooLarge)
    def file_too_large(error):
        return jsonify({"error": "Upload exceeds the 25 MB request limit"}), 413
    
    @app.route("/")
    def index():
        return {
            "name": "IntelliDocs - Multi-Document RAG API",
            "version": "1.0.0",
            "status": "running"
        }

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
