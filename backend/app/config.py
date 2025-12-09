from contextlib import asynccontextmanager
from fastapi import FastAPI
from .db import engine
from .models import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    print("Creating database tables if there is any new table...")
    Base.metadata.create_all(bind=engine)
    yield
    print("Database tables created.")
