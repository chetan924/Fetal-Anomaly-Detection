from pathlib import Path

import numpy as np
from PIL import Image

import torch
import torch.nn as nn


# ============================================================
# PATHS
# ============================================================

MODEL_PATH = Path(
    r"D:\Fetal Anomaly Detection\backend\app\ml\models\heart_segmentation.pt"
)

IMAGE_DIR = Path(
    r"D:\Fetal Anomaly Detection\FOCUS-dataset\testing\images"
)

MASK_DIR = Path(
    r"D:\Fetal Anomaly Detection\FOCUS-dataset\testing\annfiles_mask"
)

OUTPUT_ROOT = Path(
    r"D:\Fetal Anomaly Detection\backend\app\ml\heart_predictions"
)

PREDICTION_DIR = OUTPUT_ROOT / "masks"

PREDICTION_DIR.mkdir(
    parents=True,
    exist_ok=True
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
        out_channels
    ):
        super().__init__()

        self.block = nn.Sequential(

            nn.Conv2d(
                in_channels,
                out_channels,
                3,
                padding=1
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
                3,
                padding=1
            ),

            nn.BatchNorm2d(
                out_channels
            ),

            nn.ReLU(
                inplace=True
            )
        )

    def forward(self, x):

        return self.block(x)


class SmallUNet(nn.Module):

    def __init__(self):

        super().__init__()

        # Encoder

        self.enc1 = DoubleConv(
            1,
            16
        )

        self.pool1 = nn.MaxPool2d(
            2
        )

        self.enc2 = DoubleConv(
            16,
            32
        )

        self.pool2 = nn.MaxPool2d(
            2
        )

        self.enc3 = DoubleConv(
            32,
            64
        )

        self.pool3 = nn.MaxPool2d(
            2
        )

        # Bottleneck

        self.bottleneck = DoubleConv(
            64,
            128
        )

        # Decoder

        self.up3 = nn.ConvTranspose2d(
            128,
            64,
            2,
            stride=2
        )

        self.dec3 = DoubleConv(
            128,
            64
        )

        self.up2 = nn.ConvTranspose2d(
            64,
            32,
            2,
            stride=2
        )

        self.dec2 = DoubleConv(
            64,
            32
        )

        self.up1 = nn.ConvTranspose2d(
            32,
            16,
            2,
            stride=2
        )

        self.dec1 = DoubleConv(
            32,
            16
        )

        # Output

        self.output = nn.Conv2d(
            16,
            1,
            1
        )

    def forward(self, x):

        # Encoder

        e1 = self.enc1(x)

        e2 = self.enc2(
            self.pool1(e1)
        )

        e3 = self.enc3(
            self.pool2(e2)
        )

        # Bottleneck

        b = self.bottleneck(
            self.pool3(e3)
        )

        # Decoder

        d3 = self.up3(b)

        d3 = torch.cat(
            [
                d3,
                e3
            ],
            dim=1
        )

        d3 = self.dec3(d3)

        d2 = self.up2(d3)

        d2 = torch.cat(
            [
                d2,
                e2
            ],
            dim=1
        )

        d2 = self.dec2(d2)

        d1 = self.up1(d2)

        d1 = torch.cat(
            [
                d1,
                e1
            ],
            dim=1
        )

        d1 = self.dec1(d1)

        return self.output(d1)


# ============================================================
# LOAD MODEL
# ============================================================

def load_model():

    print("Loading model...")

    if not MODEL_PATH.exists():

        raise FileNotFoundError(
            f"Model not found:\n{MODEL_PATH}"
        )

    checkpoint = torch.load(
        MODEL_PATH,
        map_location=DEVICE
    )

    model = SmallUNet()

    model.load_state_dict(
        checkpoint["model_state_dict"]
    )

    model.to(DEVICE)

    model.eval()

    print(
        "Model loaded successfully."
    )

    if "best_dice" in checkpoint:

        print(
            "Best validation Dice:",
            f"{checkpoint['best_dice']:.4f}"
        )

    return model


