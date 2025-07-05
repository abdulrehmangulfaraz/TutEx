from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException, status, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas import LoginForm, RegisterForm
from ..utils import send_otp_email
from passlib.context import CryptContext
import random
import re
import os
import logging
import aiofiles
from datetime import datetime, timezone

router = APIRouter()
templates = Jinja2Templates(directory="../../frontend/templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)

@router.get("/login")
async def get_login_page(request: Request, error: str = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...), user_type: str = Form("student"), db: Session = Depends(get_db)):
    user_type_normalized = user_type.capitalize() if user_type else "Student"
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.hashed_password):
        return RedirectResponse(url="/login?error=Invalid username or password", status_code=status.HTTP_303_SEE_OTHER)
    if user.user_type != user_type_normalized:
        return RedirectResponse(url="/login?error=Invalid user type", status_code=status.HTTP_303_SEE_OTHER)
    if not user.is_verified:
        return RedirectResponse(url="/login?error=Please verify your account with OTP", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/verify-otp")
async def verify_otp(email: str = Form(...), otp: str = Form(...), db: Session = Depends(get_db)):
    if not email or not otp or len(otp) != 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP format")
    user = db.query(User).filter(User.email == email, User.otp == otp, User.otp_created_at >= datetime.now(timezone.utc) - timedelta(minutes=5), User.is_verified == False).first()
    if not user:
        user_exists = db.query(User).filter(User.email == email).first()
        if not user_exists:
            detail = "Email not registered"
        elif user_exists.is_verified:
            detail = "Account already verified"
        else:
            otp_valid = db.query(User).filter(User.email == email, User.otp == otp).first()
            detail = "Invalid OTP" if otp_valid else "OTP expired"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    user.is_verified = True
    user.otp = None
    user.otp_created_at = None
    db.commit()
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "verified", "message": "Account verified successfully"})

@router.post("/signup")
async def signup(username: str = Form(...), password: str = Form(...), user_type: str = Form(...), full_name: str = Form(...), phone_number: str = Form(...), email: str = Form(None), fathers_name: str = Form(None), last_qualification: str = Form(None), register_as_parent: bool = Form(False), cnic_front: UploadFile = File(None), cnic_back: UploadFile = File(None), db: Session = Depends(get_db)):
    logger.debug(f"Received signup request for username: {username}, user_type: {user_type}")
    if db.query(User).filter(User.username == username).first():
        logger.warning(f"Username {username} already exists")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    if user_type.capitalize() not in ["Student", "Tutor", "Admin"]:
        logger.warning(f"Invalid user_type: {user_type}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user type")
    otp = str(random.randint(100000, 999999))
    otp_created_at = datetime.now(timezone.utc)
    cnic_front_path = None
    cnic_back_path = None
    if user_type.lower() == "tutor":
        if not (cnic_front and cnic_back):
            logger.warning("CNIC images missing for tutor")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CNIC images required for tutors")
        try:
            front_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', cnic_front.filename)
            back_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', cnic_back.filename)
            cnic_front_path = os.path.join("../frontend/uploads", f"{username}_cnic_front_{front_filename}")
            cnic_back_path = os.path.join("../frontend/uploads", f"{username}_cnic_back_{back_filename}")
            front_abs_path = os.path.join("..", "frontend", cnic_front_path)
            back_abs_path = os.path.join("..", "frontend", cnic_back_path)
            os.makedirs(os.path.dirname(front_abs_path), exist_ok=True)
            async with aiofiles.open(front_abs_path, "wb") as f:
                await f.write(await cnic_front.read())
            async with aiofiles.open(back_abs_path, "wb") as f:
                await f.write(await cnic_back.read())
        except Exception as e:
            logger.error(f"Failed to save CNIC files: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save CNIC files: {str(e)}")
    try:
        user = User(username=username, hashed_password=pwd_context.hash(password), user_type=user_type.capitalize(), full_name=full_name, phone_number=phone_number, email=email, fathers_name=fathers_name, last_qualification=last_qualification, register_as_parent=register_as_parent, cnic_front_path=cnic_front_path, cnic_back_path=cnic_back_path, otp=otp, otp_created_at=otp_created_at, is_verified=False)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.debug(f"User {username} added to database")
        if email:
            try:
                await send_otp_email(email, otp)
            except Exception as e:
                logger.error(f"Failed to send OTP email: {str(e)}")
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "Registration successful, OTP sent", "email": email, "next_step": "verify"})
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        if cnic_front_path and os.path.exists(front_abs_path):
            os.remove(front_abs_path)
        if cnic_back_path and os.path.exists(back_abs_path):
            os.remove(back_abs_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")