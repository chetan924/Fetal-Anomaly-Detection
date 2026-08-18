from pathlib import Path
import copy
import time

import pandas as pd
import torch
from PIL import Image
from sklearn.metrics import classification_report
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms


# =========================================================
# CONFIGURATION
# =========================================================

DATASET_ROOT = Path(r"D:\Fetal_Dataset")
IMAGES_DIR = DATASET_ROOT / "Images"

TRAIN_CSV = (
    Path(__file__).resolve().parent
    / "splits"
    / "train.csv"
)

VAL_CSV = (
    Path(__file__).resolve().parent
    / "splits"
    / "val.csv"
)

MODEL_DIR = (
    Path(__file__).resolve().parents[1]
    / "models"
)

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

MODEL_PATH = MODEL_DIR / "fetal_plane_efficientnet_b0.pth"


# =========================================================
# TRAINING SETTINGS
# =========================================================

IMAGE_SIZE = 224
BATCH_SIZE = 16
EPOCHS = 10
LEARNING_RATE = 0.0003
NUM_WORKERS = 0


# =========================================================
# CLASSES
# =========================================================

CLASS_NAMES = [
    "Other",
    "Maternal cervix",
    "Fetal abdomen",
    "Fetal brain",
    "Fetal femur",
    "Fetal thorax",
]

CLASS_TO_IDX = {
    name: index
    for index, name in enumerate(CLASS_NAMES)
}

NUM_CLASSES = len(CLASS_NAMES)


# =========================================================
# DEVICE
# =========================================================

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("=" * 60)
print("FETAL ULTRASOUND PLANE CLASSIFIER")
print("=" * 60)

print(f"Device: {device}")

if torch.cuda.is_available():
    print(
        "GPU:",
        torch.cuda.get_device_name(0),
    )

    print(
        "VRAM:",
        round(
            torch.cuda.get_device_properties(0).total_memory
            / 1024**3,
            2,
        ),
        "GB",
    )


# =========================================================
# DATASET
# =========================================================

class FetalPlaneDataset(Dataset):

    def __init__(
        self,
        csv_path,
        transform=None,
    ):
        self.df = pd.read_csv(csv_path)

        self.transform = transform

    def __len__(self):
        return len(self.df)

    def __getitem__(self, index):

        row = self.df.iloc[index]

        image_name = row["Image_name"]

        image_path = (
            IMAGES_DIR
            / f"{image_name}.png"
        )

        image = Image.open(
            image_path
        ).convert("RGB")

        label_name = row["Plane"]

        label = CLASS_TO_IDX[
            label_name
        ]

        if self.transform:
            image = self.transform(
                image
            )

        return image, label


# =========================================================
# IMAGE TRANSFORMS
# =========================================================

