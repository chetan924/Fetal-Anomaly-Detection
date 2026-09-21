from pathlib import Path

import numpy as np
from PIL import Image

import torch
import torch.nn as nn


# ============================================================
# PATHS
# ============================================================

APP_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = APP_DIR.parents[1]

MODEL_PATH = (
    APP_DIR
    / "models"
    / "heart_segmentation.pt"
)

OUTPUT_ROOT = (
    APP_DIR
    / "heart_predictions"
)

OUTPUT_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)

DEVICE = torch.device("cpu")

IMAGE_SIZE = (256, 256)
THRESHOLD = 0.5


# ============================================================
# SMALL U-NET
# ============================================================

class DoubleConv(nn.Module):

    def __init__(
        self,
        in_channels,
        out_channels,
    ):
        super().__init__()

        self.block = nn.Sequential(

            nn.Conv2d(
                in_channels,
                out_channels,
                kernel_size=3,
                padding=1,
            ),

            nn.BatchNorm2d(
                out_channels
            ),

            nn.ReLU(
                inplace=True
            ),

            nn.Conv2d(
                out_channels,
                out_channels,
                kernel_size=3,
                padding=1,
            ),

            nn.BatchNorm2d(
                out_channels
            ),

            nn.ReLU(
                inplace=True
            ),
        )

    def forward(self, x):

        return self.block(x)


class SmallUNet(nn.Module):

    def __init__(self):

        super().__init__()

        self.enc1 = DoubleConv(
            1,
            16,
        )

        self.pool1 = nn.MaxPool2d(
            2
        )

        self.enc2 = DoubleConv(
            16,
            32,
        )

        self.pool2 = nn.MaxPool2d(
            2
        )

        self.enc3 = DoubleConv(
            32,
            64,
        )

        self.pool3 = nn.MaxPool2d(
            2
        )

        self.bottleneck = DoubleConv(
            64,
            128,
        )

        self.up3 = nn.ConvTranspose2d(
            128,
            64,
            kernel_size=2,
            stride=2,
        )

        self.dec3 = DoubleConv(
            128,
            64,
        )

        self.up2 = nn.ConvTranspose2d(
            64,
            32,
            kernel_size=2,
            stride=2,
        )

        self.dec2 = DoubleConv(
            64,
            32,
        )

        self.up1 = nn.ConvTranspose2d(
            32,
            16,
            kernel_size=2,
            stride=2,
        )

        self.dec1 = DoubleConv(
            32,
            16,
        )

        self.output = nn.Conv2d(
            16,
            1,
            kernel_size=1,
        )

    def forward(self, x):

        e1 = self.enc1(x)

        e2 = self.enc2(
            self.pool1(e1)
        )

        e3 = self.enc3(
            self.pool2(e2)
        )

        b = self.bottleneck(
            self.pool3(e3)
        )

        d3 = self.up3(b)

        d3 = torch.cat(
            [d3, e3],
            dim=1,
        )

        d3 = self.dec3(d3)

        d2 = self.up2(d3)

        d2 = torch.cat(
            [d2, e2],
            dim=1,
        )

        d2 = self.dec2(d2)

        d1 = self.up1(d2)

        d1 = torch.cat(
            [d1, e1],
            dim=1,
        )

        d1 = self.dec1(d1)

        return self.output(d1)


# ============================================================
# MODEL LOADING
# ============================================================

_model = None


def load_model():

    global _model

    if _model is not None:
        return _model

    if not MODEL_PATH.exists():

        raise FileNotFoundError(
            f"Heart model not found: {MODEL_PATH}"
        )

    print(
        "Loading heart segmentation model..."
    )

    checkpoint = torch.load(
        MODEL_PATH,
        map_location=DEVICE,
    )

    model = SmallUNet()

    if isinstance(
        checkpoint,
        dict
    ) and "model_state_dict" in checkpoint:

        model.load_state_dict(
            checkpoint[
                "model_state_dict"
            ]
        )

    else:

        model.load_state_dict(
            checkpoint
        )

    model.to(
        DEVICE
    )

    model.eval()

    _model = model

    if isinstance(
        checkpoint,
        dict
    ):

        if "best_dice" in checkpoint:

            print(
                "Best validation Dice:",
                f"{checkpoint['best_dice']:.4f}",
            )

    print(
        "Heart model loaded successfully."
    )

    return _model


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def preprocess_image(
    image_path: str | Path,
):

    image_path = Path(
        image_path
    )

    if not image_path.exists():

        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    image = Image.open(
        image_path
    ).convert("L")

    original_size = image.size

    resized = image.resize(
        IMAGE_SIZE,
        Image.Resampling.BILINEAR,
    )

    image_array = np.asarray(
        resized,
        dtype=np.float32,
    ) / 255.0

    tensor = torch.from_numpy(
        image_array
    ).unsqueeze(
        0
    ).unsqueeze(
        0
    )

    return (
        tensor.to(DEVICE),
        original_size,
    )


# ============================================================
# HEART SEGMENTATION
# ============================================================

def predict_heart(
    image_path: str | Path,
    threshold: float = THRESHOLD,
    save_mask: bool = True,
):

    model = load_model()

    tensor, original_size = (
        preprocess_image(
            image_path
        )
    )

    with torch.no_grad():

        output = model(
            tensor
        )

        probability = torch.sigmoid(
            output
        )

    probability = (
        probability[
            0,
            0
        ]
        .cpu()
        .numpy()
    )

    mask_256 = (
        probability
        >= threshold
    )

    # Convert prediction back to
    # original ultrasound resolution.
    mask_image = Image.fromarray(
        (
            mask_256.astype(
                np.uint8
            )
            * 255
        )
    )

    mask_original = mask_image.resize(
        original_size,
        Image.Resampling.NEAREST,
    )

    mask = (
        np.asarray(
            mask_original
        ) > 0
    )

    result = {
        "mask": mask,
        "probability": probability,
        "original_size": original_size,
        "threshold": threshold,
    }

    if save_mask:

        image_path = Path(
            image_path
        )

        output_path = (
            OUTPUT_ROOT
            / f"{image_path.stem}_heart_mask.png"
        )

        mask_original.save(
            output_path
        )

        result[
            "mask_path"
        ] = output_path

    return result


# ============================================================
# SIMPLE HELPER
# ============================================================

def segment_heart(
    image_path: str | Path,
):

    return predict_heart(
        image_path
    )


# ============================================================
# TEST
# ============================================================

def main():

    print(
        "=" * 60
    )

    print(
        "FETALAI HEART SEGMENTATION"
    )

    print(
        "=" * 60
    )

    print()

    print(
        "Model:",
        MODEL_PATH,
    )

    print(
        "Model exists:",
        MODEL_PATH.exists(),
    )

    print(
        "Device:",
        DEVICE,
    )

    print()

    load_model()

    print()

    print(
        "Heart segmentation model is ready."
    )

    print(
        "=" * 60
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()