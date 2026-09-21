from pathlib import Path
import copy
import random

import numpy as np
from PIL import Image, ImageEnhance
from tqdm import tqdm

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader


# ============================================================
# CONFIG
# ============================================================

IMAGE_DIR = Path(r"D:\Fetal_Lung_Dataset\images")
MASK_DIR = Path(r"D:\Fetal_Lung_Dataset\masks")

MODEL_DIR = Path(
    r"D:\Fetal Anomaly Detection\backend\app\ml\models"
)

MODEL_PATH = MODEL_DIR / "fetal_lung_unet_v2.pth"

IMAGE_SIZE = 256
BATCH_SIZE = 4
EPOCHS = 120
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 1e-4
NUM_WORKERS = 0

VAL_RATIO = 0.10
TEST_RATIO = 0.10

PATIENCE = 8
SEED = 42

THRESHOLD = 0.5

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# ============================================================
# REPRODUCIBILITY
# ============================================================

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


# ============================================================
# CONFIG PRINT
# ============================================================

print("=" * 70)
print("FETAL LUNG ULTRASOUND SEGMENTATION V2")
print("=" * 70)
print(f"Device       : {DEVICE}")
print(f"Image size   : {IMAGE_SIZE}")
print(f"Batch size   : {BATCH_SIZE}")
print(f"Epochs       : {EPOCHS}")
print(f"Learning rate: {LEARNING_RATE}")
print(f"Workers      : {NUM_WORKERS}")
print(f"Image dir    : {IMAGE_DIR}")
print(f"Mask dir     : {MASK_DIR}")
print(f"Model path   : {MODEL_PATH}")
print("=" * 70)


# ============================================================
# PATH VALIDATION
# ============================================================

if not IMAGE_DIR.exists():
    raise FileNotFoundError(
        f"Image directory not found:\n{IMAGE_DIR}"
    )

if not MASK_DIR.exists():
    raise FileNotFoundError(
        f"Mask directory not found:\n{MASK_DIR}"
    )


# ============================================================
# IMAGE / MASK PAIRS
# ============================================================

image_files = sorted(
    IMAGE_DIR.glob("*.png")
)

mask_lookup = {
    p.stem: p
    for p in MASK_DIR.glob("*.png")
}

pairs = []

for image_path in image_files:

    mask_path = mask_lookup.get(
        image_path.stem
    )

    if mask_path is not None:
        pairs.append(
            (image_path, mask_path)
        )


if not pairs:
    raise RuntimeError(
        "No matching image/mask pairs found."
    )


print(f"\nMatched pairs: {len(pairs)}")


# ============================================================
# SHUFFLE + SPLIT
# ============================================================

random.Random(SEED).shuffle(pairs)

total = len(pairs)

test_count = max(
    1,
    int(round(total * TEST_RATIO))
)

val_count = max(
    1,
    int(round(total * VAL_RATIO))
)

train_count = (
    total
    - val_count
    - test_count
)

if train_count <= 0:
    raise RuntimeError(
        "Dataset too small for train/val/test split."
    )

train_pairs = pairs[:train_count]

val_pairs = pairs[
    train_count:
    train_count + val_count
]

test_pairs = pairs[
    train_count + val_count:
]


print("\nDATASET SPLIT")
print("-" * 40)
print(f"Train : {len(train_pairs)}")
print(f"Val   : {len(val_pairs)}")
print(f"Test  : {len(test_pairs)}")


# ============================================================
# DATASET
# ============================================================

