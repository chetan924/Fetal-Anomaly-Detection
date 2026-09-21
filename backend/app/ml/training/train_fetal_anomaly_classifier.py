from pathlib import Path
import copy
import json

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
from tqdm import tqdm


# ============================================================
# CONFIG
# ============================================================

DATASET_ROOT = Path(
    r"D:\Fetal Anomaly Detection\Datasets\Datasets"
)

MODEL_DIR = Path(
    r"D:\Fetal Anomaly Detection\backend\app\ml\models"
)

MODEL_PATH = MODEL_DIR / "fetal_anomaly_classifier.pt"
CLASS_MAP_PATH = MODEL_DIR / "fetal_anomaly_classes.json"

IMAGE_SIZE = 160
BATCH_SIZE = 16
EPOCHS = 15
LEARNING_RATE = 5e-5
NUM_WORKERS = 0
PATIENCE = 5

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

EXPECTED_CLASSES = [
    "benign",
    "malignant",
    "normal",
]


# ============================================================
# PRINT CONFIG
# ============================================================

print("=" * 70)
print("FETAL ULTRASOUND ANOMALY CLASSIFIER")
print("=" * 70)
print(f"Device        : {DEVICE}")
print(f"Image size    : {IMAGE_SIZE}")
print(f"Batch size    : {BATCH_SIZE}")
print(f"Epochs        : {EPOCHS}")
print(f"Learning rate : {LEARNING_RATE}")
print(f"Workers       : {NUM_WORKERS}")
print(f"Dataset       : {DATASET_ROOT}")
print(f"Model path    : {MODEL_PATH}")
print("=" * 70)


# ============================================================
# CHECK DATASET
# ============================================================

TRAIN_DIR = DATASET_ROOT / "train"
VAL_DIR = DATASET_ROOT / "validation"
TEST_DIR = DATASET_ROOT / "test"

for folder in [TRAIN_DIR, VAL_DIR, TEST_DIR]:
    if not folder.exists():
        raise FileNotFoundError(
            f"Dataset folder not found:\n{folder}"
        )


# ============================================================
# TRANSFORMS
# ============================================================

train_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(7),
    transforms.ColorJitter(
        brightness=0.15,
        contrast=0.15
    ),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
])

eval_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
])


# ============================================================
# DATASETS
# ============================================================

print("\n" + "=" * 70)
print("LOADING DATASET")
print("=" * 70)

train_dataset = datasets.ImageFolder(
    TRAIN_DIR,
    transform=train_transform
)

val_dataset = datasets.ImageFolder(
    VAL_DIR,
    transform=eval_transform
)

test_dataset = datasets.ImageFolder(
    TEST_DIR,
    transform=eval_transform
)


print(f"Train samples : {len(train_dataset)}")
print(f"Val samples   : {len(val_dataset)}")
print(f"Test samples  : {len(test_dataset)}")

print("\nClasses:")
print(train_dataset.classes)

if train_dataset.classes != EXPECTED_CLASSES:
    raise ValueError(
        "Unexpected class order.\n"
        f"Expected: {EXPECTED_CLASSES}\n"
        f"Found   : {train_dataset.classes}"
    )


# ============================================================
# CLASS DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("CLASS DISTRIBUTION")
print("=" * 70)

for split_name, dataset in [
    ("TRAIN", train_dataset),
    ("VALIDATION", val_dataset),
    ("TEST", test_dataset),
]:
    counts = [0] * len(dataset.classes)

    for _, label in dataset.samples:
        counts[label] += 1

    print(f"\n{split_name}")
    for class_name, count in zip(
        dataset.classes,
        counts
    ):
        print(f"{class_name:12s}: {count}")


# ============================================================
# CLASS WEIGHTS
# ============================================================

train_counts = [0] * len(train_dataset.classes)

for _, label in train_dataset.samples:
    train_counts[label] += 1

total_train = sum(train_counts)

class_weights = []

for count in train_counts:
    if count == 0:
        class_weights.append(0.0)
    else:
        class_weights.append(
            total_train / (len(train_counts) * count)
        )

class_weights_tensor = torch.tensor(
    class_weights,
    dtype=torch.float32,
    device=DEVICE
)

print("\nClass weights:")
for name, weight in zip(
    train_dataset.classes,
    class_weights
):
    print(
        f"{name:12s}: {weight:.4f}"
    )


# ============================================================
# DATALOADERS
# ============================================================

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

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=NUM_WORKERS,
    pin_memory=False,
)


# ============================================================
# MODEL
# ============================================================

print("\n" + "=" * 70)
print("BUILDING MODEL")
print("=" * 70)

weights = models.EfficientNet_B0_Weights.DEFAULT

model = models.efficientnet_b0(
    weights=weights
)

in_features = model.classifier[1].in_features

model.classifier[1] = nn.Linear(
    in_features,
    len(train_dataset.classes)
)

model = model.to(DEVICE)


# ============================================================
# LOSS
# ============================================================

criterion = nn.CrossEntropyLoss(
    weight=class_weights_tensor
)


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
    mode="min",
    factor=0.5,
    patience=2
)


# ============================================================
# TRAIN FUNCTION
# ============================================================

