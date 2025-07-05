import logging
from email.message import EmailMessage
import aiosmtplib
from decouple import config

async def send_otp_email(to_email: str, otp: str):
    if not to_email:
        raise ValueError("Email address is required to send OTP")
    msg = EmailMessage()
    msg["From"] = config('EMAIL_USER')
    msg["To"] = to_email
    msg["Subject"] = "Your TutEx OTP Verification Code"
    msg.set_content(f"Your TutEx OTP code is: {otp}\nThis code is valid for 5 minutes.")
    try:
        await aiosmtplib.send(msg, hostname="smtp.gmail.com", port=587, start_tls=True, username=config('EMAIL_USER'), password=config('EMAIL_PASSWORD'))
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
        return False