train_transform = transforms.Compose(
    [
        transforms.Resize(
            (IMAGE_SIZE, IMAGE_SIZE)
        ),

        transforms.RandomHorizontalFlip(
            p=0.5
        ),

        transforms.RandomRotation(
            degrees=10
        ),

        transforms.ColorJitter(
            brightness=0.10,
            contrast=0.10,
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


val_transform = transforms.Compose(
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
# LOAD DATASETS
# =========================================================

print("\nLoading datasets...")

train_dataset = FetalPlaneDataset(
    TRAIN_CSV,
    transform=train_transform,
)

val_dataset = FetalPlaneDataset(
    VAL_CSV,
    transform=val_transform,
)

print(
    f"Train images: {len(train_dataset)}"
)

print(
    f"Validation images: {len(val_dataset)}"
)


# =========================================================
# DATA LOADERS
# =========================================================

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=NUM_WORKERS,
    pin_memory=torch.cuda.is_available(),
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=NUM_WORKERS,
    pin_memory=torch.cuda.is_available(),
)


# =========================================================
# CLASS WEIGHTS
# =========================================================

train_counts = (
    train_dataset.df["Plane"]
    .value_counts()
)

total_samples = len(
    train_dataset
)

class_weights = []

for class_name in CLASS_NAMES:

    count = train_counts[
        class_name
    ]

    weight = (
        total_samples
        / (
            NUM_CLASSES
            * count
        )
    )

    class_weights.append(
        weight
    )


class_weights = torch.tensor(
    class_weights,
    dtype=torch.float32,
).to(device)


print("\nClass weights:")

for name, weight in zip(
    CLASS_NAMES,
    class_weights.tolist(),
):
    print(
        f"{name:20s}: "
        f"{weight:.4f}"
    )


# =========================================================
# MODEL
# =========================================================

print(
    "\nLoading EfficientNet-B0..."
)

weights = (
    models.EfficientNet_B0_Weights.DEFAULT
)

model = models.efficientnet_b0(
    weights=weights
)


# Replace classifier

input_features = (
    model.classifier[1].in_features
)

model.classifier[1] = nn.Linear(
    input_features,
    NUM_CLASSES,
)

model = model.to(device)


# =========================================================
# LOSS
# =========================================================

criterion = nn.CrossEntropyLoss(
    weight=class_weights
)


# =========================================================
# OPTIMIZER
# =========================================================

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=1e-4,
)


# =========================================================
# LR SCHEDULER
# =========================================================

scheduler = (
    torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="max",
        factor=0.5,
        patience=2,
    )
)


# =========================================================
# MIXED PRECISION
# =========================================================

use_amp = torch.cuda.is_available()

scaler = torch.amp.GradScaler(
    "cuda",
    enabled=use_amp,
)


# =========================================================
# TRAIN FUNCTION
# =========================================================

def train_one_epoch():

    model.train()

    running_loss = 0.0
    correct = 0
    total = 0

    for batch_index, (
        images,
        labels,
    ) in enumerate(
        train_loader,
        start=1,
    ):

        images = images.to(
            device,
            non_blocking=True,
        )

        labels = labels.to(
            device,
            non_blocking=True,
        )

        optimizer.zero_grad(
            set_to_none=True
        )

        with torch.amp.autocast(
            device_type=device.type,
            enabled=use_amp,
        ):

            outputs = model(
                images
            )

            loss = criterion(
                outputs,
                labels,
            )

        scaler.scale(
            loss
        ).backward()

        scaler.step(
            optimizer
        )

        scaler.update()

        running_loss += (
            loss.item()
            * images.size(0)
        )

        predictions = (
            outputs.argmax(
                dim=1
            )
        )

        correct += (
            predictions
            == labels
        ).sum().item()

        total += labels.size(0)

        if batch_index % 100 == 0:

            print(
                f"  Batch "
                f"{batch_index}/"
                f"{len(train_loader)}"
            )

    epoch_loss = (
        running_loss
        / total
    )

    epoch_accuracy = (
        100.0
        * correct
        / total
    )

    return (
        epoch_loss,
        epoch_accuracy,
    )


# =========================================================
# VALIDATION FUNCTION
# =========================================================

def validate():

    model.eval()

    running_loss = 0.0
    correct = 0
    total = 0

    all_predictions = []
    all_labels = []

    with torch.no_grad():

        for images, labels in val_loader:

            images = images.to(
                device,
                non_blocking=True,
            )

            labels = labels.to(
                device,
                non_blocking=True,
            )

            with torch.amp.autocast(
                device_type=device.type,
                enabled=use_amp,
            ):

                outputs = model(
                    images
                )

                loss = criterion(
                    outputs,
                    labels,
                )

            predictions = (
                outputs.argmax(
                    dim=1
                )
            )

            running_loss += (
                loss.item()
                * images.size(0)
            )

            correct += (
                predictions
                == labels
            ).sum().item()

            total += labels.size(0)

            all_predictions.extend(
                predictions.cpu().tolist()
            )

            all_labels.extend(
                labels.cpu().tolist()
            )

    epoch_loss = (
        running_loss
        / total
    )

    epoch_accuracy = (
        100.0
        * correct
        / total
    )

    return (
        epoch_loss,
        epoch_accuracy,
        all_labels,
        all_predictions,
    )


# =========================================================
# TRAINING LOOP
# =========================================================

best_accuracy = 0.0
best_model_state = None

print("\nStarting training...")
print("=" * 60)


for epoch in range(
    1,
    EPOCHS + 1,
):

    start_time = time.time()

    print(
        f"\nEpoch "
        f"{epoch}/{EPOCHS}"
    )

    train_loss, train_accuracy = (
        train_one_epoch()
    )

    (
        val_loss,
        val_accuracy,
        val_labels,
        val_predictions,
    ) = validate()

    scheduler.step(
        val_accuracy
    )

    elapsed = (
        time.time()
        - start_time
    )

    print(
        f"Train Loss: "
        f"{train_loss:.4f}"
    )

    print(
        f"Train Accuracy: "
        f"{train_accuracy:.2f}%"
    )

    print(
        f"Val Loss: "
        f"{val_loss:.4f}"
    )

    print(
        f"Val Accuracy: "
        f"{val_accuracy:.2f}%"
    )

    print(
        f"Time: "
        f"{elapsed / 60:.2f} min"
    )

    # Save best model

    if val_accuracy > best_accuracy:

        best_accuracy = (
            val_accuracy
        )

        best_model_state = (
            copy.deepcopy(
                model.state_dict()
            )
        )

        torch.save(
            {
                "model_state_dict":
                    best_model_state,

                "class_names":
                    CLASS_NAMES,

                "image_size":
                    IMAGE_SIZE,

                "best_val_accuracy":
                    best_accuracy,
            },
            MODEL_PATH,
        )

        print(
            "✓ New best model saved!"
        )


# =========================================================
# FINAL REPORT
# =========================================================

print("\n" + "=" * 60)
print("TRAINING COMPLETE")
print("=" * 60)

print(
    f"Best validation accuracy: "
    f"{best_accuracy:.2f}%"
)

print(
    f"Model saved to:\n"
    f"{MODEL_PATH}"
)


# Reload best model for report

if best_model_state is not None:

    model.load_state_dict(
        best_model_state
    )

    (
        _,
        _,
        final_labels,
        final_predictions,
    ) = validate()

    print(
        "\nClassification Report:\n"
    )

    print(
        classification_report(
            final_labels,
            final_predictions,
            target_names=CLASS_NAMES,
            digits=4,
            zero_division=0,
        )
    )