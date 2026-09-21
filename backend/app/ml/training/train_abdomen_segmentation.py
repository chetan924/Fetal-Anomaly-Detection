from pathlib import Path
import random
import json

import numpy as np
from PIL import Image

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split
from torchvision import transforms


# ============================================================
# CONFIG
# ============================================================

IMAGE_DIR = Path(r"D:\Fetal_Abdomen_Processed\images")
MASK_DIR = Path(r"D:\Fetal_Abdomen_Processed\masks")

OUTPUT_DIR = Path(
    r"D:\Fetal Anomaly Detection\backend\models\abdomen_segmentation"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

IMG_SIZE = 512
NUM_CLASSES = 5

BATCH_SIZE = 4
EPOCHS = 30

LEARNING_RATE = 1e-4

VAL_SPLIT = 0.20

SEED = 42

NUM_WORKERS = 0


# ============================================================
# REPRODUCIBILITY
# ============================================================

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("=" * 70)
print("FETAL ABDOMINAL STRUCTURE SEGMENTATION TRAINING")
print("=" * 70)

print(f"Device      : {DEVICE}")
print(f"Image size  : {IMG_SIZE}")
print(f"Classes     : {NUM_CLASSES}")
print(f"Batch size  : {BATCH_SIZE}")
print(f"Epochs      : {EPOCHS}")
print()


# ============================================================
# DATASET
# ============================================================

class AbdomenDataset(Dataset):

    def __init__(self, image_dir, mask_dir):

        self.image_dir = Path(image_dir)
        self.mask_dir = Path(mask_dir)

        self.images = sorted(
            self.image_dir.glob("*.png")
        )

        valid_pairs = []

        for image_path in self.images:

            mask_path = (
                self.mask_dir /
                image_path.name
            )

            if mask_path.exists():

                valid_pairs.append(
                    (
                        image_path,
                        mask_path
                    )
                )

        self.samples = valid_pairs

        if len(self.samples) == 0:

            raise RuntimeError(
                "No image/mask pairs found."
            )

        print(
            f"Dataset samples: {len(self.samples)}"
        )


    def __len__(self):

        return len(self.samples)


    def __getitem__(self, index):

        image_path, mask_path = self.samples[index]

        # ----------------------------------------------------
        # IMAGE
        # ----------------------------------------------------

        image = Image.open(
            image_path
        ).convert("RGB")

        image = image.resize(
            (IMG_SIZE, IMG_SIZE),
            Image.Resampling.BILINEAR
        )

        image = np.asarray(
            image,
            dtype=np.float32
        ) / 255.0

        image = torch.from_numpy(
            image
        ).permute(2, 0, 1)


        # ----------------------------------------------------
        # MASK
        # ----------------------------------------------------

        mask = Image.open(
            mask_path
        ).convert("L")

        mask = mask.resize(
            (IMG_SIZE, IMG_SIZE),
            Image.Resampling.NEAREST
        )

        mask = np.asarray(
            mask,
            dtype=np.int64
        )

        mask = torch.from_numpy(
            mask
        ).long()


        return image, mask


# ============================================================
# DOUBLE CONV
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

            nn.BatchNorm2d(
                out_channels
            ),

            nn.ReLU(
                inplace=True
            )
        )


    def forward(self, x):

        return self.block(x)


# ============================================================
# U-NET
# ============================================================

