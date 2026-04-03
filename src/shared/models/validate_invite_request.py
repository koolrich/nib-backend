from pydantic import BaseModel, field_validator, ValidationInfo


class ValidateInviteRequest(BaseModel):
    activation_code: str

    @field_validator("activation_code")
    @classmethod
    def not_empty(cls, v: str, info: ValidationInfo) -> str:
        if not v.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return v
