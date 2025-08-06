# create_admin.py

import sys
import os
from datetime import datetime
from passlib.context import CryptContext
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

# Import from your backend
from models import User, Base
from database import DATABASE_URL  # make sure this points to correct DB

# Hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_admin_user():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Check if admin already exists
    existing_admin = session.query(User).filter_by(username="admin").first()
    if existing_admin:
        print("Admin user already exists.")
        return

    admin = User(
        username="admin",
        hashed_password=hash_password("admin123"),  # Change password as needed
        user_type="Admin",
        full_name="Admin User",
        phone_number="00000000000",
        email="admin@example.com",
        fathers_name="N/A",
        last_qualification="N/A",
        register_as_parent="No",
        cnic_front_path="",
        cnic_back_path="",
        otp=None,
        otp_created_at=None,
        is_verified=True
    )

    session.add(admin)
    session.commit()
    session.close()

    print("✅ Admin account created successfully.")

if __name__ == "__main__":
    create_admin_user()