# ============================================================
# PREPARE IMAGE
# ============================================================

def prepare_image(image_path):

    image = Image.open(
        image_path
    ).convert("L")

    original_size = image.size

    image = image.resize(
        IMAGE_SIZE,
        Image.Resampling.BILINEAR
    )

    image_array = np.asarray(
        image,
        dtype=np.float32
    ) / 255.0

    tensor = torch.from_numpy(
        image_array
    )

    tensor = tensor.unsqueeze(
        0
    ).unsqueeze(
        0
    )

    return tensor, original_size


# ============================================================
# PREDICT ONE IMAGE
# ============================================================

def predict_image(
    model,
    image_path
):

    tensor, original_size = prepare_image(
        image_path
    )

    tensor = tensor.to(
        DEVICE
    )

    with torch.no_grad():

        output = model(
            tensor
        )

        probability = torch.sigmoid(
            output
        )

    mask = (
        probability[0, 0]
        .cpu()
        .numpy()
        > THRESHOLD
    )

    return mask, original_size


# ============================================================
# LOAD GROUND TRUTH MASK
# ============================================================

def load_target_mask(
    mask_path
):

    mask = Image.open(
        mask_path
    ).convert("L")

    # IMPORTANT:
    # Model output = 256 x 256
    # Ground truth may have original size
    # Therefore resize target to 256 x 256.

    mask = mask.resize(
        IMAGE_SIZE,
        Image.Resampling.NEAREST
    )

    mask = np.asarray(
        mask
    ) > 0

    return mask


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(
    prediction,
    target,
    smooth=1e-6
):

    prediction = np.asarray(
        prediction
    ).astype(bool)

    target = np.asarray(
        target
    ).astype(bool)

    # Safety check

    if prediction.shape != target.shape:

        raise ValueError(
            "Prediction and target shapes do not match: "
            f"{prediction.shape} vs {target.shape}"
        )

    intersection = np.logical_and(
        prediction,
        target
    ).sum()

    prediction_area = prediction.sum()

    target_area = target.sum()

    union = np.logical_or(
        prediction,
        target
    ).sum()

    dice = (
        (
            2 * intersection
            + smooth
        )
        /
        (
            prediction_area
            + target_area
            + smooth
        )
    )

    iou = (
        (
            intersection
            + smooth
        )
        /
        (
            union
            + smooth
        )
    )

    return float(dice), float(iou)


# ============================================================
# SAVE MASK
# ============================================================

def save_mask(
    mask,
    output_path
):

    mask_image = (
        mask.astype(
            np.uint8
        )
        * 255
    )

    image = Image.fromarray(
        mask_image
    )

    image.save(
        output_path
    )


# ============================================================
# SAVE OVERLAY
# ============================================================

def save_overlay(
    image_path,
    prediction,
    output_path
):

    original = Image.open(
        image_path
    ).convert("L")

    original = original.resize(
        IMAGE_SIZE,
        Image.Resampling.BILINEAR
    )

    original_array = np.asarray(
        original
    )

    # Create RGB image

    overlay = np.stack(
        [
            original_array,
            original_array,
            original_array
        ],
        axis=-1
    ).astype(
        np.uint8
    )

    # Highlight predicted heart region

    overlay[prediction, 0] = 255
    overlay[prediction, 1] = 0
    overlay[prediction, 2] = 0

    Image.fromarray(
        overlay
    ).save(
        output_path
    )


# ============================================================
# MAIN TESTING
# ============================================================

