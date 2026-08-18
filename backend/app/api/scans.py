from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.patient import Patient
from app.models.scan import Scan
from app.models.user import User

from app.ml.fetal_analysis_pipeline import (
    analyze_fetal_ultrasound,
)

from app.ml.gradcam import (
    generate_gradcam,
)


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

BACKEND_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


STORAGE_DIR = (
    BACKEND_ROOT
    / "storage"
)


SCAN_STORAGE_DIR = (
    STORAGE_DIR
    / "scans"
)


EXPLAINABILITY_DIR = (
    STORAGE_DIR
    / "explainability"
)


SCAN_STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


EXPLAINABILITY_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# UPLOAD SECURITY
# =========================================================

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


ALLOWED_CONTENT_TYPES = {
    "image/jpeg": {
        ".jpg",
        ".jpeg",
    },
    "image/png": {
        ".png",
    },
    "image/webp": {
        ".webp",
    },
}


MAX_UPLOAD_SIZE = (
    10 * 1024 * 1024
)


UPLOAD_CHUNK_SIZE = (
    1024 * 1024
)


# =========================================================
# IMAGE VALIDATION
# =========================================================

def validate_image_content(
    image_path: Path,
) -> None:

    """
    Validate actual image bytes instead of trusting only
    filename extension or browser-provided content type.
    """

    try:

        from PIL import (
            Image,
            UnidentifiedImageError,
        )

        with Image.open(
            image_path
        ) as image:

            image.verify()


    except ImportError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
                "Image validation dependency is unavailable.",
        ) from exc


    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,

            detail=
                "Uploaded file is not a valid image.",
        ) from exc


# =========================================================
# HELPER
# =========================================================

def scan_to_response(
    scan: Scan,
    patient: Patient,
) -> dict:

    # -----------------------------------------------------
    # Complete stored AI result
    # -----------------------------------------------------

    analysis_result = (
        scan.analysis_result
        or {}
    )


    # -----------------------------------------------------
    # Grad-CAM / Explainability
    # -----------------------------------------------------

    explainability = (
        analysis_result.get(
            "explainability"
        )
    )


    # -----------------------------------------------------
    # Normalize explainability URLs
    # -----------------------------------------------------

    if isinstance(
        explainability,
        dict,
    ):

        explainability = dict(
            explainability
        )


        heatmap_path = (
            explainability.get(
                "heatmap_path"
            )
        )


        overlay_path = (
            explainability.get(
                "overlay_path"
            )
        )


        if heatmap_path:

            heatmap_path = (
                str(heatmap_path)
                .replace("\\", "/")
                .lstrip("/")
            )


            if not heatmap_path.startswith(
                "storage/"
            ):

                heatmap_path = (
                    f"storage/{heatmap_path}"
                )


            explainability[
                "heatmap_url"
            ] = f"/{heatmap_path}"


        if overlay_path:

            overlay_path = (
                str(overlay_path)
                .replace("\\", "/")
                .lstrip("/")
            )


            if not overlay_path.startswith(
                "storage/"
            ):

                overlay_path = (
                    f"storage/{overlay_path}"
                )


            explainability[
                "overlay_url"
            ] = f"/{overlay_path}"


    # =====================================================
    # RESPONSE
    # =====================================================

    return {

        "id":
            scan.id,

        "patient_id":
            patient.patient_id,

        "patient_name":
            patient.full_name,

        "uploaded_by":
            scan.uploaded_by,

        "image_filename":
            scan.image_filename,

        "predicted_plane":
            scan.predicted_plane,

        "confidence":
            scan.confidence,

        "confidence_percent":
            round(
                scan.confidence * 100,
                2,
            ),

        "created_at":
            scan.created_at,

        "analysis_result":
            analysis_result,

        "explainability":
            explainability,
    }


