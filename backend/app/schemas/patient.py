from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PatientCreate(BaseModel):
    patient_id: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=2, max_length=120)
    age: int = Field(ge=10, le=60)
    gestational_age: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    age: int | None = Field(default=None, ge=10, le=60)
    gestational_age: str | None = Field(default=None, min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: str
    full_name: str
    age: int
    gestational_age: str
    phone: str | None
    created_at: datetime