def run_train_epoch():

    model.train()

    running_loss = 0.0
    correct = 0
    total = 0

    progress = tqdm(
        train_loader,
        desc="Training",
        leave=False
    )

    for images, labels in progress:

        images = images.to(DEVICE)
        labels = labels.to(DEVICE)

        optimizer.zero_grad()

        outputs = model(images)

        loss = criterion(
            outputs,
            labels
        )

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=5.0
        )

        optimizer.step()

        batch_size = labels.size(0)

        running_loss += (
            loss.item() * batch_size
        )

        predictions = outputs.argmax(
            dim=1
        )

        correct += (
            predictions == labels
        ).sum().item()

        total += batch_size

        progress.set_postfix(
            loss=f"{loss.item():.4f}"
        )

    epoch_loss = (
        running_loss / total
    )

    epoch_acc = (
        correct / total
    )

    return epoch_loss, epoch_acc


# ============================================================
# VALIDATION FUNCTION
# ============================================================

@torch.no_grad()
def run_eval(loader):

    model.eval()

    running_loss = 0.0
    correct = 0
    total = 0

    all_predictions = []
    all_labels = []

    for images, labels in loader:

        images = images.to(DEVICE)
        labels = labels.to(DEVICE)

        outputs = model(images)

        loss = criterion(
            outputs,
            labels
        )

        batch_size = labels.size(0)

        running_loss += (
            loss.item() * batch_size
        )

        predictions = outputs.argmax(
            dim=1
        )

        correct += (
            predictions == labels
        ).sum().item()

        total += batch_size

        all_predictions.extend(
            predictions.cpu().tolist()
        )

        all_labels.extend(
            labels.cpu().tolist()
        )

    epoch_loss = (
        running_loss / total
    )

    epoch_acc = (
        correct / total
    )

    return (
        epoch_loss,
        epoch_acc,
        all_labels,
        all_predictions
    )


# ============================================================
# TRAINING LOOP
# ============================================================

best_val_loss = float("inf")
best_val_acc = 0.0
best_epoch = 0
best_state = None

no_improvement = 0

print("\n" + "=" * 70)
print("STARTING TRAINING")
print("=" * 70)

for epoch in range(
    1,
    EPOCHS + 1
):

    print(
        f"\nEpoch {epoch:02d}/{EPOCHS}"
    )

    train_loss, train_acc = (
        run_train_epoch()
    )

    val_loss, val_acc, _, _ = (
        run_eval(val_loader)
    )

    scheduler.step(
        val_loss
    )

    current_lr = optimizer.param_groups[0]["lr"]

    print(
        f"Train Loss : {train_loss:.4f}"
    )

    print(
        f"Train Acc  : {train_acc * 100:.2f}%"
    )

    print(
        f"Val Loss   : {val_loss:.4f}"
    )

    print(
        f"Val Acc    : {val_acc * 100:.2f}%"
    )

    print(
        f"LR         : {current_lr:.7f}"
    )

    if val_loss < best_val_loss:

        best_val_loss = val_loss
        best_val_acc = val_acc
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
# RESTORE BEST MODEL
# ============================================================

if best_state is None:
    raise RuntimeError(
        "No valid model checkpoint was produced."
    )

model.load_state_dict(
    best_state
)


# ============================================================
# TEST EVALUATION
# ============================================================

print("\n" + "=" * 70)
print("FINAL TEST EVALUATION")
print("=" * 70)

test_loss, test_acc, test_labels, test_predictions = (
    run_eval(test_loader)
)

print(
    f"Test Loss : {test_loss:.4f}"
)

print(
    f"Test Acc  : {test_acc * 100:.2f}%"
)


# ============================================================
# CONFUSION MATRIX
# ============================================================

confusion = [
    [0] * len(train_dataset.classes)
    for _ in range(len(train_dataset.classes))
]

for true_label, pred_label in zip(
    test_labels,
    test_predictions
):
    confusion[true_label][pred_label] += 1

print("\n" + "=" * 70)
print("CONFUSION MATRIX")
print("=" * 70)

print(
    "Rows = True | Columns = Predicted"
)

print(
    " " * 15 +
    "".join(
        f"{name:14s}"
        for name in train_dataset.classes
    )
)

for name, row in zip(
    train_dataset.classes,
    confusion
):
    print(
        f"{name:15s}" +
        "".join(
            f"{value:<14d}"
            for value in row
        )
    )


# ============================================================
# SAVE MODEL
# ============================================================

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

checkpoint = {
    "model_state_dict": model.state_dict(),
    "classes": train_dataset.classes,
    "class_to_idx": train_dataset.class_to_idx,
    "image_size": IMAGE_SIZE,
    "best_epoch": best_epoch,
    "best_val_loss": best_val_loss,
    "best_val_accuracy": best_val_acc,
    "test_loss": test_loss,
    "test_accuracy": test_acc,
}

torch.save(
    checkpoint,
    MODEL_PATH
)


# ============================================================
# SAVE CLASS MAP
# ============================================================

with open(
    CLASS_MAP_PATH,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        {
            "classes": train_dataset.classes,
            "class_to_idx": train_dataset.class_to_idx
        },
        file,
        indent=2
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("FETAL ANOMALY CLASSIFIER TRAINING COMPLETE")
print("=" * 70)

print(
    f"Best epoch          : {best_epoch}"
)

print(
    f"Best validation loss: {best_val_loss:.4f}"
)

print(
    f"Best validation acc : {best_val_acc * 100:.2f}%"
)

print(
    f"Test loss           : {test_loss:.4f}"
)

print(
    f"Test accuracy       : {test_acc * 100:.2f}%"
)

print(
    f"\nModel saved:\n{MODEL_PATH}"
)

print(
    f"\nClass map saved:\n{CLASS_MAP_PATH}"
)

print("=" * 70)