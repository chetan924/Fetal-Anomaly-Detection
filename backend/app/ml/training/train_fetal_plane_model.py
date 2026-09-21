# ================================================================
# FETAL PLANES BRAIN PLANE CLASSIFIER
# ================================================================
#
# Dataset:
# FETAL_PLANES_DB_data.csv
# Images/
#
# Classes:
#   Not A Brain
#   Trans-thalamic
#   Trans-cerebellum
#   Trans-ventricular
#   Other
#
# Patient-wise split
# ResNet18
# CPU optimized
# Early stopping
# Best model saved
# ================================================================

import os
import random
import shutil
from pathlib import Path
from collections import Counter

import pandas as pd
from PIL import Image

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

from torchvision import transforms
from torchvision.models import resnet18


# ================================================================
# CONFIGURATION
# ================================================================

SEED = 42

EPOCHS = 15
BATCH_SIZE = 16
LEARNING_RATE = 5e-5

IMAGE_SIZE = 160

PATIENCE = 12

NUM_WORKERS = 0

NUM_CLASSES = 5

CLASS_NAMES = [
    "Not A Brain",
    "Trans-thalamic",
    "Trans-cerebellum",
    "Trans-ventricular",
    "Other",
]

CLASS_TO_INDEX = {
    name: index
    for index, name in enumerate(CLASS_NAMES)
}

# ================================================================
# PATHS
# ================================================================

PROJECT_ROOT = Path(
    r"D:\Fetal Anomaly Detection"
)

MODEL_DIR = (
    PROJECT_ROOT
    / "backend"
    / "app"
    / "ml"
    / "models"
)

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

MODEL_PATH = (
    MODEL_DIR
    / "fetal_plane_classifier.pt"
)

# Dataset is now on D drive
DATASET_ROOT = Path(
    r"D:\FETAL_PLANES_extract"
)

CSV_PATH = (
    DATASET_ROOT
    / "FETAL_PLANES_DB_data.csv"
)

IMAGE_DIR = (
    DATASET_ROOT
    / "Images"
)

PREPARED_DIR = (
    DATASET_ROOT
    / "fetal_planes_prepared"
)


# ================================================================
# REPRODUCIBILITY
# ================================================================

random.seed(SEED)

torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


# ================================================================
# DEVICE
# ================================================================

DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


# ================================================================
# HEADER
# ================================================================

print()
print("=" * 70)
print("FETAL PLANES BRAIN PLANE CLASSIFIER")
print("=" * 70)

print(f"Device        : {DEVICE}")
print(f"Epochs        : {EPOCHS}")
print(f"Batch size    : {BATCH_SIZE}")
print(f"Learning rate : {LEARNING_RATE}")
print(f"Image size    : {IMAGE_SIZE}")
print(f"Patience      : {PATIENCE}")
print(f"Workers       : {NUM_WORKERS}")
print(f"Dataset       : {DATASET_ROOT}")
print(f"Model path    : {MODEL_PATH}")

print("=" * 70)


# ================================================================
# CHECK DATASET
# ================================================================

print()
print("=" * 70)
print("CHECKING FETAL PLANES DATASET")
print("=" * 70)

if not DATASET_ROOT.exists():

    raise FileNotFoundError(
        f"\nDataset folder not found:\n"
        f"{DATASET_ROOT}\n"
    )

if not CSV_PATH.exists():

    raise FileNotFoundError(
        f"\nCSV not found:\n"
        f"{CSV_PATH}\n"
    )

if not IMAGE_DIR.exists():

    raise FileNotFoundError(
        f"\nImages folder not found:\n"
        f"{IMAGE_DIR}\n"
    )

print("Dataset folder : OK")
print("CSV            : OK")
print("Images folder  : OK")


# ================================================================
# LOAD CSV
# ================================================================

print()
print("=" * 70)
print("LOADING DATASET")
print("=" * 70)


# HC18-style CSV issue is not present here.
# FETAL_PLANES CSV uses semicolon delimiter.

