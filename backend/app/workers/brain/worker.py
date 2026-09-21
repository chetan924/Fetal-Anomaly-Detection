from io import BytesIO
from pathlib import Path
import gc
import pickle

import numpy as np
import torch

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image
from torchvision import transforms
from torchvision.models import (
    EfficientNet_B0_Weights,
    efficientnet_b0,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
    / "ml"
)

BRAIN_PLANE_MODEL_PATH = (
    BASE_DIR
    / "models"
    / "brain_plane_efficientnet_b0.pth"
)

BRAIN_ANOMALY_ARTIFACT_PATH = (
    BASE_DIR
    / "models"
    / "brain_anomaly_detector.pkl"
)

WORKER_NAME = "brain"

BRAIN_PLANE_MODEL_NAME = (
    "brain_plane_efficientnet_b0"
)

BRAIN_ANOMALY_MODEL_NAME = (
    "brain_anomaly_detector"
)


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="FetalAI Brain Worker",
    version="1.0.0",
    description=(
        "Dedicated brain-plane classifier and "
        "statistical brain outlier worker."
    ),
)


# ============================================================
# GLOBAL MODELS / ARTIFACTS
# ============================================================

brain_plane_model = None
brain_plane_transform = None
brain_plane_classes = None
brain_plane_image_size = 224
brain_plane_validation_accuracy = "Unknown"

brain_anomaly_feature_model = None
brain_anomaly_transform = None

brain_anomaly_pca = None
brain_anomaly_plane_models = None


VALID_PLANES = [
    "Trans-thalamic",
    "Trans-cerebellum",
    "Trans-ventricular",
]


# ============================================================
# LOAD BRAIN PLANE MODEL
# ============================================================

def load_brain_plane_model():

    global brain_plane_model
    global brain_plane_transform
    global brain_plane_classes
    global brain_plane_image_size
    global brain_plane_validation_accuracy

    print()
    print("=" * 70)
    print("LOADING BRAIN PLANE CLASSIFIER")
    print("=" * 70)

    print(
        "Model:",
        BRAIN_PLANE_MODEL_PATH,
    )

    if not BRAIN_PLANE_MODEL_PATH.exists():

        raise FileNotFoundError(
            "Brain plane model not found: "
            f"{BRAIN_PLANE_MODEL_PATH}"
        )

    checkpoint = torch.load(
        BRAIN_PLANE_MODEL_PATH,
        map_location=DEVICE,
        weights_only=False,
    )

    classes = checkpoint.get(
        "classes"
    )

    if not classes:

        raise RuntimeError(
            "Brain plane checkpoint does not "
            "contain 'classes'."
        )

    image_size = checkpoint.get(
        "image_size",
        224,
    )

    validation_accuracy = checkpoint.get(
        "best_validation_accuracy",
        checkpoint.get(
            "best_val_accuracy",
            "Unknown",
        ),
    )

    model = efficientnet_b0(
        weights=None
    )

    input_features = (
        model.classifier[1].in_features
    )

    model.classifier[1] = torch.nn.Linear(
        input_features,
        len(classes),
    )

    if (
        "model_state_dict"
        not in checkpoint
    ):

        raise RuntimeError(
            "Brain plane checkpoint does not "
            "contain 'model_state_dict'."
        )

    model.load_state_dict(
        checkpoint[
            "model_state_dict"
        ]
    )

    model = model.to(
        DEVICE
    )

    model.eval()

    transform = transforms.Compose(
        [
            transforms.Resize(
                (
                    image_size,
                    image_size,
                )
            ),

            transforms.ToTensor(),

            transforms.Normalize(
                mean=[
                    0.485,
                    0.456,
                    0.406,
                ],

                std=[
                    0.229,
                    0.224,
                    0.225,
                ],
            ),
        ]
    )

    brain_plane_model = model
    brain_plane_transform = transform
    brain_plane_classes = classes
    brain_plane_image_size = image_size
    brain_plane_validation_accuracy = (
        validation_accuracy
    )

    del checkpoint

    gc.collect()

    print(
        "Device:",
        DEVICE,
    )

    print(
        "Classes:",
        brain_plane_classes,
    )

    print(
        "Image size:",
        brain_plane_image_size,
    )

    print(
        "Best validation accuracy:",
        brain_plane_validation_accuracy,
    )

    print(
        "Brain plane classifier loaded."
    )


# ============================================================
# LOAD BRAIN ANOMALY ARTIFACT
# ============================================================

