import re
from typing import Optional
from pydantic import BaseModel, field_validator, ValidationInfo


class RegisterRequest(BaseModel):
    activation_code: str
    first_name: str
    last_name: str
    email: str
    mobile: str
    password: str
    birthday_day: int
    birthday_month: int
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    town: Optional[str] = None
    post_code: Optional[str] = None
    state_of_origin: Optional[str] = None
    lga: Optional[str] = None
    relationship_status: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    membership_type: Optional[str] = None

    @field_validator("activation_code", "first_name", "last_name", "email", "mobile", "password")
    @classmethod
    def not_empty(cls, v: str, info: ValidationInfo) -> str:
        if not v.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return v

    @field_validator("mobile")
    @classmethod
    def valid_mobile(cls, v: str) -> str:
        if not re.match(r"^\+?\d{10,15}$", v):
            raise ValueError("mobile must be digits and may start with '+'")
        return v

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("email is not valid")
        return v

    @field_validator("birthday_day")
    @classmethod
    def valid_day(cls, v: int) -> int:
        if not 1 <= v <= 31:
            raise ValueError("birthday_day must be between 1 and 31")
        return v

    @field_validator("birthday_month")
    @classmethod
    def valid_month(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("birthday_month must be between 1 and 12")
        return v
