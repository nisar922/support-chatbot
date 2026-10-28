from sqlalchemy.orm import Session
from app.models import Chunk, Document
from app.services.embeddings import embed

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
TOP_K = 4
MAX_DISTANCE = 0.5  # isse zyada door wale chunks ko irrelevant maante hain


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        piece = text[start:start + size].strip()
        if piece:
            chunks.append(piece)
        if start + size >= len(text):
            break
        start += size - overlap
    return chunks


def add_document(db: Session, filename: str, text: str):
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("Document is empty")
    vectors = embed(chunks)
    doc = Document(filename=filename)
    db.add(doc)
    db.flush()
    db.add_all(
        [Chunk(document_id=doc.id, content=c, embedding=v)
         for c, v in zip(chunks, vectors)]
    )
    db.commit()
    db.refresh(doc)
    return doc, len(chunks)


def search(db: Session, query: str, k: int = TOP_K) -> list[str]:
    query_vec = embed([query])[0]
    distance = Chunk.embedding.cosine_distance(query_vec)
    rows = (
        db.query(Chunk.content, distance.label("distance"))
        .order_by(distance)
        .limit(k)
        .all()
    )
    return [r.content for r in rows if r.distance <= MAX_DISTANCE]