# Python Standard Library
import os
import re
import logging
import shutil
import random
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Literal, Optional
from collections import defaultdict

from datetime import datetime
from collections import defaultdict
from fastapi import Request, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from fastapi import APIRouter, Depends, Request, status, Query, HTTPException


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
# Update imports in main.py
from models import User, StudentRegistration, LeadStatus, TuitionStatus, FeeDeduction

# SlowAPI for rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# ... (after your imports)

def flash(request: Request, message: str, category: str = "primary"):
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append({"message": message, "category": category})

def get_flashed_messages(request: Request):
    return request.session.pop("_messages") if "_messages" in request.session else []

# ... (rest of your app code, starting with @app.get("/"))

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
def flash(request: Request, message: str, category: str = "message"):
    if "_flash_messages" not in request.session:
        request.session["_flash_messages"] = []
    request.session["_flash_messages"].append({"message": message, "category": category})

def get_flashed_messages(request: Request, with_categories=False):
    messages = request.session.pop("_flash_messages", [])
    if with_categories:
        return [(msg["category"], msg["message"]) for msg in messages]
    return [msg["message"] for msg in messages]

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
    address: str
    fathers_name: Optional[str] = None
    last_qualification: Optional[str] = None
    register_as_parent: Optional[bool] = False

class StudentForm(BaseModel):
    area: str
    board: str
    subjects: list[str]
    full_name: str
    phone_number: str
    email: EmailStr
    address: str
    total_fee: float

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
# Add to the API ENDPOINTS section in main.py
@app.post("/update_tuition_status/{lead_id}")
async def update_tuition_status(
    lead_id: int,
    # ⭐️ RENAMED the parameter to 'new_status' to avoid conflict
    # The Query(alias="status") part means it still reads the 'status' from the URL
    new_status: TuitionStatus = Query(..., alias="status"),
    db: Session = Depends(get_db),
    request: Request = None,
):
    if "user" not in request.session:
        # Now 'status' correctly refers to the FastAPI status module
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    user_info = request.session["user"]
    if user_info["user_type"] != "tutor":
        # Using HTTPException is better practice for API errors
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Unauthorized"
        )
    
    lead = db.query(StudentRegistration).filter(StudentRegistration.id == lead_id).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Lead not found"
        )

    # Use the new parameter name here
    lead.tuition_status = new_status
    lead.end_date = datetime.now(timezone.utc) # Using timezone-aware datetime
    db.commit()

    # Admin notification logic can be added here
    
    # This redirect now works correctly
    return RedirectResponse(url="/tutor_dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/tutor_dashboard", name="tutor_dashboard")
