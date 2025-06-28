from pydantic import BaseModel, Field, field_validator, ValidationInfo
import re


class InviteRequest(BaseModel):
    first_name: str
    last_name: str
    mobile: str

    @field_validator("first_name", "last_name")
    @classmethod
    def not_empty(cls, v, info: ValidationInfo):
        if not v.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return v

    @field_validator("mobile")
    @classmethod
    def valid_mobile(cls, v: str) -> str:
        if not re.match(r"^\+?\d{10,15}$", v):
            raise ValueError("mobile must be digits and may start with '+'")
        return v
