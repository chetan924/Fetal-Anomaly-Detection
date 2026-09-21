from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.audit_logger import security_audit
from app.db.database import get_db
from app.inference.worker_client import worker_client
from app.models.patient import Patient
from app.models.scan import Scan
from app.models.user import User


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/api/scans",
    tags=["Scans"],
)


# =========================================================
# CONFIG
# =========================================================

BACKEND_ROOT = Path(__file__).resolve().parents[2]
STORAGE_DIR = BACKEND_ROOT / "storage"
SCAN_STORAGE_DIR = STORAGE_DIR / "scans"
EXPLAINABILITY_DIR = STORAGE_DIR / "explainability"

SCAN_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
EXPLAINABILITY_DIR.mkdir(parents=True, exist_ok=True)

PLANE_WORKER_NAME = "plane"

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
}

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
UPLOAD_CHUNK_SIZE = 1024 * 1024


def validate_image_content(image_path: Path) -> None:
    try:
        from PIL import Image, UnidentifiedImageError
        with Image.open(image_path) as image:
            image.verify()
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image validation dependency is unavailable.",
        ) from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid image.",
        ) from exc


def read_stored_image(image_path: Path) -> bytes:
    try:
        return image_path.read_bytes()
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read stored image.",
        ) from exc


async def run_plane_worker(
    image_path: Path,
    filename: str,
    content_type: str,
) -> dict:
    image_bytes = read_stored_image(image_path)
    try:
        worker_response = await worker_client.predict(
            model_name=PLANE_WORKER_NAME,
            filename=filename,
            content=image_bytes,
            content_type=content_type,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Plane worker unavailable: {exc}",
        ) from exc

    if not isinstance(worker_response, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Plane worker returned an invalid response.",
        )

    result = worker_response.get("result")
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Plane worker returned an invalid prediction.",
        )

    return result


def build_analysis_result(fetal_plane: dict) -> dict:
    predicted_class = fetal_plane.get("predicted_class")
    confidence = fetal_plane.get("confidence")
    probabilities = fetal_plane.get("probabilities", [])

    if predicted_class is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Plane worker did not return a predicted class.",
        )

    try:
        confidence = float(confidence)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Plane worker returned an invalid confidence.",
        ) from exc

    if not (0.0 <= confidence <= 1.0):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Plane worker returned an invalid confidence range.",
        )

    return {
        "fetal_plane": {
            "predicted_class": predicted_class,
            "confidence": confidence,
            "confidence_percent": round(confidence * 100, 2),
            "probabilities": probabilities,
        },
        "brain_analysis_performed": False,
        "brain_plane": None,
        "outlier_analysis": None,
        "gradcam": {
            "available": False,
            "status": "worker_migration_pending",
            "message": "Grad-CAM is temporarily unavailable while ML inference is being moved to isolated workers.",
        },
        "explainability": {
            "type": "Grad-CAM",
            "status": "unavailable",
            "message": "Explainability worker is not connected yet.",
        },
        "pipeline_status": "Plane analysis completed",
        "message": "Fetal plane analysis completed through the isolated Plane Worker.",
        "architecture": {
            "type": "multi_model_worker",
            "plane": {"enabled": True, "worker": "plane", "port": 8100},
            "spine": {"enabled": True, "worker": "spine", "port": 8101},
            "brain": {"enabled": False, "worker": "brain", "port": 8102},
            "lungs": {"enabled": False},
            "abdomen": {"enabled": False},
            "bone": {"enabled": False},
            "placenta": {"enabled": False},
            "face": {"enabled": False},
            "kidney": {"enabled": False},
        },
    }


def scan_to_response(scan: Scan, patient: Patient) -> dict:
    analysis_result = scan.analysis_result or {}
    explainability = analysis_result.get("explainability")

    if isinstance(explainability, dict):
        explainability = dict(explainability)
        heatmap_path = explainability.get("heatmap_path")
        overlay_path = explainability.get("overlay_path")

        if heatmap_path:
            heatmap_path = str(heatmap_path).replace("\\", "/").lstrip("/")
            if not heatmap_path.startswith("storage/"):
                heatmap_path = f"storage/{heatmap_path}"
            explainability["heatmap_url"] = f"/{heatmap_path}"

        if overlay_path:
            overlay_path = str(overlay_path).replace("\\", "/").lstrip("/")
            if not overlay_path.startswith("storage/"):
                overlay_path = f"storage/{overlay_path}"
            explainability["overlay_url"] = f"/{overlay_path}"

    confidence = scan.confidence if scan.confidence is not None else 0.0

    return {
        "id": scan.id,
        "patient_id": patient.patient_id,
        "patient_name": patient.full_name,
        "uploaded_by": scan.uploaded_by,
        "image_filename": scan.image_filename,
        "predicted_plane": scan.predicted_plane,
        "confidence": confidence,
        "confidence_percent": round(confidence * 100, 2),
        "created_at": scan.created_at,
        "analysis_result": analysis_result,
        "explainability": explainability,
    }


