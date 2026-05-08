import os
import io
import json
import logging
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import (
    init_db, get_db,
    create_session, get_session, list_sessions, delete_session, rename_session,
    add_message, get_session_messages, clear_session_messages,
    upsert_drive_link, list_drive_links,
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialized.")
    try:
        from embedder import get_embedding_model
        get_embedding_model()
        logger.info("Embedding model loaded.")
    except Exception as e:
        logger.warning(f"Embedding model preload failed: {e}")
    yield


app = FastAPI(
    title="Drive Chatbot API — Phase 6",
    description="RAG chatbot with Voice I/O and persistent chat history",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from citation_router import router as citation_router
app.include_router(citation_router)


# ─────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: str = "New Chat"
    file_filter: Optional[str] = None
    model: str = "llama-3.3-70b-versatile"

class SessionRename(BaseModel):
    title: str

class ChatRequest(BaseModel):
    question: str
    model: str = "llama-3.3-70b-versatile"
    top_k: int = 5
    enable_tts: bool = False         # auto-generate TTS for response
    voice: str = "nova"              # TTS voice

class IngestRequest(BaseModel):
    drive_link: str
    use_vision: bool = True
    reset_store: bool = False

class IngestResponse(BaseModel):
    status: str
    files_processed: int
    chunks_stored: int
    total_chunks: int
    files: List[str]
    errors: List[str]

class TTSRequest(BaseModel):
    text: str
    voice: str = "nova"
    speed: float = 1.0


# ─────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "features": ["rag", "voice", "history"]}


# ─────────────────────────────────────────────
# Google Drive helpers
# ─────────────────────────────────────────────

def parse_drive_link(link: str) -> tuple[str, str]:
    import re
    folder_match = re.search(r"/folders/([a-zA-Z0-9_-]+)", link)
    if folder_match: return folder_match.group(1), "folder"
    file_match = re.search(r"/d/([a-zA-Z0-9_-]+)", link)
    if file_match: return file_match.group(1), "file"
    id_match = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", link)
    if id_match: return id_match.group(1), "file"
    raise ValueError(f"Could not parse Google Drive ID from link: {link}")


def get_drive_service():
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]

    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
    if os.path.exists(creds_path):
        credentials = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
        return build("drive", "v3", credentials=credentials)
    
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
        raise FileNotFoundError("Authentication file not found.")


def list_drive_files(folder_id: str, drive_service) -> List[Dict]:
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
                files.extend(list_drive_files(item["id"], drive_service))
            else:
                files.append(item)
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return files


def download_drive_file(file_id: str, mime_type: str, drive_service) -> bytes:
    from googleapiclient.http import MediaIoBaseDownload
    EXPORT_MAP = {
        "application/vnd.google-apps.document": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.google-apps.presentation": "application/pdf",
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
# Ingest
# ─────────────────────────────────────────────

@app.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest, db: Session = Depends(get_db)):
    from extractor import extract_content
    from ingestion_pipeline import ingest_extracted_contents, IngestionConfig

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

    if item_type == "folder":
        drive_files = list_drive_files(item_id, drive_service)
    else:
        meta = drive_service.files().get(fileId=item_id, fields="id,name,mimeType,size").execute()
        drive_files = [meta]

    if not drive_files:
        raise HTTPException(status_code=404, detail="No files found at the provided Drive link.")

    EXPORT_MIME_MAP = {
        "application/vnd.google-apps.document": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    for file_meta in drive_files:
        file_id   = file_meta["id"]
        file_name = file_meta["name"]
        mime_type = file_meta["mimeType"]

        try:
            file_bytes = download_drive_file(file_id, mime_type, drive_service)
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
        raise HTTPException(status_code=422, detail=f"No content could be extracted. Errors: {errors}")

    config = IngestionConfig(reset_store=req.reset_store)
    stats = ingest_extracted_contents(extracted_contents, config=config)

    upsert_drive_link(
        db, req.drive_link, item_id, item_type,
        files_count=len(extracted_contents),
        chunks_count=stats.get("stored_this_run", 0),
    )

    return IngestResponse(
        status="success",
        files_processed=len(extracted_contents),
        chunks_stored=stats.get("stored_this_run", 0),
        total_chunks=stats.get("total_chunks", 0),
        files=stats.get("files", []),
        errors=errors,
    )


@app.post("/upload", response_model=IngestResponse)
async def upload_file(file: UploadFile = File(...), use_vision: bool = True, reset_store: bool = False, db: Session = Depends(get_db)):
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


# ─────────────────────────────────────────────
# Session endpoints
# ─────────────────────────────────────────────

async def get_current_user(x_user_email: Optional[str] = Header("anonymous")):
    return x_user_email

@app.post("/sessions", status_code=201)
async def create_chat_session(req: SessionCreate, db: Session = Depends(get_db), user_email: str = Depends(get_current_user)):
    session = create_session(db, title=req.title, file_filter=req.file_filter, model=req.model, user_email=user_email)
    return _session_dict(session)


@app.get("/sessions")
async def get_all_sessions(db: Session = Depends(get_db), user_email: str = Depends(get_current_user)):
    sessions = list_sessions(db, user_email=user_email)
    return [_session_dict(s) for s in sessions]


@app.get("/sessions/{session_id}")
async def get_one_session(session_id: str, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(404, "Session not found.")
    messages = get_session_messages(db, session_id)
    return {**_session_dict(session), "messages": messages}


@app.patch("/sessions/{session_id}/rename")
async def rename_chat_session(session_id: str, req: SessionRename, db: Session = Depends(get_db)):
    session = rename_session(db, session_id, req.title)
    if not session:
        raise HTTPException(404, "Session not found.")
    return _session_dict(session)


@app.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str, db: Session = Depends(get_db)):
    ok = delete_session(db, session_id)
    if not ok:
        raise HTTPException(404, "Session not found.")
    return {"message": f"Session {session_id} deleted."}


# ─────────────────────────────────────────────
# Chat with history
# ─────────────────────────────────────────────

@app.post("/sessions/{session_id}/chat")
async def chat_in_session(
    session_id: str,
    req: ChatRequest,
    db: Session = Depends(get_db),
):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(404, "Session not found.")

    from vector_store import get_store_stats
    if get_store_stats()["total_chunks"] == 0:
        raise HTTPException(400, "No documents indexed. POST to /ingest first.")

    from chatbot import chat_with_docs

    all_msgs   = get_session_messages(db, session_id)
    history    = [{"role": m["role"], "content": m["content"]} for m in all_msgs[-10:]]

    result = chat_with_docs(
        question=req.question,
        chat_history=history,
        model=req.model,
        top_k=req.top_k,
        filter_file=session.file_filter,
    )

    add_message(db, session_id, "user", req.question)

    saved_msg = add_message(
        db, session_id, "assistant",
        content=result["answer"],
        sources=result["sources"],
        chunks_used=result["chunks_used"],
        prompt_tokens=result["usage"]["prompt_tokens"],
        completion_tokens=result["usage"]["completion_tokens"],
        has_audio=req.enable_tts,
        voice=req.voice if req.enable_tts else None,
    )

    response = {
        "message_id": saved_msg.id,
        "answer":      result["answer"],
        "sources":     result["sources"],
        "chunks_used": result["chunks_used"],
        "model":       result["model"],
        "usage":       result["usage"],
        "session_id":  session_id,
    }

    return response


@app.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(404, "Session not found.")
    return get_session_messages(db, session_id)


@app.delete("/sessions/{session_id}/messages")
async def clear_messages(session_id: str, db: Session = Depends(get_db)):
    count = clear_session_messages(db, session_id)
    return {"message": f"Cleared {count} messages."}


# ─────────────────────────────────────────────
# Voice endpoints
# ─────────────────────────────────────────────

@app.post("/voice/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    from voice import transcribe_audio

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(400, "Empty audio file.")

    try:
        result = transcribe_audio(
            audio_bytes=audio_bytes,
            filename=audio.filename or "audio.webm",
            language=language or None,
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"Transcription failed: {str(e)}")


@app.post("/voice/speak")
async def speak(req: TTSRequest):
    from voice import text_to_speech

    if not req.text.strip():
        raise HTTPException(400, "Text cannot be empty.")

    try:
        audio_bytes = text_to_speech(req.text, voice=req.voice, speed=req.speed)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"},
        )
    except Exception as e:
        raise HTTPException(500, f"TTS failed: {str(e)}")


@app.get("/voice/voices")
async def list_voices():
    from voice import VOICES
    return {"voices": [{"id": k, "label": v} for k, v in VOICES.items()]}


# ─────────────────────────────────────────────
# Files / Stats (Phase 4 retained)
# ─────────────────────────────────────────────

@app.get("/files")
async def list_files():
    from vector_store import get_store_stats
    stats = get_store_stats()
    return {"files": stats.get("files", []), "total_chunks": stats.get("total_chunks", 0)}


@app.delete("/files/{file_name}")
async def delete_file(file_name: str):
    from vector_store import delete_file_chunks
    deleted = delete_file_chunks(file_name)
    if deleted == 0:
        raise HTTPException(404, f"File '{file_name}' not found in index.")
    return {"message": f"Deleted {deleted} chunks for '{file_name}'"}


@app.get("/stats")
async def stats(db: Session = Depends(get_db)):
    from vector_store import get_store_stats
    vs = get_store_stats()
    links = list_drive_links(db)
    return {
        **vs,
        "drive_links_indexed": len(links),
        "drive_links": [
            {"link": l.drive_link, "files": l.files_count, "chunks": l.chunks_count, "at": l.indexed_at.isoformat()}
            for l in links
        ],
    }


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _session_dict(s) -> dict:
    return {
        "id":            s.id,
        "title":         s.title,
        "model":         s.model,
        "file_filter":   s.file_filter,
        "message_count": s.message_count,
        "created_at":    s.created_at.isoformat(),
        "updated_at":    s.updated_at.isoformat(),
    }