class UNet(nn.Module):

    def __init__(
        self,
        num_classes=5
    ):

        super().__init__()


        # ----------------------------------------------------
        # ENCODER
        # ----------------------------------------------------

        self.enc1 = DoubleConv(
            3,
            32
        )

        self.enc2 = DoubleConv(
            32,
            64
        )

        self.enc3 = DoubleConv(
            64,
            128
        )

        self.enc4 = DoubleConv(
            128,
            256
        )


        # ----------------------------------------------------
        # BOTTLENECK
        # ----------------------------------------------------

        self.bottleneck = DoubleConv(
            256,
            512
        )


        # ----------------------------------------------------
        # POOL
        # ----------------------------------------------------

        self.pool = nn.MaxPool2d(
            2
        )


        # ----------------------------------------------------
        # DECODER
        # ----------------------------------------------------

        self.up4 = nn.ConvTranspose2d(
            512,
            256,
            kernel_size=2,
            stride=2
        )

        self.dec4 = DoubleConv(
            512,
            256
        )


        self.up3 = nn.ConvTranspose2d(
            256,
            128,
            kernel_size=2,
            stride=2
        )

        self.dec3 = DoubleConv(
            256,
            128
        )


        self.up2 = nn.ConvTranspose2d(
            128,
            64,
            kernel_size=2,
            stride=2
        )

        self.dec2 = DoubleConv(
            128,
            64
        )


        self.up1 = nn.ConvTranspose2d(
            64,
            32,
            kernel_size=2,
            stride=2
        )

        self.dec1 = DoubleConv(
            64,
            32
        )


        # ----------------------------------------------------
        # OUTPUT
        # ----------------------------------------------------

        self.output = nn.Conv2d(
            32,
            num_classes,
            kernel_size=1
        )


    def forward(self, x):

        # Encoder

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


        # Bottleneck

        b = self.bottleneck(
            self.pool(e4)
        )


        # Decoder

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


        return self.output(d1)


# ============================================================
# DICE SCORE
# ============================================================

def dice_score(
    predictions,
    targets,
    num_classes
):

    predictions = torch.argmax(
        predictions,
        dim=1
    )

    scores = []

    for class_id in range(
        1,
        num_classes
    ):

        pred = (
            predictions == class_id
        ).float()

        target = (
            targets == class_id
        ).float()


        intersection = (
            pred * target
        ).sum()


        denominator = (
            pred.sum()
            +
            target.sum()
        )


        if denominator == 0:

            continue


        dice = (
            2.0 * intersection + 1e-6
        ) / (
            denominator + 1e-6
        )

        scores.append(
            dice.item()
        )


    if not scores:

        return 0.0


    return sum(scores) / len(scores)


# ============================================================
# IOU SCORE
# ============================================================

def iou_score(
    predictions,
    targets,
    num_classes
):

    predictions = torch.argmax(
        predictions,
        dim=1
    )

    scores = []

    for class_id in range(
        1,
        num_classes
    ):

        pred = (
            predictions == class_id
        ).float()

        target = (
            targets == class_id
        ).float()


        intersection = (
            pred * target
        ).sum()


        union = (
            pred.sum()
            +
            target.sum()
            -
            intersection
        )


        if union == 0:

            continue


        iou = (
            intersection + 1e-6
        ) / (
            union + 1e-6
        )

        scores.append(
            iou.item()
        )


    if not scores:

        return 0.0


    return sum(scores) / len(scores)


# ============================================================
# DATASET
# ============================================================

dataset = AbdomenDataset(
    IMAGE_DIR,
    MASK_DIR
)


# ============================================================
# TRAIN / VALIDATION SPLIT
# ============================================================

val_size = int(
    len(dataset) * VAL_SPLIT
)

train_size = (
    len(dataset) - val_size
)


generator = torch.Generator().manual_seed(
    SEED
)


train_dataset, val_dataset = random_split(
    dataset,
    [train_size, val_size],
    generator=generator
)


print(
    f"Training samples   : {len(train_dataset)}"
)

print(
    f"Validation samples : {len(val_dataset)}"
)

print()


# ============================================================
# DATALOADERS
# ============================================================

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=NUM_WORKERS,
    pin_memory=torch.cuda.is_available()
)


val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=NUM_WORKERS,
    pin_memory=torch.cuda.is_available()
)


# ============================================================
# MODEL
# ============================================================

model = UNet(
    num_classes=NUM_CLASSES
).to(DEVICE)


# ============================================================
# LOSS
# ============================================================

criterion = nn.CrossEntropyLoss()


# ============================================================
# OPTIMIZER
# ============================================================

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=1e-4
)


# ============================================================
# SCHEDULER
# ============================================================

scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode="max",
    factor=0.5,
    patience=3
)


# ============================================================
# TRAINING HISTORY
# ============================================================

history = {

    "train_loss": [],
    "val_loss": [],
    "val_dice": [],
    "val_iou": []
}


best_dice = 0.0


# ============================================================
# TRAINING LOOP
# ============================================================

