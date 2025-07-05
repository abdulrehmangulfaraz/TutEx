from sqlalchemy import Column, Integer, String, Boolean, DateTime  # Added DateTime import
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime  # Regular datetime import for Python operations

Base = declarative_base()

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
    otp_created_at = Column(DateTime, nullable=True)  # Now using the properly imported DateTime
    is_verified = Column(Boolean, default=False)