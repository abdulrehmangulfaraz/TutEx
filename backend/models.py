from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text,Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta, timezone
from datetime import datetime

Base = declarative_base()

# -------------------- USERS --------------------

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    user_type = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    email = Column(String, nullable=True)
    fathers_name = Column(String, nullable=True)
    last_qualification = Column(String, nullable=True)
    register_as_parent = Column(Boolean, default=False)
    cnic_front_path = Column(String, nullable=True)
    cnic_back_path = Column(String, nullable=True)
    otp = Column(String(6), nullable=True)
    otp_created_at = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, default=False)

# -------------------- StudentRegistration --------------------

class StudentRegistration(Base):
    __tablename__ = "student_registrations"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    phone_number = Column(String)
    email = Column(String, unique=True, index=True)
    area = Column(String)
    board = Column(String)
    subjects = Column(String)  # Comma-separated list
    total_fee = Column(Float)
    is_verified = Column(Boolean, default=False)
    otp = Column(String, nullable=True)
    otp_created_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))