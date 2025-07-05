# Python Standard Library
import os
import re
import logging
import shutil
import random
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Literal, Optional

# Third-Party Libraries
import aiofiles
import aiosmtplib
from fastapi import Depends, FastAPI, Form, File, HTTPException, Request, status, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

# Local Application Imports
from database import SessionLocal
from models import User

# SlowAPI for rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Load environment variables from .env file
load_dotenv()


# --- APPLICATION SETUP ---
app = FastAPI()

# Add SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key="a_very_secret_key")

# Set up rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="../frontend/templates")

# Configure password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# --- DATABASE DEPENDENCY ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Pydantic Models ---
class LoginForm(BaseModel):
    username: str
    password: str
    user_type: Optional[Literal["student", "tutor", "admin"]] = "student"

class RegisterForm(BaseModel):
    username: str
    password: str
    user_type: str
    full_name: str
    phone_number: str
    email: Optional[EmailStr] = None
    fathers_name: Optional[str] = None
    last_qualification: Optional[str] = None
    register_as_parent: Optional[bool] = False


# --- EMAIL SENDING ---
async def send_otp_email(to_email: str, otp: str):
    if not to_email:
        raise ValueError("Email address is required to send OTP")

    # Get email credentials from environment variables
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")

    if not email_user or not email_password:
        logger.error("Email credentials are not set in the environment.")
        return False

    msg = EmailMessage()
    msg["From"] = email_user
    msg["To"] = to_email
    msg["Subject"] = "Your TutEx OTP Verification Code"
    msg.set_content(f"Your TutEx OTP code is: {otp}\nThis code is valid for 5 minutes.")

    try:
        await aiosmtplib.send(
            msg,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=email_user,
            password=email_password,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False


# --- API ENDPOINTS ---
@app.post("/verify-otp")
async def verify_otp(
    email: str = Form(...),
    otp: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == email,
        User.otp == otp,
        User.otp_created_at >= datetime.now(timezone.utc) - timedelta(minutes=5),
        User.is_verified == False
    ).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP.")

    user.is_verified = True
    user.otp = None
    user.otp_created_at = None
    db.commit()
    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Account verified successfully"})


@app.post("/signup", name="signup")
@limiter.limit("5/minute")
async def signup(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    user_type: str = Form(...),
    full_name: str = Form(...),
    phone_number: str = Form(...),
    email: Optional[EmailStr] = Form(None),
    fathers_name: Optional[str] = Form(None),
    last_qualification: Optional[str] = Form(None),
    register_as_parent: bool = Form(False),
    cnic_front: Optional[UploadFile] = File(None),
    cnic_back: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    otp = str(random.randint(100000, 999999))
    user = User(
        username=username,
        hashed_password=pwd_context.hash(password),
        user_type=user_type.capitalize(),
        full_name=full_name,
        phone_number=phone_number,
        email=email,
        fathers_name=fathers_name,
        last_qualification=last_qualification,
        register_as_parent=register_as_parent,
        otp=otp,
        otp_created_at=datetime.now(timezone.utc)
    )
    db.add(user)
    db.commit()

    if email:
        await send_otp_email(email, otp)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Registration successful. Please check your email for the OTP."}
    )


@app.get("/login", name="login")
async def get_login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse("login.html", {"request": request, "session": request.session, "error": error})


@app.post("/login", name="login_post")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.hashed_password):
        return RedirectResponse(url="/login?error=Invalid username or password", status_code=status.HTTP_303_SEE_OTHER)

    if not user.is_verified:
        return RedirectResponse(url="/login?error=Please verify your account with OTP first.", status_code=status.HTTP_303_SEE_OTHER)

    request.session['user'] = {'username': user.username, 'user_type': user.user_type}
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/logout", name="logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


# --- Basic Page Routes ---
@app.get("/", name="home")
async def root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "session": request.session})

@app.get("/dashboard", name="dashboard")
async def dashboard(request: Request):
    if 'user' not in request.session:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("dashboard.html", {"request": request, "session": request.session})

@app.get("/courses", name="courses")
async def get_courses_page(request: Request):
    return templates.TemplateResponse("courses.html", {"request": request, "session": request.session})

@app.get("/student", name="student")
async def get_student_page(request: Request):
    return templates.TemplateResponse("student.html", {"request": request, "session": request.session})

@app.get("/tutor_dashboard", name="tutor_dashboard")
async def get_tutor_dashboard_page(request: Request):
    return templates.TemplateResponse("tutor_dashboard.html", {"request": request, "session": request.session})

@app.get("/how_it_works", name="how_it_works")
async def get_how_it_works_page(request: Request):
    return templates.TemplateResponse("how_it_works.html", {"request": request, "session": request.session})

@app.get("/contact", name="contact")
async def get_contact_page(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request, "session": request.session})