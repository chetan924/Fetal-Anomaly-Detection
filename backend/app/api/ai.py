from io import BytesIO

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.ml.predict_plane import predict_plane
from app.ml.fetal_analysis_pipeline import analyze_fetal_ultrasound
from app.models.patient import Patient
from app.models.scan import Scan
from app.models.user import User


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api/ai",
    tags=["AI Analysis"],
)


# ============================================================
# FILE VALIDATION
# ============================================================

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ============================================================
# HELPER: FIND PATIENT
# ============================================================

def _get_patient(
    patient_id: str,
    db: Session,
) -> Patient:

    patient_id = patient_id.strip()

    if not patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient ID is required",
        )

    patient = db.scalar(
        select(Patient).where(
            Patient.patient_id == patient_id
        )
    )

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    return patient


# ============================================================
# HELPER: READ AND VALIDATE IMAGE
# ============================================================

async def _read_uploaded_image(
    file: UploadFile,
) -> Image.Image:

    # --------------------------------------------------------
    # CONTENT TYPE
    # --------------------------------------------------------

    if file.content_type not in ALLOWED_CONTENT_TYPES:

        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PNG and JPEG images are supported",
        )

    # --------------------------------------------------------
    # READ FILE
    # --------------------------------------------------------

    contents = await file.read()

    if not contents:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    # --------------------------------------------------------
    # FILE SIZE
    # --------------------------------------------------------

    if len(contents) > MAX_FILE_SIZE:

        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image size must not exceed 10 MB",
        )

    # --------------------------------------------------------
    # VALIDATE ACTUAL IMAGE
    # --------------------------------------------------------

    try:

        image = Image.open(
            BytesIO(contents)
        ).convert("RGB")

    except (
        UnidentifiedImageError,
        OSError,
    ) as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file",
        ) from exc

    return image


# ============================================================
# PREDICT FETAL PLANE
# ============================================================

@router.post("/predict-plane")
async def predict_fetal_plane(
    patient_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # ========================================================
    # FIND PATIENT
    # ========================================================

    patient = _get_patient(
        patient_id,
        db,
    )

    # ========================================================
    # READ IMAGE
    # ========================================================

    image = await _read_uploaded_image(
        file
    )

    # ========================================================
    # AI PREDICTION
    # ========================================================

    try:

        result = predict_plane(
            image
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI prediction failed: {str(exc)}",
        ) from exc

    # ========================================================
    # VALIDATE AI RESULT
    # ========================================================

    if not isinstance(
        result,
        dict,
    ):

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI model returned an invalid result",
        )

    predicted_class = result.get(
        "predicted_class"
    )

    confidence = result.get(
        "confidence"
    )

    probabilities = result.get(
        "probabilities",
        [],
    )

    if predicted_class is None:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI model did not return a predicted class",
        )

    if confidence is None:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI model did not return confidence",
        )

    confidence = float(
        confidence
    )

    # ========================================================
    # SAVE BASIC SCAN RESULT
    # ========================================================

    scan = Scan(
        patient_id=patient.id,
        uploaded_by=current_user.id,
        image_filename=file.filename or "unknown",
        predicted_plane=predicted_class,
        confidence=confidence,

        # Store the prediction result as JSON.
        analysis_result={
            "fetal_plane": {
                "predicted_class": predicted_class,
                "confidence": confidence,
                "confidence_percent": round(
                    confidence * 100,
                    2,
                ),
                "probabilities": probabilities,
            },
        },
    )

    # ========================================================
    # DATABASE SAVE
    # ========================================================

    try:

        db.add(scan)

        db.commit()

        db.refresh(scan)

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Prediction succeeded but scan "
                "result could not be saved"
            ),
        ) from exc

    # ========================================================
    # RESPONSE
    # ========================================================

    return {

        "scan_id": scan.id,

        "patient_id": patient.patient_id,

        "patient_name": patient.full_name,

        "filename": file.filename,

        "predicted_class": predicted_class,

        "confidence": confidence,

        "confidence_percent": round(
            confidence * 100,
            2,
        ),

        "probabilities": probabilities,

        "created_at": scan.created_at,
    }


# ============================================================
# COMPLETE FETAL ULTRASOUND ANALYSIS
# ============================================================

@router.post("/analyze")
async def analyze_fetal_ultrasound_api(
    patient_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # ========================================================
    # FIND PATIENT
    # ========================================================

    patient = _get_patient(
        patient_id,
        db,
    )

    # ========================================================
    # READ IMAGE
    # ========================================================

    image = await _read_uploaded_image(
        file
    )

    # ========================================================
    # COMPLETE AI PIPELINE
    # ========================================================

    try:

        result = analyze_fetal_ultrasound(
            image
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fetal analysis failed: {str(exc)}",
        ) from exc

    # ========================================================
    # VALIDATE PIPELINE RESULT
    # ========================================================

    if not isinstance(
        result,
        dict,
    ):

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI pipeline returned an invalid result",
        )

    # ========================================================
    # FETAL PLANE
    # ========================================================

    fetal_plane = result.get(
        "fetal_plane"
    )

    if not isinstance(
        fetal_plane,
        dict,
    ):

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "AI pipeline result does not contain "
                "valid fetal-plane analysis"
            ),
        )

    predicted_class = fetal_plane.get(
        "predicted_class"
    )

    confidence = fetal_plane.get(
        "confidence"
    )

    if predicted_class is None:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "AI pipeline did not return "
                "a fetal-plane prediction"
            ),
        )

    if confidence is None:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "AI pipeline did not return "
                "a fetal-plane confidence"
            ),
        )

    confidence = float(
        confidence
    )

    # ========================================================
    # COMPLETE AI RESULT
    # ========================================================
    #
    # Store the complete pipeline result.
    #
    # This contains:
    #
    # - fetal_plane
    # - brain_analysis_performed
    # - brain_plane
    # - outlier_analysis
    # - gradcam
    # - pipeline_status
    # - message
    #
    # ========================================================

    scan = Scan(

        patient_id=patient.id,

        uploaded_by=current_user.id,

        image_filename=file.filename or "unknown",

        predicted_plane=predicted_class,

        confidence=confidence,

        analysis_result=result,
    )

    # ========================================================
    # DATABASE SAVE
    # ========================================================

    try:

        db.add(scan)

        db.commit()

        db.refresh(scan)

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "AI analysis succeeded but scan "
                "result could not be saved"
            ),
        ) from exc

    # ========================================================
    # RESPONSE
    # ========================================================

    return {

        "scan_id": scan.id,

        "patient": {

            "patient_id":
                patient.patient_id,

            "patient_name":
                patient.full_name,
        },

        "filename":
            file.filename,

        "analysis":
            result,

        "created_at":
            scan.created_at,
    }