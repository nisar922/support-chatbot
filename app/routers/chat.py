from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import get_current_user
from app.models import Conversation, Message, User
from app.schemas import ChatRequest, ChatResponse, MessageOut
from app.services import llm, rag, cache
from app.services.rate_limit import rate_limit_chat

router = APIRouter(prefix="/chat", tags=["chat"])

UNKNOWN_MARKER = "[UNKNOWN]"
HISTORY_LIMIT = 10

BASE_PROMPT = (
    "You are a customer support assistant. "
    "Answer using ONLY the context below and the conversation so far. "
    "Be clear and brief. For greetings or small talk, reply normally. "
    f"If the answer is not in the context, start your reply with {UNKNOWN_MARKER} "
    "and politely say a human agent will follow up.\n\n"
)

def build_system_prompt(chunks: list[str]) -> str:
    context = "\n\n---\n\n".join(chunks) if chunks else "(no relevant context found)"
    return BASE_PROMPT + "Context:\n" + context

@router.post("", response_model=ChatResponse, dependencies=[Depends(rate_limit_chat)])
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

    reply = None
    resolved = True
    from_cache = False

    if not history:
        hit = cache.get_cached_answer(data.message)
        if hit:
            reply, resolved, from_cache = hit["reply"], hit["resolved"], True

    if reply is None:
        chunks = rag.search(db, data.message)
        messages = [{"role": "system", "content": build_system_prompt(chunks)}]
        messages += [{"role": m.role, "content": m.content} for m in history]
        messages.append({"role": "user", "content": data.message})

    try:
        reply = llm.generate(messages)
    except llm.LLMError:
        raise HTTPException(status_code=502, detail="LLM service unavailable")

    resolved = UNKNOWN_MARKER not in reply
    reply = reply.replace(UNKNOWN_MARKER, "").strip()

    if resolved and not history:
        cache.set_cached_answer(data.message, reply, resolved)

    db.add_all(
        [
            Message(conversation_id=convo.id, role="user",
                    content=data.message, resolved=resolved),
            Message(conversation_id=convo.id, role="assistant",
                    content=reply, resolved=resolved),
        ]
    )
    db.commit()
    return ChatResponse(conversation_id=convo.id, 
                        reply=reply, 
                        resolved=resolved,
                        cached=from_cache,)


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