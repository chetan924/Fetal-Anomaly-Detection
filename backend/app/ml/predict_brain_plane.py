from pathlib import Path
import gc
import sys

import torch
from PIL import Image
from torchvision import transforms
from torchvision.models import efficientnet_b0



# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = (
    BASE_DIR
    / "models"
    / "brain_plane_efficientnet_b0.pth"
)

DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


# ============================================================
# LOAD MODEL CHECKPOINT
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


# ============================================================
# CHECKPOINT CONFIGURATION
# ============================================================

CLASSES = checkpoint.get("classes")

if not CLASSES:
    raise RuntimeError(
        "Model checkpoint does not contain "
        "'classes'."
    )


IMAGE_SIZE = checkpoint.get(
    "image_size",
    224,
)


BEST_VALIDATION_ACCURACY = checkpoint.get(
    "best_validation_accuracy",
    checkpoint.get(
        "best_val_accuracy",
        "Unknown",
    ),
)


print(
    "Device:",
    DEVICE,
)

print(
    "Classes:",
    CLASSES,
)

print(
    "Best validation accuracy:",
    BEST_VALIDATION_ACCURACY,
)


# ============================================================
# IMAGE TRANSFORMATION
# ============================================================

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


# ============================================================
# MODEL ARCHITECTURE
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


# ============================================================
# LOAD TRAINED WEIGHTS
# ============================================================

if "model_state_dict" not in checkpoint:
    raise RuntimeError(
        "Model checkpoint does not contain "
        "'model_state_dict'."
    )


model.load_state_dict(
    checkpoint["model_state_dict"]
)


model = model.to(
    DEVICE
)


model.eval()


# ============================================================
# RELEASE CHECKPOINT MEMORY
# ============================================================

del checkpoint

gc.collect()



# ============================================================
# PREDICTION FUNCTION
# ============================================================

def predict_brain_plane(image):
    """
    Predict fetal brain ultrasound plane.

    Supported input:
        1. Image file path
        2. pathlib.Path
        3. PIL.Image.Image

    Returns:
        dict containing:
            predicted_class
            confidence
            confidence_percent
            probabilities
    """

    # --------------------------------------------------------
    # HANDLE FILE PATH
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

        if not image_path.is_file():
            raise ValueError(
                f"Image path is not a file: "
                f"{image_path}"
            )

        pil_image = Image.open(
            image_path
        ).convert("RGB")


    # --------------------------------------------------------
    # HANDLE PIL IMAGE
    # --------------------------------------------------------

    elif isinstance(
        image,
        Image.Image,
    ):

        pil_image = image.convert(
            "RGB"
        )


    # --------------------------------------------------------
    # INVALID INPUT
    # --------------------------------------------------------

    else:

        raise TypeError(
            "image must be a PIL Image "
            "or an image file path."
        )


    # --------------------------------------------------------
    # IMAGE TRANSFORMATION
    # --------------------------------------------------------

    tensor = transform(
        pil_image
    )


    tensor = tensor.unsqueeze(
        0
    )


    tensor = tensor.to(
        DEVICE
    )


    # --------------------------------------------------------
    # MODEL INFERENCE
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
    # BEST PREDICTION
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
    # ALL CLASS PROBABILITIES
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

                "confidence_percent": round(
                    float(
                        probabilities[
                            index
                        ].item()
                    ) * 100,
                    2,
                ),
            }
        )


    # --------------------------------------------------------
    # SORT BY CONFIDENCE
    # --------------------------------------------------------

    probability_results.sort(
        key=lambda item:
        item["confidence"],

        reverse=True,
    )


    # --------------------------------------------------------
    # FINAL RESPONSE
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
# COMMAND LINE TEST
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) != 2:

        print()
        print(
            "Usage:"
        )

        print()

        print(
            'python app\\ml\\predict_brain_plane.py '
            '"IMAGE_PATH"'
        )

        print()

        sys.exit(1)


    image_path = sys.argv[1]


    try:

        result = predict_brain_plane(
            image_path
        )


        print()
        print(
            "=" * 60
        )

        print(
            "BRAIN PLANE PREDICTION"
        )

        print(
            "=" * 60
        )


        print()

        print(
            "Predicted plane :",
            result[
                "predicted_class"
            ],
        )


        print(
            "Confidence      :",
            f'{result["confidence_percent"]:.2f}%',
        )


        print()

        print(
            "All probabilities:"
        )

        print()


        for item in result[
            "probabilities"
        ]:

            print(
                f'{item["class"]:22s} '
                f'{item["confidence_percent"]:7.2f}%'
            )


        print()

        print(
            "=" * 60
        )


    except Exception as exc:

        print()

        print(
            "Prediction failed:"
        )

        print(
            str(exc)
        )

        print()

        sys.exit(1)