try:

    df = pd.read_csv(
        CSV_PATH,
        sep=";",
        engine="python",
    )

except Exception as exc:

    print(
        "Semicolon CSV read failed:",
        exc
    )

    df = pd.read_csv(
        CSV_PATH,
        engine="python",
    )


# Remove accidental whitespace
df.columns = [
    str(column).strip()
    for column in df.columns
]


print(
    "CSV rows:",
    len(df)
)

print(
    "Columns:",
    list(df.columns)
)


# ================================================================
# COLUMN VALIDATION
# ================================================================

required_columns = [
    "Image_name",
    "Patient_num",
    "Brain_plane",
]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:

    raise KeyError(
        "\nRequired columns missing: "
        + str(missing_columns)
        + "\nAvailable columns: "
        + str(list(df.columns))
    )


# ================================================================
# CLEAN DATA
# ================================================================

df = df.copy()

df["Image_name"] = (
    df["Image_name"]
    .astype(str)
    .str.strip()
)

df["Brain_plane"] = (
    df["Brain_plane"]
    .astype(str)
    .str.strip()
)

df["Patient_num"] = (
    pd.to_numeric(
        df["Patient_num"],
        errors="coerce",
    )
)

df = df.dropna(
    subset=[
        "Image_name",
        "Patient_num",
        "Brain_plane",
    ]
)

print(
    "Clean rows:",
    len(df)
)


# ================================================================
# CLASS VALIDATION
# ================================================================

print()
print("=" * 70)
print("CLASS DISTRIBUTION")
print("=" * 70)

class_counts = (
    df["Brain_plane"]
    .value_counts()
)

for class_name in CLASS_NAMES:

    print(
        f"{class_name:20s}: "
        f"{int(class_counts.get(class_name, 0))}"
    )


# ================================================================
# IMAGE INDEX
# ================================================================

print()
print("=" * 70)
print("INDEXING IMAGES")
print("=" * 70)

print(
    "Searching:",
    IMAGE_DIR
)


image_files = {}

extensions = {
    ".png",
    ".jpg",
    ".jpeg",
}

for path in IMAGE_DIR.rglob("*"):

    if not path.is_file():
        continue

    if path.suffix.lower() not in extensions:
        continue

    image_files[path.stem] = path


print(
    "Images indexed:",
    len(image_files)
)


# ================================================================
# RESOLVE IMAGE PATHS
# ================================================================

print()
print("=" * 70)
print("RESOLVING IMAGE PATHS")
print("=" * 70)


records = []

missing_images = []


for _, row in df.iterrows():

    image_name = str(
        row["Image_name"]
    ).strip()

    # Remove possible extension
    image_stem = Path(
        image_name
    ).stem

    image_path = image_files.get(
        image_stem
    )

    if image_path is None:

        # Try exact filename
        for extension in [
            ".png",
            ".jpg",
            ".jpeg",
        ]:

            candidate = (
                IMAGE_DIR
                / f"{image_name}{extension}"
            )

            if candidate.exists():

                image_path = candidate

                break

    if image_path is None:

        missing_images.append(
            image_name
        )

        continue

    brain_plane = (
        str(
            row["Brain_plane"]
        ).strip()
    )

    if brain_plane not in CLASS_TO_INDEX:

        continue

    records.append(
        {
            "image_name": image_name,
            "image_path": str(
                image_path
            ),
            "patient_num": int(
                row["Patient_num"]
            ),
            "brain_plane": brain_plane,
            "label": CLASS_TO_INDEX[
                brain_plane
            ],
        }
    )


print(
    "Missing images:",
    len(missing_images)
)

if missing_images:

    print()
    print("First missing images:")

    for name in missing_images[:20]:

        print(
            " -",
            name
        )


print()
print(
    "Usable images:",
    len(records)
)


if len(records) == 0:

    raise RuntimeError(
        "\nNo usable images found.\n"
        "Check:\n"
        f"Images folder = {IMAGE_DIR}\n"
        "CSV Image_name values.\n"
    )


