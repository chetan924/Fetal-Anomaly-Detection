from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


# ============================================================
# REGISTER
# ============================================================

class UserRegister(BaseModel):

    full_name: str = Field(
        min_length=2,
        max_length=120,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )


# ============================================================
# SIGNUP OTP VERIFICATION
# ============================================================

class VerifySignupOTPRequest(BaseModel):

    email: EmailStr

    otp: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    )


# ============================================================
# USER RESPONSE
# ============================================================

class UserResponse(BaseModel):

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    full_name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime


# ============================================================
# LOGIN
# ============================================================

class UserLogin(BaseModel):

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )


# ============================================================
# LOGIN OTP VERIFICATION
# ============================================================

class VerifyLoginOTPRequest(BaseModel):

    email: EmailStr

    otp: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    )


# ============================================================
# TOKEN RESPONSE
# ============================================================

class TokenResponse(BaseModel):

    access_token: str

    token_type: str = "bearer"


# ============================================================
# FORGOT PASSWORD
# ============================================================

class ForgotPasswordRequest(BaseModel):

    email: EmailStr


# ============================================================
# FORGOT PASSWORD OTP VERIFICATION
# ============================================================

class VerifyForgotPasswordOTPRequest(BaseModel):

    email: EmailStr

    otp: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    )


# ============================================================
# RESET PASSWORD WITH OTP
# ============================================================

class ResetPasswordWithOTPRequest(BaseModel):

    email: EmailStr

    otp: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    )

    new_password: str = Field(
        min_length=8,
        max_length=128,
    )


# ============================================================
# RESET PASSWORD WITH TOKEN
# ============================================================

class ResetPasswordRequest(BaseModel):

    token: str = Field(
        min_length=20,
        max_length=500,
    )

    new_password: str = Field(
        min_length=8,
        max_length=128,
    )


# ============================================================
# CHANGE PASSWORD
# ============================================================

class ChangePasswordRequest(BaseModel):

    current_password: str = Field(
        min_length=8,
        max_length=128,
    )

    new_password: str = Field(
        min_length=8,
        max_length=128,
    )
    