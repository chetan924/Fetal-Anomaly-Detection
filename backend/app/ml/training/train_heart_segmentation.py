from pathlib import Path

import numpy as np
from PIL import Image

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader


# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATA_ROOT = PROJECT_ROOT / "backend" / "app" / "ml" / "heart_data"
MODEL_DIR = PROJECT_ROOT / "backend" / "app" / "ml" / "models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_SIZE = 256
BATCH_SIZE = 4
EPOCHS = 100
LEARNING_RATE = 1e-3

DEVICE = torch.device("cpu")

BEST_MODEL_PATH = MODEL_DIR / "heart_segmentation.pt"


# ============================================================
# DATASET
# ============================================================

class HeartDataset(Dataset):

    def __init__(self, split):

        self.image_dir = DATA_ROOT / split / "images"
        self.mask_dir = DATA_ROOT / split / "masks"

        self.images = sorted(self.image_dir.glob("*.png"))

        if not self.images:
            raise RuntimeError(
                f"No images found in {self.image_dir}"
            )

    def __len__(self):
        return len(self.images)

    def __getitem__(self, index):

        image_path = self.images[index]

        mask_path = (
            self.mask_dir /
            image_path.name
        )

        image = Image.open(image_path).convert("L")
        mask = Image.open(mask_path).convert("L")

        image = np.asarray(
            image,
            dtype=np.float32
        ) / 255.0

        mask = np.asarray(
            mask,
            dtype=np.float32
        ) / 255.0

        image = torch.from_numpy(
            image
        ).unsqueeze(0)

        mask = torch.from_numpy(
            mask
        ).unsqueeze(0)

        return image, mask


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
                kernel_size=3,
                padding=1
            ),

            nn.BatchNorm2d(out_channels),

            nn.ReLU(inplace=True),

            nn.Conv2d(
                out_channels,
                out_channels,
                kernel_size=3,
                padding=1
            ),

            nn.BatchNorm2d(out_channels),

            nn.ReLU(inplace=True)
        )

    def forward(self, x):

        return self.block(x)


class SmallUNet(nn.Module):

    def __init__(self):

        super().__init__()

        self.enc1 = DoubleConv(1, 16)

        self.pool1 = nn.MaxPool2d(2)

        self.enc2 = DoubleConv(16, 32)

        self.pool2 = nn.MaxPool2d(2)

        self.enc3 = DoubleConv(32, 64)

        self.pool3 = nn.MaxPool2d(2)

        self.bottleneck = DoubleConv(64, 128)

        self.up3 = nn.ConvTranspose2d(
            128,
            64,
            kernel_size=2,
            stride=2
        )

        self.dec3 = DoubleConv(
            128,
            64
        )

        self.up2 = nn.ConvTranspose2d(
            64,
            32,
            kernel_size=2,
            stride=2
        )

        self.dec2 = DoubleConv(
            64,
            32
        )

        self.up1 = nn.ConvTranspose2d(
            32,
            16,
            kernel_size=2,
            stride=2
        )

        self.dec1 = DoubleConv(
            32,
            16
        )

        self.output = nn.Conv2d(
            16,
            1,
            kernel_size=1
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
            dim=1
        )

        d3 = self.dec3(d3)

        d2 = self.up2(d3)

        d2 = torch.cat(
            [d2, e2],
            dim=1
        )

        d2 = self.dec2(d2)

        d1 = self.up1(d2)

        d1 = torch.cat(
            [d1, e1],
            dim=1
        )

        d1 = self.dec1(d1)

        return self.output(d1)


# ============================================================
# DICE LOSS
# ============================================================

def dice_score(
    predictions,
    targets,
    smooth=1e-6
):

    predictions = torch.sigmoid(
        predictions
    )

    predictions = predictions.reshape(
        predictions.size(0),
        -1
    )

    targets = targets.reshape(
        targets.size(0),
        -1
    )

    intersection = (
        predictions * targets
    ).sum(dim=1)

    dice = (
        (2 * intersection + smooth)
        /
        (
            predictions.sum(dim=1)
            +
            targets.sum(dim=1)
            +
            smooth
        )
    )

    return dice.mean()


def dice_loss(
    predictions,
    targets
):

    return 1.0 - dice_score(
        predictions,
        targets
    )


