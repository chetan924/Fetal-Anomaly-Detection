from pathlib import Path
import time

import pandas as pd
import torch
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torchvision.models import (
    EfficientNet_B0_Weights,
    efficientnet_b0,
)


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TRAIN_CSV = BASE_DIR / "brain_anomaly_splits" / "train.csv"
VAL_CSV = BASE_DIR / "brain_anomaly_splits" / "val.csv"
TEST_CSV = BASE_DIR / "brain_anomaly_splits" / "test.csv"

MODEL_DIR = BASE_DIR.parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "brain_plane_efficientnet_b0.pth"

CLASSES = [
    "Trans-thalamic",
    "Trans-cerebellum",
    "Trans-ventricular",
]

CLASS_TO_IDX = {
    name: index
    for index, name in enumerate(CLASSES)
}

NUM_CLASSES = len(CLASSES)

IMAGE_SIZE = 224
BATCH_SIZE = 16
NUM_WORKERS = 0
EPOCHS = 10
LEARNING_RATE = 0.0003

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# ============================================================
# INFO
# ============================================================

print("=" * 65)
print("FETAL BRAIN PLANE CLASSIFIER")
print("=" * 65)

print("Device:", DEVICE)

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


# ============================================================
# TRANSFORMS
# ============================================================

train_transform = transforms.Compose(
    [
        transforms.Resize(
            (IMAGE_SIZE, IMAGE_SIZE)
        ),

        transforms.RandomRotation(8),

        transforms.RandomAffine(
            degrees=0,
            translate=(0.04, 0.04),
            scale=(0.95, 1.05),
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


eval_transform = transforms.Compose(
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


# ============================================================
# DATASET
# ============================================================

class BrainPlaneDataset(Dataset):

    def __init__(
        self,
        csv_path,
        transform,
    ):

        self.df = pd.read_csv(csv_path)

        self.transform = transform

    def __len__(self):

        return len(self.df)

    def __getitem__(
        self,
        index,
    ):

        row = self.df.iloc[index]

        image = Image.open(
            row["image_path"]
        ).convert("RGB")

        image = self.transform(
            image
        )

        label_name = row[
            "Brain_plane"
        ]

        label = CLASS_TO_IDX[
            label_name
        ]

        return image, label


# ============================================================
# DATASETS
# ============================================================

train_dataset = BrainPlaneDataset(
    TRAIN_CSV,
    train_transform,
)

val_dataset = BrainPlaneDataset(
    VAL_CSV,
    eval_transform,
)

test_dataset = BrainPlaneDataset(
    TEST_CSV,
    eval_transform,
)


print("\nDataset sizes:")

print(
    "Train:",
    len(train_dataset),
)

print(
    "Validation:",
    len(val_dataset),
)

print(
    "Test:",
    len(test_dataset),
)


# ============================================================
# CLASS WEIGHTS
# ============================================================

train_df = pd.read_csv(
    TRAIN_CSV
)

class_counts = (
    train_df["Brain_plane"]
    .value_counts()
)

total_samples = len(train_df)


class_weights = []

print("\nClass distribution / weights:")

for class_name in CLASSES:

    count = int(
        class_counts.get(
            class_name,
            0,
        )
    )

    if count == 0:

        raise RuntimeError(
            f"No training images for {class_name}"
        )

    weight = (
        total_samples
        / (NUM_CLASSES * count)
    )

    class_weights.append(
        weight
    )

    print(
        f"{class_name:20s}: "
        f"{count:4d} images | "
        f"weight {weight:.4f}"
    )


class_weights = torch.tensor(
    class_weights,
    dtype=torch.float32,
    device=DEVICE,
)


# ============================================================
# LOADERS
# ============================================================

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

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=NUM_WORKERS,
    pin_memory=torch.cuda.is_available(),
)


# ============================================================
# MODEL
# ============================================================

print("\nLoading EfficientNet-B0...")

weights = EfficientNet_B0_Weights.DEFAULT

model = efficientnet_b0(
    weights=weights
)


input_features = (
    model.classifier[1].in_features
)


model.classifier[1] = nn.Linear(
    input_features,
    NUM_CLASSES,
)


model = model.to(
    DEVICE
)


# ============================================================
# LOSS / OPTIMIZER
# ============================================================

criterion = nn.CrossEntropyLoss(
    weight=class_weights
)


optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=1e-4,
)


scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode="max",
    factor=0.5,
    patience=2,
)


# ============================================================
# TRAIN FUNCTION
# ============================================================

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
            DEVICE,
            non_blocking=True,
        )

        labels = labels.to(
            DEVICE,
            non_blocking=True,
        )

        optimizer.zero_grad(
            set_to_none=True
        )

        outputs = model(
            images
        )

        loss = criterion(
            outputs,
            labels
        )

        loss.backward()

        optimizer.step()


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


        if batch_index % 50 == 0:

            print(
                f"  Batch "
                f"{batch_index}/"
                f"{len(train_loader)}"
            )


    epoch_loss = (
        running_loss / total
    )

    epoch_accuracy = (
        correct / total
    )

    return (
        epoch_loss,
        epoch_accuracy,
    )


