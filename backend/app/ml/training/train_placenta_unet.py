from pathlib import Path
import random

import numpy as np
from PIL import Image

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader


# ============================================================
# CONFIG
# ============================================================

DATASET_ROOT = Path(
    r"D:\Fetal_Placenta_YOLO"
)

MODEL_OUTPUT = Path(
    r"D:\Fetal Anomaly Detection\backend\app\ml\models\fetal_placenta_unet.pt"
)

BEST_OUTPUT = Path(
    r"D:\Fetal Anomaly Detection\backend\app\ml\models\fetal_placenta_unet_best.pt"
)

IMAGE_SIZE = 256
BATCH_SIZE = 4
EPOCHS = 60
LEARNING_RATE = 1e-4
PATIENCE = 10
NUM_WORKERS = 0
SEED = 42


# ============================================================
# DEVICE / SEED
# ============================================================

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available()
    else "cpu"
)

print("=" * 70)
print("FETAL PLACENTA U-NET TRAINING")
print("=" * 70)

print(
    f"Device: {DEVICE}"
)


# ============================================================
# DATASET
# ============================================================

class PlacentaDataset(Dataset):

    def __init__(
        self,
        image_dir: Path,
        mask_dir: Path,
        image_size: int = 256,
    ):
        self.image_dir = image_dir
        self.mask_dir = mask_dir
        self.image_size = image_size

        images = sorted(
            image_dir.glob("*.png")
        )

        self.samples = []

        for image_path in images:

            mask_path = (
                mask_dir / image_path.name
            )

            if mask_path.exists():
                self.samples.append(
                    (
                        image_path,
                        mask_path,
                    )
                )

        if not self.samples:
            raise RuntimeError(
                f"No valid image-mask pairs found in:\n"
                f"{image_dir}\n{mask_dir}"
            )

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):

        image_path, mask_path = (
            self.samples[index]
        )

        image = Image.open(
            image_path
        ).convert("RGB")

        mask = Image.open(
            mask_path
        ).convert("L")

        image = image.resize(
            (
                self.image_size,
                self.image_size,
            ),
            Image.Resampling.BILINEAR,
        )

        mask = mask.resize(
            (
                self.image_size,
                self.image_size,
            ),
            Image.Resampling.NEAREST,
        )

        image = np.asarray(
            image,
            dtype=np.float32,
        ) / 255.0

        mask = np.asarray(
            mask,
            dtype=np.float32,
        ) / 255.0

        image = (
            np.transpose(
                image,
                (2, 0, 1),
            )
        )

        mask = np.expand_dims(
            mask,
            axis=0,
        )

        image = torch.from_numpy(
            image
        )

        mask = torch.from_numpy(
            mask
        )

        mask = (
            mask > 0.5
        ).float()

        return image, mask


# ============================================================
# U-NET BLOCKS
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
                bias=False,
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
                bias=False,
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


class UNet(nn.Module):

    def __init__(self):

        super().__init__()

        self.enc1 = DoubleConv(
            3,
            32,
        )

        self.enc2 = DoubleConv(
            32,
            64,
        )

        self.enc3 = DoubleConv(
            64,
            128,
        )

        self.enc4 = DoubleConv(
            128,
            256,
        )

        self.pool = nn.MaxPool2d(
            kernel_size=2
        )

        self.bottleneck = DoubleConv(
            256,
            512,
        )

        self.up4 = nn.ConvTranspose2d(
            512,
            256,
            kernel_size=2,
            stride=2,
        )

        self.dec4 = DoubleConv(
            512,
            256,
        )

        self.up3 = nn.ConvTranspose2d(
            256,
            128,
            kernel_size=2,
            stride=2,
        )

        self.dec3 = DoubleConv(
            256,
            128,
        )

        self.up2 = nn.ConvTranspose2d(
            128,
            64,
            kernel_size=2,
            stride=2,
        )

        self.dec2 = DoubleConv(
            128,
            64,
        )

        self.up1 = nn.ConvTranspose2d(
            64,
            32,
            kernel_size=2,
            stride=2,
        )

        self.dec1 = DoubleConv(
            64,
            32,
        )

        self.final = nn.Conv2d(
            32,
            1,
            kernel_size=1,
        )

    def forward(self, x):

        e1 = self.enc1(x)

        e2 = self.enc2(
            self.pool(e1)
        )

        e3 = self.enc3(
            self.pool(e2)
        )

        e4 = self.enc4(
            self.pool(e3)
        )

        b = self.bottleneck(
            self.pool(e4)
        )

        d4 = self.up4(b)

        d4 = torch.cat(
            [d4, e4],
            dim=1,
        )

        d4 = self.dec4(d4)

        d3 = self.up3(d4)

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

        return self.final(d1)


# ============================================================
# LOSSES / METRICS
# ============================================================

def dice_score(
    prediction,
    target,
    smooth=1e-6,
):

    prediction = (
        prediction
        .sigmoid()
    )

    prediction = (
        prediction
        .reshape(-1)
    )

    target = (
        target
        .reshape(-1)
    )

    intersection = (
        prediction * target
    ).sum()

    return (
        (2.0 * intersection + smooth)
        /
        (
            prediction.sum()
            + target.sum()
            + smooth
        )
    )


class DiceBCELoss(nn.Module):

    def __init__(self):
        super().__init__()

        self.bce = nn.BCEWithLogitsLoss()

    def forward(
        self,
        logits,
        target,
    ):

        bce = self.bce(
            logits,
            target,
        )

        dice = dice_score(
            logits,
            target,
        )

        return (
            bce
            +
            (1.0 - dice)
        )


