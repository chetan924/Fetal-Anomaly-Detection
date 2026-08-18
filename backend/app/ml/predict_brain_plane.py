from pathlib import Path
import sys

import torch
from PIL import Image
from torchvision import transforms
from torchvision.models import efficientnet_b0


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = (
    BASE_DIR
    / "models"
    / "brain_plane_efficientnet_b0.pth"
)

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# ============================================================
# LOAD CHECKPOINT
# ============================================================

print("Loading brain plane classifier...")

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Brain plane model not found: {MODEL_PATH}"
    )

checkpoint = torch.load(
    MODEL_PATH,
    map_location=DEVICE,
    weights_only=False,
)

CLASSES = checkpoint["classes"]

IMAGE_SIZE = checkpoint.get(
    "image_size",
    224,
)

print("Device:", DEVICE)
print("Classes:", CLASSES)

print(
    "Best validation accuracy:",
    checkpoint.get(
        "best_validation_accuracy",
        "Unknown",
    ),
)


# ============================================================
# TRANSFORM
# ============================================================

transform = transforms.Compose(
    [
        transforms.Resize(
            (IMAGE_SIZE, IMAGE_SIZE)
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


# ============================================================
# MODEL
# ============================================================

model = efficientnet_b0(
    weights=None
)

input_features = (
    model.classifier[1].in_features
)

model.classifier[1] = torch.nn.Linear(
    input_features,
    len(CLASSES),
)

model.load_state_dict(
    checkpoint["model_state_dict"]
)

model = model.to(DEVICE)

model.eval()


# ============================================================
# PREDICTION
# ============================================================

def predict_brain_plane(image):

    # --------------------------------------------------------
    # Accept image path or PIL Image
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
            "or image file path"
        )

    # --------------------------------------------------------
    # Transform
    # --------------------------------------------------------

    tensor = transform(
        image
    ).unsqueeze(0)

    tensor = tensor.to(
        DEVICE
    )

    # --------------------------------------------------------
    # Inference
    # --------------------------------------------------------

    with torch.inference_mode():

        logits = model(
            tensor
        )

        probabilities = torch.softmax(
            logits,
            dim=1,
        )[0]

    # --------------------------------------------------------
    # Prediction
    # --------------------------------------------------------

    predicted_index = int(
        torch.argmax(
            probabilities
        ).item()
    )

    predicted_class = CLASSES[
        predicted_index
    ]

    confidence = float(
        probabilities[
            predicted_index
        ].item()
    )

    # --------------------------------------------------------
    # All probabilities
    # --------------------------------------------------------

    probability_results = []

    for index, class_name in enumerate(
        CLASSES
    ):

        probability_results.append(
            {
                "class": class_name,
                "confidence": float(
                    probabilities[
                        index
                    ].item()
                ),
            }
        )

    probability_results.sort(
        key=lambda item: item["confidence"],
        reverse=True,
    )

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

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
# CLI TEST
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) < 2:

        print()
        print("Usage:")

        print(
            'python app\\ml\\predict_brain_plane.py '
            '"IMAGE_PATH"'
        )

        sys.exit(1)

    image_path = sys.argv[1]

    result = predict_brain_plane(
        image_path
    )

    print()
    print("=" * 60)
    print("BRAIN PLANE PREDICTION")
    print("=" * 60)

    print(
        "Predicted plane :",
        result["predicted_class"],
    )

    print(
        "Confidence      :",
        f'{result["confidence_percent"]:.2f}%',
    )

    print()
    print("All probabilities:")

    for item in result[
        "probabilities"
    ]:

        print(
            f'{item["class"]:22s} '
            f'{item["confidence"] * 100:7.2f}%'
        )