# ============================================================
# EVALUATION FUNCTION
# ============================================================

def evaluate(loader):

    model.eval()

    running_loss = 0.0

    correct = 0
    total = 0

    all_labels = []
    all_predictions = []


    with torch.inference_mode():

        for images, labels in loader:

            images = images.to(
                DEVICE,
                non_blocking=True,
            )

            labels = labels.to(
                DEVICE,
                non_blocking=True,
            )

            outputs = model(
                images
            )

            loss = criterion(
                outputs,
                labels
            )


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


            all_labels.extend(
                labels
                .cpu()
                .numpy()
                .tolist()
            )

            all_predictions.extend(
                predictions
                .cpu()
                .numpy()
                .tolist()
            )


    loss = (
        running_loss / total
    )

    accuracy = (
        correct / total
    )


    return (
        loss,
        accuracy,
        all_labels,
        all_predictions,
    )


# ============================================================
# TRAINING
# ============================================================

best_val_accuracy = 0.0


print("\nStarting training...")
print("=" * 65)


for epoch in range(
    1,
    EPOCHS + 1,
):

    print(
        f"\nEpoch {epoch}/{EPOCHS}"
    )

    start_time = time.time()


    train_loss, train_accuracy = (
        train_one_epoch()
    )


    (
        val_loss,
        val_accuracy,
        _,
        _,
    ) = evaluate(
        val_loader
    )


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
        f"{train_accuracy * 100:.2f}%"
    )

    print(
        f"Val Loss: "
        f"{val_loss:.4f}"
    )

    print(
        f"Val Accuracy: "
        f"{val_accuracy * 100:.2f}%"
    )

    print(
        f"Time: "
        f"{elapsed / 60:.2f} min"
    )


    if (
        val_accuracy
        > best_val_accuracy
    ):

        best_val_accuracy = (
            val_accuracy
        )


        torch.save(
            {
                "model_state_dict":
                    model.state_dict(),

                "classes":
                    CLASSES,

                "best_validation_accuracy":
                    best_val_accuracy
                    * 100,

                "image_size":
                    IMAGE_SIZE,

                "architecture":
                    "EfficientNet-B0",

                "task":
                    "fetal_brain_plane_classification",
            },
            MODEL_PATH,
        )


        print(
            "✓ New best model saved!"
        )


# ============================================================
# LOAD BEST MODEL
# ============================================================

print("\nLoading best model...")

checkpoint = torch.load(
    MODEL_PATH,
    map_location=DEVICE,
    weights_only=False,
)

model.load_state_dict(
    checkpoint[
        "model_state_dict"
    ]
)


# ============================================================
# FINAL TEST EVALUATION
# ============================================================

(
    test_loss,
    test_accuracy,
    test_labels,
    test_predictions,
) = evaluate(
    test_loader
)


print("\n" + "=" * 65)
print("TRAINING COMPLETE")
print("=" * 65)


print(
    "Best validation accuracy:",
    f"{best_val_accuracy * 100:.2f}%",
)


print(
    "Test accuracy:",
    f"{test_accuracy * 100:.2f}%",
)


print(
    "Test loss:",
    f"{test_loss:.4f}",
)


print(
    "\nModel saved to:"
)

print(
    MODEL_PATH
)


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

print("\nClassification Report:\n")


print(
    classification_report(
        test_labels,
        test_predictions,
        labels=list(
            range(NUM_CLASSES)
        ),
        target_names=CLASSES,
        digits=4,
        zero_division=0,
    )
)


# ============================================================
# CONFUSION MATRIX
# ============================================================

print(
    "Confusion Matrix:\n"
)


matrix = confusion_matrix(
    test_labels,
    test_predictions,
    labels=list(
        range(NUM_CLASSES)
    ),
)


print(matrix)