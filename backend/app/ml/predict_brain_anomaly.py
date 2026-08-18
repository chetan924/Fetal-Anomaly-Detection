from pathlib import Path
import pickle
import sys

import numpy as np
import torch
from PIL import Image
from torchvision.models import (
    EfficientNet_B0_Weights,
    efficientnet_b0,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ARTIFACT_PATH = (
    BASE_DIR
    / "models"
    / "brain_anomaly_detector.pkl"
)

VALID_PLANES = [
    "Trans-thalamic",
    "Trans-cerebellum",
    "Trans-ventricular",
]


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# ============================================================
# LOAD ARTIFACT
# ============================================================

print("Loading brain outlier detector...")

if not ARTIFACT_PATH.exists():
    raise FileNotFoundError(
        f"Model artifact not found: {ARTIFACT_PATH}"
    )

with open(ARTIFACT_PATH, "rb") as file:
    artifact = pickle.load(file)

pca = artifact["pca"]
plane_models = artifact["plane_models"]


# ============================================================
# LOAD FEATURE EXTRACTOR
# ============================================================

weights = EfficientNet_B0_Weights.DEFAULT

transform = weights.transforms()

feature_model = efficientnet_b0(
    weights=weights
)

feature_model.classifier = torch.nn.Identity()

feature_model = feature_model.to(DEVICE)

feature_model.eval()

for parameter in feature_model.parameters():
    parameter.requires_grad = False


# ============================================================
# MAHALANOBIS DISTANCE
# ============================================================

def mahalanobis_score(
    feature,
    mean,
    precision,
):
    diff = feature - mean

    squared_distance = np.einsum(
        "ij,jk,ik->i",
        diff,
        precision,
        diff,
    )

    squared_distance = np.maximum(
        squared_distance,
        0,
    )

    return float(
        np.sqrt(squared_distance)[0]
    )


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def extract_feature(image: Image.Image):

    image = image.convert("RGB")

    tensor = transform(image)

    tensor = tensor.unsqueeze(0)

    tensor = tensor.to(DEVICE)

    with torch.inference_mode():
        feature = feature_model(tensor)

    feature = (
        feature
        .detach()
        .cpu()
        .numpy()
    )

    return feature


# ============================================================
# PREDICTION
# ============================================================

def predict_brain_anomaly(
    image,
    brain_plane,
):

    if brain_plane not in VALID_PLANES:
        raise ValueError(
            "Unsupported brain plane. "
            f"Expected one of: {VALID_PLANES}"
        )

    # --------------------------------------------------------
    # Accept PIL image or image path
    # --------------------------------------------------------

    if isinstance(image, (str, Path)):

        image_path = Path(image)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        image = Image.open(
            image_path
        ).convert("RGB")

    elif isinstance(image, Image.Image):

        image = image.convert("RGB")

    else:
        raise TypeError(
            "image must be a PIL Image "
            "or a file path"
        )

    # --------------------------------------------------------
    # EfficientNet features
    # --------------------------------------------------------

    feature = extract_feature(image)

    # --------------------------------------------------------
    # PCA
    # --------------------------------------------------------

    reduced_feature = pca.transform(
        feature
    )

    # --------------------------------------------------------
    # Plane-specific reference
    # --------------------------------------------------------

    reference = plane_models[
        brain_plane
    ]

    mean = reference["mean"]

    precision = reference["precision"]

    threshold = float(
        reference["threshold"]
    )

    # --------------------------------------------------------
    # Score
    # --------------------------------------------------------

    score = mahalanobis_score(
        reduced_feature,
        mean,
        precision,
    )

    is_outlier = score > threshold

    status = (
        "Unusual / Outlier"
        if is_outlier
        else "In-distribution"
    )

    # Ratio is useful for UI,
    # but it is NOT a medical probability.
    threshold_ratio = (
        score / threshold
        if threshold > 0
        else 0.0
    )

    return {
        "brain_plane": brain_plane,

        "status": status,

        "is_outlier": bool(
            is_outlier
        ),

        "anomaly_score": round(
            score,
            4,
        ),

        "threshold": round(
            threshold,
            4,
        ),

        "threshold_ratio": round(
            threshold_ratio,
            4,
        ),

        "interpretation": (
            "The image is a statistical outlier "
            "relative to the reference dataset."
            if is_outlier
            else
            "The image is within the statistical "
            "distribution of the reference dataset."
        ),

        "medical_disclaimer": (
            "This result is an experimental "
            "statistical outlier score and is not "
            "a clinically validated fetal anomaly "
            "diagnosis."
        ),
    }


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) < 3:

        print()
        print("Usage:")
        print(
            'python app\\ml\\predict_brain_anomaly.py '
            '"IMAGE_PATH" "BRAIN_PLANE"'
        )

        print()
        print("Supported brain planes:")

        for plane in VALID_PLANES:
            print(f"  - {plane}")

        sys.exit(1)

    image_path = sys.argv[1]

    brain_plane = sys.argv[2]

    print("Device:", DEVICE)
    print("Brain plane:", brain_plane)

    result = predict_brain_anomaly(
        image_path,
        brain_plane,
    )

    print()
    print("=" * 60)
    print("BRAIN OUTLIER ANALYSIS")
    print("=" * 60)

    print(
        "Brain plane     :",
        result["brain_plane"],
    )

    print(
        "Status          :",
        result["status"],
    )

    print(
        "Anomaly score   :",
        result["anomaly_score"],
    )

    print(
        "Threshold       :",
        result["threshold"],
    )

    print(
        "Threshold ratio :",
        result["threshold_ratio"],
    )

    print()
    print(
        "Interpretation:",
        result["interpretation"],
    )

    print()
    print(
        "NOTE:",
        result["medical_disclaimer"],
    )