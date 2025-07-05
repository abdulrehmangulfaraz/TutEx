# models.py
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

# Define Models (db will be injected by app.py)
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    hashed_password = db.Column(db.String(120), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    fathers_name = db.Column(db.String(120))
    last_qualification = db.Column(db.String(120))
    register_as_parent = db.Column(db.Boolean)
    cnic_front_path = db.Column(db.String(120))
    cnic_back_path = db.Column(db.String(120))
    otp = db.Column(db.String(6))
    otp_created_at = db.Column(db.DateTime)
    is_verified = db.Column(db.Boolean)

class Tutor(db.Model):
    __tablename__ = 'tutors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    father_name = db.Column(db.String(120))
    cnic_front = db.Column(db.String(120))
    cnic_back = db.Column(db.String(120))
    qualification = db.Column(db.String(120))
    status = db.Column(db.String(20), server_default='pending')

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    relation = db.Column(db.String(120))
    status = db.Column(db.String(20), server_default='pending')

class StudentLead(db.Model):
    __tablename__ = 'student_leads'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    area = db.Column(db.String(120))
    board = db.Column(db.String(120))
    subjects = db.Column(db.String(255))
    fee = db.Column(db.Integer)
    accepted_by = db.Column(db.String(80))
    status = db.Column(db.String(50), server_default='Pending Approval')
    verified = db.Column(db.Integer, server_default='0')
    tutor_approved = db.Column(db.Integer, server_default='0')

# Function to initialize database (to be called from app.py or db_init.py)
def init_db(app):
    with app.app_context():
        db.create_all()