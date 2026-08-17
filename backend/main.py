import os
import shutil
import uuid
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import gemini_is_configured, settings
from database import (
    DatabaseError,
    init_db,
    get_all_documents,
    get_document_by_id,
    add_document,
    update_document_status,
    delete_document
)
from vector_store import vector_store
from rag import rag_pipeline

# Import LangChain text splitter and PDF reader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI

app = FastAPI(title="Lexis AI Policy Intelligence API")
logger = logging.getLogger(__name__)

# Parse CORS origins from .env configuration
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
cors_methods = [method.strip() for method in settings.CORS_ALLOW_METHODS.split(",")]
cors_headers = [header.strip() for header in settings.CORS_ALLOW_HEADERS.split(",")]

# Configure CORS middleware with secure settings from .env
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=cors_methods,
    allow_headers=cors_headers,
)


class ChatRequest(BaseModel):
    message: str


def ensure_database_ready() -> None:
    """Fail fast with a useful status instead of surfacing Supabase errors as 500s."""
    try:
        init_db()
        app.state.supabase_error = None
    except DatabaseError as exc:
        app.state.supabase_error = str(exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def ensure_chat_services_ready() -> None:
    if not gemini_is_configured():
        raise HTTPException(
            status_code=503,
            detail="Gemini is not configured. Set a real GEMINI_API_KEY value in backend/.env.",
        )


@app.on_event("startup")
async def verify_database_connection() -> None:
    try:
        init_db()
        app.state.supabase_error = None
    except DatabaseError as exc:
        app.state.supabase_error = str(exc)
        logger.warning("Supabase is not ready. Run supabase_schema.sql before using document or chat endpoints.")


@app.get("/health")
async def health_check():
    try:
        init_db()
    except DatabaseError as exc:
        app.state.supabase_error = str(exc)
        return {
            "status": "degraded",
            "database": "supabase",
            "detail": str(exc),
        }
    app.state.supabase_error = None
    return {"status": "ok", "database": "supabase"}

def extract_text_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif isinstance(part, str):
                text_parts.append(part)
        return "".join(text_parts)
    return str(content)

def detect_company_name(filename: str, sample_text: str) -> str:
    """
    Detects company/organization name from filename or snippet content.
    """
    known_companies = [
        "TCS", "Tata Consultancy Services", "Cognizant", "CTS", "Infosys", 
        "Wipro", "Accenture", "Google", "Microsoft", "Amazon", "IBM", 
        "Meta", "Apple", "Lexis AI", "Capgemini", "HCL", "Tech Mahindra"
    ]
    fname_upper = filename.upper()
    text_upper = sample_text[:1000].upper()
    
    for comp in known_companies:
        if comp.upper() in fname_upper or comp.upper() in text_upper:
            if comp == "Tata Consultancy Services":
                return "TCS"
            if comp == "CTS":
                return "Cognizant"
            return comp
            
    base = filename.split('.')[0].replace('_', ' ').replace('-', ' ')
    words = base.split()
    if len(words) > 0 and len(words[0]) > 2 and words[0].lower() not in ["sample", "global", "corporate", "remote", "leave", "employee", "handbook", "policy"]:
        return words[0].capitalize()
        
    return "Corporate Policy"

def generate_doc_summary_and_tag(filename: str, sample_text: str) -> tuple[str, str]:
    """
    Uses Gemini to generate a 1-sentence description and a category tag for the document.
    """
    tag = "GEN-POL"
    fname_lower = filename.lower()
    
    # Auto-tag based on filename keywords
    if "employee" in fname_lower or "handbook" in fname_lower or "hr" in fname_lower or "conduct" in fname_lower or "mobility" in fname_lower or "work" in fname_lower or "leave" in fname_lower:
        tag = "HR-POL-01"
    elif "privacy" in fname_lower or "data" in fname_lower or "security" in fname_lower or "gdpr" in fname_lower or "cyber" in fname_lower:
        tag = "SEC-PRO-99"
    elif "travel" in fname_lower or "expense" in fname_lower or "finance" in fname_lower or "tax" in fname_lower or "corporate" in fname_lower:
        tag = "FIN-POL-04"
        
    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.0
        )
        prompt = (
            "You are a policy assistant. Read this snippet of a document and write a 1-sentence description "
            "(maximum 20 words) explaining what this document is. Make it professional.\n\n"
            f"Document Title: {filename}\n"
            f"Snippet: {sample_text[:1500]}\n\n"
            "Summary:"
        )
        try:
            response = llm.invoke(prompt)
            summary = extract_text_content(response.content).strip()
        except Exception as model_err:
            print(f"Primary summary LLM failed: {model_err}. Trying fallback gemini-2.5-flash...")
            fallback_llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.0
            )
            response = fallback_llm.invoke(prompt)
            summary = extract_text_content(response.content).strip()
    except Exception as e:
        print(f"Summary generation error: {e}")
        summary = f"Policy document outlining guidelines and procedures regarding {filename.split('.')[0]}."
        
    return summary, tag