def load_brain_anomaly_artifact():

    global brain_anomaly_pca
    global brain_anomaly_plane_models

    print()
    print("=" * 70)
    print("LOADING BRAIN ANOMALY ARTIFACT")
    print("=" * 70)

    print(
        "Artifact:",
        BRAIN_ANOMALY_ARTIFACT_PATH,
    )

    if not BRAIN_ANOMALY_ARTIFACT_PATH.exists():

        raise FileNotFoundError(
            "Brain anomaly artifact not found: "
            f"{BRAIN_ANOMALY_ARTIFACT_PATH}"
        )

    with open(
        BRAIN_ANOMALY_ARTIFACT_PATH,
        "rb",
    ) as file:

        artifact = pickle.load(
            file
        )

    if "pca" not in artifact:

        raise RuntimeError(
            "Brain anomaly artifact does not "
            "contain 'pca'."
        )

    if "plane_models" not in artifact:

        raise RuntimeError(
            "Brain anomaly artifact does not "
            "contain 'plane_models'."
        )

    brain_anomaly_pca = artifact[
        "pca"
    ]

    brain_anomaly_plane_models = (
        artifact["plane_models"]
    )

    del artifact

    gc.collect()

    print(
        "Brain anomaly artifact loaded."
    )

    print(
        "Valid planes:",
        VALID_PLANES,
    )


# ============================================================
# LOAD ANOMALY FEATURE EXTRACTOR
# ============================================================

def load_brain_anomaly_feature_model():

    global brain_anomaly_feature_model
    global brain_anomaly_transform

    print()
    print("=" * 70)
    print("LOADING BRAIN FEATURE EXTRACTOR")
    print("=" * 70)

    weights = (
        EfficientNet_B0_Weights.DEFAULT
    )

    transform = weights.transforms()

    model = efficientnet_b0(
        weights=weights
    )

    # Remove classification head.
    model.classifier = (
        torch.nn.Identity()
    )

    model = model.to(
        DEVICE
    )

    model.eval()

    # Inference only.
    for parameter in model.parameters():

        parameter.requires_grad = False

    brain_anomaly_feature_model = (
        model
    )

    brain_anomaly_transform = (
        transform
    )

    print(
        "Brain feature extractor loaded."
    )


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup_brain_worker():

    print()
    print("=" * 70)
    print("STARTING BRAIN WORKER")
    print("=" * 70)

    load_brain_plane_model()

    load_brain_anomaly_artifact()

    load_brain_anomaly_feature_model()

    print()
    print(
        "Brain worker initialization complete."
    )

    print(
        "Worker:",
        WORKER_NAME,
    )

    print("=" * 70)


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "worker": WORKER_NAME,

        "brain_plane_model": {
            "name": BRAIN_PLANE_MODEL_NAME,
            "loaded": (
                brain_plane_model
                is not None
            ),
        },

        "brain_anomaly_model": {
            "name": BRAIN_ANOMALY_MODEL_NAME,
            "artifact_loaded": (
                brain_anomaly_pca
                is not None
                and brain_anomaly_plane_models
                is not None
            ),
            "feature_extractor_loaded": (
                brain_anomaly_feature_model
                is not None
            ),
        },

        "device": str(
            DEVICE
        ),
    }


# ============================================================
# IMAGE READER
# ============================================================

def bytes_to_image(
    raw: bytes,
) -> Image.Image:

    if not raw:

        raise ValueError(
            "Image data is empty."
        )

    return Image.open(
        BytesIO(raw)
    ).convert("RGB")


# ============================================================
# BRAIN PLANE PREDICTION
# ============================================================

def predict_brain_plane_image(
    image: Image.Image,
) -> dict:

    if brain_plane_model is None:

        raise RuntimeError(
            "Brain plane model is not loaded."
        )

    image = image.convert(
        "RGB"
    )

    tensor = brain_plane_transform(
        image
    )

    tensor = tensor.unsqueeze(
        0
    )

    tensor = tensor.to(
        DEVICE
    )

    with torch.inference_mode():

        logits = brain_plane_model(
            tensor
        )

        probabilities = torch.softmax(
            logits,
            dim=1,
        )[0]

    predicted_index = int(
        torch.argmax(
            probabilities
        ).item()
    )

    predicted_class = (
        brain_plane_classes[
            predicted_index
        ]
    )

    confidence = float(
        probabilities[
            predicted_index
        ].item()
    )

    probability_results = []

    for index, class_name in enumerate(
        brain_plane_classes
    ):

        value = float(
            probabilities[
                index
            ].item()
        )

        probability_results.append(
            {
                "class": class_name,
                "confidence": value,
                "confidence_percent": round(
                    value * 100,
                    2,
                ),
            }
        )

    probability_results.sort(
        key=lambda item:
        item["confidence"],
        reverse=True,
    )

    del tensor
    del logits
    del probabilities

    if DEVICE.type == "cuda":

        torch.cuda.empty_cache()

    return {
        "predicted_class":
            predicted_class,

        "confidence":
            confidence,

        "confidence_percent":
            round(
                confidence * 100,
                2,
            ),

        "probabilities":
            probability_results,
    }


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def extract_anomaly_feature(
    image: Image.Image,
):

    if (
        brain_anomaly_feature_model
        is None
    ):

        raise RuntimeError(
            "Brain anomaly feature extractor "
            "is not loaded."
        )

    image = image.convert(
        "RGB"
    )

    tensor = (
        brain_anomaly_transform(
            image
        )
    )

    tensor = tensor.unsqueeze(
        0
    )

    tensor = tensor.to(
        DEVICE
    )

    with torch.inference_mode():

        feature = (
            brain_anomaly_feature_model(
                tensor
            )
        )

    feature = (
        feature
        .detach()
        .cpu()
        .numpy()
    )

    del tensor

    if DEVICE.type == "cuda":

        torch.cuda.empty_cache()

    gc.collect()

    return feature


