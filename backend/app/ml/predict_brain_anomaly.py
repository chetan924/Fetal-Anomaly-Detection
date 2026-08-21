from pathlib import Path
import gc
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
# ARTIFACT
# ============================================================

print("Loading brain outlier detector artifact...")

if not ARTIFACT_PATH.exists():
    raise FileNotFoundError(
        f"Model artifact not found: {ARTIFACT_PATH}"
    )


with open(
    ARTIFACT_PATH,
    "rb",
) as file:

    artifact = pickle.load(file)


pca = artifact["pca"]

plane_models = artifact["plane_models"]


# Release temporary artifact reference.

del artifact

gc.collect()


# ============================================================
# FEATURE MODEL
# ============================================================

_feature_model = None
_transform = None


def get_feature_model():
    """
    Lazily load EfficientNet-B0 feature extractor.

    The model is loaded only when brain anomaly
    prediction actually requires it.

    This reduces backend startup memory usage.
    """

    global _feature_model
    global _transform

    if _feature_model is not None:
        return (
            _feature_model,
            _transform,
        )

    print(
        "Loading EfficientNet-B0 brain feature extractor..."
    )

    weights = (
        EfficientNet_B0_Weights.DEFAULT
    )

    _transform = weights.transforms()

    model = efficientnet_b0(
        weights=weights
    )

    # Remove classification head.
    model.classifier = torch.nn.Identity()

    model = model.to(
        DEVICE
    )

    model.eval()

    # Disable gradients completely.
    for parameter in model.parameters():
        parameter.requires_grad = False

    _feature_model = model

    print(
        "Brain feature extractor loaded."
    )

    return (
        _feature_model,
        _transform,
    )


# ============================================================
# MAHALANOBIS DISTANCE
# ============================================================

def mahalanobis_score(
    feature,
    mean,
    precision,
):
    """
    Calculate Mahalanobis distance.

    This is a statistical outlier score,
    not a medical diagnosis.
    """

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
        np.sqrt(
            squared_distance
        )[0]
    )


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def extract_feature(
    image: Image.Image,
):
    """
    Extract EfficientNet-B0 feature vector
    from a PIL image.
    """

    feature_model, transform = (
        get_feature_model()
    )

    image = image.convert(
        "RGB"
    )

    tensor = transform(
        image
    )

    tensor = tensor.unsqueeze(
        0
    )

    tensor = tensor.to(
        DEVICE
    )

    with torch.inference_mode():

        feature = feature_model(
            tensor
        )

    # Move result to CPU immediately.
    feature = (
        feature
        .detach()
        .cpu()
        .numpy()
    )

    # Explicitly release inference tensor.
    del tensor

    if DEVICE.type == "cuda":
        torch.cuda.empty_cache()

    gc.collect()

    return feature


# ============================================================
# PREDICTION
# ============================================================

