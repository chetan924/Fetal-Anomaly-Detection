from pathlib import Path
import sys

from PIL import Image

from app.ml.predict_plane import predict_plane
from app.ml.predict_brain_plane import predict_brain_plane
from app.ml.predict_brain_anomaly import predict_brain_anomaly


# ============================================================
# CONFIG
# ============================================================

BRAIN_CLASS = "Fetal brain"

# Brain-plane classifier is not reliable enough to blindly
# select an anomaly reference when confidence is low.
BRAIN_PLANE_CONFIDENCE_THRESHOLD = 0.70


# ============================================================
# COMPLETE FETAL ANALYSIS PIPELINE
# ============================================================

def analyze_fetal_ultrasound(image):

    # --------------------------------------------------------
    # Accept path or PIL image
    # --------------------------------------------------------

    if isinstance(image, (str, Path)):

        image_path = Path(image)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        pil_image = Image.open(
            image_path
        ).convert("RGB")

    elif isinstance(image, Image.Image):

        pil_image = image.convert("RGB")

    else:

        raise TypeError(
            "image must be a PIL Image "
            "or image file path"
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
        plane_result["confidence"]
    )

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

        "brain_analysis_performed": False,

        "brain_plane": None,

        "outlier_analysis": None,
    }

    # ========================================================
    # NOT A FETAL BRAIN IMAGE
    # ========================================================

    if predicted_plane != BRAIN_CLASS:

        response["pipeline_status"] = (
            "Plane classification complete"
        )

        response["message"] = (
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
        brain_result["confidence"]
    )

    response["brain_plane"] = {
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

        response["pipeline_status"] = (
            "Brain plane uncertain"
        )

        response["message"] = (
            "The fetal-brain image was detected, "
            "but brain-plane classification confidence "
            "was below the automatic-analysis threshold. "
            "Statistical outlier analysis was therefore "
            "not performed."
        )

        response["required_confidence"] = round(
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

    response["brain_analysis_performed"] = True

    response["outlier_analysis"] = (
        anomaly_result
    )

    response["pipeline_status"] = (
        "Brain analysis complete"
    )

    response["message"] = (
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
        print("Usage:")

        print(
            'python -m app.ml.fetal_analysis_pipeline '
            '"IMAGE_PATH"'
        )

        sys.exit(1)

    image_path = sys.argv[1]

    print()
    print("=" * 65)
    print("AUTOMATIC FETAL ULTRASOUND ANALYSIS")
    print("=" * 65)

    result = analyze_fetal_ultrasound(
        image_path
    )

    # --------------------------------------------------------
    # MODEL 1
    # --------------------------------------------------------

    fetal_plane = result[
        "fetal_plane"
    ]

    print()
    print("MODEL 1 — FETAL PLANE")

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

    # --------------------------------------------------------
    # MODEL 1.5
    # --------------------------------------------------------

    if result["brain_plane"] is not None:

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

    # --------------------------------------------------------
    # MODEL 2
    # --------------------------------------------------------

    if (
        result["outlier_analysis"]
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
            anomaly["status"],
        )

        print(
            "Score     :",
            anomaly["anomaly_score"],
        )

        print(
            "Threshold :",
            anomaly["threshold"],
        )

        print(
            "Ratio     :",
            anomaly["threshold_ratio"],
        )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    print()
    print("-" * 65)

    print(
        "Pipeline status:",
        result["pipeline_status"],
    )

    print(
        "Message:",
        result["message"],
    )

    print()
    print(
        "IMPORTANT: Statistical outlier analysis "
        "is experimental and is not a clinically "
        "validated fetal anomaly diagnosis."
    )