# =========================================================
# CREATE / UPLOAD SCAN
# =========================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_scan(
    patient_id: str,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_patient_id = patient_id.strip() if isinstance(patient_id, str) else ""

    if not normalized_patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient ID is required",
        )

    patient = db.scalar(
        select(Patient).where(
            Patient.patient_id == normalized_patient_id,
            Patient.created_by == current_user.id,
        )
    )

    if patient is None:
        security_audit.log_authz_denied(
            user_id=current_user.id,
            resource_type="patient",
            resource_id=normalized_patient_id,
            action="UPLOAD_SCAN",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    raw_filename = file.filename or ""
    safe_filename = Path(raw_filename).name

    if not safe_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image filename is required",
        )

    extension = Path(safe_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image format. Allowed formats: JPG, JPEG, PNG, WEBP",
        )

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    allowed_extensions_for_type = ALLOWED_CONTENT_TYPES.get(content_type)

    if allowed_extensions_for_type is None or extension not in allowed_extensions_for_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image content type does not match the file extension.",
        )

    saved_filename = f"{uuid4().hex}{extension}"
    image_path = SCAN_STORAGE_DIR / saved_filename

    try:
        total_size = 0
        with image_path.open("wb") as output_file:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Image file exceeds the 10 MB upload limit.",
                    )
                output_file.write(chunk)
    except HTTPException:
        if image_path.exists():
            image_path.unlink()
        raise
    except Exception as exc:
        if image_path.exists():
            image_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded image.",
        ) from exc

    try:
        validate_image_content(image_path)
    except HTTPException:
        if image_path.exists():
            image_path.unlink()
        raise

    try:
        fetal_plane = await run_plane_worker(
            image_path=image_path,
            filename=safe_filename,
            content_type=content_type,
        )
        analysis_result = build_analysis_result(fetal_plane)
    except HTTPException:
        if image_path.exists():
            image_path.unlink()
        raise
    except Exception as exc:
        if image_path.exists():
            image_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Fetal ultrasound analysis failed: {exc}",
        ) from exc

    fetal_plane = analysis_result.get("fetal_plane", {})
    predicted_plane = fetal_plane.get("predicted_class")
    confidence = float(fetal_plane.get("confidence", 0.0))

    scan = Scan(
        patient_id=patient.id,
        uploaded_by=current_user.id,
        image_filename=saved_filename,
        predicted_plane=predicted_plane,
        confidence=confidence,
        analysis_result=analysis_result,
    )

    try:
        db.add(scan)
        db.commit()
        db.refresh(scan)

        security_audit.log_resource_access(
            event_type="SCAN_UPLOAD",
            user_id=current_user.id,
            resource_type="scan",
            resource_id=str(scan.id),
            request=request,
            details={
                "patient_id": patient.patient_id,
                "predicted_plane": predicted_plane,
                "confidence": confidence,
            },
        )
    except Exception as exc:
        db.rollback()
        if image_path.exists():
            image_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save scan to database.",
        ) from exc

    return {
        "scan": scan_to_response(scan, patient),
        "analysis": analysis_result,
        "original_filename": safe_filename,
    }


# =========================================================
# GET ALL SCANS
# =========================================================

@router.get("")
def get_scans(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.execute(
        select(Scan, Patient)
        .join(Patient, Scan.patient_id == Patient.id)
        .where(
            Scan.uploaded_by == current_user.id,
            Patient.created_by == current_user.id,
        )
        .order_by(Scan.id.desc())
    ).all()

    security_audit.log_resource_access(
        event_type="SCAN_LIST",
        user_id=current_user.id,
        resource_type="scan",
        resource_id="list",
        request=request,
        details={"count": len(rows)},
    )

    return [scan_to_response(scan, patient) for scan, patient in rows]


# =========================================================
# GET SCANS FOR ONE PATIENT
# =========================================================

@router.get("/patient/{patient_id}")
def get_patient_scans(
    patient_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_patient_id = patient_id.strip() if isinstance(patient_id, str) else ""

    if not normalized_patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient ID is required",
        )

    patient = db.scalar(
        select(Patient).where(
            Patient.patient_id == normalized_patient_id,
            Patient.created_by == current_user.id,
        )
    )

    if patient is None:
        security_audit.log_authz_denied(
            user_id=current_user.id,
            resource_type="patient_scans",
            resource_id=normalized_patient_id,
            action="VIEW",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    scans = db.scalars(
        select(Scan).where(
            Scan.patient_id == patient.id,
            Scan.uploaded_by == current_user.id,
        ).order_by(Scan.id.desc())
    ).all()

    security_audit.log_resource_access(
        event_type="SCAN_LIST_PATIENT",
        user_id=current_user.id,
        resource_type="patient_scans",
        resource_id=patient.patient_id,
        request=request,
        details={"count": len(scans)},
    )

    return {
        "patient_id": patient.patient_id,
        "patient_name": patient.full_name,
        "total_scans": len(scans),
        "scans": [scan_to_response(scan, patient) for scan in scans],
    }


# =========================================================
# GET SINGLE SCAN
# =========================================================

@router.get("/{scan_id}")
def get_scan(
    scan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if scan_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scan ID",
        )

    row = db.execute(
        select(Scan, Patient)
        .join(Patient, Scan.patient_id == Patient.id)
        .where(
            Scan.id == scan_id,
            Scan.uploaded_by == current_user.id,
            Patient.created_by == current_user.id,
        )
    ).first()

    if row is None:
        security_audit.log_authz_denied(
            user_id=current_user.id,
            resource_type="scan",
            resource_id=str(scan_id),
            action="VIEW",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    scan, patient = row

    security_audit.log_resource_access(
        event_type="SCAN_VIEW",
        user_id=current_user.id,
        resource_type="scan",
        resource_id=str(scan.id),
        request=request,
    )

    return scan_to_response(scan, patient)
