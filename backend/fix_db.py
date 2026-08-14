from app.db.session import get_engine
from sqlalchemy import text

engine = get_engine()
with engine.begin() as conn:
    print("Dropping checkpoint_migrations...")
    conn.execute(text("DROP TABLE IF EXISTS checkpoint_migrations CASCADE;"))
    

    conn.execute(text("DROP TABLE IF EXISTS checkpoints CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS checkpoint_blobs CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS checkpoint_writes CASCADE;"))
    print("LangGraph tables dropped successfully!")