class LungDataset(Dataset):

    def __init__(
        self,
        samples,
        training=False
    ):
        self.samples = samples
        self.training = training

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

        # ----------------------------------------------------
        # Resize
        # ----------------------------------------------------

        image = image.resize(
            (IMAGE_SIZE, IMAGE_SIZE),
            Image.Resampling.BILINEAR
        )

        mask = mask.resize(
            (IMAGE_SIZE, IMAGE_SIZE),
            Image.Resampling.NEAREST
        )

        # ----------------------------------------------------
        # SAFE AUGMENTATION
        #
        # Horizontal flip is reasonable.
        # Vertical flip is intentionally NOT used because
        # anatomical orientation should not be inverted.
        # ----------------------------------------------------

        if self.training:

            if random.random() < 0.5:

                image = image.transpose(
                    Image.Transpose.FLIP_LEFT_RIGHT
                )

                mask = mask.transpose(
                    Image.Transpose.FLIP_LEFT_RIGHT
                )

            # Mild brightness variation
            if random.random() < 0.30:

                factor = random.uniform(
                    0.90,
                    1.10
                )

                image = ImageEnhance.Brightness(
                    image
                ).enhance(factor)

            # Mild contrast variation
            if random.random() < 0.30:

                factor = random.uniform(
                    0.90,
                    1.10
                )

                image = ImageEnhance.Contrast(
                    image
                ).enhance(factor)

        # ----------------------------------------------------
        # NUMPY
        # ----------------------------------------------------

        image_np = np.asarray(
            image,
            dtype=np.float32
        ) / 255.0

        mask_np = np.asarray(
            mask,
            dtype=np.uint8
        )

        mask_np = (
            mask_np > 0
        ).astype(np.float32)

        # ----------------------------------------------------
        # CHW
        # ----------------------------------------------------

        image_np = np.transpose(
            image_np,
            (2, 0, 1)
        )

        image_tensor = torch.from_numpy(
            image_np
        )

        # ----------------------------------------------------
        # ImageNet-style normalization
        # ----------------------------------------------------

        mean = torch.tensor(
            [0.485, 0.456, 0.406],
            dtype=torch.float32
        ).view(3, 1, 1)

        std = torch.tensor(
            [0.229, 0.224, 0.225],
            dtype=torch.float32
        ).view(3, 1, 1)

        image_tensor = (
            image_tensor - mean
        ) / std

        mask_tensor = torch.from_numpy(
            mask_np
        ).unsqueeze(0)

        return (
            image_tensor,
            mask_tensor
        )


# ============================================================
# DATA LOADERS
# ============================================================

train_dataset = LungDataset(
    train_pairs,
    training=True
)

val_dataset = LungDataset(
    val_pairs,
    training=False
)

test_dataset = LungDataset(
    test_pairs,
    training=False
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

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=NUM_WORKERS,
    pin_memory=False
)


# ============================================================
# CONV BLOCK
# ============================================================

class ConvBlock(nn.Module):

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

            nn.GroupNorm(
                num_groups=8,
                num_channels=out_channels
            ),

            nn.ReLU(
                inplace=True
            ),

            nn.Conv2d(
                out_channels,
                out_channels,
                kernel_size=3,
                padding=1,
                bias=False
            ),

            nn.GroupNorm(
                num_groups=8,
                num_channels=out_channels
            ),

            nn.ReLU(
                inplace=True
            )
        )

    def forward(self, x):
        return self.block(x)


# ============================================================
# U-NET V2
# ============================================================