# ================================================================
# PATIENT-WISE SPLIT
# ================================================================

print()
print("=" * 70)
print("PATIENT-WISE DATA SPLIT")
print("=" * 70)


patients = sorted(
    set(
        record["patient_num"]
        for record in records
    )
)

random.shuffle(patients)

total_patients = len(patients)


train_patient_count = int(
    total_patients * 0.70
)

validation_patient_count = int(
    total_patients * 0.15
)

train_patients = set(
    patients[
        :train_patient_count
    ]
)

validation_patients = set(
    patients[
        train_patient_count:
        train_patient_count
        + validation_patient_count
    ]
)

test_patients = set(
    patients[
        train_patient_count
        + validation_patient_count:
    ]
)


print(
    "Total patients:",
    total_patients
)

print(
    "Train patients:",
    len(train_patients)
)

print(
    "Validation patients:",
    len(validation_patients)
)

print(
    "Test patients:",
    len(test_patients)
)


# ================================================================
# SPLIT RECORDS
# ================================================================

train_records = []

validation_records = []

test_records = []


for record in records:

    patient = record[
        "patient_num"
    ]

    if patient in train_patients:

        train_records.append(
            record
        )

    elif patient in validation_patients:

        validation_records.append(
            record
        )

    else:

        test_records.append(
            record
        )


# ================================================================
# DISTRIBUTION FUNCTION
# ================================================================

def print_distribution(
    name,
    data,
):

    counter = Counter(
        item["brain_plane"]
        for item in data
    )

    print()
    print(name)

    for class_name in CLASS_NAMES:

        print(
            f"{class_name:20s}: "
            f"{counter.get(class_name, 0)}"
        )


print_distribution(
    "TRAIN:",
    train_records,
)

print_distribution(
    "VALIDATION:",
    validation_records,
)

print_distribution(
    "TEST:",
    test_records,
)


# ================================================================
# PREPARED DATASET
# ================================================================

print()
print("=" * 70)
print("PREPARING IMAGE DATASET")
print("=" * 70)


if PREPARED_DIR.exists():

    print(
        "Removing old prepared dataset..."
    )

    shutil.rmtree(
        PREPARED_DIR
    )


for split in [
    "train",
    "validation",
    "test",
]:

    for class_name in CLASS_NAMES:

        (
            PREPARED_DIR
            / split
            / class_name
        ).mkdir(
            parents=True,
            exist_ok=True,
        )


# ================================================================
# COPY FUNCTION
# ================================================================

def copy_split(
    split_name,
    data,
):

    print()
    print(
        f"Copying {split_name}: "
        f"{len(data)} images"
    )

    copied = 0

    for index, record in enumerate(
        data
    ):

        source = Path(
            record["image_path"]
        )

        class_name = record[
            "brain_plane"
        ]

        destination_dir = (
            PREPARED_DIR
            / split_name
            / class_name
        )

        destination = (
            destination_dir
            / source.name
        )

        try:

            shutil.copy2(
                source,
                destination,
            )

            copied += 1

        except Exception as exc:

            print(
                "Copy failed:",
                source,
                exc,
            )

    print(
        f"Copied: {copied}"
    )


copy_split(
    "train",
    train_records,
)

copy_split(
    "validation",
    validation_records,
)

copy_split(
    "test",
    test_records,
)


# ================================================================
# SAVE METADATA
# ================================================================

metadata = []

for split_name, split_data in [
    ("train", train_records),
    ("validation", validation_records),
    ("test", test_records),
]:

    for record in split_data:

        metadata.append(
            {
                "split": split_name,
                "image_name": record[
                    "image_name"
                ],
                "patient_num": record[
                    "patient_num"
                ],
                "brain_plane": record[
                    "brain_plane"
                ],
                "label": record[
                    "label"
                ],
            }
        )


metadata_df = pd.DataFrame(
    metadata
)

metadata_path = (
    PREPARED_DIR
    / "metadata.csv"
)

metadata_df.to_csv(
    metadata_path,
    index=False,
)