async def get_tutor_dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    area: Optional[str] = None,
    board: Optional[str] = None,
    subject: Optional[str] = None,
):
    if 'user' not in request.session:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    user_info = request.session["user"]
    tutor = db.query(User).filter(User.username == user_info["username"]).first()

    if not tutor:
        return RedirectResponse(url="/login?error=Tutor+profile+not+found", status_code=status.HTTP_303_SEE_OTHER)

    # Fetch all leads assigned to this tutor
    assigned_leads = db.query(StudentRegistration).filter(
        StudentRegistration.accepted_by_tutor_id == tutor.id,
        StudentRegistration.status == LeadStatus.TUTOR_MATCHED
    ).all()

    # --- ⭐️ IMPROVED INCOME CALCULATION LOGIC ⭐️ ---
    monthly_income = defaultdict(float)
    current_date = datetime.now(timezone.utc)

    for lead in assigned_leads:
        if lead.created_at and lead.total_fee is not None:
            start_date = lead.created_at.replace(tzinfo=timezone.utc)
            
            # If the tuition has an end date, use it; otherwise, use the current date
            end_date = lead.end_date.replace(tzinfo=timezone.utc) if lead.end_date else current_date

            iter_date = start_date.replace(day=1)
            
            while iter_date <= end_date:
                month_year_key = iter_date.strftime("%Y-%m")
                monthly_income[month_year_key] += lead.total_fee
                
                next_month = iter_date.month + 1
                next_year = iter_date.year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                iter_date = iter_date.replace(year=next_year, month=next_month)

    total_earnings = sum(monthly_income.values())
    
    # --- Chart Data Preparation (this part is now correct) ---
    sorted_months = sorted(monthly_income.keys())
    chart_labels = [datetime.strptime(my, "%Y-%m").strftime("%b %Y") for my in sorted_months]
    chart_data = [monthly_income[my] for my in sorted_months]
    # --- END OF IMPROVED LOGIC ---

    # Fetch other lead categories
    available_leads_query = db.query(StudentRegistration).filter(
        StudentRegistration.status == LeadStatus.VERIFIED_AVAILABLE
    )
    if area:
        available_leads_query = available_leads_query.filter(StudentRegistration.area == area)
    if board:
        available_leads_query = available_leads_query.filter(StudentRegistration.board == board)
    if subject:
        available_leads_query = available_leads_query.filter(StudentRegistration.subjects.contains(subject))
    available_leads = available_leads_query.all()

    pending_leads = db.query(StudentRegistration).filter(
        StudentRegistration.accepted_by_tutor_id == tutor.id,
        StudentRegistration.status == LeadStatus.PENDING_TUTOR_APPROVAL
    ).all()

    context = {
        "request": request,
        "session": request.session,
        "user": user_info["username"],
        "role": user_info["user_type"],
        "tutor": tutor,
        "available_leads": available_leads,
        "pending_leads": pending_leads,
        "assigned_leads": assigned_leads,
        "selected_area": area,
        "selected_board": board,
        "selected_subject": subject,
        "get_flashed_messages": get_flashed_messages,
        "total_earnings": total_earnings,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
    }
    
    return templates.TemplateResponse("tutor_dashboard.html", context)

    print(f"--- DEBUG: Context dictionary prepared. Keys: {list(context.keys())} ---")
    # Specifically check if 'tutor' is in the context before rendering
    if 'tutor' in context and context['tutor'] is not None:
        print(f"--- DEBUG: 'tutor' key EXISTS in context. Value: {context['tutor'].full_name} ---")
    else:
        print("--- DEBUG: CRITICAL ERROR - 'tutor' key is MISSING or None in context right before render! ---")

    print("--- DEBUG: Attempting to render tutor_dashboard.html template. ---")
    return templates.TemplateResponse("tutor_dashboard.html", context)
    
@app.post("/accept_lead/{lead_id}", name="accept_lead")
async def accept_lead(
    request: Request,
    lead_id: int,
    db: Session = Depends(get_db)
):
    if 'user' not in request.session:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    user_info = request.session["user"]
    tutor = db.query(User).filter(User.username == user_info["username"]).first()

    if not tutor:
        flash(request, "Tutor profile not found.", "danger")
        return RedirectResponse(url=request.url_for('tutor_dashboard'), status_code=status.HTTP_303_SEE_OTHER)

    lead = db.query(StudentRegistration).filter(StudentRegistration.id == lead_id).first()
    if lead and lead.status == LeadStatus.VERIFIED_AVAILABLE:
        lead.status = LeadStatus.PENDING_TUTOR_APPROVAL
        lead.accepted_by_tutor_id = tutor.id
        db.commit()
        flash(request, "Lead accepted successfully! It is now pending admin approval.", "success")
    else:
        flash(request, "Lead could not be accepted. It may have been taken by another tutor.", "warning")

    # Redirect back to the tutor dashboard
    return RedirectResponse(url=request.url_for('tutor_dashboard'), status_code=status.HTTP_303_SEE_OTHER)

# --- Admin Panel Routes ---



@app.post("/reject_tutor_match/{lead_id}", name="reject_tutor_match")
async def reject_tutor_match(request: Request, lead_id: int, db: Session = Depends(get_db)):
    if 'user' not in request.session or request.session.get('user', {}).get('user_type') != 'admin':
        return RedirectResponse(url="/login?error=Admin access required", status_code=status.HTTP_303_SEE_OTHER)

    lead = db.query(StudentRegistration).filter(StudentRegistration.id == lead_id).first()
    if lead and lead.status == LeadStatus.PENDING_TUTOR_APPROVAL:
        lead.status = LeadStatus.VERIFIED_AVAILABLE
        lead.accepted_by_tutor_id = None  # Remove the association with the tutor
        db.commit()
        flash(request, "Tutor match rejected. The lead is now available again.", "success")
    else:
        flash(request, "Lead not found or already processed.", "error")

    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

# In backend/main.py
# In backend/main.py, replace the old get_lead_details function with this one

@app.get("/api/lead/{lead_id}", name="get_lead_details")
async def get_lead_details(lead_id: int, db: Session = Depends(get_db)):
    """API endpoint to get the full details of a student lead."""
    lead = db.query(StudentRegistration).filter(StudentRegistration.id == lead_id).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    # CORRECTED: Only include fields that exist in your models.py
    lead_details = {
        "id": lead.id,
        "full_name": lead.full_name,
        "email": lead.email,
        "phone_number": lead.phone_number,
        "area": lead.area,
        "address": lead.address,
        "board": lead.board,
        "subjects": lead.subjects,
        "total_fee": f"Rs. {lead.total_fee:,.0f}",
        "registration_date": lead.created_at.strftime("%d %b, %Y")
    }
    
    return JSONResponse(content=lead_details)

