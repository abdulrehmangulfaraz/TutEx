from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
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


# -------------------- STUDENT_LEADS --------------------

class StudentLead(Base):
    __tablename__ = 'student_leads'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), nullable=False)
    area = Column(String(120), nullable=True)
    board = Column(String(120), nullable=True)
    subjects = Column(String(255), nullable=True)
    fee = Column(Integer, nullable=True)
    accepted_by = Column(String(80), nullable=True)
    status = Column(String(50), nullable=True, default='Pending Approval')
    verified = Column(Integer, nullable=True, default=0)
    tutor_approved = Column(Integer, nullable=True, default=0)


# -------------------- STUDENTS --------------------

class Student(Base):
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    full_name = Column(String(120), nullable=False)
    relation = Column(String(120), nullable=True)
    status = Column(String(20), nullable=True, default='pending')


# -------------------- TUTORS --------------------

class Tutor(Base):
    __tablename__ = 'tutors'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    full_name = Column(String(120), nullable=False)
    father_name = Column(String(120), nullable=True)
    cnic_front = Column(String(120), nullable=True)
    cnic_back = Column(String(120), nullable=True)
