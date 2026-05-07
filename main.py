import os
import io
import logging
import tempfile
from typing import List, Optional, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# App startup
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Drive Chatbot API...")
    # Pre-load embedding model so first request isn't slow
    try:
        from embedder import get_embedding_model
        get_embedding_model()
        logger.info("Embedding model loaded.")
    except Exception as e:
        logger.warning(f"Could not pre-load embedding model: {e}")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Drive Chatbot API",
    description="RAG-powered Q&A over Google Drive files using Groq + ChromaDB",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────

class IngestRequest(BaseModel):
    drive_link: str                         # Google Drive file or folder URL
    use_vision: bool = True                 # Use Groq Vision for images
    reset_store: bool = False               # Wipe existing data first

class IngestResponse(BaseModel):
    status: str
    files_processed: int
    chunks_stored: int
    total_chunks: int
    files: List[str]
    errors: List[str]

class ChatRequest(BaseModel):
    question: str
    history: List[Dict[str, str]] = []      # [{"role": "user", "content": "..."}]
    filter_file: Optional[str] = None       # restrict to one file
    model: str = "llama-3.3-70b-versatile"
    top_k: int = 5

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    model: str
    chunks_used: int
    usage: Dict


# ─────────────────────────────────────────────
# Google Drive helpers
# ─────────────────────────────────────────────

def parse_drive_link(link: str) -> tuple[str, str]:
    """
    Extract file/folder ID and type from a Google Drive URL.
    Returns (item_id, item_type) where item_type is 'file' or 'folder'.
    """
    import re

    # Folder: /folders/{id}
    folder_match = re.search(r"/folders/([a-zA-Z0-9_-]+)", link)
    if folder_match:
        return folder_match.group(1), "folder"

    # File: /file/d/{id} or /d/{id} or ?id={id}
    file_match = re.search(r"/d/([a-zA-Z0-9_-]+)", link)
    if file_match:
        return file_match.group(1), "file"

    id_match = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", link)
    if id_match:
        return id_match.group(1), "file"

    raise ValueError(f"Could not parse Google Drive ID from link: {link}")


def get_drive_service():
    """Build authenticated Google Drive service."""
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]

    # Try service account first
    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
    if os.path.exists(creds_path):
        credentials = service_account.Credentials.from_service_account_file(
            creds_path, scopes=scopes
        )
        return build("drive", "v3", credentials=credentials)
    
    # Fallback to OAuth2
    elif os.path.exists('credentials.json'):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', scopes)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
                creds = flow.run_local_server(port=0)
            
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
                
        return build('drive', 'v3', credentials=creds)

    else:
        raise FileNotFoundError(
            "Authentication file not found. "
            "Please provide 'service_account.json' or 'credentials.json'."
        )


def list_drive_files(folder_id: str, drive_service) -> List[Dict]:
    """Recursively list all files in a Drive folder."""
    files = []
    page_token = None

    while True:
        response = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageToken=page_token,
            pageSize=100,
        ).execute()

        for item in response.get("files", []):
            if item["mimeType"] == "application/vnd.google-apps.folder":
                # Recurse into subfolders
                files.extend(list_drive_files(item["id"], drive_service))
            else:
                files.append(item)

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return files


def download_drive_file(file_id: str, mime_type: str, drive_service) -> bytes:
    """Download file bytes from Drive, handling Google Docs export."""
    from googleapiclient.http import MediaIoBaseDownload

    EXPORT_MAP = {
        "application/vnd.google-apps.document":
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.google-apps.spreadsheet":
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.google-apps.presentation":
            "application/pdf",
    }

    buf = io.BytesIO()
    if mime_type in EXPORT_MAP:
        req = drive_service.files().export_media(fileId=file_id, mimeType=EXPORT_MAP[mime_type])
    else:
        req = drive_service.files().get_media(fileId=file_id)

    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    return buf.getvalue()


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "Drive Chatbot API"}


