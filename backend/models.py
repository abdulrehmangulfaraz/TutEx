# backend/models.py

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    Enum,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
import enum

Base = declarative_base()


# Define an Enum for our lead statuses
class LeadStatus(enum.Enum):
    PENDING_ADMIN_VERIFICATION = "PENDING_ADMIN_VERIFICATION"
    VERIFIED_AVAILABLE = "VERIFIED_AVAILABLE"
    PENDING_TUTOR_APPROVAL = "PENDING_TUTOR_APPROVAL"
    TUTOR_MATCHED = "TUTOR_MATCHED"
    REJECTED = "REJECTED"


class User(Base):
    # ... (Your User class remains unchanged)
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    user_type = Column(String, default="Tutor")
    full_name = Column(String)
    phone_number = Column(String)
    email = Column(String)
    fathers_name = Column(String)
    last_qualification = Column(String)
    register_as_parent = Column(String)
    cnic_front_path = Column(String)
    cnic_back_path = Column(String)
    otp = Column(String, nullable=True)
    otp_created_at = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, default=False)


class StudentRegistration(Base):
    __tablename__ = "student_registrations"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    phone_number = Column(String)
    email = Column(String, index=True)
    area = Column(String)
    address = Column(String) # <-- ADD THIS LINE
    board = Column(String)
    subjects = Column(String)
    total_fee = Column(Float)
    is_verified = Column(Boolean, default=False)
    otp = Column(String, nullable=True)
    otp_created_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(
        Enum(LeadStatus),
        default=LeadStatus.PENDING_ADMIN_VERIFICATION,
        nullable=False,
    )
    accepted_by_tutor_id = Column(Integer, ForeignKey("users.id"), nullable=True)