print()
print(
    "Metadata saved:",
    metadata_path
)


# ================================================================
# FINAL DATASET COUNTS
# ================================================================

print()
print("=" * 70)
print("FINAL DATASET")
print("=" * 70)

print(
    "Training:",
    len(train_records)
)

print(
    "Validation:",
    len(validation_records)
)

print(
    "Test:",
    len(test_records)
)


# ================================================================
# DATASET CLASS
# ================================================================

class FetalPlaneDataset(
    Dataset
):

    def __init__(
        self,
        records,
        transform=None,
    ):

        self.records = records

        self.transform = transform

    def __len__(self):

        return len(
            self.records
        )

    def __getitem__(
        self,
        index,
    ):

        record = self.records[
            index
        ]

        image = Image.open(
            record["image_path"]
        ).convert(
            "RGB"
        )

        if self.transform:

            image = self.transform(
                image
            )

        label = torch.tensor(
            record["label"],
            dtype=torch.long,
        )

        return image, label


# ================================================================
# TRANSFORMS
# ================================================================

train_transform = transforms.Compose(
    [

        transforms.Resize(
            (
                IMAGE_SIZE,
                IMAGE_SIZE,
            )
        ),

        transforms.RandomHorizontalFlip(
            p=0.5
        ),

        transforms.RandomRotation(
            degrees=5
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


validation_transform = transforms.Compose(
    [

        transforms.Resize(
            (
                IMAGE_SIZE,
                IMAGE_SIZE,
            )
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


# ================================================================
# DATASETS
# ================================================================

train_dataset = FetalPlaneDataset(
    train_records,
    train_transform,
)

validation_dataset = FetalPlaneDataset(
    validation_records,
    validation_transform,
)

test_dataset = FetalPlaneDataset(
    test_records,
    validation_transform,
)


if len(train_dataset) == 0:

    raise RuntimeError(
        "Training dataset is empty."
    )

if len(validation_dataset) == 0:

    raise RuntimeError(
        "Validation dataset is empty."
    )


# ================================================================
# DATALOADERS
# ================================================================

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=NUM_WORKERS,
    pin_memory=False,
)

validation_loader = DataLoader(
    validation_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=NUM_WORKERS,
    pin_memory=False,
)

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=NUM_WORKERS,
    pin_memory=False,
)


# ================================================================
# MODEL
# ================================================================

print()
print("=" * 70)
print("BUILDING MODEL")
print("=" * 70)


model = resnet18(
    weights=None
)

model.fc = nn.Linear(
    model.fc.in_features,
    NUM_CLASSES,
)

model = model.to(
    DEVICE
)


print(
    "Architecture : ResNet18"
)

print(
    "Pretrained   : False"
)

print(
    "Classes      :",
    NUM_CLASSES
)


# ================================================================
# LOSS
# ================================================================

criterion = nn.CrossEntropyLoss()


# ================================================================
# OPTIMIZER
# ================================================================

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=1e-4,
)


# ================================================================
# SCHEDULER
# ================================================================

scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode="min",
    factor=0.5,
    patience=4,
)


# ================================================================
# TRAINING FUNCTIONS
# ================================================================

def train_one_epoch():

    model.train()

    total_loss = 0.0

    correct = 0

    total = 0


    for images, labels in train_loader:

        images = images.to(
            DEVICE
        )

        labels = labels.to(
            DEVICE
        )


        optimizer.zero_grad()


        outputs = model(
            images
        )


        loss = criterion(
            outputs,
            labels,
        )


        loss.backward()


        optimizer.step()


        total_loss += (
            loss.item()
            * images.size(0)
        )


        predictions = (
            outputs.argmax(
                dim=1
            )
        )


        correct += (
            predictions == labels
        ).sum().item()


        total += labels.size(0)


    average_loss = (
        total_loss / total
    )

    accuracy = (
        correct / total
    ) * 100


    return (
        average_loss,
        accuracy,
    )


# ================================================================
# VALIDATION
# ================================================================

@torch.no_grad()
def evaluate(
    loader
):

    model.eval()

    total_loss = 0.0

    correct = 0

    total = 0


    for images, labels in loader:

        images = images.to(
            DEVICE
        )

        labels = labels.to(
            DEVICE
        )


        outputs = model(
            images
        )


        loss = criterion(
            outputs,
            labels,
        )


        total_loss += (
            loss.item()
            * images.size(0)
        )


        predictions = (
            outputs.argmax(
                dim=1
            )
        )


        correct += (
            predictions == labels
        ).sum().item()


        total += labels.size(0)


    average_loss = (
        total_loss / total
    )

    accuracy = (
        correct / total
    ) * 100


    return (
        average_loss,
        accuracy,
    )


# ================================================================
# TRAINING
# ================================================================

print()
print("=" * 70)
print("FETAL PLANE TRAINING")
print("=" * 70)


best_val_loss = float(
    "inf"
)

best_val_accuracy = 0.0

best_epoch = 0

no_improvement = 0


for epoch in range(
    1,
    EPOCHS + 1,
):

    print()
    print(
        f"Epoch {epoch:02d}/{EPOCHS}"
    )


    train_loss, train_accuracy = (
        train_one_epoch()
    )


    val_loss, val_accuracy = (
        evaluate(
            validation_loader
        )
    )


    scheduler.step(
        val_loss
    )


    current_lr = (
        optimizer.param_groups[0][
            "lr"
        ]
    )


    print(
        f"Train Loss : {train_loss:.4f}"
    )

    print(
        f"Train Acc  : {train_accuracy:.2f}%"
    )

    print(
        f"Val Loss   : {val_loss:.4f}"
    )

    print(
        f"Val Acc    : {val_accuracy:.2f}%"
    )

    print(
        f"LR         : {current_lr:.7f}"
    )


    if val_loss < best_val_loss:

        best_val_loss = val_loss

        best_val_accuracy = (
            val_accuracy
        )

        best_epoch = epoch

        no_improvement = 0


        checkpoint = {

            "model_state_dict":
                model.state_dict(),

            "class_names":
                CLASS_NAMES,

            "image_size":
                IMAGE_SIZE,

            "architecture":
                "resnet18",

            "best_epoch":
                best_epoch,

            "best_val_loss":
                best_val_loss,

            "best_val_accuracy":
                best_val_accuracy,

        }


        torch.save(
            checkpoint,
            MODEL_PATH,
        )


        print(
            "✓ New best model saved"
        )


    else:

        no_improvement += 1

        print(
            f"No improvement: "
            f"{no_improvement}/{PATIENCE}"
        )


    if no_improvement >= PATIENCE:

        print()
        print(
            "⚠ Early stopping triggered."
        )

        print(
            f"No improvement for "
            f"{PATIENCE} epochs."
        )

        break


# ================================================================
# FINAL TEST
# ================================================================

print()
print("=" * 70)
print("FINAL TEST EVALUATION")
print("=" * 70)


if MODEL_PATH.exists():

    checkpoint = torch.load(
        MODEL_PATH,
        map_location=DEVICE,
    )

    model.load_state_dict(
        checkpoint[
            "model_state_dict"
        ]
    )


    test_loss, test_accuracy = (
        evaluate(
            test_loader
        )
    )


    print(
        f"Test Loss : {test_loss:.4f}"
    )

    print(
        f"Test Acc  : {test_accuracy:.2f}%"
    )


# ================================================================
# COMPLETE
# ================================================================

print()
print("=" * 70)
print("FETAL PLANES TRAINING COMPLETE")
print("=" * 70)

print(
    "Best epoch:",
    best_epoch
)

print(
    f"Best validation loss: "
    f"{best_val_loss:.4f}"
)

print(
    f"Best validation accuracy: "
    f"{best_val_accuracy:.2f}%"
)

print(
    "Model saved:",
    MODEL_PATH
)

print(
    "Model exists:",
    MODEL_PATH.exists()
)

print("=" * 70)