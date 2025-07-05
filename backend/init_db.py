import sys
import os

# Add Tutex/ to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from backend.models import Base
from backend.database import DATABASE_URL

def init_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)  # This creates all tables

if __name__ == "__main__":
    init_db()
    print("Database tables created successfully")