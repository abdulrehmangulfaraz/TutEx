from dotenv import load_dotenv
import os

load_dotenv()  # Load variables from .env file

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "postgresql://your_username:your_password@localhost/tutex_db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False