@app.get("/admin_logout", name="admin_logout")
async def admin_logout(request: Request):
    """Logs the admin out by clearing the session and redirecting to login."""
    request.session.clear()
    flash(request, "You have been logged out from the admin panel.", "success")
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin", name="admin")
async def get_admin_page(request: Request, db: Session = Depends(get_db)):
    if 'user' not in request.session or request.session.get('user', {}).get('user_type') != 'admin':
        return RedirectResponse(url="/login?error=Admin access required", status_code=status.HTTP_303_SEE_OTHER)

    # Fetch data for the Control Panel (existing queries)
    unverified_leads = db.query(StudentRegistration).filter(
        StudentRegistration.status == LeadStatus.PENDING_ADMIN_VERIFICATION,
        StudentRegistration.is_verified == True
    ).all()

    pending_requests = db.query(StudentRegistration, User).join(
        User, StudentRegistration.accepted_by_tutor_id == User.id
    ).filter(
        StudentRegistration.status == LeadStatus.PENDING_TUTOR_APPROVAL
    ).all()

    available_leads = db.query(StudentRegistration).filter(
        StudentRegistration.status == LeadStatus.VERIFIED_AVAILABLE
    ).all()

    matched_leads = db.query(StudentRegistration, User).join(
        User, StudentRegistration.accepted_by_tutor_id == User.id
    ).filter(
        StudentRegistration.status == LeadStatus.TUTOR_MATCHED
    ).all()
        
    # --- NEW QUERIES ---
    # Fetch all users who are tutors
    all_tutors = db.query(User).filter(User.user_type == 'Tutor').all()
    
    # Fetch all student registrations
    all_students = db.query(StudentRegistration).all()
    # --- END NEW QUERIES ---

    context = {
        "request": request,
        "session": request.session,
        "unverified_leads": unverified_leads,
        "pending_requests": pending_requests,
        "available_leads": available_leads,
        "matched_leads": matched_leads,
        "all_tutors": all_tutors,          # Add tutors to context
        "all_students": all_students,      # Add students to context
        "get_flashed_messages": get_flashed_messages,
    }
    return templates.TemplateResponse("admin.html", context)

@app.post("/verify_lead/{lead_id}", name="verify_lead")
async def verify_lead(
    request: Request,
    lead_id: int,
    db: Session = Depends(get_db),
    deducted_fee: float = Form(0.0)  # New field for the deducted fee
):
    if 'user' not in request.session or request.session.get('user', {}).get('user_type') != 'admin':
        return RedirectResponse(url="/login?error=Admin access required", status_code=status.HTTP_303_SEE_OTHER)

    admin_user = request.session.get("user")
    admin_id = db.query(User).filter(User.username == admin_user["username"]).first().id if admin_user else None


    lead = db.query(StudentRegistration).filter(StudentRegistration.id == lead_id).first()
    if lead:
        original_fee = lead.total_fee
        final_fee = original_fee - deducted_fee

        # Log the deduction
        deduction_record = FeeDeduction(
            lead_id=lead_id,
            original_fee=original_fee,
            deducted_amount=deducted_fee,
            final_fee=final_fee,
            admin_id=admin_id
        )
        db.add(deduction_record)

        # Update the lead's fee and status
        lead.total_fee = final_fee
        lead.status = LeadStatus.VERIFIED_AVAILABLE
        db.commit()

        flash(request, f"Lead verified successfully! Final fee is now Rs. {final_fee:.0f}.", "success")
    else:
        flash(request, "Lead not found.", "error")

    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/approve_tutor_match/{lead_id}", name="approve_tutor_match")
async def approve_tutor_match(request: Request, lead_id: int, db: Session = Depends(get_db)):
    if 'user' not in request.session or request.session.get('user', {}).get('user_type') != 'admin':
        return RedirectResponse(url="/login?error=Admin access required", status_code=status.HTTP_303_SEE_OTHER)

    lead = db.query(StudentRegistration).filter(StudentRegistration.id == lead_id).first()
    
    if lead and lead.status == LeadStatus.PENDING_TUTOR_APPROVAL:
        # Set the status to TUTOR_MATCHED
        lead.status = LeadStatus.TUTOR_MATCHED
        db.commit()
        flash(request, "Tutor match approved successfully!", "success")
    else:
        flash(request, "Lead not found or its status was not pending approval.", "error")

    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/student/submit")