for epoch in range(
    EPOCHS
):

    print()
    print(
        "=" * 70
    )

    print(
        f"Epoch {epoch + 1}/{EPOCHS}"
    )

    print(
        "=" * 70
    )


    # --------------------------------------------------------
    # TRAIN
    # --------------------------------------------------------

    model.train()

    train_loss = 0.0


    for images, masks in train_loader:

        images = images.to(
            DEVICE,
            non_blocking=True
        )

        masks = masks.to(
            DEVICE,
            non_blocking=True
        )


        optimizer.zero_grad(
            set_to_none=True
        )


        outputs = model(
            images
        )


        loss = criterion(
            outputs,
            masks
        )


        loss.backward()


        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0
        )


        optimizer.step()


        train_loss += (
            loss.item()
            *
            images.size(0)
        )


    train_loss /= len(
        train_loader.dataset
    )


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    model.eval()

    val_loss = 0.0

    total_dice = 0.0
    total_iou = 0.0

    batches = 0


    with torch.no_grad():

        for images, masks in val_loader:

            images = images.to(
                DEVICE,
                non_blocking=True
            )

            masks = masks.to(
                DEVICE,
                non_blocking=True
            )


            outputs = model(
                images
            )


            loss = criterion(
                outputs,
                masks
            )


            val_loss += (
                loss.item()
                *
                images.size(0)
            )


            total_dice += dice_score(
                outputs,
                masks,
                NUM_CLASSES
            )


            total_iou += iou_score(
                outputs,
                masks,
                NUM_CLASSES
            )


            batches += 1


    val_loss /= len(
        val_loader.dataset
    )


    val_dice = (
        total_dice / batches
    )


    val_iou = (
        total_iou / batches
    )


    scheduler.step(
        val_dice
    )


    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    history["train_loss"].append(
        train_loss
    )

    history["val_loss"].append(
        val_loss
    )

    history["val_dice"].append(
        val_dice
    )

    history["val_iou"].append(
        val_iou
    )


    # --------------------------------------------------------
    # PRINT
    # --------------------------------------------------------

    current_lr = optimizer.param_groups[
        0
    ]["lr"]


    print(
        f"Train Loss : {train_loss:.4f}"
    )

    print(
        f"Val Loss   : {val_loss:.4f}"
    )

    print(
        f"Val Dice   : {val_dice:.4f}"
    )

    print(
        f"Val IoU    : {val_iou:.4f}"
    )

    print(
        f"LR         : {current_lr:.6f}"
    )


    # --------------------------------------------------------
    # SAVE BEST MODEL
    # --------------------------------------------------------

    if val_dice > best_dice:

        best_dice = val_dice


        checkpoint = {

            "epoch": epoch + 1,

            "model_state_dict":
                model.state_dict(),

            "optimizer_state_dict":
                optimizer.state_dict(),

            "val_dice":
                val_dice,

            "val_iou":
                val_iou,

            "classes": [
                "background",
                "artery",
                "liver",
                "stomach",
                "vein"
            ],

            "image_size":
                IMG_SIZE
        }


        checkpoint_path = (
            OUTPUT_DIR /
            "best_abdomen_unet.pth"
        )


        torch.save(
            checkpoint,
            checkpoint_path
        )


        print()
        print(
            "🔥 BEST MODEL SAVED"
        )

        print(
            checkpoint_path
        )


# ============================================================
# SAVE FINAL MODEL
# ============================================================

final_path = (
    OUTPUT_DIR /
    "final_abdomen_unet.pth"
)


torch.save(
    model.state_dict(),
    final_path
)


# ============================================================
# SAVE HISTORY
# ============================================================

history_path = (
    OUTPUT_DIR /
    "training_history.json"
)


with open(
    history_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        history,
        f,
        indent=2
    )


# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 70)
print("TRAINING COMPLETE")
print("=" * 70)

print(
    f"Best Dice : {best_dice:.4f}"
)

print(
    f"Best model:\n{OUTPUT_DIR / 'best_abdomen_unet.pth'}"
)

print(
    f"Final model:\n{final_path}"
)

print(
    f"History:\n{history_path}"
)

print()
print("Classes:")

print("0 = Background")
print("1 = Artery")
print("2 = Liver")
print("3 = Stomach")
print("4 = Vein")

print()