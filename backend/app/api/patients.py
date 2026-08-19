from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import (
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/api/patients",
    tags=["Patients"],
)


# =========================================================
# CREATE PATIENT
# =========================================================

@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a patient for the currently authenticated user.
    """

    # =====================================================
    # VERIFY AUTHENTICATED USER
    # =====================================================

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    # =====================================================
    # NORMALIZE PATIENT ID
    # =====================================================

    normalized_patient_id = payload.patient_id.strip()

    if not normalized_patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient ID is required",
        )

    # =====================================================
    # CHECK GLOBAL PATIENT ID UNIQUENESS
    # =====================================================

    existing_patient = db.scalar(
        select(Patient).where(
            Patient.patient_id == normalized_patient_id
        )
    )

    if existing_patient is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A patient with this patient ID already exists",
        )

    # =====================================================
    # NORMALIZE TEXT FIELDS
    # =====================================================

    full_name = payload.full_name.strip()

    gestational_age = payload.gestational_age.strip()

    phone = (
        payload.phone.strip()
        if payload.phone
        else None
    )

    # =====================================================
    # VALIDATE REQUIRED FIELDS
    # =====================================================

    if not full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient name is required",
        )

    if not gestational_age:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gestational age is required",
        )

    # =====================================================
    # CREATE PATIENT
    # =====================================================
    #
    # IMPORTANT:
    # The owner is ALWAYS taken from the authenticated user.
    #
    # The frontend/client cannot choose created_by.
    #
    # =====================================================

    patient = Patient(
        patient_id=normalized_patient_id,
        full_name=full_name,
        age=payload.age,
        gestational_age=gestational_age,
        phone=phone,
        created_by=current_user.id,
    )

    # =====================================================
    # SAVE PATIENT
    # =====================================================

    try:
        db.add(patient)
        db.commit()
        db.refresh(patient)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create patient",
        )

    return patient


# =========================================================
# GET ALL PATIENTS
# =========================================================

@router.get(
    "",
    response_model=list[PatientResponse],
)
def get_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get patients belonging to the authenticated user.
    """

    if current_user is None or current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    patients = db.scalars(
        select(Patient)
        .where(
            Patient.created_by == current_user.id
        )
        .order_by(
            Patient.id.desc()
        )
    ).all()

    return patients


# =========================================================
# GET SINGLE PATIENT
# =========================================================

@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get one patient belonging to the authenticated user.
    """

    if current_user is None or current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # =====================================================
    # NORMALIZE PATIENT ID
    # =====================================================

    normalized_patient_id = patient_id.strip()

    if not normalized_patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient ID is required",
        )

    # =====================================================
    # FIND PATIENT OWNED BY CURRENT USER
    # =====================================================

    patient = db.scalar(
        select(Patient).where(
            Patient.patient_id == normalized_patient_id,
            Patient.created_by == current_user.id,
        )
    )

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    return patient


# =========================================================
# UPDATE PATIENT
# =========================================================

@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
)
def update_patient(
    patient_id: str,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a patient belonging to the authenticated user.
    """

    if current_user is None or current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # =====================================================
    # NORMALIZE PATIENT ID
    # =====================================================

    normalized_patient_id = patient_id.strip()

    if not normalized_patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient ID is required",
        )

    # =====================================================
    # FIND ONLY CURRENT USER'S PATIENT
    # =====================================================

    patient = db.scalar(
        select(Patient).where(
            Patient.patient_id == normalized_patient_id,
            Patient.created_by == current_user.id,
        )
    )

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # =====================================================
    # EXTRACT UPDATE DATA
    # =====================================================

    update_data = payload.model_dump(
        exclude_unset=True
    )

    # =====================================================
    # VALIDATE PATIENT ID CHANGE
    # =====================================================

    if "patient_id" in update_data:

        new_patient_id = update_data["patient_id"]

        if isinstance(new_patient_id, str):
            new_patient_id = new_patient_id.strip()

        if not new_patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Patient ID cannot be empty",
            )

        update_data["patient_id"] = new_patient_id

        # -------------------------------------------------
        # Check global uniqueness
        # -------------------------------------------------

        if new_patient_id != patient.patient_id:

            duplicate_patient = db.scalar(
                select(Patient).where(
                    Patient.patient_id == new_patient_id
                )
            )

            if duplicate_patient is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A patient with this patient ID already exists",
                )

    # =====================================================
    # NORMALIZE STRING VALUES
    # =====================================================

    for field, value in list(update_data.items()):

        if isinstance(value, str):

            value = value.strip()

            if not value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field} cannot be empty",
                )

            update_data[field] = value

    # =====================================================
    # SECURITY
    # =====================================================
    #
    # The client must NEVER be able to change ownership.
    #
    # =====================================================

    update_data.pop(
        "created_by",
        None,
    )

    # =====================================================
    # APPLY UPDATE
    # =====================================================

    for field, value in update_data.items():

        if hasattr(patient, field):

            setattr(
                patient,
                field,
                value,
            )

    # =====================================================
    # SAVE UPDATE
    # =====================================================

    try:
        db.commit()
        db.refresh(patient)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update patient",
        )

    return patient