async def submit_student_form(
    request: Request,
    db: Session = Depends(get_db),
    area: str = Form(...),
    board: str = Form(...),
    subjects: list[str] = Form(...),
    full_name: str = Form(...),
    phone_number: str = Form(...),
    email: EmailStr = Form(...),
    address: str = Form(...),
    total_fee: float = Form(...)
):
    # Manually create the Pydantic model instance for validation and use
    try:
        form = StudentForm(
            area=area,
            board=board,
            subjects=subjects,
            full_name=full_name,
            phone_number=phone_number,
            email=email,
            address=address,
            total_fee=total_fee
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Validate inputs
    if not form.subjects:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please select at least one subject"
        )
    if form.total_fee < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Total fee cannot be negative"
        )
    
    # Check if email is already registered
    # if db.query(StudentRegistration).filter(StudentRegistration.email == form.email).first():
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Email already registered"
    #     )
    
    # Generate OTP
    otp = str(random.randint(100000, 999999))
    otp_created_at = datetime.now(timezone.utc)
    
    # Create student registration record
    registration = StudentRegistration(
        full_name=form.full_name,
        phone_number=form.phone_number,
        email=form.email,
        area=form.area,
        address=form.address,
        board=form.board,
        subjects=",".join(form.subjects),  # Store as comma-separated string
        total_fee=form.total_fee,
        is_verified=False,
        otp=otp,
        otp_created_at=otp_created_at
    )
    
    try:
        db.add(registration)
        db.commit()
        db.refresh(registration)
        logger.debug(f"Student registration created for {form.email}")
        
        # Send OTP email
        try:
            await send_otp_email(form.email, otp)
            flash(request, "OTP sent to your email", "success")
            # Store email in session for OTP verification
            request.session["student_email"] = form.email
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "status": "success",
                    "message": "Form submitted, OTP sent",
                    "next_step": "verify"
                }
            )
        except Exception as e:
            logger.error(f"Failed to send OTP email: {str(e)}")
            db.delete(registration)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP"
            )
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    

@app.post("/student/verify-otp")
async def student_verify_otp(
    request: Request,
    email: str = Form(...),
    otp: str = Form(...),
    db: Session = Depends(get_db)
):
    print("\n===============================")
    print("🚀 Incoming Student OTP Verification Request")
    print("===============================")
    print(f"📧 Email Received: {email}")
    print(f"🔢 OTP Received: {otp}")
    print(f"🕒 Current Server Time (UTC): {datetime.now(timezone.utc)}")

    # Input validation
    print("🔍 Step 1: Validating Inputs...")
    if not email or not otp or len(otp) != 6:
        print("❌ Validation Failed: Missing or Invalid OTP Format")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP format"
        )
    print("✅ Inputs Validated")

    # Fetch registration
    print("🔍 Step 2: Querying StudentRegistration Table...")
    registration = db.query(StudentRegistration).filter(
        StudentRegistration.email == email,
        StudentRegistration.is_verified == False
    ).order_by(StudentRegistration.created_at.desc()).first()
    
    if not registration:
        print(f"❌ Email not found in registrations: {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not registered"
        )
    print(f"✅ Registration Found: ID={registration.id}")
    print(f"   - Is Verified: {registration.is_verified}")
    print(f"   - Stored OTP: {registration.otp}")
    print(f"   - OTP Timestamp: {registration.otp_created_at}")

    # Already verified
    print("🔍 Step 3: Checking Verification Status...")
    if registration.is_verified:
        print("❌ Account is already verified, no action needed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already verified"
        )
    print("✅ Account is not yet verified")

    # Check OTP match
    print("🔍 Step 4: Matching OTP...")
    if registration.otp != otp:
        print(f"❌ OTP mismatch - Expected: {registration.otp}, Got: {otp}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )
    print("✅ OTP matches")

    # Check OTP expiration
    print("🔍 Step 5: Checking OTP Expiry...")
    otp_created_at_utc = registration.otp_created_at.replace(tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc)
    time_difference = now_utc - otp_created_at_utc
    print(f"🕒 OTP Age: {time_difference.total_seconds()} seconds")

    if time_difference > timedelta(minutes=5):
        print("❌ OTP has expired")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP expired"
        )
    print("✅ OTP is valid and within time limit")

    # Mark as verified
    print("🔧 Step 6: Updating Verification Status in DB...")
    registration.is_verified = True
    registration.otp = None
    registration.otp_created_at = None

    print("📦 Committing changes to database...")
    db.commit()
    print("✅ Changes committed successfully")

    print("🎉 ✅ Student verification successful")
    print(f"   - ID: {registration.id}")
    print(f"   - Verified at: {now_utc}")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "verified", "message": "Account verified successfully", "next_step": "summary"}
    )

