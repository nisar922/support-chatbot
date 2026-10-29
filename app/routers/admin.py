from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import require_admin
from app.models import Chunk, Conversation, Document, Message, User
from app.schemas import (
    ConversationSummary,
    MessageOut,
    StatsOut,
    UnresolvedQuery
)
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    total_users = db.query(func.count(User.id)).scalar()
    total_conversations = db.query(func.count(Conversation.id)).scalar()
    total_documents = db.query(func.count(Document.id)).scalar()
    total_chunks = db.query(func.count(Chunk.id)).scalar()

    user_messages = db.query(func.count(Message.id)).filter(Message.role == "user")
    total_questions = user_messages.scalar()
    unresolved = user_messages.filter(Message.resolved.is_(False)).scalar()
    resolved = total_questions - unresolved
    rate = round(resolved / total_questions * 100, 1) if total_questions else 0.0

    return StatsOut(
        total_users=total_users,
        total_conversations=total_conversations,
        total_questions=total_questions,
        resolved_questions=resolved,
        unresolved_questions=unresolved,
        resolution_rate=rate,
        total_documents=total_documents,
        total_chunks=total_chunks,
    )


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    unresolved_flag = case(
        (and_(Message.role == "user", Message.resolved.is_(False)), 1),
        else_=0,
    )
    rows = (
        db.query(
            Conversation.id.label("id"),
            User.email.label("user_email"),
            Conversation.created_at.label("created_at"),
            func.count(Message.id).label("message_count"),
            func.coalesce(func.sum(unresolved_flag), 0).label("unresolved_count"),
            func.max(Message.created_at).label("last_message_at"),
        )
        .join(User, User.id == Conversation.user_id)
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .group_by(Conversation.id, User.email, Conversation.created_at)
        .order_by(Conversation.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [r._asdict() for r in rows]


@router.get("/conversations/{conversation_id}", response_model=list[MessageOut])
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    if db.get(Conversation, conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id)
        .all()
    )


@router.get("/unresolved", response_model=list[UnresolvedQuery])
def list_unresolved(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Message.id.label("message_id"),
            Message.conversation_id.label("conversation_id"),
            User.email.label("user_email"),
            Message.content.label("question"),
            Message.created_at.label("created_at"),
        )
        .join(Conversation, Conversation.id == Message.conversation_id)
        .join(User, User.id == Conversation.user_id)
        .filter(Message.role == "user", Message.resolved.is_(False))
        .order_by(Message.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [r._asdict() for r in rows]