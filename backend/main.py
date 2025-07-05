import sys
import os
import re
import logging
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from fastapi import Depends, Form, File, UploadFile, HTTPException
from typing import Optional
import shutil
import random
import aiofiles 
from email.message import EmailMessage
import aiosmtplib
import smtplib
from fastapi import FastAPI, Request, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Literal
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from fastapi.middleware import Middleware
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
middleware = [Middleware(limiter)]

app = FastAPI(middleware=middleware)
app = FastAPI()

# Initialize OTP storage
otp_storage = {}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/verify-otp")
async def verify_otp(
    email: str = Form(...),
    otp: str = Form(...),
    db: Session = Depends(get_db)
):
    # Input validation
    if not email or not otp or len(otp) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP format"
        )

    # Find user with matching email and unexpired OTP (5 minute window)
    user = db.query(User).filter(
        User.email == email,
        User.otp == otp,
        User.otp_created_at >= datetime.now(timezone.utc) - timedelta(minutes=5),
        User.is_verified == False
    ).first()

    if not user:
        # More specific error messages
        user_exists = db.query(User).filter(User.email == email).first()
        if not user_exists:
            detail = "Email not registered"
        elif user_exists.is_verified:
            detail = "Account already verified"
        else:
            otp_valid = db.query(User).filter(
                User.email == email,
                User.otp == otp
            ).first()
            detail = "Invalid OTP" if otp_valid else "OTP expired"
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

    # Mark as verified
    user.is_verified = True
    user.otp = None  # Clear OTP after verification
    user.otp_created_at = None
    db.commit()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "verified", "message": "Account verified successfully"}
    )

# Add Tutex/ to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.models import User


# Configure Jinja2 templates
templates = Jinja2Templates(directory="../frontend/templates")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pydantic model for login form validation
class LoginForm(BaseModel):
    username: str
    password: str
    user_type: Optional[Literal["student", "tutor", "admin"]] = "student"

# Pydantic model for registration
class RegisterForm(BaseModel):
    username: str
    password: str
    user_type: str
    full_name: str
    phone_number: str
    email: Optional[str] = None
    fathers_name: Optional[str] = None
    last_qualification: Optional[str] = None
    register_as_parent: Optional[bool] = False

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def send_otp_email(to_email: str, otp: str):
    if not to_email:
        raise ValueError("Email address is required to send OTP")
    
    msg = EmailMessage()
    msg["From"] = "example@gmail.com"
    msg["To"] = to_email
    msg["Subject"] = "Your TutEx OTP Verification Code"
    msg.set_content(f"Your TutEx OTP code is: {otp}\nThis code is valid for 5 minutes.")

    try:
        await aiosmtplib.send(
            msg,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username="example@gmail.com",
            password="16 digit app password",
        )
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
        return False

@app.get("/login")
async def get_login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@app.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    user_type: str = Form("student"),
    db: Session = Depends(get_db)
):
    user_type_normalized = user_type.capitalize() if user_type else "Student"
    user = db.query(User).filter(User.username == username).first()
    
    if not user or not pwd_context.verify(password, user.hashed_password):
        return RedirectResponse(
            url="/login?error=Invalid username or password", 
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    if user.user_type != user_type_normalized:
        return RedirectResponse(
            url="/login?error=Invalid user type", 
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    if not user.is_verified:
        return RedirectResponse(
            url="/login?error=Please verify your account with OTP", 
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.post("/signup")
async def signup(
    username: str = Form(...),
    password: str = Form(...),
    user_type: str = Form(...),
    full_name: str = Form(...),
    phone_number: str = Form(...),
    email: Optional[str] = Form(None),
    fathers_name: Optional[str] = Form(None),
    last_qualification: Optional[str] = Form(None),
    register_as_parent: bool = Form(False),
    cnic_front: Optional[UploadFile] = File(None),
    cnic_back: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    logger.debug(f"Received signup request for username: {username}, user_type: {user_type}")

    # Check if username exists
    if db.query(User).filter(User.username == username).first():
        logger.warning(f"Username {username} already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Validate user_type
    if user_type.capitalize() not in ["Student", "Tutor", "Admin"]:
        logger.warning(f"Invalid user_type: {user_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user type"
        )
    
    # Generate OTP for all user types
    otp = str(random.randint(100000, 999999))
    otp_created_at = datetime.now(timezone.utc)
    
    # Handle file uploads for tutors
    cnic_front_path = None
    cnic_back_path = None
    if user_type.lower() == "tutor":
        if not (cnic_front and cnic_back):
            logger.warning("CNIC images missing for tutor")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CNIC images required for tutors"
            )
            
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
            user_type=user_type.capitalize(),
            full_name=full_name,
            phone_number=phone_number,
            email=email,
            fathers_name=fathers_name,
            last_qualification=last_qualification,
            register_as_parent=register_as_parent,
            cnic_front_path=cnic_front_path,
            cnic_back_path=cnic_back_path,
            otp=otp,
            otp_created_at=otp_created_at,
            is_verified=False
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.debug(f"User {username} added to database")
        
        # Send OTP email if email provided
        if email:
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

@app.get("/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/")
async def root():
    return {"message": "TutEx Backend Running"}