# Add to the API ENDPOINTS section in main.py
@app.post("/student/resend-otp")
async def student_resend_otp(
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    registration = db.query(StudentRegistration).filter(StudentRegistration.email == email).first()
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not registered"
        )

    if registration.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already verified"
        )

    # Generate new OTP
    new_otp = str(random.randint(100000, 999999))
    registration.otp = new_otp
    registration.otp_created_at = datetime.now(timezone.utc)
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
    
    # Add to the API ENDPOINTS section in main.py


# In backend/main.py

@app.get("/student/summary")
async def get_student_summary(
    request: Request,
    db: Session = Depends(get_db)
):
    # Get the email of the most recently verified student from the session
    email = request.session.get("student_email")
    if not email:
        # If no email, redirect to the start of the student form
        return RedirectResponse(url="/student", status_code=status.HTTP_303_SEE_OTHER)
    
    # Fetch the most recent registration for that email
    # This ensures we show the correct summary if a user registers multiple times
    registration = db.query(StudentRegistration).filter(
        StudentRegistration.email == email
    ).order_by(StudentRegistration.created_at.desc()).first()

    if not registration:
        # This is a fallback, in case the registration isn't found
        return RedirectResponse(url="/student", status_code=status.HTTP_303_SEE_OTHER)
    
    # Prepare the data for the template
    context = {
        "request": request,
        "full_name": registration.full_name,
        "email": registration.email,
        "phone_number": registration.phone_number,
        "address": registration.address,
        "area": registration.area,
        "board": registration.board,
        "subjects": registration.subjects.split(','), # Turn the string back into a list
        "total_fee": int(registration.total_fee) # Show fee as a whole number
    }
    
    # Render the new summary template
    return templates.TemplateResponse("student_summary.html", context)

@app.post("/student/new-calculation")
async def new_calculation(request: Request):
    request.session.pop("student_email", None)
    flash(request, "Started new calculation", "success")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "success", "message": "New calculation started", "next_step": "area"}
    )

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
    # Print received data
    print("\n=== Received OTP Verification Request ===")
    print(f"Email: {email}")
    print(f"OTP: {otp}")
    print(f"Current time: {datetime.now(timezone.utc)}")

    # Input validation
    if not email or not otp or len(otp) != 6:
        print("!!! Validation failed - Invalid OTP format")
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP format"
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f"!!! User not found for email: {email}")
        raise HTTPException(
            status_code=400,
            detail="Email not registered"
        )

    print(f"User found: ID={user.id}, Verified={user.is_verified}")
    print(f"Stored OTP: {user.otp}, OTP Created At: {user.otp_created_at}")

    if user.is_verified:
        print("!!! Account already verified")
        raise HTTPException(
            status_code=400,
            detail=" We found an existing account on this email, Kindly use another email or try to login into that account"
        )

    if user.otp != otp:
        print(f"!!! OTP mismatch. Expected: {user.otp}, Received: {otp}")
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP"
        )

    # Convert stored datetime to UTC before comparison
    otp_created_at_utc = user.otp_created_at.replace(tzinfo=timezone.utc)
    time_difference = datetime.now() - user.otp_created_at
    print(f"OTP Age: {time_difference.total_seconds()} seconds")

    if time_difference > timedelta(minutes=5):
        print("!!! OTP expired")
        raise HTTPException(
            status_code=400,
            detail="OTP expired"
        )

    # Mark as verified
    user.is_verified = True
    user.otp = None
    user.otp_created_at = None
    db.commit()

    print("=== Verification successful ===")
    print(f"User {user.id} marked as verified at {datetime.now(timezone.utc)}")

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
            detail=" We found an existing account on this email, Kindly use another email or try to login into that account"
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
    user_type: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    
    # Check credentials
    if not user or not pwd_context.verify(password, user.hashed_password):
        return RedirectResponse(
            url="/login?error=Invalid username or password", 
            status_code=status.HTTP_303_SEE_OTHER
        )

    # Check verification status
    if not user.is_verified:
        return RedirectResponse(
            url="/login?error=Please verify your account with OTP first", 
            status_code=status.HTTP_303_SEE_OTHER
        )

    # Check user type
    if user.user_type.lower() != user_type.lower():
        return RedirectResponse(
            url="/login?error=User type mismatch", 
            status_code=status.HTTP_303_SEE_OTHER
        )

    # Store user in session
    request.session["user"] = {
        "username": user.username,
        "user_type": user.user_type.lower()
    }


    # Redirect based on user type
    if user.user_type.lower() == "tutor":
        return RedirectResponse(url="/tutor_dashboard", status_code=status.HTTP_303_SEE_OTHER)
    elif user.user_type.lower() == "admin":
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    else:  # Default to student dashboard
        return RedirectResponse(url="/student", status_code=status.HTTP_303_SEE_OTHER)
