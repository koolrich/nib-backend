import re
from pydantic import BaseModel, field_validator, ValidationInfo


class LoginRequest(BaseModel):
    mobile: str
    password: str

    @field_validator("mobile", "password")
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
