from pathlib import Path
import sys

import numpy as np
import torch
import torch.nn.functional as F

from PIL import Image

from torch import nn
from torchvision import models, transforms


# =========================================================
# CONFIG
# =========================================================

BACKEND_ROOT = (
    Path(__file__).resolve().parents[2]
)

MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "fetal_plane_efficientnet_b0.pth"
)

EXPLAINABILITY_DIR = (
    BACKEND_ROOT
    / "storage"
    / "explainability"
)

EXPLAINABILITY_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


# =========================================================
# LOAD CHECKPOINT
# =========================================================

print(
    "Loading fetal plane model for Grad-CAM..."
)

if not MODEL_PATH.exists():

    raise FileNotFoundError(
        f"Fetal plane model not found: "
        f"{MODEL_PATH}"
    )


checkpoint = torch.load(
    MODEL_PATH,
    map_location=DEVICE,
    weights_only=False,
)


CLASS_NAMES = checkpoint[
    "class_names"
]

IMAGE_SIZE = checkpoint.get(
    "image_size",
    224,
)


print(
    f"Grad-CAM device: {DEVICE}"
)

print(
    f"Grad-CAM classes: {CLASS_NAMES}"
)


# =========================================================
# MODEL
# =========================================================

model = models.efficientnet_b0(
    weights=None
)

input_features = (
    model.classifier[1].in_features
)

