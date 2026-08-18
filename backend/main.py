import os
import sys
from pathlib import Path

# Add backend directory to sys.path to support execution from repository root
sys.path.append(str(Path(__file__).resolve().parent))

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
    delete_document,
    run_schema_migration,
    init_storage
)
from vector_store import vector_store
from rag import rag_pipeline

# Import LangChain text splitter and PDF reader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from fastapi import Response

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
    document_id: Optional[int] = None


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
        # 1. Run database schema migrations if tables do not exist
        run_schema_migration()
        # 2. Ensure storage bucket is created
        init_storage()
        # 3. Verify API connection
        init_db()
        app.state.supabase_error = None
    except Exception as exc:
        app.state.supabase_error = str(exc)
        logger.warning(f"Database or storage startup degraded: {exc}")


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
    Detects company/organization name dynamically from text snippet using Gemini,
    with a fallback to parsing the filename.
    """
    try:
        if gemini_is_configured() and sample_text.strip():
            llm = ChatGoogleGenerativeAI(
                model=settings.LLM_MODEL,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.0
            )
            prompt = (
                "Identify the primary company or organization name mentioned in the following text. "
                "If no clear company/organization name is mentioned, try to deduce it or return 'Corporate'. "
                "Provide ONLY the name, nothing else (maximum 3 words).\n\n"
                f"Document Title: {filename}\n"
                f"Text snippet: {sample_text[:1200]}"
            )
            response = llm.invoke(prompt)
            detected = extract_text_content(response.content).strip()
            # Clean response from any markdown or formatting issues
            detected = detected.replace('"', '').replace("'", "").strip()
            if detected and len(detected) < 40 and "error" not in detected.lower():
                return detected
    except Exception as e:
        print(f"Error detecting company name dynamically: {e}")
        
    # Fallback parser
    base = filename.split('.')[0].replace('_', ' ').replace('-', ' ')
    words = base.split()
    if len(words) > 0 and len(words[0]) > 2 and words[0].lower() not in ["sample", "global", "corporate", "remote", "leave", "employee", "handbook", "policy"]:
        return words[0].capitalize()
        
    return "Corporate"

def generate_doc_summary_and_tag(filename: str, sample_text: str) -> tuple[str, str]:
    """
    Uses Gemini to dynamically generate a 1-sentence description and a category tag for the document.
    """
    summary = f"Document outlining details for {filename.split('.')[0]}."
    tag = "DOCUMENT"
    
    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.0
        )
        prompt = (
            "You are a document analyzer. Read this snippet of a document and return two things:\n"
            "1. A 1-sentence summary description (maximum 25 words) explaining what this document is. Make it professional.\n"
            "2. A short category tag (3 to 12 characters, alphanumeric, capitalized, e.g., 'PRICE-LIST', 'SERVICES', 'GUIDELINE', 'OFFERS', 'CONTRACT', 'FAQ', 'POLICY').\n\n"
            f"Document Title: {filename}\n"
            f"Snippet: {sample_text[:1500]}\n\n"
            "Format the output exactly as:\n"
            "Summary: <your summary>\n"
            "Tag: <your tag>"
        )
        try:
            response = llm.invoke(prompt)
            output = extract_text_content(response.content).strip()
        except Exception as model_err:
            print(f"Primary summary/tag LLM failed: {model_err}. Trying fallback gemini-2.5-flash...")
            fallback_llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.0
            )
            response = fallback_llm.invoke(prompt)
            output = extract_text_content(response.content).strip()
            
        for line in output.split("\n"):
            if line.strip().startswith("Summary:"):
                summary = line.replace("Summary:", "").strip()
            elif line.strip().startswith("Tag:"):
                tag = line.replace("Tag:", "").strip().upper()
                
    except Exception as e:
        print(f"Summary/Tag generation error: {e}")
        # Default tag detection as a fallback
        fname_lower = filename.lower()
        if "price" in fname_lower or "rate" in fname_lower or "cost" in fname_lower:
            tag = "PRICE-LIST"
        elif "service" in fname_lower:
            tag = "SERVICES"
        elif "offer" in fname_lower or "deal" in fname_lower:
            tag = "OFFERS"
        elif "employee" in fname_lower or "hr" in fname_lower or "conduct" in fname_lower:
            tag = "HR-POL"
        else:
            tag = "DOCUMENT"
            
    return summary, tag

def process_and_index_document(doc_id: int, stored_filename: str, filename: str):
    """
    Background task to parse documents from Supabase Storage, chunk them, embed, and store in Supabase.
    """
    try:
        # Download file bytes from Supabase Storage
        from supabase import create_client
        supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
        file_bytes = supabase_client.storage.from_("policies").download(stored_filename)

        text_content = ""
        pages_metadata = []
        lower_filename = filename.lower()
        
        # 1. Extract text from file
        if lower_filename.endswith(".pdf"):
            import io
            reader = PdfReader(io.BytesIO(file_bytes))
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                text_content += page_text + "\n"
                pages_metadata.append((page_text, idx + 1))
        elif lower_filename.endswith((".png", ".jpg", ".jpeg")):
            # Perform Gemini Multimodal OCR on the image
            import base64
            image_b64 = base64.b64encode(file_bytes).decode("utf-8")
            ext = os.path.splitext(lower_filename)[1].lower()
            mime_type = f"image/{ext[1:] if ext != '.jpg' else 'jpeg'}"
            
            message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            "You are a policy assistant. Analyze this corporate policy document image. "
                            "Transcribe all visible text, tables, numbers, compliance guidelines, and policies exactly. "
                            "Output a clean, detailed text layout suitable for vector chunking. Do not include introductory notes or markdown metadata headers, just output the transcribed content."
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}
                    }
                ]
            )
            
            llm = ChatGoogleGenerativeAI(
                model=settings.LLM_MODEL,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.0
            )
            response = llm.invoke([message])
            text_content = response.content
            pages_metadata.append((text_content, 1))
        else:
            # Plain text/markdown
            text_content = file_bytes.decode("utf-8", errors="ignore")
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
        
        if lower_filename.endswith(".pdf"):
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
        response = rag_pipeline.query(request.message, request.document_id)
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

    for upload_file in selected_files:
        allowed_exts = [".pdf", ".txt", ".md", ".png", ".jpg", ".jpeg"]
        _, ext = os.path.splitext(upload_file.filename or "")
        if ext.lower() not in allowed_exts:
            raise HTTPException(status_code=400, detail=f"Only PDF, TXT, MD, PNG, JPG, and JPEG files are supported. Invalid file: {upload_file.filename}")

        original_name = os.path.basename(upload_file.filename or "")
        safe_name = f"{uuid.uuid4().hex}_{original_name}"

        try:
            file_bytes = await upload_file.read()
            size_bytes = len(file_bytes)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read file {upload_file.filename}: {str(e)}")

        if size_bytes > settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"{original_name} exceeds the {settings.UPLOAD_MAX_SIZE_MB} MB upload limit.")
            
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

        try:
            from supabase import create_client
            supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
            supabase_client.storage.from_("policies").upload(
                path=safe_name,
                file=file_bytes,
                file_options={"content-type": upload_file.content_type or "application/octet-stream"}
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload {upload_file.filename} to Supabase Storage: {str(e)}")

        try:
            doc_id = add_document(
                filename=original_name,
                storage_size=size_str,
                status="Processing",
                description="Extracting text and generating vector index...",
                stored_filename=safe_name,
            )
        except Exception as e:
            try:
                supabase_client.storage.from_("policies").remove([safe_name])
            except:
                pass
            raise HTTPException(status_code=500, detail=f"Database error for {upload_file.filename}: {str(e)}")

        background_tasks.add_task(
            process_and_index_document,
            doc_id,
            safe_name,
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

@app.get("/api/documents/file/{stored_filename}")
async def get_document_file(stored_filename: str):
    """
    Streams the uploaded document or image file directly from Supabase Storage.
    """
    try:
        from supabase import create_client
        supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
        file_bytes = supabase_client.storage.from_("policies").download(stored_filename)
        
        # Determine content type dynamically
        ext = os.path.splitext(stored_filename)[1].lower()
        mime_types = {
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif"
        }
        mime_type = mime_types.get(ext, "application/octet-stream")
        
        return Response(content=file_bytes, media_type=mime_type)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")

@app.delete("/api/documents/{id}")
async def delete_document_endpoint(id: int):
    ensure_database_ready()
    doc = get_document_by_id(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    stored_filename = doc.get("stored_filename") or doc.get("filename")

    try:
        # Delete from DB (metadata and embeddings)
        delete_document(id)

        # Delete from Supabase Storage
        from supabase import create_client
        supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
        try:
            supabase_client.storage.from_("policies").remove([stored_filename])
        except Exception as storage_err:
            logger.warning(f"Could not remove {stored_filename} from storage: {storage_err}")

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