class UNetV2(nn.Module):

    def __init__(self):

        super().__init__()

        self.enc1 = ConvBlock(
            3,
            32
        )

        self.enc2 = ConvBlock(
            32,
            64
        )

        self.enc3 = ConvBlock(
            64,
            128
        )

        self.enc4 = ConvBlock(
            128,
            256
        )

        self.pool = nn.MaxPool2d(
            2
        )

        self.bottleneck = ConvBlock(
            256,
            384
        )

        self.up4 = nn.ConvTranspose2d(
            384,
            256,
            kernel_size=2,
            stride=2
        )

        self.dec4 = ConvBlock(
            512,
            256
        )

        self.up3 = nn.ConvTranspose2d(
            256,
            128,
            kernel_size=2,
            stride=2
        )

        self.dec3 = ConvBlock(
            256,
            128
        )

        self.up2 = nn.ConvTranspose2d(
            128,
            64,
            kernel_size=2,
            stride=2
        )

        self.dec2 = ConvBlock(
            128,
            64
        )

        self.up1 = nn.ConvTranspose2d(
            64,
            32,
            kernel_size=2,
            stride=2
        )

        self.dec1 = ConvBlock(
            64,
            32
        )

        self.head = nn.Conv2d(
            32,
            1,
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

        e4 = self.enc4(
            self.pool(e3)
        )

        b = self.bottleneck(
            self.pool(e4)
        )

        d4 = self.up4(b)

        d4 = torch.cat(
            [d4, e4],
            dim=1
        )

        d4 = self.dec4(d4)

        d3 = self.up3(d4)

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

        return self.head(d1)


# ============================================================
# SOFT DICE
# ============================================================

def soft_dice(
    logits,
    targets,
    eps=1e-6
):

    probs = torch.sigmoid(
        logits
    )

    probs = probs.flatten(
        start_dim=1
    )

    targets = targets.flatten(
        start_dim=1
    )

    intersection = (
        probs * targets
    ).sum(dim=1)

    denominator = (
        probs.sum(dim=1)
        + targets.sum(dim=1)
    )

    dice = (
        2.0 * intersection + eps
    ) / (
        denominator + eps
    )

    return dice.mean()


# ============================================================
# HARD DICE
# ============================================================

def hard_dice(
    logits,
    targets,
    threshold=0.5,
    eps=1e-6
):

    probs = torch.sigmoid(
        logits
    )

    preds = (
        probs >= threshold
    ).float()

    preds = preds.flatten(
        start_dim=1
    )

    targets = targets.flatten(
        start_dim=1
    )

    intersection = (
        preds * targets
    ).sum(dim=1)

    denominator = (
        preds.sum(dim=1)
        + targets.sum(dim=1)
    )

    dice = (
        2.0 * intersection + eps
    ) / (
        denominator + eps
    )

    return dice.mean()


# ============================================================
# HARD IOU
# ============================================================

def hard_iou(
    logits,
    targets,
    threshold=0.5,
    eps=1e-6
):

    probs = torch.sigmoid(
        logits
    )

    preds = (
        probs >= threshold
    ).float()

    intersection = (
        preds * targets
    ).sum(dim=(1, 2, 3))

    pred_area = preds.sum(
        dim=(1, 2, 3)
    )

    target_area = targets.sum(
        dim=(1, 2, 3)
    )

    union = (
        pred_area
        + target_area
        - intersection
    )

    iou = (
        intersection + eps
    ) / (
        union + eps
    )

    return iou.mean()


# ============================================================
# LOSS
# ============================================================

bce_fn = nn.BCEWithLogitsLoss()


def segmentation_loss(
    logits,
    targets
):

    bce = bce_fn(
        logits,
        targets
    )

    dice = soft_dice(
        logits,
        targets
    )

    return (
        0.4 * bce
        + 0.6 * (1.0 - dice)
    )


# ============================================================
# MODEL / OPTIMIZER
# ============================================================

model = UNetV2().to(
    DEVICE
)

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY
)

scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode="max",
    factor=0.5,
    patience=3
)


# ============================================================
# EVALUATION
# ============================================================

@torch.no_grad()
def evaluate(loader):

    model.eval()

    total_loss = 0.0
    total_soft_dice = 0.0
    total_hard_dice = 0.0
    total_iou = 0.0
    batches = 0

    for images, masks in loader:

        images = images.to(
            DEVICE
        )

        masks = masks.to(
            DEVICE
        )

        logits = model(
            images
        )

        loss = segmentation_loss(
            logits,
            masks
        )

        soft = soft_dice(
            logits,
            masks
        )

        hard = hard_dice(
            logits,
            masks,
            THRESHOLD
        )

        iou = hard_iou(
            logits,
            masks,
            THRESHOLD
        )

        total_loss += loss.item()
        total_soft_dice += soft.item()
        total_hard_dice += hard.item()
        total_iou += iou.item()

        batches += 1

    if batches == 0:
        return (
            0.0,
            0.0,
            0.0,
            0.0
        )

    return (
        total_loss / batches,
        total_soft_dice / batches,
        total_hard_dice / batches,
        total_iou / batches
    )


# ============================================================
# TRAINING
# ============================================================

best_val_dice = -1.0
best_epoch = 0
best_state = None
no_improvement = 0

print("\n")
print("=" * 70)
print("STARTING V2 LUNG TRAINING")
print("=" * 70)

