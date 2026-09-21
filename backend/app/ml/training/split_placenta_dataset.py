from pathlib import Path
import random
import shutil


# ============================================================
# CONFIG
# ============================================================

SOURCE_IMAGES = Path(
    r"D:\Fetal_Placenta_Seg\images"
)

SOURCE_MASKS = Path(
    r"D:\Fetal_Placenta_Seg\masks"
)

OUTPUT = Path(
    r"D:\Fetal_Placenta_YOLO"
)

TRAIN_RATIO = 0.80

RANDOM_SEED = 42


# ============================================================
# SETUP
# ============================================================

random.seed(
    RANDOM_SEED
)


# ============================================================
# CHECK SOURCE
# ============================================================

if not SOURCE_IMAGES.exists():
    raise FileNotFoundError(
        f"Images directory not found:\n{SOURCE_IMAGES}"
    )

if not SOURCE_MASKS.exists():
    raise FileNotFoundError(
        f"Masks directory not found:\n{SOURCE_MASKS}"
    )


# ============================================================
# CREATE DIRECTORIES
# ============================================================

train_images = (
    OUTPUT / "images" / "train"
)

val_images = (
    OUTPUT / "images" / "val"
)

train_masks = (
    OUTPUT / "masks" / "train"
)

val_masks = (
    OUTPUT / "masks" / "val"
)


for directory in [
    train_images,
    val_images,
    train_masks,
    val_masks,
]:
    directory.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# FIND VALID PAIRS
# ============================================================

image_files = sorted(
    SOURCE_IMAGES.glob("*.png")
)

pairs = []

for image_path in image_files:

    mask_path = (
        SOURCE_MASKS
        / image_path.name
    )

    if mask_path.exists():
        pairs.append(
            (
                image_path,
                mask_path
            )
        )


print("=" * 70)
print("PLACENTA DATASET SPLIT")
print("=" * 70)

print(
    f"Images found : {len(image_files)}"
)

print(
    f"Valid pairs  : {len(pairs)}"
)


if not pairs:
    raise RuntimeError(
        "No image-mask pairs found."
    )


# ============================================================
# SHUFFLE
# ============================================================

random.shuffle(
    pairs
)


split_index = int(
    len(pairs) * TRAIN_RATIO
)


train_pairs = pairs[
    :split_index
]

val_pairs = pairs[
    split_index:
]


# ============================================================
# COPY TRAIN
# ============================================================

print(
    f"\nTrain pairs: {len(train_pairs)}"
)

print(
    f"Val pairs  : {len(val_pairs)}"
)


for image_path, mask_path in train_pairs:

    shutil.copy2(
        image_path,
        train_images / image_path.name
    )

    shutil.copy2(
        mask_path,
        train_masks / mask_path.name
    )


# ============================================================
# COPY VAL
# ============================================================

for image_path, mask_path in val_pairs:

    shutil.copy2(
        image_path,
        val_images / image_path.name
    )

    shutil.copy2(
        mask_path,
        val_masks / mask_path.name
    )


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 70)
print("PLACENTA DATASET SPLIT COMPLETE")
print("=" * 70)

print(
    f"Train images : "
    f"{len(list(train_images.glob('*.png')))}"
)

print(
    f"Train masks  : "
    f"{len(list(train_masks.glob('*.png')))}"
)

print(
    f"Val images   : "
    f"{len(list(val_images.glob('*.png')))}"
)

print(
    f"Val masks    : "
    f"{len(list(val_masks.glob('*.png')))}"
)

print(
    f"\nDataset:\n{OUTPUT}"
)

print("=" * 70)