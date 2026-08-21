from pathlib import Path
import gc
import sys

from PIL import Image

from app.ml.predict_plane import predict_plane
from app.ml.predict_brain_plane import predict_brain_plane
from app.ml.predict_brain_anomaly import predict_brain_anomaly
from app.ml.gradcam import generate_gradcam



# ============================================================
# CONFIG
# ============================================================

BRAIN_CLASS = "Fetal brain"

# Brain-plane classification must reach this confidence
# before statistical brain analysis is performed.
BRAIN_PLANE_CONFIDENCE_THRESHOLD = 0.70

# FastAPI exposes the backend storage directory through:
#
# /storage
#
# Therefore explainability files become accessible through:
#
# /storage/explainability/<filename>
#
STORAGE_URL_PREFIX = "/storage"


# ============================================================
# IMAGE HELPER
# ============================================================

def _load_pil_image(image):
    """
    Accept either:
        - image file path
        - pathlib.Path
        - PIL.Image.Image

    and return an RGB PIL image.
    """

    if isinstance(image, (str, Path)):

        image_path = Path(image)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        return Image.open(
            image_path
        ).convert("RGB")

    if isinstance(image, Image.Image):

        return image.convert("RGB")

    raise TypeError(
        "image must be a PIL Image "
        "or image file path"
    )


# ============================================================
# STORAGE URL HELPER
# ============================================================

def _gradcam_storage_url(filename):
    """
    Convert an explainability filename into
    a browser-accessible storage URL.
    """

    if not filename:
        return None

    return (
        f"{STORAGE_URL_PREFIX}"
        f"/explainability/"
        f"{filename}"
    )


# ============================================================
# GRAD-CAM EXPLAINABILITY
# ============================================================

