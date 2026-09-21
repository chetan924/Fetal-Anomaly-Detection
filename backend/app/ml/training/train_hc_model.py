# ============================================================
# HC18 HEAD CIRCUMFERENCE MODEL TRAINING
# 100 EPOCHS + BEST CHECKPOINT + EARLY STOPPING
# ============================================================

from pathlib import Path
import random
import copy

import numpy as np
import pandas as pd
from PIL import Image

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(
    r"D:\Fetal Anomaly Detection"
)

PREPARED_ROOT = Path(
    r"C:\Users\Lenovo\Downloads\HC18_extract\hc_prepared"
)

MODEL_DIR = (
    PROJECT_ROOT
    / "backend"
    / "app"
    / "ml"
    / "models"
)

MODEL_PATH = (
    MODEL_DIR
    / "hc18_head_circumference.pt"
)


# Training configuration

EPOCHS = 100

BATCH_SIZE = 8

LEARNING_RATE = 5e-5

WEIGHT_DECAY = 1e-4

PATIENCE = 12

NUM_WORKERS = 0

IMAGE_SIZE = 224

RANDOM_SEED = 42


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


# ============================================================
# RANDOM SEED
# ============================================================

def set_seed(seed=42):

    random.seed(seed)

    np.random.seed(seed)

    torch.manual_seed(seed)

    if torch.cuda.is_available():

        torch.cuda.manual_seed_all(seed)


set_seed(RANDOM_SEED)


# ============================================================
# DIRECTORIES
# ============================================================

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# PRINT CONFIG
# ============================================================

print()
print("=" * 65)
print("HC18 HEAD CIRCUMFERENCE TRAINING")
print("=" * 65)

print(
    f"Device       : {DEVICE}"
)

print(
    f"Epochs       : {EPOCHS}"
)

print(
    f"Batch size   : {BATCH_SIZE}"
)

print(
    f"Learning rate: {LEARNING_RATE}"
)

print(
    f"Patience     : {PATIENCE}"
)

print(
    f"Image size   : {IMAGE_SIZE}"
)

print(
    f"Model path   : {MODEL_PATH}"
)

print("=" * 65)


# ============================================================
# FIND IMAGE PATH
# ============================================================

def resolve_image_path(
    image_name,
    split_dir
):

    image_name = str(image_name)

    candidates = [

        split_dir / image_name,

        split_dir / "images" / image_name,

        split_dir / "image" / image_name,

    ]

    for candidate in candidates:

        if candidate.exists():

            return candidate


    matches = list(
        split_dir.rglob(image_name)
    )

    if matches:

        return matches[0]


    return None


# ============================================================
# DATASET
# ============================================================

class HC18Dataset(Dataset):

    def __init__(
        self,
        metadata_path,
        split,
        transform=None
    ):

        self.metadata_path = Path(
            metadata_path
        )

        self.split = split

        self.transform = transform

        if not self.metadata_path.exists():

            raise FileNotFoundError(
                f"Metadata not found:\n"
                f"{self.metadata_path}"
            )


        # ----------------------------------------------------
        # READ CSV
        # ----------------------------------------------------

        self.df = pd.read_csv(
            self.metadata_path
        )


        # ----------------------------------------------------
        # NORMALIZE COLUMN NAMES
        # ----------------------------------------------------

        self.df.columns = [

            str(column).strip()

            for column in self.df.columns

        ]


        # ----------------------------------------------------
        # FIND FILENAME COLUMN
        # ----------------------------------------------------

        filename_candidates = [

            "filename",

            "file_name",

            "image",

            "image_name",

            "path",

        ]


        self.filename_column = None


        for column in filename_candidates:

            if column in self.df.columns:

                self.filename_column = column

                break


        if self.filename_column is None:

            raise ValueError(
                "Could not find image filename "
                "column in metadata.\n"
                f"Available columns: "
                f"{list(self.df.columns)}"
            )


        # ----------------------------------------------------
        # FIND HC COLUMN
        # ----------------------------------------------------

        hc_candidates = [

            "head circumference (mm)",

            "head circumference",

            "head_circumference",

            "head_circumference_mm",

            "HC",

            "hc",

            "target",

            "label",

        ]


        self.hc_column = None


        for column in hc_candidates:

            if column in self.df.columns:

                self.hc_column = column

                break


        if self.hc_column is None:

            raise ValueError(
                "Could not find head circumference "
                "column in metadata.\n"
                f"Available columns: "
                f"{list(self.df.columns)}"
            )


        # ----------------------------------------------------
        # SPLIT DIRECTORY
        # ----------------------------------------------------

        self.split_dir = (
            self.metadata_path.parent
        )


        # ----------------------------------------------------
        # VALID RECORDS
        # ----------------------------------------------------

        valid_records = []


        for _, row in self.df.iterrows():

            filename = str(
                row[self.filename_column]
            ).strip()


            try:

                target = float(
                    row[self.hc_column]
                )

            except (
                ValueError,
                TypeError
            ):

                continue


            image_path = resolve_image_path(
                filename,
                self.split_dir
            )


            if image_path is None:

                continue


            valid_records.append(
                (
                    image_path,
                    target
                )
            )


        self.records = valid_records


        print(
            f"{split.capitalize()} dataset:"
            f" {len(self.records)} samples"
        )


        if len(self.records) == 0:

            raise RuntimeError(
                f"No valid samples found for "
                f"{split} dataset."
            )


    # --------------------------------------------------------
    # LENGTH
    # --------------------------------------------------------

    def __len__(self):

        return len(self.records)


    # --------------------------------------------------------
    # GET ITEM
    # --------------------------------------------------------

    def __getitem__(self, index):

        image_path, target = (
            self.records[index]
        )


        # ----------------------------------------------------
        # LOAD IMAGE
        # ----------------------------------------------------

        image = Image.open(
            image_path
        ).convert("RGB")


        # ----------------------------------------------------
        # TRANSFORM
        # ----------------------------------------------------

        if self.transform is not None:

            image = self.transform(
                image
            )


        target = torch.tensor(
            target,
            dtype=torch.float32
        )


        return image, target