model.classifier[1] = nn.Linear(
    input_features,
    len(CLASS_NAMES),
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


# =========================================================
# TARGET LAYER
# =========================================================

TARGET_LAYER = (
    model.features[-1]
)


# =========================================================
# IMAGE TRANSFORM
# =========================================================

transform = transforms.Compose(
    [
        transforms.Resize(
            (
                IMAGE_SIZE,
                IMAGE_SIZE,
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


# =========================================================
# GRAD-CAM STATE
# =========================================================

_activation = None
_gradient = None


# =========================================================
# FORWARD HOOK
# =========================================================

def _forward_hook(
    module,
    inputs,
    output,
):

    global _activation

    _activation = output


# =========================================================
# BACKWARD HOOK
# =========================================================

def _backward_hook(
    module,
    grad_input,
    grad_output,
):

    global _gradient

    _gradient = grad_output[0]


# =========================================================
# REGISTER HOOKS
# =========================================================

_forward_handle = (
    TARGET_LAYER.register_forward_hook(
        _forward_hook
    )
)

_backward_handle = (
    TARGET_LAYER.register_full_backward_hook(
        _backward_hook
    )
)


# =========================================================
# IMAGE LOADER
# =========================================================

def _load_image(image):

    if isinstance(
        image,
        (str, Path),
    ):

        image_path = Path(
            image
        )

        if not image_path.exists():

            raise FileNotFoundError(
                f"Image not found: "
                f"{image_path}"
            )

        pil_image = Image.open(
            image_path
        ).convert(
            "RGB"
        )

    elif isinstance(
        image,
        Image.Image,
    ):

        pil_image = image.convert(
            "RGB"
        )

    else:

        raise TypeError(
            "image must be a PIL Image "
            "or an image file path"
        )

    return pil_image


# =========================================================
# NORMALIZE HEATMAP
# =========================================================

def _normalize_heatmap(cam):

    cam_min = cam.min()
    cam_max = cam.max()

    if (
        cam_max - cam_min
    ) > 1e-8:

        cam = (
            cam - cam_min
        ) / (
            cam_max - cam_min
        )

    else:

        cam = torch.zeros_like(
            cam
        )

    return cam


# =========================================================
# ATTENTION CONCENTRATION
# =========================================================

def _calculate_attention_concentration(
    heatmap,
):
    """
    Calculate normalized spatial entropy and
    concentration from a Grad-CAM heatmap.

    IMPORTANT:

    This is an explainability metric only.

    It does NOT indicate:

        - anatomical correctness
        - clinical reliability
        - diagnostic accuracy
        - disease severity
        - medical diagnosis

    Higher concentration means that the
    Grad-CAM activation is more spatially
    concentrated.

    Lower concentration means that the
    activation is more spatially distributed.
    """

    # -----------------------------------------------------
    # Convert to numpy
    # -----------------------------------------------------

    cam = np.asarray(
        heatmap,
        dtype=np.float32,
    )

    # -----------------------------------------------------
    # Remove invalid values
    # -----------------------------------------------------

    cam = np.nan_to_num(
        cam,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    # -----------------------------------------------------
    # Keep activation non-negative
    # -----------------------------------------------------

    cam = np.maximum(
        cam,
        0.0,
    )

    # -----------------------------------------------------
    # Flatten
    # -----------------------------------------------------

    values = cam.reshape(
        -1
    )

    # -----------------------------------------------------
    # Total activation
    # -----------------------------------------------------

    total_activation = float(
        values.sum()
    )

    # -----------------------------------------------------
    # Empty / degenerate heatmap
    # -----------------------------------------------------

    if total_activation <= 1e-8:

        return {
            "score": 0.0,
            "entropy": 1.0,
            "interpretation": (
                "No meaningful "
                "activation concentration"
            ),
            "status": "insufficient_activation",
        }

    # -----------------------------------------------------
    # Convert activation to probability distribution
    # -----------------------------------------------------

    probabilities = (
        values
        / total_activation
    )

    probabilities = np.clip(
        probabilities,
        1e-12,
        None,
    )

    # -----------------------------------------------------
    # Spatial entropy
    # -----------------------------------------------------

    entropy = float(
        -np.sum(
            probabilities
            * np.log(
                probabilities
            )
        )
    )

    # -----------------------------------------------------
    # Maximum possible entropy
    # -----------------------------------------------------

    max_entropy = float(
        np.log(
            len(probabilities)
        )
    )

    if max_entropy <= 1e-8:

        normalized_entropy = 1.0

    else:

        normalized_entropy = (
            entropy
            / max_entropy
        )

    normalized_entropy = float(
        np.clip(
            normalized_entropy,
            0.0,
            1.0,
        )
    )

    # -----------------------------------------------------
    # Concentration score
    # -----------------------------------------------------

    concentration_score = (
        1.0
        - normalized_entropy
    )

    concentration_score = float(
        np.clip(
            concentration_score,
            0.0,
            1.0,
        )
    )

    # -----------------------------------------------------
    # Interpretation
    # -----------------------------------------------------

    if concentration_score >= 0.50:

        interpretation = (
            "Relatively concentrated "
            "model attention"
        )

        status = "relatively_concentrated"

    elif concentration_score >= 0.20:

        interpretation = (
            "Moderately distributed "
            "model attention"
        )

        status = "moderately_distributed"

    else:

        interpretation = (
            "Broadly distributed "
            "model attention"
        )

        status = "broadly_distributed"

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {

        "score":
            round(
                concentration_score,
                4,
            ),

        "entropy":
            round(
                normalized_entropy,
                4,
            ),

        "interpretation":
            interpretation,

        "status":
            status,
    }


# =========================================================
# HEATMAP → IMAGE
# =========================================================

def _heatmap_to_image(
    heatmap,
):

    heatmap_uint8 = (
        np.clip(
            heatmap,
            0.0,
            1.0,
        )
        * 255
    ).astype(
        np.uint8
    )

    grayscale = Image.fromarray(
        heatmap_uint8,
        mode="L",
    )

    return grayscale.convert(
        "RGB"
    )


# =========================================================
# CREATE OVERLAY
# =========================================================

def _create_overlay(
    original_image,
    heatmap,
    alpha=0.45,
):

    original = (
        original_image.convert(
            "RGB"
        )
    )

    original = original.resize(
        (
            IMAGE_SIZE,
            IMAGE_SIZE,
        )
    )

    heatmap_image = (
        _heatmap_to_image(
            heatmap
        )
    )

    overlay = Image.blend(
        original,
        heatmap_image,
        alpha=float(alpha),
    )

    return overlay


# =========================================================
# GENERATE GRAD-CAM
# =========================================================

def generate_gradcam(
    image,
    target_class_index=None,
    output_prefix=None,
):
    """
    Generate Grad-CAM and explainability metrics.

    Returns:

        - target class
        - confidence
        - heatmap
        - heatmap path
        - overlay path
        - attention concentration

    Attention concentration is an explainability
    metric only. It is NOT clinical reliability.
    """

    global _activation
    global _gradient

    # -----------------------------------------------------
    # Reset hook state
    # -----------------------------------------------------

    _activation = None
    _gradient = None

    # -----------------------------------------------------
    # Load image
    # -----------------------------------------------------

    pil_image = _load_image(
        image
    )

    # -----------------------------------------------------
    # Transform
    # -----------------------------------------------------

    image_tensor = transform(
        pil_image
    ).unsqueeze(
        0
    )

    image_tensor = image_tensor.to(
        DEVICE
    )

    # -----------------------------------------------------
    # Reset gradients
    # -----------------------------------------------------

    model.zero_grad(
        set_to_none=True
    )

    # -----------------------------------------------------
    # Forward
    # -----------------------------------------------------

    outputs = model(
        image_tensor
    )

    probabilities = torch.softmax(
        outputs,
        dim=1,
    )

    # -----------------------------------------------------
    # Target class
    # -----------------------------------------------------

    if target_class_index is None:

        target_class_index = int(
            torch.argmax(
                probabilities,
                dim=1,
            ).item()
        )

    target_score = outputs[
        0,
        target_class_index,
    ]

    # -----------------------------------------------------
    # Backward
    # -----------------------------------------------------

    target_score.backward()

    # -----------------------------------------------------
    # Validate hooks
    # -----------------------------------------------------

    if _activation is None:

        raise RuntimeError(
            "Grad-CAM activation "
            "was not captured."
        )

    if _gradient is None:

        raise RuntimeError(
            "Grad-CAM gradient "
            "was not captured."
        )

    # -----------------------------------------------------
    # Activation
    # -----------------------------------------------------

    activation = _activation

    # -----------------------------------------------------
    # Gradient
    # -----------------------------------------------------

    gradient = _gradient

    # -----------------------------------------------------
    # Global average pooling
    # -----------------------------------------------------

    weights = gradient.mean(
        dim=(2, 3),
        keepdim=True,
    )

    # -----------------------------------------------------
    # Weighted activation
    # -----------------------------------------------------

    cam = (
        weights * activation
    ).sum(
        dim=1,
        keepdim=True,
    )

    # -----------------------------------------------------
    # ReLU
    # -----------------------------------------------------

    cam = F.relu(
        cam
    )

    # -----------------------------------------------------
    # Resize
    # -----------------------------------------------------

    cam = F.interpolate(
        cam,
        size=(
            IMAGE_SIZE,
            IMAGE_SIZE,
        ),
        mode="bilinear",
        align_corners=False,
    )

    # -----------------------------------------------------
    # Remove batch/channel
    # -----------------------------------------------------

    cam = cam[
        0,
        0,
    ]

    # -----------------------------------------------------
    # Normalize
    # -----------------------------------------------------

    cam = _normalize_heatmap(
        cam
    )

    # -----------------------------------------------------
    # Convert to numpy
    # -----------------------------------------------------

    heatmap = (
        cam
        .detach()
        .cpu()
        .numpy()
    )

    # =====================================================
    # ATTENTION CONCENTRATION
    # =====================================================

    attention_concentration = (
        _calculate_attention_concentration(
            heatmap
        )
    )

    # =====================================================
    # OUTPUT PREFIX
    # =====================================================

    if output_prefix:

        safe_prefix = (
            str(output_prefix)
            .strip()
            .replace(
                " ",
                "_",
            )
        )

    else:

        safe_prefix = (
            "gradcam"
        )

    # =====================================================
    # OUTPUT PATHS
    # =====================================================

    heatmap_filename = (
        f"{safe_prefix}_heatmap.png"
    )

    overlay_filename = (
        f"{safe_prefix}_overlay.png"
    )

    heatmap_path = (
        EXPLAINABILITY_DIR
        / heatmap_filename
    )

    overlay_path = (
        EXPLAINABILITY_DIR
        / overlay_filename
    )

    # =====================================================
    # SAVE HEATMAP
    # =====================================================

    heatmap_image = (
        _heatmap_to_image(
            heatmap
        )
    )

    heatmap_image.save(
        heatmap_path
    )

    # =====================================================
    # SAVE OVERLAY
    # =====================================================

    overlay_image = (
        _create_overlay(
            pil_image,
            heatmap,
            alpha=0.45,
        )
    )

    overlay_image.save(
        overlay_path
    )

    # =====================================================
    # CONFIDENCE
    # =====================================================

    confidence = float(
        probabilities[
            0,
            target_class_index,
        ]
        .detach()
        .cpu()
        .item()
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    return {

        "target_class":
            CLASS_NAMES[
                target_class_index
            ],

        "target_class_index":
            target_class_index,

        "confidence":
            confidence,

        "confidence_percent":
            round(
                confidence * 100,
                2,
            ),

        "attention_concentration":
            attention_concentration,

        "heatmap":
            heatmap,

        "heatmap_path":
            str(
                heatmap_path
            ),

        "overlay_path":
            str(
                overlay_path
            ),
    }


# =========================================================
# REMOVE HOOKS
# =========================================================

def remove_hooks():

    global _forward_handle
    global _backward_handle

    if (
        _forward_handle
        is not None
    ):

        _forward_handle.remove()

        _forward_handle = None

    if (
        _backward_handle
        is not None
    ):

        _backward_handle.remove()

        _backward_handle = None


# =========================================================
# COMMAND LINE TEST
# =========================================================

if __name__ == "__main__":

    if len(sys.argv) != 2:

        print()

        print(
            "Usage:"
        )

        print(
            'python -m app.ml.gradcam '
            '"D:\\path\\image.png"'
        )

        sys.exit(1)

    image_path = sys.argv[1]

    try:

        result = generate_gradcam(
            image_path,
            output_prefix="test_gradcam",
        )

        print()
        print("=" * 60)
        print(
            "GRAD-CAM RESULT"
        )
        print("=" * 60)

        print(
            f"Target class : "
            f"{result['target_class']}"
        )

        print(
            f"Confidence   : "
            f"{result['confidence_percent']:.2f}%"
        )

        attention = (
            result[
                "attention_concentration"
            ]
        )

        print()
        print(
            "ATTENTION CONCENTRATION"
        )

        print(
            f"Score        : "
            f"{attention['score']:.4f}"
        )

        print(
            f"Interpretation : "
            f"{attention['interpretation']}"
        )

        print(
            f"Status       : "
            f"{attention['status']}"
        )

        print(
            f"Entropy      : "
            f"{attention['entropy']:.4f}"
        )

        print()

        print(
            f"Heatmap      : "
            f"{result['heatmap_path']}"
        )

        print(
            f"Overlay      : "
            f"{result['overlay_path']}"
        )

        print()

        print(
            "Grad-CAM heatmap generated successfully."
        )

        print(
            "Attention concentration is an "
            "explainability metric only."
        )

        print(
            "It is not a clinical reliability "
            "score or medical diagnosis."
        )

    except Exception as exc:

        print()

        print(
            "Grad-CAM generation failed:"
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        sys.exit(1)

    finally:

        remove_hooks()