@app.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest):
    """
    Process a Google Drive link:
    1. Fetch file(s) from Drive
    2. Extract content (Phase 2)
    3. Chunk + Embed + Store (Phase 3)
    """
    from extractor import extract_content
    from ingestion_pipeline import ingest_extracted_contents, IngestionConfig
    from types import SimpleNamespace

    errors = []
    extracted_contents = []

    try:
        item_id, item_type = parse_drive_link(req.drive_link)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        drive_service = get_drive_service()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Collect files to process
    if item_type == "folder":
        drive_files = list_drive_files(item_id, drive_service)
    else:
        meta = drive_service.files().get(
            fileId=item_id, fields="id,name,mimeType,size"
        ).execute()
        drive_files = [meta]

    if not drive_files:
        raise HTTPException(status_code=404, detail="No files found at the provided Drive link.")

    # Download + Extract each file
    EXPORT_MIME_MAP = {
        "application/vnd.google-apps.document":
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.google-apps.spreadsheet":
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    for file_meta in drive_files:
        file_id   = file_meta["id"]
        file_name = file_meta["name"]
        mime_type = file_meta["mimeType"]

        try:
            file_bytes = download_drive_file(file_id, mime_type, drive_service)
            # Remap Google Docs MIME for extractor
            effective_mime = EXPORT_MIME_MAP.get(mime_type, mime_type)

            content = extract_content(
                file_bytes=file_bytes,
                file_name=file_name,
                mime_type=effective_mime,
                use_vision_for_images=req.use_vision,
            )

            if content.error:
                errors.append(f"{file_name}: {content.error}")
            else:
                extracted_contents.append(content)

        except Exception as e:
            errors.append(f"{file_name}: {str(e)}")
            logger.error(f"Error processing {file_name}: {e}")

    if not extracted_contents:
        raise HTTPException(
            status_code=422,
            detail=f"No content could be extracted. Errors: {errors}"
        )

    # Ingest into vector store
    config = IngestionConfig(reset_store=req.reset_store)
    stats = ingest_extracted_contents(extracted_contents, config=config)

    return IngestResponse(
        status="success",
        files_processed=len(extracted_contents),
        chunks_stored=stats.get("stored_this_run", 0),
        total_chunks=stats.get("total_chunks", 0),
        files=stats.get("files", []),
        errors=errors,
    )


@app.post("/upload", response_model=IngestResponse)
async def upload_file(file: UploadFile = File(...), use_vision: bool = True, reset_store: bool = False):
    """
    Process a local file upload:
    1. Extract content (Phase 2)
    2. Chunk + Embed + Store (Phase 3)
    """
    from extractor import extract_content
    from ingestion_pipeline import ingest_extracted_contents, IngestionConfig

    file_bytes = await file.read()

    content = extract_content(
        file_bytes=file_bytes,
        file_name=file.filename,
        mime_type=file.content_type,
        use_vision_for_images=use_vision,
    )

    if content.error:
        raise HTTPException(status_code=422, detail=content.error)

    config = IngestionConfig(reset_store=reset_store)
    stats = ingest_extracted_contents([content], config=config)

    return IngestResponse(
        status="success",
        files_processed=1,
        chunks_stored=stats.get("stored_this_run", 0),
        total_chunks=stats.get("total_chunks", 0),
        files=stats.get("files", []),
        errors=[],
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """RAG-powered Q&A: retrieve context → Groq → answer."""
    from chatbot import chat_with_docs
    from vector_store import get_store_stats

    stats = get_store_stats()
    if stats["total_chunks"] == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents indexed yet. Please POST to /ingest first."
        )

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = chat_with_docs(
        question=req.question,
        chat_history=req.history,
        model=req.model,
        top_k=req.top_k,
        filter_file=req.filter_file,
    )

    return ChatResponse(**result)


@app.get("/files")
async def list_files():
    """List all files currently indexed in the vector store."""
    from vector_store import list_stored_files, get_store_stats
    stats = get_store_stats()
    return {
        "files": stats.get("files", []),
        "total_files": stats.get("total_files", 0),
        "total_chunks": stats.get("total_chunks", 0),
    }


@app.delete("/files/{file_name}")
async def delete_file(file_name: str):
    """Remove all chunks for a specific file from the vector store."""
    from vector_store import delete_file_chunks
    deleted = delete_file_chunks(file_name)
    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"File '{file_name}' not found in index.")
    return {"message": f"Deleted {deleted} chunks for '{file_name}'"}


@app.get("/stats")
async def stats():
    """Return vector store statistics."""
    from vector_store import get_store_stats
    return get_store_stats()
