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
from app.inference.worker_client import worker_client
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
):
    """
    Read and validate uploaded image.

    Returns:
        image      -> PIL RGB image
        raw_bytes  -> original uploaded bytes
    """

    # --------------------------------------------------------
    # CONTENT TYPE
    # --------------------------------------------------------

    content_type = (
        (file.content_type or "")
        .split(";")[0]
        .strip()
        .lower()
    )

    if content_type not in ALLOWED_CONTENT_TYPES:

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

    return image, contents


# ============================================================
# HELPER: CALL PLANE WORKER
# ============================================================

async def _run_plane_worker(
    file: UploadFile,
    contents: bytes,
):
    """
    Send image to isolated Plane Worker.

    Main FastAPI does not load the plane ML model.
    """

    try:

        result = await worker_client.predict(
            model_name="plane",
            filename=file.filename or "image.png",
            content=contents,
            content_type=(
                file.content_type
                or "image/png"
            ),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Plane worker unavailable: {exc}",
        ) from exc

    # --------------------------------------------------------
    # Worker response validation
    # --------------------------------------------------------

    if not isinstance(result, dict):

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Plane worker returned an invalid response",
        )

    worker_result = result.get(
        "result"
    )

    if not isinstance(
        worker_result,
        dict,
    ):

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Plane worker returned an invalid prediction",
        )

    return worker_result


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

    image, contents = (
        await _read_uploaded_image(
            file
        )
    )

    # Avoid unused-variable warnings while
    # still validating the image.
    _ = image

    # ========================================================
    # AI PREDICTION
    # ========================================================

    result = await _run_plane_worker(
        file,
        contents,
    )

    # ========================================================
    # VALIDATE AI RESULT
    # ========================================================

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
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI model did not return a predicted class",
        )

    if confidence is None:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI model did not return confidence",
        )

    try:

        confidence = float(
            confidence
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI model returned invalid confidence",
        ) from exc

    if not 0.0 <= confidence <= 1.0:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI model returned invalid confidence range",
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
            "architecture": {
                "mode": "worker_based",
                "plane_worker": "http://127.0.0.1:8100",
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

    image, contents = (
        await _read_uploaded_image(
            file
        )
    )

    _ = image

    # ========================================================
    # PLANE WORKER ANALYSIS
    # ========================================================

    fetal_plane = await _run_plane_worker(
        file,
        contents,
    )

    predicted_class = fetal_plane.get(
        "predicted_class"
    )

    confidence = fetal_plane.get(
        "confidence"
    )

    probabilities = fetal_plane.get(
        "probabilities",
        [],
    )

    if predicted_class is None:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Plane worker did not return "
                "a fetal-plane prediction"
            ),
        )

    if confidence is None:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Plane worker did not return "
                "a fetal-plane confidence"
            ),
        )

    try:

        confidence = float(
            confidence
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid fetal-plane confidence",
        ) from exc

    # ========================================================
    # MULTI-MODEL RESULT
    # ========================================================
    #
    # Brain workers are intentionally not called yet.
    # They will be added through the worker architecture.
    #
    # ========================================================

    result = {

        "fetal_plane": {
            "predicted_class": predicted_class,
            "confidence": confidence,
            "confidence_percent": round(
                confidence * 100,
                2,
            ),
            "probabilities": probabilities,
        },

        "brain_analysis_performed": False,

        "brain_plane": None,

        "outlier_analysis": None,

        "gradcam": {
            "available": False,
            "status": "not_available_in_worker_migration",
        },

        "pipeline_status": (
            "Plane analysis completed"
        ),

        "message": (
            "Fetal plane analysis completed "
            "through the isolated Plane Worker. "
            "Brain-specific workers are not connected yet."
        ),

        "architecture": {
            "type": "multi_model_worker",
            "plane_worker": {
                "enabled": True,
                "url": "http://127.0.0.1:8100",
            },
            "spine_worker": {
                "enabled": True,
                "url": "http://127.0.0.1:8101",
            },
            "brain_worker": {
                "enabled": False,
                "url": "http://127.0.0.1:8102",
            },
        },
    }

    # ========================================================
    # SAVE SCAN
    # ========================================================

    scan = Scan(
        patient_id=patient.id,
        uploaded_by=current_user.id,
        image_filename=file.filename or "unknown",
        predicted_plane=predicted_class,
        confidence=confidence,
        analysis_result=result,
    )

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
            "patient_id": patient.patient_id,
            "patient_name": patient.full_name,
        },

        "filename": file.filename,

        "analysis": result,

        "created_at": scan.created_at,
    }