# ============================================================
# DATA
# ============================================================

train_dataset = PlacentaDataset(
    DATASET_ROOT
    / "images"
    / "train",
    DATASET_ROOT
    / "masks"
    / "train",
    IMAGE_SIZE,
)

val_dataset = PlacentaDataset(
    DATASET_ROOT
    / "images"
    / "val",
    DATASET_ROOT
    / "masks"
    / "val",
    IMAGE_SIZE,
)


train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=NUM_WORKERS,
    pin_memory=False,
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=NUM_WORKERS,
    pin_memory=False,
)


print(
    f"Train samples: {len(train_dataset)}"
)

print(
    f"Val samples  : {len(val_dataset)}"
)


# ============================================================
# MODEL
# ============================================================

model = UNet().to(
    DEVICE
)

criterion = DiceBCELoss()

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=1e-4,
)

scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode="max",
    factor=0.5,
    patience=3,
)


# ============================================================
# TRAINING
# ============================================================

best_val_dice = -1.0
epochs_without_improvement = 0

MODEL_OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

for epoch in range(
    1,
    EPOCHS + 1,
):

    # --------------------------------------------------------
    # TRAIN
    # --------------------------------------------------------

    model.train()

    train_loss_sum = 0.0
    train_dice_sum = 0.0
    train_batches = 0

    for images, masks in train_loader:

        images = images.to(
            DEVICE
        )

        masks = masks.to(
            DEVICE
        )

        optimizer.zero_grad(
            set_to_none=True
        )

        outputs = model(
            images
        )

        loss = criterion(
            outputs,
            masks,
        )

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0,
        )

        optimizer.step()

        train_loss_sum += (
            loss.item()
        )

        train_dice_sum += (
            dice_score(
                outputs.detach(),
                masks,
            ).item()
        )

        train_batches += 1

    train_loss = (
        train_loss_sum
        /
        max(train_batches, 1)
    )

    train_dice = (
        train_dice_sum
        /
        max(train_batches, 1)
    )


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    model.eval()

    val_loss_sum = 0.0
    val_dice_sum = 0.0
    val_batches = 0

    with torch.no_grad():

        for images, masks in val_loader:

            images = images.to(
                DEVICE
            )

            masks = masks.to(
                DEVICE
            )

            outputs = model(
                images
            )

            loss = criterion(
                outputs,
                masks,
            )

            val_loss_sum += (
                loss.item()
            )

            val_dice_sum += (
                dice_score(
                    outputs,
                    masks,
                ).item()
            )

            val_batches += 1

    val_loss = (
        val_loss_sum
        /
        max(val_batches, 1)
    )

    val_dice = (
        val_dice_sum
        /
        max(val_batches, 1)
    )


    scheduler.step(
        val_dice
    )


    current_lr = (
        optimizer.param_groups[0]["lr"]
    )


    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    print(
        f"\n{'=' * 70}"
    )

    print(
        f"Epoch {epoch}/{EPOCHS}"
    )

    print(
        f"Train Loss      : {train_loss:.4f}"
    )

    print(
        f"Train Soft Dice : {train_dice:.4f}"
    )

    print(
        f"Val Loss        : {val_loss:.4f}"
    )

    print(
        f"Val Soft Dice   : {val_dice:.4f}"
    )

    print(
        f"LR              : {current_lr:.8f}"
    )


    # --------------------------------------------------------
    # BEST MODEL
    # --------------------------------------------------------

    if val_dice > best_val_dice:

        best_val_dice = (
            val_dice
        )

        epochs_without_improvement = 0

        torch.save(
            {
                "model_state_dict":
                    model.state_dict(),

                "image_size":
                    IMAGE_SIZE,

                "best_val_dice":
                    best_val_dice,
            },
            BEST_OUTPUT,
        )

        print(
            f"New best model: "
            f"{best_val_dice:.4f}"
        )

    else:

        epochs_without_improvement += 1

        print(
            f"No improvement: "
            f"{epochs_without_improvement}/"
            f"{PATIENCE}"
        )


    if (
        epochs_without_improvement
        >= PATIENCE
    ):

        print(
            "\nEarly stopping triggered."
        )

        break


# ============================================================
# LOAD BEST
# ============================================================

checkpoint = torch.load(
    BEST_OUTPUT,
    map_location=DEVICE,
)

model.load_state_dict(
    checkpoint[
        "model_state_dict"
    ]
)


# ============================================================
# FINAL VALIDATION
# ============================================================

model.eval()

final_dice_sum = 0.0
final_batches = 0

with torch.no_grad():

    for images, masks in val_loader:

        images = images.to(
            DEVICE
        )

        masks = masks.to(
            DEVICE
        )

        outputs = model(
            images
        )

        final_dice_sum += (
            dice_score(
                outputs,
                masks,
            ).item()
        )

        final_batches += 1


final_dice = (
    final_dice_sum
    /
    max(final_batches, 1)
)


# ============================================================
# SAVE FINAL MODEL
# ============================================================

torch.save(
    model.state_dict(),
    MODEL_OUTPUT,
)


print("\n" + "=" * 70)

print(
    "FINAL PLACENTA U-NET EVALUATION"
)

print("=" * 70)

print(
    f"Best Val Dice : "
    f"{best_val_dice:.4f}"
)

print(
    f"Final Val Dice: "
    f"{final_dice:.4f}"
)

print(
    f"Best model    : "
    f"{BEST_OUTPUT}"
)

print(
    f"Final model   : "
    f"{MODEL_OUTPUT}"
)

print("=" * 70)

print(
    "FETAL PLACENTA U-NET TRAINING COMPLETE"
)

print("=" * 70)