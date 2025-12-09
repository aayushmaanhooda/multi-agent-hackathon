import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use SQLite database - always use SQLite3
# Database file will be created in the backend directory
db_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(db_dir, "roster.db")
DATABASE_URL = f"sqlite:///{db_path}"

print(f"Using SQLite database: {DATABASE_URL}")

# Create engine with SQLite-specific connection args
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite with FastAPI
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