def predict_brain_anomaly(
    image,
    brain_plane,
):
    """
    Perform statistical brain-plane
    outlier analysis.

    Supported input:
        1. image file path
        2. pathlib.Path
        3. PIL.Image.Image

    Supported brain planes:
        - Trans-thalamic
        - Trans-cerebellum
        - Trans-ventricular
    """

    # --------------------------------------------------------
    # Validate brain plane
    # --------------------------------------------------------

    if brain_plane not in VALID_PLANES:

        raise ValueError(
            "Unsupported brain plane. "
            f"Expected one of: {VALID_PLANES}"
        )

    # --------------------------------------------------------
    # Accept image path
    # --------------------------------------------------------

    if isinstance(
        image,
        (str, Path),
    ):

        image_path = Path(
            image
        )

        if not image_path.exists():

            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        pil_image = Image.open(
            image_path
        ).convert(
            "RGB"
        )

    # --------------------------------------------------------
    # Accept PIL image
    # --------------------------------------------------------

    elif isinstance(
        image,
        Image.Image,
    ):

        pil_image = image.convert(
            "RGB"
        )

    # --------------------------------------------------------
    # Invalid input
    # --------------------------------------------------------

    else:

        raise TypeError(
            "image must be a PIL Image "
            "or a file path"
        )

    # --------------------------------------------------------
    # EfficientNet features
    # --------------------------------------------------------

    feature = extract_feature(
        pil_image
    )

    # --------------------------------------------------------
    # PCA
    # --------------------------------------------------------

    reduced_feature = pca.transform(
        feature
    )

    # Release original feature.
    del feature

    # --------------------------------------------------------
    # Plane-specific reference
    # --------------------------------------------------------

    reference = plane_models[
        brain_plane
    ]

    mean = reference[
        "mean"
    ]

    precision = reference[
        "precision"
    ]

    threshold = float(
        reference[
            "threshold"
        ]
    )

    # --------------------------------------------------------
    # Mahalanobis score
    # --------------------------------------------------------

    score = mahalanobis_score(
        reduced_feature,
        mean,
        precision,
    )

    # --------------------------------------------------------
    # Outlier decision
    # --------------------------------------------------------

    is_outlier = (
        score > threshold
    )

    status = (
        "Unusual / Outlier"
        if is_outlier
        else "In-distribution"
    )

    # --------------------------------------------------------
    # Threshold ratio
    # --------------------------------------------------------

    threshold_ratio = (
        score / threshold
        if threshold > 0
        else 0.0
    )

    # --------------------------------------------------------
    # Interpretation
    # --------------------------------------------------------

    if is_outlier:

        interpretation = (
            "The image is a statistical "
            "outlier relative to the "
            "reference dataset."
        )

    else:

        interpretation = (
            "The image is within the "
            "statistical distribution "
            "of the reference dataset."
        )

    # --------------------------------------------------------
    # Cleanup temporary arrays
    # --------------------------------------------------------

    del reduced_feature

    gc.collect()

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {
        "brain_plane":
            brain_plane,

        "status":
            status,

        "is_outlier":
            bool(
                is_outlier
            ),

        "anomaly_score":
            round(
                score,
                4,
            ),

        "threshold":
            round(
                threshold,
                4,
            ),

        "threshold_ratio":
            round(
                threshold_ratio,
                4,
            ),

        "interpretation":
            interpretation,

        "medical_disclaimer":
            (
                "This result is an experimental "
                "statistical outlier score and is "
                "not a clinically validated fetal "
                "anomaly diagnosis."
            ),
    }


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) < 3:

        print()

        print(
            "Usage:"
        )

        print(
            'python app\\ml\\predict_brain_anomaly.py '
            '"IMAGE_PATH" "BRAIN_PLANE"'
        )

        print()

        print(
            "Supported brain planes:"
        )

        for plane in VALID_PLANES:

            print(
                f"  - {plane}"
            )

        sys.exit(1)

    image_path = sys.argv[1]

    brain_plane = sys.argv[2]

    print(
        "Device:",
        DEVICE,
    )

    print(
        "Brain plane:",
        brain_plane,
    )

    result = predict_brain_anomaly(
        image_path,
        brain_plane,
    )

    print()

    print(
        "=" * 60
    )

    print(
        "BRAIN OUTLIER ANALYSIS"
    )

    print(
        "=" * 60
    )

    print(
        "Brain plane     :",
        result[
            "brain_plane"
        ],
    )

    print(
        "Status          :",
        result[
            "status"
        ],
    )

    print(
        "Anomaly score   :",
        result[
            "anomaly_score"
        ],
    )

    print(
        "Threshold       :",
        result[
            "threshold"
        ],
    )

    print(
        "Threshold ratio :",
        result[
            "threshold_ratio"
        ],
    )

    print()

    print(
        "Interpretation:",
        result[
            "interpretation"
        ],
    )

    print()

    print(
        "NOTE:",
        result[
            "medical_disclaimer"
        ],
    )