# ============================================================
# TRANSFORMS
# ============================================================

train_transform = transforms.Compose([

    transforms.Resize(
        (IMAGE_SIZE, IMAGE_SIZE)
    ),

    transforms.RandomHorizontalFlip(
        p=0.5
    ),

    transforms.RandomRotation(
        degrees=5
    ),

    transforms.ColorJitter(
        brightness=0.15,
        contrast=0.15
    ),

    transforms.ToTensor(),

    transforms.Normalize(

        mean=[
            0.485,
            0.456,
            0.406
        ],

        std=[
            0.229,
            0.224,
            0.225
        ]

    ),

])


val_transform = transforms.Compose([

    transforms.Resize(
        (IMAGE_SIZE, IMAGE_SIZE)
    ),

    transforms.ToTensor(),

    transforms.Normalize(

        mean=[
            0.485,
            0.456,
            0.406
        ],

        std=[
            0.229,
            0.224,
            0.225
        ]

    ),

])


# ============================================================
# METADATA PATHS
# ============================================================

TRAIN_METADATA = (
    PREPARED_ROOT
    / "train"
    / "metadata.csv"
)


VAL_METADATA = (
    PREPARED_ROOT
    / "validation"
    / "metadata.csv"
)


# ============================================================
# LOAD DATASETS
# ============================================================

print()
print("=" * 65)
print("LOADING HC18 DATASET")
print("=" * 65)


train_dataset = HC18Dataset(

    metadata_path=TRAIN_METADATA,

    split="training",

    transform=train_transform

)


val_dataset = HC18Dataset(

    metadata_path=VAL_METADATA,

    split="validation",

    transform=val_transform

)


# ============================================================
# DATA LOADERS
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

print()
print("=" * 65)
print("BUILDING HC18 MODEL")
print("=" * 65)


model = models.resnet18(
    weights=None
)


# Replace classification head

model.fc = nn.Sequential(

    nn.Linear(
        model.fc.in_features,
        128
    ),

    nn.ReLU(),

    nn.Dropout(
        p=0.30
    ),

    nn.Linear(
        128,
        1
    )

)


model = model.to(
    DEVICE
)


print(
    "Architecture: ResNet18"
)

print(
    "Pretrained weights: False"
)


# ============================================================
# LOSS
# ============================================================

criterion = nn.SmoothL1Loss()


# ============================================================
# OPTIMIZER
# ============================================================

optimizer = torch.optim.AdamW(

    model.parameters(),

    lr=LEARNING_RATE,

    weight_decay=WEIGHT_DECAY

)


# ============================================================
# LR SCHEDULER
# ============================================================

scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(

    optimizer,

    mode="min",

    factor=0.5,

    patience=4,

    min_lr=1e-7

)


# ============================================================
# METRIC FUNCTION
# ============================================================

def calculate_metrics(
    predictions,
    targets
):

    predictions = np.asarray(
        predictions
    )

    targets = np.asarray(
        targets
    )


    mae = np.mean(
        np.abs(
            predictions - targets
        )
    )


    rmse = np.sqrt(
        np.mean(
            (
                predictions - targets
            ) ** 2
        )
    )


    return mae, rmse


# ============================================================
# TRAINING VARIABLES
# ============================================================

best_mae = float(
    "inf"
)

best_rmse = float(
    "inf"
)

best_epoch = 0

best_state = None

patience_counter = 0


# ============================================================
# TRAINING
# ============================================================

print()
print("=" * 65)
print("HC18 TRAINING")
print("=" * 65)


