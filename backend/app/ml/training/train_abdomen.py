from pathlib import Path
import random

import numpy as np
from PIL import Image
from tqdm import tqdm

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader


# ============================================================
# CONFIG
# ============================================================

DATASET_ROOT = Path(r"D:\Fetal_Abdomen_Processed")

IMAGE_DIR = DATASET_ROOT / "images"
MASK_DIR = DATASET_ROOT / "masks"

OUTPUT_DIR = Path(r"D:\Fetal Anomaly Detection\backend\models")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = OUTPUT_DIR / "fetal_abdomen_unet.pth"

IMAGE_SIZE = 256
NUM_CLASSES = 5

BATCH_SIZE = 2
EPOCHS = 10

LEARNING_RATE = 1e-3

VAL_SPLIT = 0.20
SEED = 42

NUM_WORKERS = 0


# ============================================================
# REPRODUCIBILITY
# ============================================================

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


print("=" * 70)
print("FETAL ABDOMINAL STRUCTURE SEGMENTATION")
print("=" * 70)

print(f"Device       : {DEVICE}")
print(f"Image size   : {IMAGE_SIZE}")
print(f"Classes      : {NUM_CLASSES}")
print(f"Batch size   : {BATCH_SIZE}")
print(f"Epochs       : {EPOCHS}")
print(f"Learning rate: {LEARNING_RATE}")
print()


# ============================================================
# DATASET
# ============================================================

class AbdomenDataset(Dataset):

    def __init__(self, image_paths, mask_paths):
        self.image_paths = image_paths
        self.mask_paths = mask_paths

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, index):

        image_path = self.image_paths[index]
        mask_path = self.mask_paths[index]

        # ----------------------------------------------------
        # IMAGE
        # ----------------------------------------------------

        image = Image.open(image_path).convert("RGB")

        image = image.resize(
            (IMAGE_SIZE, IMAGE_SIZE),
            Image.Resampling.BILINEAR
        )

        image = np.asarray(
            image,
            dtype=np.float32
        )

        image = image / 255.0

        image = torch.from_numpy(
            image
        ).permute(2, 0, 1)

        # ----------------------------------------------------
        # MASK
        # ----------------------------------------------------

        mask = Image.open(mask_path)

        mask = mask.resize(
            (IMAGE_SIZE, IMAGE_SIZE),
            Image.Resampling.NEAREST
        )

        mask = np.asarray(
            mask,
            dtype=np.int64
        )

        mask = torch.from_numpy(mask)

        return image, mask


# ============================================================
# LOAD DATA
# ============================================================

image_paths = sorted(
    IMAGE_DIR.glob("*.png")
)

mask_paths = sorted(
    MASK_DIR.glob("*.png")
)


if len(image_paths) == 0:
    raise RuntimeError(
        f"No images found in {IMAGE_DIR}"
    )


if len(mask_paths) == 0:
    raise RuntimeError(
        f"No masks found in {MASK_DIR}"
    )


image_map = {
    p.stem: p
    for p in image_paths
}

mask_map = {
    p.stem: p
    for p in mask_paths
}


sample_ids = sorted(
    set(image_map.keys())
    & set(mask_map.keys())
)


print(f"Dataset samples: {len(sample_ids)}")


# ============================================================
# TRAIN / VALIDATION SPLIT
# ============================================================

random.shuffle(sample_ids)

val_count = int(
    len(sample_ids) * VAL_SPLIT
)

val_ids = sample_ids[:val_count]
train_ids = sample_ids[val_count:]


train_images = [
    image_map[x]
    for x in train_ids
]

train_masks = [
    mask_map[x]
    for x in train_ids
]

val_images = [
    image_map[x]
    for x in val_ids
]

val_masks = [
    mask_map[x]
    for x in val_ids
]


print(f"Training samples   : {len(train_ids)}")
print(f"Validation samples : {len(val_ids)}")
print()


# ============================================================
# DATA LOADERS
# ============================================================

train_dataset = AbdomenDataset(
    train_images,
    train_masks
)

val_dataset = AbdomenDataset(
    val_images,
    val_masks
)


train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=NUM_WORKERS,
    pin_memory=False
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=NUM_WORKERS,
    pin_memory=False
)


# ============================================================
# LIGHTWEIGHT U-NET
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
                padding=1,
                bias=False
            ),

            nn.BatchNorm2d(
                out_channels
            ),

            nn.ReLU(inplace=True),

            nn.Conv2d(
                out_channels,
                out_channels,
                kernel_size=3,
                padding=1,
                bias=False
            ),

            nn.BatchNorm2d(
                out_channels
            ),

            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.block(x)