def process_and_index_document(doc_id: int, file_path: str, filename: str):
    """
    Background task to parse documents, chunk them, embed, and store in Supabase.
    """
    try:
        text_content = ""
        pages_metadata = []
        
        # 1. Extract text from file
        if filename.lower().endswith(".pdf"):
            reader = PdfReader(file_path)
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                text_content += page_text + "\n"
                pages_metadata.append((page_text, idx + 1))
        else:
            # Plain text/markdown
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text_content = f.read()
            pages_metadata.append((text_content, 1))
            
        if not text_content.strip():
            raise ValueError("No text could be extracted from the document.")
            
        # 2. Detect company & summary & tag using text content
        company_name = detect_company_name(filename, text_content)
        summary, tag = generate_doc_summary_and_tag(filename, text_content)
        
        # 3. Chunk text using LangChain
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        chunks = []
        metadatas = []
        
        if filename.lower().endswith(".pdf"):
            for page_text, page_num in pages_metadata:
                if not page_text.strip():
                    continue
                page_chunks = text_splitter.split_text(page_text)
                for chunk in page_chunks:
                    chunks.append(chunk)
                    metadatas.append({
                        "source": filename,
                        "company": company_name,
                        "page": page_num,
                        "section": f"Page {page_num}"
                    })
        else:
            file_chunks = text_splitter.split_text(text_content)
            for idx, chunk in enumerate(file_chunks):
                chunks.append(chunk)
                metadatas.append({
                    "source": filename,
                    "company": company_name,
                    "section": f"Section {idx + 1}"
                })
                
        # 4. Generate embeddings and save to vector store
        vector_store.add_chunks(doc_id, chunks, metadatas)
        
        # 5. Update document status to Indexed
        update_document_status(doc_id, "Indexed", company=company_name, tag=tag, description=summary)
        print(f"Successfully indexed document ID: {doc_id} (Company: {company_name})")
        
    except Exception as e:
        print(f"Error processing document {filename}: {e}")
        update_document_status(doc_id, "Failed", description=f"Failed to index: {str(e)}")

@app.post("/api/chat")
async def chat_query(request: ChatRequest):
    try:
        ensure_chat_services_ready()
        response = rag_pipeline.query(request.message)
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents")
async def list_documents():
    try:
        ensure_database_ready()
        return get_all_documents()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(default_factory=list),
    file: UploadFile | None = File(default=None),
):
    ensure_chat_services_ready()
    selected_files = files if files else ([file] if file else [])
    if not selected_files:
        raise HTTPException(status_code=400, detail="No file was provided.")

    uploaded_docs = []
    os.makedirs(settings.DOCUMENTS_DIR, exist_ok=True)

    for upload_file in selected_files:
        allowed_exts = [".pdf", ".txt", ".md"]
        _, ext = os.path.splitext(upload_file.filename or "")
        if ext.lower() not in allowed_exts:
            raise HTTPException(status_code=400, detail=f"Only PDF, TXT, and MD files are supported. Invalid file: {upload_file.filename}")

        original_name = os.path.basename(upload_file.filename or "")
        safe_name = f"{uuid.uuid4().hex}_{original_name}"
        file_path = os.path.join(settings.DOCUMENTS_DIR, safe_name)

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file {upload_file.filename}: {str(e)}")

        size_bytes = os.path.getsize(file_path)
        if size_bytes > settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024:
            os.remove(file_path)
            raise HTTPException(status_code=413, detail=f"{original_name} exceeds the {settings.UPLOAD_MAX_SIZE_MB} MB upload limit.")
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

        try:
            doc_id = add_document(
                filename=original_name,
                storage_size=size_str,
                status="Processing",
                description="Extracting text and generating vector index...",
                stored_filename=safe_name,
            )
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"Database error for {upload_file.filename}: {str(e)}")

        background_tasks.add_task(
            process_and_index_document,
            doc_id,
            file_path,
            original_name,
        )

        uploaded_docs.append({
            "id": doc_id,
            "filename": upload_file.filename,
            "storage_size": size_str,
            "status": "Processing",
        })

    if len(uploaded_docs) == 1:
        return {
            "message": "File uploaded successfully. Processing started in background.",
            "document": uploaded_docs[0],
        }

    return {
        "message": f"{len(uploaded_docs)} files uploaded successfully. Processing started in background.",
        "documents": uploaded_docs,
    }

@app.delete("/api/documents/{id}")
async def delete_document_endpoint(id: int):
    ensure_database_ready()
    # Fetch file details to remove from disk
    doc = get_document_by_id(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    stored_filename = doc.get("stored_filename") or doc.get("filename")
    file_path = os.path.join(settings.DOCUMENTS_DIR, stored_filename)

    try:
        # Delete from DB (metadata and embeddings)
        delete_document(id)

        # Delete from disk
        if os.path.exists(file_path):
            os.remove(file_path)

        return {"message": "Document successfully deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        log_level=settings.LOG_LEVEL.lower()
    )
