import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentProcessor:
    def __init__(self, chunk_size=500, chunk_overlap=50):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def process_file(self, file_path, doc_id, doc_name):
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
            pages = loader.load()
        elif ext in [".txt", ".md"]:
            loader = TextLoader(file_path, encoding="utf-8")
            pages = loader.load()
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        chunks = self.text_splitter.split_documents(pages)
        chunks = [chunk for chunk in chunks if chunk.page_content.strip()]
        if not chunks:
            raise ValueError("Document contains no extractable text. Scanned PDFs require OCR.")
        
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            page_num = chunk.metadata.get("page", 0) + 1 if "page" in chunk.metadata else 1
            processed_chunks.append({
                "id": f"{doc_id}_{i}",
                "text": chunk.page_content,
                "metadata": {
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                    "page": page_num,
                    "chunk_index": i
                }
            })
            
        return len(pages), processed_chunks
