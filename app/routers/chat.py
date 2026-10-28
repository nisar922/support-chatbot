from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import get_current_user
from app.models import Conversation, Message, User
from app.schemas import ChatRequest, ChatResponse, MessageOut
from app.services import llm

router = APIRouter(prefix="/chat", tags=["chat"])

UNKNOWN_MARKER = "[UNKNOWN]"
HISTORY_LIMIT = 10

SYSTEM_PROMPT = (
    "You are a helpful customer support assistant. "
    "Answer clearly and briefly. "
    "If you cannot answer confidently, start your reply with "
    f"{UNKNOWN_MARKER} and politely say a human agent will follow up."
)
@router.post("", response_model=ChatResponse)
def chat(
    data: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.conversation_id:
        convo = db.get(Conversation, data.conversation_id)
        if convo is None or convo.user_id != user.id:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        convo = Conversation(user_id=user.id)
        db.add(convo)
        db.commit()
        db.refresh(convo)

    history = (
        db.query(Message)
        .filter(Message.conversation_id == convo.id)
        .order_by(Message.id.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    history.reverse()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": data.message})

    try:
        reply = llm.generate(messages)
    except llm.LLMError:
        raise HTTPException(status_code=502, detail="LLM service unavailable")

    resolved = UNKNOWN_MARKER not in reply
    reply = reply.replace(UNKNOWN_MARKER, "").strip()


    db.add_all(
        [
            Message(conversation_id=convo.id, role="user",
                    content=data.message, resolved=resolved),
            Message(conversation_id=convo.id, role="assistant",
                    content=reply, resolved=resolved),
        ]
    )
    db.commit()
    return ChatResponse(conversation_id=convo.id, reply=reply, resolved=resolved)


@router.get("/conversations/{conversation_id}", response_model=list[MessageOut])
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    convo = db.get(Conversation, conversation_id)
    if convo is None or convo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return (
        db.query(Message)
        .filter(Message.conversation_id == convo.id)
        .order_by(Message.id)
        .all()
    )