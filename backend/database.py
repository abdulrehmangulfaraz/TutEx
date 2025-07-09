import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get database credentials from environment variables
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

# Database connection URL constructed from environment variables
DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # The number of connections to keep open in the pool
    max_overflow=10,       # The number of extra connections to allow beyond pool_size
    pool_timeout=30,       # How long to wait for a connection before timing out
    pool_recycle=1800      # Recycle connections after 30 minutes to prevent stale connections
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()