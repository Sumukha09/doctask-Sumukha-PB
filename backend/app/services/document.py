import hashlib
import os
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.document import Document


def get_or_create_document(session: Session, run_id: uuid.UUID, file_path: str) -> Document:
    """Read a file, hash it, and return the deduplicated Document record.

    If a Document with the same hash already exists, returns the existing record.
    Gracefully handles concurrent insertion race conditions via IntegrityError.

    Args:
        session: Active SQLAlchemy session.
        run_id: The UUID of the run that initiated ingestion.
        file_path: The local filesystem path to the document.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path is a directory, not a file.
        OSError: If reading the file fails.
        RuntimeError: If a database error occurs outside of the expected race condition.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    if not os.path.isfile(file_path):
        raise IsADirectoryError(f"Path is not a regular file: {file_path}")

    with open(file_path, "rb") as f:
        content = f.read()

    file_hash = hashlib.sha256(content).hexdigest()
    byte_size = len(content)
    name = os.path.basename(file_path)

    # Fast path: check for duplicate hash
    existing = session.query(Document).filter_by(hash=file_hash).first()
    if existing:
        return existing

    document = Document(
        run_id=run_id,
        hash=file_hash,
        name=name,
        byte_size=byte_size,
        metadata_json={"source": file_path},
    )
    session.add(document)
    
    try:
        session.commit()
        return document
    except IntegrityError as e:
        session.rollback()
        # Race condition handling: check if someone else inserted it while we were trying
        existing = session.query(Document).filter_by(hash=file_hash).first()
        if existing:
            return existing
        else:
            raise RuntimeError(f"Database error during document insertion: {e}") from e

def get_document(session: Session, document_id: uuid.UUID) -> Document | None:
    """Retrieve a document by its ID."""
    return session.get(Document, document_id)
