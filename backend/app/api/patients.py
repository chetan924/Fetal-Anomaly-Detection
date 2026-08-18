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
    current_user: User = Depends(
        get_current_user
    ),
):
    # =====================================================
    # NORMALIZE PATIENT ID
    # =====================================================

    normalized_patient_id = (
        payload.patient_id.strip()
    )


    if not normalized_patient_id:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,

            detail=
                "Patient ID is required",
        )


    # =====================================================
    # CHECK GLOBAL PATIENT ID UNIQUENESS
    # =====================================================

    existing_patient = db.scalar(
        select(Patient).where(
            Patient.patient_id
            == normalized_patient_id
        )
    )


    if existing_patient:

        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail=
                "A patient with this patient ID already exists",
        )


    # =====================================================
    # NORMALIZE TEXT FIELDS
    # =====================================================

    full_name = (
        payload.full_name.strip()
    )


    gestational_age = (
        payload.gestational_age.strip()
    )


    phone = (
        payload.phone.strip()
        if payload.phone
        else None
    )


    if not full_name:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,

            detail=
                "Patient name is required",
        )


    if not gestational_age:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,

            detail=
                "Gestational age is required",
        )


    # =====================================================
    # CREATE PATIENT
    # =====================================================
    #
    # IMPORTANT:
    # Ownership is assigned from the authenticated JWT user.
    #
    # Client cannot choose created_by.
    #
    # =====================================================

    patient = Patient(

        patient_id=
            normalized_patient_id,

        full_name=
            full_name,

        age=
            payload.age,

        gestational_age=
            gestational_age,

        phone=
            phone,

        created_by=
            current_user.id,
    )


    # =====================================================
    # SAVE
    # =====================================================

    try:

        db.add(
            patient
        )

        db.commit()

        db.refresh(
            patient
        )

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=
                status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
                "Failed to create patient",
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
    current_user: User = Depends(
        get_current_user
    ),
):
    # =====================================================
    # ONLY CURRENT USER'S PATIENTS
    # =====================================================

    patients = db.scalars(

        select(
            Patient
        )

        .where(
            Patient.created_by
            == current_user.id
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
    current_user: User = Depends(
        get_current_user
    ),
):
    # =====================================================
    # NORMALIZE ID
    # =====================================================

    normalized_patient_id = (
        patient_id.strip()
    )


    if not normalized_patient_id:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,

            detail=
                "Patient ID is required",
        )


    # =====================================================
    # OWNERSHIP FILTER
    # =====================================================

    patient = db.scalar(

        select(
            Patient
        )

        .where(
            Patient.patient_id
            == normalized_patient_id,

            Patient.created_by
            == current_user.id,
        )
    )


    if patient is None:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail=
                "Patient not found",
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
    current_user: User = Depends(
        get_current_user
    ),
):
    # =====================================================
    # NORMALIZE ID
    # =====================================================

    normalized_patient_id = (
        patient_id.strip()
    )


    if not normalized_patient_id:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,

            detail=
                "Patient ID is required",
        )


    # =====================================================
    # FIND ONLY OWN PATIENT
    # =====================================================

    patient = db.scalar(

        select(
            Patient
        )

        .where(
            Patient.patient_id
            == normalized_patient_id,

            Patient.created_by
            == current_user.id,
        )
    )


    if patient is None:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail=
                "Patient not found",
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

        new_patient_id = (
            update_data["patient_id"]
        )


        if isinstance(
            new_patient_id,
            str,
        ):

            new_patient_id = (
                new_patient_id.strip()
            )

            update_data[
                "patient_id"
            ] = new_patient_id


        if not new_patient_id:

            raise HTTPException(
                status_code=
                    status.HTTP_400_BAD_REQUEST,

                detail=
                    "Patient ID cannot be empty",
            )


        # -------------------------------------------------
        # If changing patient ID, ensure global uniqueness
        # -------------------------------------------------

        if (
            new_patient_id
            != patient.patient_id
        ):

            duplicate_patient = db.scalar(

                select(
                    Patient
                )

                .where(
                    Patient.patient_id
                    == new_patient_id
                )
            )


            if duplicate_patient is not None:

                raise HTTPException(
                    status_code=
                        status.HTTP_409_CONFLICT,

                    detail=
                        "A patient with this patient ID already exists",
                )


    # =====================================================
    # NORMALIZE STRING VALUES
    # =====================================================

    for field, value in list(
        update_data.items()
    ):

        if isinstance(
            value,
            str,
        ):

            value = value.strip()


            if not value:

                raise HTTPException(
                    status_code=
                        status.HTTP_400_BAD_REQUEST,

                    detail=
                        f"{field} cannot be empty",
                )


            update_data[
                field
            ] = value


    # =====================================================
    # SECURITY:
    # NEVER ALLOW CLIENT TO CHANGE OWNER
    # =====================================================

    update_data.pop(
        "created_by",
        None,
    )


    # =====================================================
    # APPLY UPDATE
    # =====================================================

    for field, value in update_data.items():

        if hasattr(
            patient,
            field,
        ):

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

        db.refresh(
            patient
        )

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=
                status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
                "Failed to update patient",
        )


    return patient