from pathlib import Path
import gc
import sys

import torch
from PIL import Image
from torch import nn
from torchvision import models, transforms



# =========================================================
# CONFIG
# =========================================================

MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "fetal_plane_efficientnet_b0.pth"
)

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# =========================================================
# LOAD CHECKPOINT
# =========================================================

print("Loading fetal plane classifier...")

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Fetal plane model not found: {MODEL_PATH}"
    )

checkpoint = torch.load(
    MODEL_PATH,
    map_location=DEVICE,
    weights_only=False,
)

CLASS_NAMES = checkpoint["class_names"]

IMAGE_SIZE = checkpoint.get(
    "image_size",
    224,
)

print(f"Device: {DEVICE}")
print(f"Classes: {CLASS_NAMES}")

print(
    f"Best validation accuracy: "
    f"{checkpoint.get('best_val_accuracy', 'N/A')}"
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
    checkpoint["model_state_dict"]
)

model = model.to(DEVICE)

model.eval()


# =========================================================
# RELEASE CHECKPOINT MEMORY
# =========================================================

# The model weights are already loaded into `model`.
# Keeping the complete checkpoint dictionary in memory
# is unnecessary after model initialization.

del checkpoint

gc.collect()



# =========================================================
# IMAGE TRANSFORM
# =========================================================

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


# =========================================================
# PREDICTION
# =========================================================

def predict_plane(image):
    """
    Predict fetal ultrasound plane.

    Supported input:
        1. str path
        2. pathlib.Path
        3. PIL.Image.Image
    """

    # -----------------------------------------------------
    # CASE 1 — FILE PATH
    # -----------------------------------------------------

    if isinstance(
        image,
        (str, Path)
    ):

        image_path = Path(image)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        pil_image = Image.open(
            image_path
        ).convert("RGB")

    # -----------------------------------------------------
    # CASE 2 — PIL IMAGE
    # -----------------------------------------------------

    elif isinstance(
        image,
        Image.Image
    ):

        pil_image = image.convert(
            "RGB"
        )

    # -----------------------------------------------------
    # INVALID INPUT
    # -----------------------------------------------------

    else:

        raise TypeError(
            "image must be a PIL Image "
            "or an image file path"
        )

    # -----------------------------------------------------
    # TRANSFORM
    # -----------------------------------------------------

    image_tensor = transform(
        pil_image
    ).unsqueeze(0)

    image_tensor = image_tensor.to(
        DEVICE
    )

    # -----------------------------------------------------
    # CLOSE IMAGE FILE
    # -----------------------------------------------------

    if isinstance(
        image,
        (str, Path)
    ):
        pil_image.close()

    # -----------------------------------------------------
    # INFERENCE
    # -----------------------------------------------------

    with torch.inference_mode():

        outputs = model(
            image_tensor
        )

        probabilities = torch.softmax(
            outputs,
            dim=1,
        )[0]

        # -------------------------------------------------
        # BEST PREDICTION
        # -------------------------------------------------

        confidence, predicted_index = (
            torch.max(
                probabilities,
                dim=0,
            )
        )

        predicted_class = CLASS_NAMES[
            predicted_index.item()
        ]

        # -------------------------------------------------
        # ALL CLASS PROBABILITIES
        # -------------------------------------------------

        results = []

        for index, class_name in enumerate(
            CLASS_NAMES
        ):

            results.append(
                {
                    "class": class_name,

                    "confidence": float(
                        probabilities[
                            index
                        ].item()
                    ),
                }
            )

    # -----------------------------------------------------
    # SORT RESULTS
    # -----------------------------------------------------

    results.sort(
        key=lambda item:
        item["confidence"],
        reverse=True,
    )

    # -----------------------------------------------------
    # RESPONSE VALUES
    # -----------------------------------------------------

    confidence_value = float(
        confidence.item()
    )

    confidence_percent = round(
        confidence_value * 100,
        2,
    )

    # -----------------------------------------------------
    # MEMORY CLEANUP
    # -----------------------------------------------------

    del outputs
    del probabilities
    del image_tensor
    del confidence
    del predicted_index

    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    return {
        "predicted_class":
            predicted_class,

        "confidence":
            confidence_value,

        "confidence_percent":
            confidence_percent,

        "probabilities":
            results,
    }


# =========================================================
# COMMAND-LINE TEST
# =========================================================

if __name__ == "__main__":

    if len(sys.argv) != 2:

        print()
        print("Usage:")

        print(
            'python app\\ml\\predict_plane.py '
            '"D:\\path\\image.png"'
        )

        sys.exit(1)

    image_path = sys.argv[1]

    result = predict_plane(
        image_path
    )

    print()
    print("=" * 60)
    print("PREDICTION RESULT")
    print("=" * 60)

    print(
        f"Predicted plane : "
        f"{result['predicted_class']}"
    )

    print(
        f"Confidence      : "
        f"{result['confidence_percent']:.2f}%"
    )

    print()
    print("All probabilities:")

    for item in result[
        "probabilities"
    ]:

        print(
            f"{item['class']:20s} "
            f"{item['confidence'] * 100:6.2f}%"
        )