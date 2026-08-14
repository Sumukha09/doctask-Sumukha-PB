import sys
import os

# Add backend directory to sys.path so app modules can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.db.session import get_session_factory
from app.models.run import Run
from sqlalchemy import delete

def delete_all_runs():
    session_factory = get_session_factory()
    with session_factory() as session:
        # Run table has cascade="all, delete-orphan" configured,
        # but bulk delete might not trigger cascades in SQLAlchemy depending on the DB level constraints.
        # FlowDocs has ON DELETE CASCADE on the foreign keys in the DB via Alembic,
        # so a simple bulk delete will wipe all related findings, claims, evidence, etc.
        try:
            num_deleted = session.query(Run).delete()
            session.commit()
            print(f"Successfully deleted {num_deleted} runs from the database.")
        except Exception as e:
            session.rollback()
            print(f"Error deleting runs: {e}")

if __name__ == "__main__":
    delete_all_runs()
