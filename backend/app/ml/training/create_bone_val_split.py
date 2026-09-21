from pathlib import Path
import random
import shutil


ROOT = Path(r"D:\Fetal_Bone_YOLO")

TRAIN_IMAGES = ROOT / "images" / "train"
TRAIN_LABELS = ROOT / "labels" / "train"

VAL_IMAGES = ROOT / "images" / "val"
VAL_LABELS = ROOT / "labels" / "val"

VAL_RATIO = 0.15
SEED = 42


VAL_IMAGES.mkdir(
    parents=True,
    exist_ok=True
)

VAL_LABELS.mkdir(
    parents=True,
    exist_ok=True
)


images = sorted(
    [
        p for p in TRAIN_IMAGES.iterdir()
        if p.suffix.lower() in {
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tif",
            ".tiff",
            ".webp",
        }
    ]
)

random.seed(SEED)
random.shuffle(images)

val_count = max(
    1,
    int(len(images) * VAL_RATIO)
)

val_images = images[:val_count]

print("=" * 70)
print("CREATING FEMUR VALIDATION SPLIT")
print("=" * 70)

print(
    f"Train images before split : {len(images)}"
)

print(
    f"Validation images         : {len(val_images)}"
)


moved = 0

for image_path in val_images:

    label_path = (
        TRAIN_LABELS
        / f"{image_path.stem}.txt"
    )

    destination_image = (
        VAL_IMAGES
        / image_path.name
    )

    destination_label = (
        VAL_LABELS
        / label_path.name
    )

    shutil.move(
        image_path,
        destination_image
    )

    if label_path.exists():

        shutil.move(
            label_path,
            destination_label
        )

    moved += 1


print(
    f"Moved to validation       : {moved}"
)

print(
    f"Remaining training images: "
    f"{len(images) - moved}"
)

print("=" * 70)