def _generate_explainability(image):
    """
    Generate Grad-CAM explainability.

    Important:
    Grad-CAM is best-effort.

    If Grad-CAM fails, the main fetal-plane
    classification should still succeed.

    The raw numpy heatmap is NOT returned because
    numpy arrays are not JSON serializable.
    """

    try:

        # ----------------------------------------------------
        # Determine output prefix
        # ----------------------------------------------------

        if isinstance(
            image,
            (str, Path),
        ):

            image_path = Path(image)

            output_prefix = (
                image_path.stem
            )

        else:

            # PIL image without a filename
            import uuid

            output_prefix = (
                f"gradcam_{uuid.uuid4().hex}"
            )

        # ----------------------------------------------------
        # Generate Grad-CAM
        # ----------------------------------------------------

        gradcam_result = generate_gradcam(
            image,
            output_prefix=output_prefix,
        )

        # ----------------------------------------------------
        # Get generated files
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Attention information
        # ----------------------------------------------------

        attention = gradcam_result.get(
            "attention_concentration",
            {},
        )

        # ----------------------------------------------------
        # JSON-safe response
        # ----------------------------------------------------

        return {

            "available": True,

            "target_class":
                gradcam_result.get(
                    "target_class"
                ),

            "target_class_index":
                gradcam_result.get(
                    "target_class_index"
                ),

            "confidence":
                gradcam_result.get(
                    "confidence"
                ),

            "confidence_percent":
                gradcam_result.get(
                    "confidence_percent"
                ),

            "attention_concentration": {

                "score":
                    attention.get(
                        "score"
                    ),

                "entropy":
                    attention.get(
                        "entropy"
                    ),

                "interpretation":
                    attention.get(
                        "interpretation"
                    ),

                "status":
                    attention.get(
                        "status"
                    ),
            },

            # ------------------------------------------------
            # Browser URLs
            # ------------------------------------------------

            "heatmap_url":
                _gradcam_storage_url(
                    heatmap_path.name
                ),

            "overlay_url":
                _gradcam_storage_url(
                    overlay_path.name
                ),

            # ------------------------------------------------
            # Filenames
            # ------------------------------------------------

            "heatmap_filename":
                heatmap_path.name,

            "overlay_filename":
                overlay_path.name,

            # ------------------------------------------------
            # Backend filesystem paths
            # ------------------------------------------------

            "heatmap_path":
                str(
                    heatmap_path
                ),

            "overlay_path":
                str(
                    overlay_path
                ),
        }

    except Exception as exc:

        # ----------------------------------------------------
        # Grad-CAM failure should NOT fail the complete
        # fetal-plane analysis.
        # ----------------------------------------------------

        print()
        print(
            "Grad-CAM generation failed:"
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        return {

            "available": False,

            "error":
                str(exc),

            "message": (
                "Fetal-plane analysis completed, "
                "but Grad-CAM explainability "
                "could not be generated."
            ),
        }


# ============================================================
# COMPLETE FETAL ANALYSIS PIPELINE
# ============================================================

def analyze_fetal_ultrasound(image):
    """
    Complete FetalAI ultrasound analysis pipeline.

    Pipeline:

        MODEL 1
        Fetal Plane Classification
                |
                v
        GRAD-CAM
        Explainability
                |
                v
        If Fetal brain
                |
                v
        MODEL 1.5
        Brain Plane Classification
                |
                v
        Confidence Guard
                |
                v
        MODEL 2
        Statistical Brain Outlier Analysis

    Notes:

    - Grad-CAM is an explainability mechanism.
    - Grad-CAM is NOT a clinical diagnosis.
    - Statistical analysis only runs when
      brain-plane confidence >= 70%.
    """

    # ========================================================
    # LOAD IMAGE
    # ========================================================

    pil_image = _load_pil_image(
        image
    )

    # ========================================================
    # MODEL 1 — FETAL PLANE CLASSIFICATION
    # ========================================================

    plane_result = predict_plane(
        pil_image
    )

    predicted_plane = plane_result[
        "predicted_class"
    ]

    plane_confidence = float(
        plane_result[
            "confidence"
        ]
    )

    # ========================================================
    # BASE RESPONSE
    # ========================================================

    response = {

        "fetal_plane": {

            "predicted_class":
                predicted_plane,

            "confidence":
                plane_confidence,

            "confidence_percent":
                round(
                    plane_confidence * 100,
                    2,
                ),

            "probabilities":
                plane_result.get(
                    "probabilities",
                    [],
                ),
        },

        "brain_analysis_performed":
            False,

        "brain_plane":
            None,

        "outlier_analysis":
            None,

        "gradcam":
            None,
    }

    # ========================================================
    # GRAD-CAM
    # ========================================================
    #
    # Generate explainability for the fetal-plane model.
    #
    # This works for:
    #
    # Fetal brain
    # Other
    # Fetal abdomen
    # Fetal thorax
    # Fetal femur
    # Maternal cervix
    #
    # ========================================================

    response[
        "gradcam"
    ] = _generate_explainability(
        image
    )

    # ========================================================
    # NOT A FETAL BRAIN IMAGE
    # ========================================================

    if predicted_plane != BRAIN_CLASS:

        response[
            "pipeline_status"
        ] = (
            "Plane classification complete"
        )

        response[
            "message"
        ] = (
            "The uploaded image was not classified "
            "as a fetal-brain plane, so brain-specific "
            "analysis was not performed."
        )

        return response

    # ========================================================
    # MODEL 1.5 — BRAIN PLANE CLASSIFICATION
    # ========================================================

    brain_result = predict_brain_plane(
        pil_image
    )

    brain_plane = brain_result[
        "predicted_class"
    ]

    brain_confidence = float(
        brain_result[
            "confidence"
        ]
    )

    response[
        "brain_plane"
    ] = {

        "predicted_class":
            brain_plane,

        "confidence":
            brain_confidence,

        "confidence_percent":
            round(
                brain_confidence * 100,
                2,
            ),

        "probabilities":
            brain_result.get(
                "probabilities",
                [],
            ),
    }

    # ========================================================
    # CONFIDENCE GUARD
    # ========================================================

    if (
        brain_confidence
        < BRAIN_PLANE_CONFIDENCE_THRESHOLD
    ):

        response[
            "pipeline_status"
        ] = (
            "Brain plane uncertain"
        )

        response[
            "message"
        ] = (
            "The fetal-brain image was detected, "
            "but brain-plane classification confidence "
            "was below the automatic-analysis threshold. "
            "Statistical outlier analysis was therefore "
            "not performed."
        )

        response[
            "required_confidence"
        ] = round(
            BRAIN_PLANE_CONFIDENCE_THRESHOLD * 100,
            2,
        )

        return response

    # ========================================================
    # MODEL 2 — STATISTICAL OUTLIER SCORING
    # ========================================================

    anomaly_result = predict_brain_anomaly(
        pil_image,
        brain_plane,
    )

    response[
        "brain_analysis_performed"
    ] = True

    response[
        "outlier_analysis"
    ] = anomaly_result

    response[
        "pipeline_status"
    ] = (
        "Brain analysis complete"
    )

    response[
        "message"
    ] = (
        "Brain-plane classification confidence was "
        "sufficient for plane-specific statistical "
        "outlier analysis."
    )

    return response


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) < 2:

        print()
        print(
            "Usage:"
        )

        print(
            'python -m app.ml.fetal_analysis_pipeline '
            '"IMAGE_PATH"'
        )

        sys.exit(1)

    image_path = sys.argv[1]

    print()
    print(
        "=" * 70
    )

    print(
        "AUTOMATIC FETAL ULTRASOUND ANALYSIS"
    )

    print(
        "=" * 70
    )

    try:

        result = analyze_fetal_ultrasound(
            image_path
        )

    except Exception as exc:

        print()
        print(
            "Fetal analysis failed:"
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        sys.exit(1)

    # ========================================================
    # MODEL 1
    # ========================================================

    fetal_plane = result[
        "fetal_plane"
    ]

    print()
    print(
        "MODEL 1 — FETAL PLANE"
    )

    print(
        "Prediction :",
        fetal_plane[
            "predicted_class"
        ],
    )

    print(
        "Confidence :",
        f'{fetal_plane["confidence_percent"]:.2f}%',
    )

    # ========================================================
    # GRAD-CAM
    # ========================================================

    gradcam = result.get(
        "gradcam"
    )

    print()
    print(
        "GRAD-CAM — AI EXPLAINABILITY"
    )

    if (
        gradcam
        and gradcam.get(
            "available"
        )
    ):

        print(
            "Target class :",
            gradcam.get(
                "target_class"
            ),
        )

        print(
            "Confidence   :",
            f'{float(gradcam.get("confidence_percent", 0)):.2f}%',
        )

        attention = gradcam.get(
            "attention_concentration",
            {},
        )

        print(
            "Attention score :",
            attention.get(
                "score"
            ),
        )

        print(
            "Attention status:",
            attention.get(
                "status"
            ),
        )

        print(
            "Heatmap URL     :",
            gradcam.get(
                "heatmap_url"
            ),
        )

        print(
            "Overlay URL     :",
            gradcam.get(
                "overlay_url"
            ),
        )

        print(
            "Heatmap file    :",
            gradcam.get(
                "heatmap_path"
            ),
        )

        print(
            "Overlay file    :",
            gradcam.get(
                "overlay_path"
            ),
        )

    else:

        print(
            "Status:",
            "Grad-CAM unavailable",
        )

        if gradcam:

            print(
                "Reason:",
                gradcam.get(
                    "error",
                    "Unknown error",
                ),
            )

    # ========================================================
    # MODEL 1.5
    # ========================================================

    if (
        result[
            "brain_plane"
        ]
        is not None
    ):

        brain_plane = result[
            "brain_plane"
        ]

        print()
        print(
            "MODEL 1.5 — BRAIN PLANE"
        )

        print(
            "Prediction :",
            brain_plane[
                "predicted_class"
            ],
        )

        print(
            "Confidence :",
            f'{brain_plane["confidence_percent"]:.2f}%',
        )

    # ========================================================
    # MODEL 2
    # ========================================================

    if (
        result[
            "outlier_analysis"
        ]
        is not None
    ):

        anomaly = result[
            "outlier_analysis"
        ]

        print()
        print(
            "MODEL 2 — STATISTICAL SCREENING"
        )

        print(
            "Status    :",
            anomaly.get(
                "status"
            ),
        )

        print(
            "Score     :",
            anomaly.get(
                "anomaly_score"
            ),
        )

        print(
            "Threshold :",
            anomaly.get(
                "threshold"
            ),
        )

        print(
            "Ratio     :",
            anomaly.get(
                "threshold_ratio"
            ),
        )

    # ========================================================
    # FINAL STATUS
    # ========================================================

    print()
    print(
        "-" * 70
    )

    print(
        "Pipeline status:",
        result[
            "pipeline_status"
        ],
    )

    print(
        "Message:",
        result[
            "message"
        ],
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "Statistical outlier analysis is experimental "
        "and is not a clinically validated fetal "
        "anomaly diagnosis."
    )

    print(
        "Grad-CAM attention metrics are explainability "
        "metrics only and are not clinical reliability "
        "scores or medical diagnoses."
    )