@app.get("/logout", name="logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)



# --- Protected Page Routes ---

@app.get("/admin", name="admin")
async def get_admin_page(request: Request):
    if 'user' not in request.session:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    user = request.session["user"]
    context = {
        "request": request,
        "session": request.session,
        "user": user["username"],
        "role": user["user_type"],
        "get_flashed_messages": lambda **kwargs: get_flashed_messages(request, **kwargs)
    }
    return templates.TemplateResponse("admin.html", context)

@app.get("/tutor_dashboard", name="tutor_dashboard")
async def get_tutor_dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    area: Optional[str] = None,
    board: Optional[str] = None,
    subject: Optional[str] = None,
):
    # 1. Check if user is logged in
    if 'user' not in request.session:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    user_info = request.session["user"]

    # 2. ✅ **CRITICAL FIX**: Fetch the tutor object from the database
    tutor = db.query(User).filter(User.username == user_info["username"]).first()

    # 3. Handle the case where the tutor might not exist
    if not tutor:
        # This is a safeguard. If the user is in session but not in the DB, log them out.
        return RedirectResponse(url="/login?error=Tutor profile not found.", status_code=status.HTTP_303_SEE_OTHER)
        
    # --- (Your existing lead-fetching logic remains the same) ---
    available_leads_query = db.query(StudentRegistration).filter(
        StudentRegistration.status == LeadStatus.VERIFIED_AVAILABLE
    )
    if area:
        available_leads_query = available_leads_query.filter(StudentRegistration.area == area)
    if board:
        available_leads_query = available_leads_query.filter(StudentRegistration.board == board)
    if subject:
        available_leads_query = available_leads_query.filter(StudentRegistration.subjects.contains(subject))
    
    available_leads = available_leads_query.all()

    pending_leads = db.query(StudentRegistration).filter(
        StudentRegistration.accepted_by_tutor_id == tutor.id,
        StudentRegistration.status == LeadStatus.PENDING_TUTOR_APPROVAL
    ).all()

    assigned_leads = db.query(StudentRegistration).filter(
        StudentRegistration.accepted_by_tutor_id == tutor.id,
        StudentRegistration.status == LeadStatus.TUTOR_MATCHED
    ).all()

    # --- Calculate Profile Stats ---
    total_earnings = sum(lead.total_fee for lead in assigned_leads if lead.total_fee is not None)
    completed_tuitions = len(assigned_leads)

    monthly_income = defaultdict(float)
    for lead in assigned_leads:
        if lead.created_at and lead.total_fee is not None:
            month_year = lead.created_at.strftime("%Y-%m")
            monthly_income[month_year] += lead.total_fee

    sorted_months = sorted(monthly_income.keys())
    chart_labels = [datetime.strptime(my, "%Y-%m").strftime("%b %Y") for my in sorted_months]
    chart_data = [monthly_income[my] for my in sorted_months]

    # 4. ✅ **CRITICAL FIX**: Add the 'tutor' object to the context dictionary
    context = {
        "request": request,
        "session": request.session,
        "user": user_info["username"],
        "role": user_info["user_type"],
        "tutor": tutor,  # <--- This line provides the tutor object to the HTML template
        "available_leads": available_leads,
        "pending_leads": pending_leads,
        "assigned_leads": assigned_leads,
        "selected_area": area,
        "selected_board": board,
        "selected_subject": subject,
        "get_flashed_messages": get_flashed_messages,
        "total_earnings": total_earnings,
        "completed_tuitions": completed_tuitions,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
    }

    # Optional: For debugging, you can print right before rendering
    # print("Tutor object being sent to template:", context.get('tutor'))
    
    return templates.TemplateResponse("tutor_dashboard.html", context)


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



