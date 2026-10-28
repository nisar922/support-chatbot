from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db import engine, Base, get_db
from app import models
from app.routers import auth,chat

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Support Chatbot")

app.include_router(auth.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"db": "ok"}