# ============================================================
# MAHALANOBIS SCORE
# ============================================================

def mahalanobis_score(
    feature,
    mean,
    precision,
):

    diff = (
        feature
        - mean
    )

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
# BRAIN ANOMALY PREDICTION
# ============================================================

def predict_brain_anomaly_image(
    image: Image.Image,
    brain_plane: str,
) -> dict:

    if brain_plane not in VALID_PLANES:

        raise ValueError(
            "Unsupported brain plane. "
            f"Expected one of: {VALID_PLANES}"
        )

    if brain_anomaly_pca is None:

        raise RuntimeError(
            "Brain anomaly PCA is not loaded."
        )

    if (
        brain_anomaly_plane_models
        is None
    ):

        raise RuntimeError(
            "Brain anomaly plane models "
            "are not loaded."
        )

    feature = extract_anomaly_feature(
        image
    )

    reduced_feature = (
        brain_anomaly_pca.transform(
            feature
        )
    )

    del feature

    reference = (
        brain_anomaly_plane_models[
            brain_plane
        ]
    )

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

    score = mahalanobis_score(
        reduced_feature,
        mean,
        precision,
    )

    is_outlier = (
        score > threshold
    )

    result_status = (
        "Unusual / Outlier"
        if is_outlier
        else "In-distribution"
    )

    threshold_ratio = (
        score / threshold
        if threshold > 0
        else 0.0
    )

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

    del reduced_feature

    gc.collect()

    return {
        "brain_plane":
            brain_plane,

        "status":
            result_status,

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

        "medical_disclaimer": (
            "This result is an experimental "
            "statistical outlier score and is "
            "not a clinically validated fetal "
            "anomaly diagnosis."
        ),
    }


# ============================================================
# COMBINED BRAIN INFERENCE
# ============================================================

def run_brain_analysis(
    image: Image.Image,
) -> dict:

    brain_plane_result = (
        predict_brain_plane_image(
            image
        )
    )

    predicted_plane = (
        brain_plane_result[
            "predicted_class"
        ]
    )

    anomaly_result = None

    anomaly_error = None

    if predicted_plane in VALID_PLANES:

        try:

            anomaly_result = (
                predict_brain_anomaly_image(
                    image,
                    predicted_plane,
                )
            )

        except Exception as exc:

            anomaly_error = str(
                exc
            )

    else:

        anomaly_error = (
            "Predicted brain plane is not "
            "supported by the anomaly detector."
        )

    return {
        "brain_plane": (
            brain_plane_result
        ),

        "brain_anomaly": (
            anomaly_result
        ),

        "anomaly_error": (
            anomaly_error
        ),

        "worker": WORKER_NAME,

        "model": {
            "brain_plane":
                BRAIN_PLANE_MODEL_NAME,

            "brain_anomaly":
                BRAIN_ANOMALY_MODEL_NAME,
        },
    }


# ============================================================
# PREDICT ENDPOINT
# ============================================================

@app.post("/predict")
async def predict(
    file: UploadFile = File(...),
):

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    content_type = (
        file.content_type or ""
    ).split(";")[0].strip().lower()

    if not content_type.startswith(
        "image/"
    ):

        raise HTTPException(
            status_code=400,
            detail="Only image files are supported.",
        )

    try:

        raw = await file.read()

        image = bytes_to_image(
            raw
        )

        result = run_brain_analysis(
            image
        )

        return {
            "status": "success",

            "worker": WORKER_NAME,

            "image": {
                "filename": file.filename,
                "width": image.width,
                "height": image.height,
            },

            **result,
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Brain inference failed: {exc}"
            ),
        ) from exc