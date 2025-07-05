from pydantic import BaseModel
from typing import Optional, Literal

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
    email: Optional[str] = None
    fathers_name: Optional[str] = None
    last_qualification: Optional[str] = None
    register_as_parent: Optional[bool] = False