def main():

    print("=" * 60)
    print("FOCUS HEART MODEL TESTING")
    print("=" * 60)

    print()

    print(
        "Device:",
        DEVICE
    )

    print(
        "Model:",
        MODEL_PATH
    )

    print(
        "Images:",
        IMAGE_DIR
    )

    print(
        "Masks:",
        MASK_DIR
    )

    print()

    # --------------------------------------------------------
    # Load model
    # --------------------------------------------------------

    model = load_model()

    # --------------------------------------------------------
    # Check directories
    # --------------------------------------------------------

    if not IMAGE_DIR.exists():

        raise FileNotFoundError(
            f"Test image directory not found:\n{IMAGE_DIR}"
        )

    if not MASK_DIR.exists():

        raise FileNotFoundError(
            f"Test mask directory not found:\n{MASK_DIR}"
        )

    # --------------------------------------------------------
    # Find images
    # --------------------------------------------------------

    image_files = sorted(
        IMAGE_DIR.glob("*.png")
    )

    print()

    print(
        "Test images:",
        len(image_files)
    )

    if len(image_files) == 0:

        raise RuntimeError(
            "No test images found."
        )

    # --------------------------------------------------------
    # Create output folders
    # --------------------------------------------------------

    prediction_dir = (
        OUTPUT_ROOT
        / "masks"
    )

    overlay_dir = (
        OUTPUT_ROOT
        / "overlays"
    )

    prediction_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    overlay_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    total_dice = 0.0

    total_iou = 0.0

    processed = 0

    # --------------------------------------------------------
    # Test images
    # --------------------------------------------------------

    for index, image_path in enumerate(
        image_files,
        start=1
    ):

        print()

        print(
            f"[{index}/{len(image_files)}]",
            image_path.name
        )

        # Ground truth filename

        target_path = (
            MASK_DIR
            /
            (
                image_path.stem
                + "-cardiac.png"
            )
        )

        if not target_path.exists():

            print(
                "  Missing target:",
                target_path.name
            )

            continue

        # ----------------------------------------------------
        # Prediction
        # ----------------------------------------------------

        prediction, original_size = predict_image(
            model,
            image_path
        )

        # ----------------------------------------------------
        # Target
        # ----------------------------------------------------

        target = load_target_mask(
            target_path
        )

        # ----------------------------------------------------
        # Metrics
        # ----------------------------------------------------

        dice, iou = calculate_metrics(
            prediction,
            target
        )

        # ----------------------------------------------------
        # Save predicted mask
        # ----------------------------------------------------

        prediction_path = (
            prediction_dir
            /
            image_path.name
        )

        save_mask(
            prediction,
            prediction_path
        )

        # ----------------------------------------------------
        # Save overlay
        # ----------------------------------------------------

        overlay_path = (
            overlay_dir
            /
            image_path.name
        )

        save_overlay(
            image_path,
            prediction,
            overlay_path
        )

        # ----------------------------------------------------
        # Accumulate metrics
        # ----------------------------------------------------

        total_dice += dice

        total_iou += iou

        processed += 1

        print(
            f"  Dice: {dice:.4f}"
        )

        print(
            f"  IoU : {iou:.4f}"
        )

        print(
            f"  Original size: {original_size}"
        )

    # --------------------------------------------------------
    # Check
    # --------------------------------------------------------

    if processed == 0:

        raise RuntimeError(
            "No test images were processed."
        )

    # --------------------------------------------------------
    # Average metrics
    # --------------------------------------------------------

    average_dice = (
        total_dice
        / processed
    )

    average_iou = (
        total_iou
        / processed
    )

    # --------------------------------------------------------
    # Final results
    # --------------------------------------------------------

    print()

    print("=" * 60)
    print("TEST RESULTS")
    print("=" * 60)

    print()

    print(
        "Images evaluated:",
        processed
    )

    print(
        "Average Dice:",
        f"{average_dice:.4f}"
    )

    print(
        "Average IoU:",
        f"{average_iou:.4f}"
    )

    print()

    print(
        "Best validation Dice:"
    )

    checkpoint = torch.load(
        MODEL_PATH,
        map_location=DEVICE
    )

    if "best_dice" in checkpoint:

        print(
            f"{checkpoint['best_dice']:.4f}"
        )

    else:

        print(
            "Not available"
        )

    print()

    print(
        "Prediction masks:"
    )

    print(
        prediction_dir
    )

    print()

    print(
        "Overlay images:"
    )

    print(
        overlay_dir
    )

    print()

    print("=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()