for epoch in range(
    1,
    EPOCHS + 1
):


    # ========================================================
    # TRAIN
    # ========================================================

    model.train()


    train_losses = []


    for images, targets in train_loader:

        images = images.to(
            DEVICE,
            non_blocking=True
        )

        targets = targets.to(
            DEVICE,
            non_blocking=True
        )


        # ----------------------------------------------------
        # ZERO GRADIENT
        # ----------------------------------------------------

        optimizer.zero_grad(
            set_to_none=True
        )


        # ----------------------------------------------------
        # FORWARD
        # ----------------------------------------------------

        outputs = model(
            images
        ).squeeze(
            1
        )


        # ----------------------------------------------------
        # LOSS
        # ----------------------------------------------------

        loss = criterion(
            outputs,
            targets
        )


        # ----------------------------------------------------
        # BACKPROP
        # ----------------------------------------------------

        loss.backward()


        # ----------------------------------------------------
        # GRADIENT CLIPPING
        # ----------------------------------------------------

        torch.nn.utils.clip_grad_norm_(

            model.parameters(),

            max_norm=1.0

        )


        # ----------------------------------------------------
        # OPTIMIZER STEP
        # ----------------------------------------------------

        optimizer.step()


        train_losses.append(
            loss.item()
        )


    # ========================================================
    # VALIDATION
    # ========================================================

    model.eval()


    val_losses = []

    predictions = []

    targets_all = []


    with torch.no_grad():

        for images, targets in val_loader:

            images = images.to(
                DEVICE,
                non_blocking=True
            )

            targets = targets.to(
                DEVICE,
                non_blocking=True
            )


            outputs = model(
                images
            ).squeeze(
                1
            )


            loss = criterion(
                outputs,
                targets
            )


            val_losses.append(
                loss.item()
            )


            predictions.extend(
                outputs.cpu().numpy()
            )


            targets_all.extend(
                targets.cpu().numpy()
            )


    # ========================================================
    # METRICS
    # ========================================================

    train_loss = float(
        np.mean(
            train_losses
        )
    )


    val_loss = float(
        np.mean(
            val_losses
        )
    )


    val_mae, val_rmse = (
        calculate_metrics(
            predictions,
            targets_all
        )
    )


    # ========================================================
    # LR SCHEDULER
    # ========================================================

    scheduler.step(
        val_mae
    )


    current_lr = optimizer.param_groups[0][
        "lr"
    ]


    # ========================================================
    # PRINT
    # ========================================================

    print()
    print(
        f"Epoch {epoch:02d}/{EPOCHS}"
    )

    print(
        f"Train Loss : "
        f"{train_loss:.4f}"
    )

    print(
        f"Val Loss   : "
        f"{val_loss:.4f}"
    )

    print(
        f"Val MAE    : "
        f"{val_mae:.2f} mm"
    )

    print(
        f"Val RMSE   : "
        f"{val_rmse:.2f} mm"
    )

    print(
        f"LR         : "
        f"{current_lr:.7f}"
    )


    # ========================================================
    # BEST MODEL
    # ========================================================

    if val_mae < best_mae:

        best_mae = val_mae

        best_rmse = val_rmse

        best_epoch = epoch

        patience_counter = 0


        # Save a CPU copy

        best_state = copy.deepcopy(

            model.state_dict()

        )


        # Save checkpoint

        checkpoint = {

            "model_state_dict":
                best_state,

            "best_val_mae":
                best_mae,

            "best_val_rmse":
                best_rmse,

            "best_epoch":
                best_epoch,

            "image_size":
                IMAGE_SIZE,

            "model_name":
                "resnet18",

            "task":
                "head_circumference_regression",

        }


        torch.save(

            checkpoint,

            MODEL_PATH

        )


        print(
            "✓ New best model saved"
        )


    else:

        patience_counter += 1


        print(
            f"No improvement: "
            f"{patience_counter}/{PATIENCE}"
        )


    # ========================================================
    # EARLY STOPPING
    # ========================================================

    if patience_counter >= PATIENCE:

        print()
        print(
            "⚠ Early stopping triggered."
        )

        print(
            f"No improvement for "
            f"{PATIENCE} epochs."
        )

        break


# ============================================================
# RESTORE BEST MODEL
# ============================================================

if best_state is not None:

    model.load_state_dict(
        best_state
    )


# ============================================================
# FINAL OUTPUT
# ============================================================

print()
print("=" * 65)
print("HC18 TRAINING COMPLETE")
print("=" * 65)

print(
    f"Best epoch: "
    f"{best_epoch}"
)

print(
    f"Best validation MAE: "
    f"{best_mae:.2f} mm"
)

print(
    f"Best validation RMSE: "
    f"{best_rmse:.2f} mm"
)

print(
    f"Model saved: "
    f"{MODEL_PATH}"
)

print(
    f"Model exists: "
    f"{MODEL_PATH.exists()}"
)

print("=" * 65)