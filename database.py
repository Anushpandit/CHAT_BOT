import os
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    create_engine, Column, String, Text, DateTime,
    Integer, ForeignKey, Boolean, Float, event
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool

# ─────────────────────────────────────────────
# DB setup
# ─────────────────────────────────────────────

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./chat_history.db")

engine = create_engine(
    DB_PATH,
    connect_args={"check_same_thread": False},   # needed for SQLite + FastAPI
    poolclass=StaticPool,
)

# Enable WAL mode for better concurrent reads
@event.listens_for(engine, "connect")
def set_sqlite_pragma(conn, _):
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class ChatSession(Base):
    __tablename__ = "sessions"

    id          = Column(String(36), primary_key=True)   # UUID
    user_email  = Column(String(150), nullable=True, default="anonymous")
    title       = Column(String(200), nullable=False, default="New Chat")
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    file_filter = Column(String(200), nullable=True)     # restrict to one file
    model       = Column(String(100), default="llama-3.3-70b-versatile")
    message_count = Column(Integer, default=0)

    messages = relationship("ChatMessage", back_populates="session",
                            cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "messages"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    session_id    = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role          = Column(String(20), nullable=False)   # "user" or "assistant"
    content       = Column(Text, nullable=False)
    sources       = Column(Text, nullable=True)          # JSON list of source file names
    chunks_used   = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    created_at    = Column(DateTime, default=datetime.utcnow)
    has_audio     = Column(Boolean, default=False)       # True if TTS was generated
    voice         = Column(String(50), nullable=True)

    session = relationship("ChatSession", back_populates="messages")


class IndexedDriveLink(Base):
    __tablename__ = "indexed_links"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    drive_link  = Column(String(500), nullable=False, unique=True)
    drive_id    = Column(String(200), nullable=False)
    item_type   = Column(String(20), nullable=False)     # "file" or "folder"
    files_count = Column(Integer, default=0)
    chunks_count = Column(Integer, default=0)
    indexed_at  = Column(DateTime, default=datetime.utcnow)
    use_vision  = Column(Boolean, default=True)


# ─────────────────────────────────────────────
# Init DB
# ─────────────────────────────────────────────

def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────────
# Session CRUD
# ─────────────────────────────────────────────

import uuid, json

def create_session(
    db: Session,
    title: str = "New Chat",
    file_filter: Optional[str] = None,
    model: str = "llama-3.3-70b-versatile",
    user_email: str = "anonymous",
) -> ChatSession:
    session = ChatSession(
        id=str(uuid.uuid4()),
        title=title,
        file_filter=file_filter,
        model=model,
        user_email=user_email,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: str) -> Optional[ChatSession]:
    return db.query(ChatSession).filter(ChatSession.id == session_id).first()


def list_sessions(db: Session, user_email: str = "anonymous", limit: int = 50) -> List[ChatSession]:
    """Return recent sessions for a user, ordered by most recently updated."""
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_email == user_email)
        .order_by(ChatSession.updated_at.desc())
        .limit(limit)
        .all()
    )


def delete_session(db: Session, session_id: str) -> bool:
    session = get_session(db, session_id)
    if not session:
        return False
    db.delete(session)
    db.commit()
    return True


def rename_session(db: Session, session_id: str, title: str) -> Optional[ChatSession]:
    session = get_session(db, session_id)
    if not session:
        return None
    session.title = title
    db.commit()
    db.refresh(session)
    return session


# ─────────────────────────────────────────────
# Message CRUD
# ─────────────────────────────────────────────

def add_message(
    db: Session,
    session_id: str,
    role: str,
    content: str,
    sources: Optional[List[str]] = None,
    chunks_used: int = 0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    has_audio: bool = False,
    voice: Optional[str] = None,
) -> ChatMessage:
    msg = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        sources=json.dumps(sources or []),
        chunks_used=chunks_used,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        has_audio=has_audio,
        voice=voice,
    )
    db.add(msg)

    # Update session metadata
    session = get_session(db, session_id)
    if session:
        session.updated_at = datetime.utcnow()
        session.message_count += 1
        # Auto-title: use first user message as session title
        if role == "user" and session.title == "New Chat":
            session.title = content[:60] + ("..." if len(content) > 60 else "")

    db.commit()
    db.refresh(msg)
    return msg


def get_session_messages(db: Session, session_id: str) -> List[dict]:
    """Return messages as plain dicts for LLM history."""
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return [
        {
            "id":           m.id,
            "role":         m.role,
            "content":      m.content,
            "sources":      json.loads(m.sources or "[]"),
            "chunks_used":  m.chunks_used,
            "prompt_tokens": m.prompt_tokens,
            "completion_tokens": m.completion_tokens,
            "has_audio":    m.has_audio,
            "voice":        m.voice,
            "created_at":   m.created_at.isoformat(),
        }
        for m in messages
    ]


def clear_session_messages(db: Session, session_id: str) -> int:
    deleted = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .delete()
    )
    session = get_session(db, session_id)
    if session:
        session.message_count = 0
    db.commit()
    return deleted


# ─────────────────────────────────────────────
# Drive link tracking
# ─────────────────────────────────────────────

def upsert_drive_link(
    db: Session,
    drive_link: str,
    drive_id: str,
    item_type: str,
    files_count: int = 0,
    chunks_count: int = 0,
    use_vision: bool = True,
) -> IndexedDriveLink:
    existing = db.query(IndexedDriveLink).filter(
        IndexedDriveLink.drive_link == drive_link
    ).first()

    if existing:
        existing.files_count  = files_count
        existing.chunks_count = chunks_count
        existing.indexed_at   = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    record = IndexedDriveLink(
        drive_link=drive_link, drive_id=drive_id, item_type=item_type,
        files_count=files_count, chunks_count=chunks_count, use_vision=use_vision,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_drive_links(db: Session) -> List[IndexedDriveLink]:
    return db.query(IndexedDriveLink).order_by(IndexedDriveLink.indexed_at.desc()).all()