class TinyUNet(nn.Module):

    def __init__(
        self,
        num_classes=5
    ):
        super().__init__()

        self.enc1 = DoubleConv(3, 16)
        self.enc2 = DoubleConv(16, 32)
        self.enc3 = DoubleConv(32, 64)

        self.pool = nn.MaxPool2d(2)

        self.bottleneck = DoubleConv(
            64,
            128
        )

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

        self.final = nn.Conv2d(
            16,
            num_classes,
            kernel_size=1
        )


    def forward(self, x):

        e1 = self.enc1(x)

        e2 = self.enc2(
            self.pool(e1)
        )

        e3 = self.enc3(
            self.pool(e2)
        )

        b = self.bottleneck(
            self.pool(e3)
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

        return self.final(d1)


# ============================================================
# MODEL
# ============================================================

model = TinyUNet(
    num_classes=NUM_CLASSES
).to(DEVICE)


print(
    f"Model parameters: "
    f"{sum(p.numel() for p in model.parameters()):,}"
)

print()


# ============================================================
# LOSS
# ============================================================

def dice_loss(
    logits,
    targets,
    num_classes=5
):

    probabilities = torch.softmax(
        logits,
        dim=1
    )

    total_loss = 0.0

    smooth = 1e-6

    for class_id in range(
        num_classes
    ):

        pred = probabilities[:, class_id]

        target = (
            targets == class_id
        ).float()

        intersection = (
            pred * target
        ).sum()

        denominator = (
            pred.sum()
            + target.sum()
        )

        dice = (
            2.0 * intersection
            + smooth
        ) / (
            denominator
            + smooth
        )

        total_loss += (
            1.0 - dice
        )

    return total_loss / num_classes


criterion_ce = nn.CrossEntropyLoss()


def combined_loss(
    logits,
    targets
):

    ce = criterion_ce(
        logits,
        targets
    )

    dice = dice_loss(
        logits,
        targets,
        NUM_CLASSES
    )

    return ce + dice


# ============================================================
# OPTIMIZER
# ============================================================

optimizer = torch.optim.Adam(
    model.parameters(),
    lr=LEARNING_RATE
)


# ============================================================
# METRIC
# ============================================================

def mean_dice(
    logits,
    targets
):

    predictions = torch.argmax(
        logits,
        dim=1
    )

    scores = []

    for class_id in range(
        1,
        NUM_CLASSES
    ):

        pred = (
            predictions == class_id
        )

        target = (
            targets == class_id
        )

        intersection = (
            pred & target
        ).sum().float()

        denominator = (
            pred.sum()
            + target.sum()
        ).float()

        if denominator == 0:
            continue

        score = (
            2 * intersection
        ) / (
            denominator + 1e-6
        )

        scores.append(score)

    if not scores:
        return 0.0

    return torch.stack(scores).mean().item()


# ============================================================
# TRAINING
# ============================================================

best_val_loss = float("inf")


for epoch in range(
    1,
    EPOCHS + 1
):

    # --------------------------------------------------------
    # TRAIN
    # --------------------------------------------------------

    model.train()

    train_loss = 0.0

    progress = tqdm(
        train_loader,
        desc=f"Epoch {epoch}/{EPOCHS}"
    )

    for images, masks in progress:

        images = images.to(
            DEVICE
        )

        masks = masks.to(
            DEVICE
        )

        optimizer.zero_grad()

        outputs = model(
            images
        )

        loss = combined_loss(
            outputs,
            masks
        )

        loss.backward()

        optimizer.step()

        train_loss += loss.item()

        progress.set_postfix(
            loss=f"{loss.item():.4f}"
        )


    train_loss /= len(
        train_loader
    )


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    model.eval()

    val_loss = 0.0
    val_dice = 0.0

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

            loss = combined_loss(
                outputs,
                masks
            )

            val_loss += loss.item()

            val_dice += mean_dice(
                outputs,
                masks
            )


    val_loss /= len(
        val_loader
    )

    val_dice /= len(
        val_loader
    )


    print()
    print(
        f"Epoch {epoch}/{EPOCHS}"
    )

    print(
        f"Train Loss : {train_loss:.4f}"
    )

    print(
        f"Val Loss   : {val_loss:.4f}"
    )

    print(
        f"Val Dice   : {val_dice:.4f}"
    )


    # --------------------------------------------------------
    # SAVE BEST MODEL
    # --------------------------------------------------------

    if val_loss < best_val_loss:

        best_val_loss = val_loss

        torch.save(
            {
                "model_state_dict":
                    model.state_dict(),

                "num_classes":
                    NUM_CLASSES,

                "image_size":
                    IMAGE_SIZE,

                "best_val_loss":
                    best_val_loss,

            },
            MODEL_PATH
        )

        print(
            f"✓ Best model saved:"
            f"\n  {MODEL_PATH}"
        )

    print()


# ============================================================
# COMPLETE
# ============================================================

print("=" * 70)
print("TRAINING COMPLETE")
print("=" * 70)

print(
    f"Best validation loss: "
    f"{best_val_loss:.4f}"
)

print(
    f"Model saved at:\n{MODEL_PATH}"
)

print()