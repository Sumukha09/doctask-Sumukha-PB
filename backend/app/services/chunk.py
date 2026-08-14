import uuid

from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk


def create_chunks(
    session: Session, document_id: uuid.UUID, run_id: uuid.UUID, contents: list[str]
) -> list[DocumentChunk]:
    """Bulk insert chunks for a document.

    Automatically assigns incrementing chunk_index values starting from 0.

    Args:
        session: Active SQLAlchemy session.
        document_id: The UUID of the parent Document.
        run_id: The UUID of the Run extracting these chunks.
        contents: A list of raw text strings for each chunk.

    Returns:
        A list of the created DocumentChunk objects.
    """
    if not contents:
        return []

    chunks = [
        DocumentChunk(
            document_id=document_id,
            run_id=run_id,
            chunk_index=i,
            text=content,
        )
        for i, content in enumerate(contents)
    ]
    
    session.add_all(chunks)
    session.commit()
    
    return chunks

def get_chunk(session: Session, chunk_id: uuid.UUID) -> DocumentChunk | None:
    """Retrieve a chunk by its ID."""
    return session.get(DocumentChunk, chunk_id)
