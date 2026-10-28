from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import require_admin
from app.models import Document, User
from app.schemas import DocumentOut, DocumentUploadOut
from app.services import rag

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_FILE_BYTES = 1_000_000  # 1 MB


@router.post("", response_model=DocumentUploadOut, status_code=201)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    name = file.filename or "upload"
    if not name.lower().endswith((".txt", ".md")):
        raise HTTPException(status_code=400, detail="Only .txt or .md files allowed")
    raw = file.file.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 1 MB)")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 text")
    try:
        doc, count = rag.add_document(db, name, text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return DocumentUploadOut(id=doc.id, filename=doc.filename, chunks=count)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    return db.query(Document).order_by(Document.id.desc()).all()

@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()