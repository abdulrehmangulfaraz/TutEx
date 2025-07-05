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

# --- Login Dependency (only for protected routes) ---
def require_login(request: Request):
    if 'user' not in request.session:
        return RedirectResponse(url="/login?error=Please log in to access this page.", status_code=status.HTTP_303_SEE_OTHER)
    return True

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
@app.post("/signup")
async def signup(
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    phone_number: str = Form(...),
    email: str = Form(...),
    fathers_name: str = Form(...),
    last_qualification: str = Form(...),
    cnic_front: UploadFile = File(...),
    cnic_back: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    logger.debug(f"Received tutor signup request for username: {username}")

    # Check if username exists
    if db.query(User).filter(User.username == username).first():
        logger.warning(f"Username {username} already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Generate OTP
    otp = str(random.randint(100000, 999999))
    otp_created_at = datetime.now(timezone.utc)
    
    # Handle file uploads
    cnic_front_path = None
    cnic_back_path = None
    try:
        # Sanitize filenames
        front_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', cnic_front.filename)
        back_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', cnic_back.filename)
        
        # Save files
        cnic_front_path = os.path.join("uploads", f"{username}_cnic_front_{front_filename}")
        cnic_back_path = os.path.join("uploads", f"{username}_cnic_back_{back_filename}")
        
        front_abs_path = os.path.join("static", cnic_front_path)
        back_abs_path = os.path.join("static", cnic_back_path)
        
        os.makedirs(os.path.dirname(front_abs_path), exist_ok=True)
        
        async with aiofiles.open(front_abs_path, "wb") as f:
            await f.write(await cnic_front.read())
        async with aiofiles.open(back_abs_path, "wb") as f:
            await f.write(await cnic_back.read())
            
    except Exception as e:
        logger.error(f"Failed to save CNIC files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save CNIC files: {str(e)}"
        )

    try:
        # Create user with OTP data
        user = User(
            username=username,
            hashed_password=pwd_context.hash(password),
            user_type="Tutor",
            full_name=full_name,
            phone_number=phone_number,
            email=email,
            fathers_name=fathers_name,
            last_qualification=last_qualification,
            cnic_front_path=cnic_front_path,
            cnic_back_path=cnic_back_path,
            otp=otp,
            otp_created_at=otp_created_at,
            is_verified=False
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.debug(f"Tutor {username} added to database")
        
        # Send OTP email
        try:
            await send_otp_email(email, otp)
        except Exception as e:
            logger.error(f"Failed to send OTP email: {str(e)}")
            # Don't fail registration if email fails
            
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Registration successful, OTP sent",
                "email": email,
                "next_step": "verify"
            }
        )
        
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        # Cleanup files if they were created
        if cnic_front_path and os.path.exists(front_abs_path):
            os.remove(front_abs_path)
        if cnic_back_path and os.path.exists(back_abs_path):
            os.remove(back_abs_path)
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@app.post("/verify-otp")
async def verify_otp(
    email: str = Form(...),
    otp: str = Form(...),
    db: Session = Depends(get_db)
):
    # Input validation
    if not email or not otp or len(otp) != 6:
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP format"
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Email not registered"
        )

    if user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="Account already verified"
        )

    if user.otp != otp:
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP"
        )

    if datetime.now(timezone.utc) - user.otp_created_at > timedelta(minutes=5):
        raise HTTPException(
            status_code=400,
            detail="OTP expired"
        )

    # Mark as verified
    user.is_verified = True
    user.otp = None
    user.otp_created_at = None
    db.commit()

    return {"status": "verified", "message": "Account verified successfully"}

@app.post("/resend-otp")
async def resend_otp(
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not registered"
        )

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already verified"
        )

    # Generate new OTP
    new_otp = str(random.randint(100000, 999999))
    user.otp = new_otp
    user.otp_created_at = datetime.now(timezone.utc)
    db.commit()

    # Send new OTP
    try:
        await send_otp_email(email, new_otp)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "success", "message": "New OTP sent successfully"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTP: {str(e)}"
        )

@app.get("/login", name="login")
async def get_login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse("login.html", {"request": request, "session": request.session, "error": error})

@app.post("/login", name="login_post")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    user_type: str = Form(...),  # Added from frontend form
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.hashed_password):
        return RedirectResponse(url="/login?error=Invalid username or password", status_code=status.HTTP_303_SEE_OTHER)

    if not user.is_verified:
        return RedirectResponse(url="/login?error=Please verify your account with OTP first.", status_code=status.HTTP_303_SEE_OTHER)

    # Use user_type from form and validate against database
    if user.user_type.lower() != user_type.lower():
        return RedirectResponse(url="/login?error=User type mismatch", status_code=status.HTTP_303_SEE_OTHER)

    request.session["user"] = {"username": user.username, "user_type": user_type.lower()}
    if user_type.lower() == "tutor":
        return RedirectResponse(url="/tutor_dashboard", status_code=status.HTTP_303_SEE_OTHER)
    elif user_type.lower() == "admin":
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    else:  # Default to student
        return RedirectResponse(url="/student", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/logout", name="logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

# --- Page Routes with Login Requirement ---
@app.get("/tutor_dashboard", name="tutor_dashboard", dependencies=[Depends(require_login)])
async def get_tutor_dashboard_page(request: Request):
    user = request.session["user"]
    return templates.TemplateResponse("tutor_dashboard.html", {"request": request, "session": request.session, "user": user["username"], "role": user["user_type"]})

@app.get("/admin", name="admin", dependencies=[Depends(require_login)])
async def get_admin_page(request: Request):
    user = request.session["user"]
    return templates.TemplateResponse("admin.html", {"request": request, "session": request.session, "user": user["username"], "role": user["user_type"]})

# --- Public Page Routes ---
@app.get("/", name="home")
async def root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "session": request.session})

@app.get("/student", name="student")
async def get_student_page(request: Request):
    user = request.session.get("user", {"username": "Guest", "user_type": "guest"})
    return templates.TemplateResponse("student.html", {"request": request, "session": request.session, "user": user["username"], "role": user["user_type"]})

@app.get("/courses", name="courses")
async def get_courses_page(request: Request):
    return templates.TemplateResponse("courses.html", {"request": request, "session": request.session})

@app.get("/how_it_works", name="how_it_works")
async def get_how_it_works_page(request: Request):
    return templates.TemplateResponse("how_it_works.html", {"request": request, "session": request.session})

@app.get("/contact", name="contact")
async def get_contact_page(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request, "session": request.session})