# ============================================================
# IOU
# ============================================================

def iou_score(
    predictions,
    targets,
    threshold=0.5,
    smooth=1e-6
):

    predictions = torch.sigmoid(
        predictions
    )

    predictions = (
        predictions > threshold
    ).float()

    predictions = predictions.reshape(
        predictions.size(0),
        -1
    )

    targets = targets.reshape(
        targets.size(0),
        -1
    )

    intersection = (
        predictions * targets
    ).sum(dim=1)

    union = (
        predictions.sum(dim=1)
        +
        targets.sum(dim=1)
        -
        intersection
    )

    iou = (
        (intersection + smooth)
        /
        (union + smooth)
    )

    return iou.mean()


# ============================================================
# LOSS
# ============================================================

class CombinedLoss(nn.Module):

    def __init__(self):

        super().__init__()

        self.bce = nn.BCEWithLogitsLoss()

    def forward(
        self,
        predictions,
        targets
    ):

        bce_loss = self.bce(
            predictions,
            targets
        )

        d_loss = dice_loss(
            predictions,
            targets
        )

        return bce_loss + d_loss


# ============================================================
# VALIDATION
# ============================================================

def validate(
    model,
    loader
):

    model.eval()

    total_loss = 0.0
    total_dice = 0.0
    total_iou = 0.0

    criterion = CombinedLoss()

    with torch.no_grad():

        for images, masks in loader:

            images = images.to(DEVICE)
            masks = masks.to(DEVICE)

            outputs = model(images)

            loss = criterion(
                outputs,
                masks
            )

            dice = dice_score(
                outputs,
                masks
            )

            iou = iou_score(
                outputs,
                masks
            )

            total_loss += loss.item()
            total_dice += dice.item()
            total_iou += iou.item()

    count = len(loader)

    return (
        total_loss / count,
        total_dice / count,
        total_iou / count
    )


# ============================================================
# TRAINING
# ============================================================

def main():

    print("=" * 60)
    print("FOCUS HEART SEGMENTATION TRAINING")
    print("=" * 60)

    print()
    print("Device:", DEVICE)
    print("Batch size:", BATCH_SIZE)
    print("Epochs:", EPOCHS)
    print("Learning rate:", LEARNING_RATE)

    train_dataset = HeartDataset(
        "training"
    )

    val_dataset = HeartDataset(
        "validation"
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0
    )

    print()
    print(
        "Training images:",
        len(train_dataset)
    )

    print(
        "Validation images:",
        len(val_dataset)
    )

    model = SmallUNet().to(DEVICE)

    criterion = CombinedLoss()

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE
    )

    best_dice = 0.0

    for epoch in range(
        1,
        EPOCHS + 1
    ):

        model.train()

        running_loss = 0.0

        for images, masks in train_loader:

            images = images.to(DEVICE)
            masks = masks.to(DEVICE)

            optimizer.zero_grad()

            outputs = model(images)

            loss = criterion(
                outputs,
                masks
            )

            loss.backward()

            optimizer.step()

            running_loss += loss.item()

        train_loss = (
            running_loss /
            len(train_loader)
        )

        val_loss, val_dice, val_iou = validate(
            model,
            val_loader
        )

        print(
            f"Epoch {epoch:02d}/{EPOCHS} | "
            f"Train Loss: {train_loss:.4f} | "
            f"Val Loss: {val_loss:.4f} | "
            f"Dice: {val_dice:.4f} | "
            f"IoU: {val_iou:.4f}"
        )

        if val_dice > best_dice:

            best_dice = val_dice

            torch.save(
                {
                    "model_state_dict":
                        model.state_dict(),

                    "image_size":
                        IMAGE_SIZE,

                    "best_dice":
                        best_dice,

                    "architecture":
                        "SmallUNet"
                },
                BEST_MODEL_PATH
            )

            print(
                f"  ✓ Best model saved "
                f"(Dice={best_dice:.4f})"
            )

    print()
    print("=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)

    print()
    print(
        "Best validation Dice:",
        f"{best_dice:.4f}"
    )

    print(
        "Model:",
        BEST_MODEL_PATH
    )


if __name__ == "__main__":
    main()
