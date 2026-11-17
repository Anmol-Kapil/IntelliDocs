import os
from dotenv import load_dotenv

# Explicitly load .env from backend directory or parent root directory
backend_env = os.path.join(os.path.dirname(__file__), ".env")
root_env = os.path.join(os.path.dirname(__file__), "..", ".env")

if os.path.exists(backend_env):
    load_dotenv(dotenv_path=backend_env)
elif os.path.exists(root_env):
    load_dotenv(dotenv_path=root_env)
else:
    load_dotenv()

class Config:
    PORT = int(os.environ.get("PORT", 5002))
    DEBUG = os.environ.get("FLASK_ENV") == "development"
    UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads"))
    CHROMA_DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "chroma_db"))
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
    EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    ALLOWED_EXTENSIONS = {"pdf", "txt", "md"}
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024