# =========================================================
# CREATE / UPLOAD SCAN
# =========================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
async def create_scan(

    patient_id: str,

    file: UploadFile = File(...),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):

    # =====================================================
    # NORMALIZE PATIENT ID
    # =====================================================

    normalized_patient_id = (
        patient_id.strip()
        if isinstance(
            patient_id,
            str,
        )
        else ""
    )


    if not normalized_patient_id:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,

            detail=
                "Patient ID is required",
        )


    # =====================================================
    # FIND CURRENT USER'S PATIENT
    # =====================================================
    #
    # SECURITY:
    # Patient must belong to current authenticated user.
    #
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
    # VALIDATE FILENAME
    # =====================================================

    if not file.filename:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,

            detail=
                "Image filename is required",
        )


    original_name = Path(
        file.filename
    )


    extension = (
        original_name.suffix.lower()
    )


    if extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,

            detail=(
                "Unsupported image format. "
                "Allowed formats: "
                "JPG, JPEG, PNG, WEBP"
            ),
        )


    # =====================================================
    # VALIDATE DECLARED CONTENT TYPE
    # =====================================================

    content_type = (
        (file.content_type or "")
        .split(";")[0]
        .strip()
        .lower()
    )


    allowed_extensions_for_type = (
        ALLOWED_CONTENT_TYPES.get(
            content_type
        )
    )


    if (
        allowed_extensions_for_type
        is None
        or extension
        not in allowed_extensions_for_type
    ):

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,

            detail=
                "Image content type does not match "
                "the file extension.",
        )


    # =====================================================
    # SAVE IMAGE SAFELY
    # =====================================================

    saved_filename = (
        f"{uuid4().hex}{extension}"
    )


    image_path = (
        SCAN_STORAGE_DIR
        / saved_filename
    )


    try:

        total_size = 0


        with image_path.open(
            "wb"
        ) as output_file:

            while True:

                chunk = await file.read(
                    UPLOAD_CHUNK_SIZE
                )


                if not chunk:
                    break


                total_size += len(
                    chunk
                )


                if (
                    total_size
                    > MAX_UPLOAD_SIZE
                ):

                    raise HTTPException(
                        status_code=
                            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,

                        detail=
                            "Image file exceeds the "
                            "10 MB upload limit.",
                    )


                output_file.write(
                    chunk
                )


    except HTTPException:

        if image_path.exists():

            image_path.unlink()

        raise


    except Exception:

        if image_path.exists():

            image_path.unlink()


        raise HTTPException(
            status_code=
                status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
                "Failed to save uploaded image.",
        )


    # =====================================================
    # VALIDATE ACTUAL IMAGE CONTENT
    # =====================================================

    try:

        validate_image_content(
            image_path
        )


    except HTTPException:

        if image_path.exists():

            image_path.unlink()

        raise


    # =====================================================
    # AI ANALYSIS
    # =====================================================

    try:

        analysis_result = (
            analyze_fetal_ultrasound(
                image_path
            )
        )


    except Exception:

        if image_path.exists():

            image_path.unlink()


        raise HTTPException(
            status_code=
                status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
                "Fetal ultrasound analysis failed.",
        )


    # =====================================================
    # VALIDATE AI RESULT
    # =====================================================

    if not isinstance(
        analysis_result,
        dict,
    ):

        if image_path.exists():

            image_path.unlink()


        raise HTTPException(
            status_code=
                status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
                "AI analysis returned an invalid result",
        )


    # =====================================================
    # EXTRACT FETAL PLANE
    # =====================================================

    fetal_plane = (
        analysis_result.get(
            "fetal_plane",
            {},
        )
    )


    if not isinstance(
        fetal_plane,
        dict,
    ):

        if image_path.exists():

            image_path.unlink()


        raise HTTPException(
            status_code=
                status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
                "Invalid fetal-plane analysis result",
        )


    predicted_plane = (
        fetal_plane.get(
            "predicted_class"
        )
    )


    try:

        confidence = float(
            fetal_plane.get(
                "confidence",
                0.0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        if image_path.exists():

            image_path.unlink()


        raise HTTPException(
            status_code=
                status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
                "AI analysis returned an invalid confidence value",
        )


    if not predicted_plane:

        if image_path.exists():

            image_path.unlink()


        raise HTTPException(
            status_code=
                status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
                "AI analysis did not return a fetal plane",
        )


    if not 0.0 <= confidence <= 1.0:

        if image_path.exists():

            image_path.unlink()


        raise HTTPException(
            status_code=
                status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
                "AI analysis returned an invalid confidence value",
        )


    # =====================================================
    # GRAD-CAM EXPLAINABILITY
    # =====================================================

    explainability = None


    try:

        gradcam_result = generate_gradcam(

            image_path,

            output_prefix=(
                Path(
                    saved_filename
                ).stem
                + "_gradcam"
            ),
        )


        heatmap_path = Path(
            gradcam_result[
                "heatmap_path"
            ]
        )


        overlay_path = Path(
            gradcam_result[
                "overlay_path"
            ]
        )


        heatmap_path = (
            heatmap_path
            .resolve()
        )


        overlay_path = (
            overlay_path
            .resolve()
        )


        explainability_root = (
            EXPLAINABILITY_DIR
            .resolve()
        )


        try:

            heatmap_relative_to_storage = (
                heatmap_path
                .relative_to(
                    explainability_root
                )
            )


            overlay_relative_to_storage = (
                overlay_path
                .relative_to(
                    explainability_root
                )
            )

        except ValueError as exc:

            raise RuntimeError(
                "Grad-CAM generated output "
                "outside the explainability directory."
            ) from exc


        heatmap_relative = (
            Path(
                "storage"
            )
            / "explainability"
            / heatmap_relative_to_storage
        ).as_posix()


        overlay_relative = (
            Path(
                "storage"
            )
            / "explainability"
            / overlay_relative_to_storage
        ).as_posix()


        explainability = {

            "type":
                "Grad-CAM",

            "status":
                "available",

            "target_class":
                gradcam_result[
                    "target_class"
                ],

            "confidence":
                gradcam_result[
                    "confidence"
                ],

            "confidence_percent":
                gradcam_result[
                    "confidence_percent"
                ],

            "heatmap_path":
                heatmap_relative,

            "overlay_path":
                overlay_relative,

            "heatmap_url":
                f"/{heatmap_relative}",

            "overlay_url":
                f"/{overlay_relative}",
        }


        analysis_result[
            "explainability"
        ] = explainability


    except Exception:

        explainability = {

            "type":
                "Grad-CAM",

            "status":
                "unavailable",

            "message":
                "Explainability output "
                "could not be generated.",
        }


        analysis_result[
            "explainability"
        ] = explainability


    # =====================================================
    # SAVE SCAN TO DATABASE
    # =====================================================

    scan = Scan(

        patient_id=
            patient.id,

        # -------------------------------------------------
        # SECURITY:
        # Always derive owner from authenticated user.
        # Never accept uploaded_by from frontend.
        # -------------------------------------------------

        uploaded_by=
            current_user.id,

        image_filename=
            saved_filename,

        predicted_plane=
            predicted_plane,

        confidence=
            confidence,

        analysis_result=
            analysis_result,
    )


    try:

        db.add(
            scan
        )

        db.commit()

        db.refresh(
            scan
        )


    except Exception:

        db.rollback()


        if image_path.exists():

            image_path.unlink()


        raise HTTPException(
            status_code=
                status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
                "Failed to save scan to database.",
        )


    # =====================================================
    # RETURN COMPLETE RESULT
    # =====================================================

    return {

        "scan":
            scan_to_response(
                scan,
                patient,
            ),

        "analysis":
            analysis_result,

        "original_filename":
            file.filename,
    }


# =========================================================
# GET ALL SCANS
# =========================================================

@router.get("")
def get_scans(

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):

    # =====================================================
    # SECURITY:
    # Return only scans belonging to current user.
    #
    # Both conditions are checked:
    #
    # 1. scan.uploaded_by
    # 2. patient.created_by
    #
    # =====================================================

    rows = db.execute(

        select(
            Scan,
            Patient,
        )

        .join(
            Patient,
            Scan.patient_id
            == Patient.id,
        )

        .where(
            Scan.uploaded_by
            == current_user.id,

            Patient.created_by
            == current_user.id,
        )

        .order_by(
            Scan.id.desc()
        )

    ).all()


    return [

        scan_to_response(
            scan,
            patient,
        )

        for scan, patient in rows
    ]


# =========================================================
# GET SCANS FOR ONE PATIENT
# =========================================================

@router.get(
    "/patient/{patient_id}"
)
def get_patient_scans(

    patient_id: str,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):

    # =====================================================
    # NORMALIZE PATIENT ID
    # =====================================================

    normalized_patient_id = (
        patient_id.strip()
        if isinstance(
            patient_id,
            str,
        )
        else ""
    )


    if not normalized_patient_id:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,

            detail=
                "Patient ID is required",
        )


    # =====================================================
    # FIND ONLY CURRENT USER'S PATIENT
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
    # GET PATIENT'S SCANS
    # =====================================================

    scans = db.scalars(

        select(
            Scan
        )

        .where(

            Scan.patient_id
            == patient.id,

            Scan.uploaded_by
            == current_user.id,

        )

        .order_by(
            Scan.id.desc()
        )

    ).all()


    return {

        "patient_id":
            patient.patient_id,

        "patient_name":
            patient.full_name,

        "total_scans":
            len(scans),

        "scans": [

            scan_to_response(
                scan,
                patient,
            )

            for scan in scans
        ],
    }


# =========================================================
# GET SINGLE SCAN
# =========================================================

@router.get(
    "/{scan_id}"
)
def get_scan(

    scan_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):

    # =====================================================
    # VALIDATE ID
    # =====================================================

    if scan_id <= 0:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,

            detail=
                "Invalid scan ID",
        )


    # =====================================================
    # SECURITY:
    # A scan is accessible only if:
    #
    # 1. Scan belongs to current user
    # 2. Patient belongs to current user
    #
    # =====================================================

    row = db.execute(

        select(
            Scan,
            Patient,
        )

        .join(
            Patient,
            Scan.patient_id
            == Patient.id,
        )

        .where(

            Scan.id
            == scan_id,

            Scan.uploaded_by
            == current_user.id,

            Patient.created_by
            == current_user.id,

        )

    ).first()


    if row is None:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail=
                "Scan not found",
        )


    scan, patient = row


    return scan_to_response(
        scan,
        patient,
    )