for epoch in range(
    1,
    EPOCHS + 1
):

    model.train()

    train_loss_total = 0.0
    train_soft_total = 0.0
    train_batches = 0

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

        optimizer.zero_grad(
            set_to_none=True
        )

        logits = model(
            images
        )

        loss = segmentation_loss(
            logits,
            masks
        )

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=3.0
        )

        optimizer.step()

        train_loss_total += (
            loss.item()
        )

        train_soft_total += (
            soft_dice(
                logits.detach(),
                masks
            ).item()
        )

        train_batches += 1

        progress.set_postfix(
            loss=f"{loss.item():.4f}"
        )

    train_loss = (
        train_loss_total
        / max(train_batches, 1)
    )

    train_soft = (
        train_soft_total
        / max(train_batches, 1)
    )

    (
        val_loss,
        val_soft_dice,
        val_hard_dice,
        val_iou
    ) = evaluate(
        val_loader
    )

    scheduler.step(
        val_hard_dice
    )

    current_lr = (
        optimizer.param_groups[0]["lr"]
    )

    print("\n" + "=" * 70)
    print(
        f"Epoch {epoch}/{EPOCHS}"
    )
    print(
        f"Train Loss      : {train_loss:.4f}"
    )
    print(
        f"Train Soft Dice : {train_soft:.4f}"
    )
    print(
        f"Val Loss        : {val_loss:.4f}"
    )
    print(
        f"Val Soft Dice   : {val_soft_dice:.4f}"
    )
    print(
        f"Val Hard Dice   : {val_hard_dice:.4f}"
    )
    print(
        f"Val IoU         : {val_iou:.4f}"
    )
    print(
        f"LR              : {current_lr:.7f}"
    )

    if val_hard_dice > best_val_dice:

        best_val_dice = (
            val_hard_dice
        )

        best_epoch = epoch

        best_state = copy.deepcopy(
            model.state_dict()
        )

        no_improvement = 0

        print(
            "✓ New best model"
        )

    else:

        no_improvement += 1

        print(
            f"No improvement: "
            f"{no_improvement}/{PATIENCE}"
        )

        if no_improvement >= PATIENCE:

            print(
                "\nEarly stopping triggered."
            )

            break


# ============================================================
# BEST MODEL RESTORE
# ============================================================

if best_state is None:

    raise RuntimeError(
        "Training did not produce a valid checkpoint."
    )

model.load_state_dict(
    best_state
)


# ============================================================
# FINAL TEST
# ============================================================

print("\n")
print("=" * 70)
print("FINAL V2 LUNG TEST EVALUATION")
print("=" * 70)

(
    test_loss,
    test_soft_dice,
    test_hard_dice,
    test_iou
) = evaluate(
    test_loader
)

print(
    f"Test Loss        : {test_loss:.4f}"
)

print(
    f"Test Soft Dice   : {test_soft_dice:.4f}"
)

print(
    f"Test Hard Dice   : {test_hard_dice:.4f}"
)

print(
    f"Test IoU         : {test_iou:.4f}"
)


# ============================================================
# SAVE CHECKPOINT
# ============================================================

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

checkpoint = {
    "model_state_dict": model.state_dict(),
    "task": "fetal_lung_segmentation",
    "architecture": "UNetV2",
    "image_size": IMAGE_SIZE,
    "threshold": THRESHOLD,
    "best_epoch": best_epoch,
    "best_val_dice": best_val_dice,
    "test_loss": test_loss,
    "test_soft_dice": test_soft_dice,
    "test_hard_dice": test_hard_dice,
    "test_iou": test_iou,
    "train_samples": len(train_pairs),
    "val_samples": len(val_pairs),
    "test_samples": len(test_pairs),
}

torch.save(
    checkpoint,
    MODEL_PATH
)


# ============================================================
# SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("FETAL LUNG TRAINING V2 COMPLETE")
print("=" * 70)

print(
    f"Best epoch       : {best_epoch}"
)

print(
    f"Best Val Dice    : {best_val_dice:.4f}"
)

print(
    f"Test Hard Dice   : {test_hard_dice:.4f}"
)

print(
    f"Test IoU         : {test_iou:.4f}"
)

print(
    f"Model saved at:\n{MODEL_PATH}"
)

print("=" * 70)