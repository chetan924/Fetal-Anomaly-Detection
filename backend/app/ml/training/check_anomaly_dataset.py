from pathlib import Path
import hashlib
from collections import defaultdict


DATASET_ROOT = Path(r"D:\Fetal_Anomaly_Dataset\Datasets")

SPLITS = ["train", "validation", "test"]
CLASSES = ["normal", "benign", "malignant"]


def file_hash(path):
    sha256 = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


print("=" * 60)
print("FETAL ANOMALY DATASET CHECK")
print("=" * 60)

hash_locations = defaultdict(list)

total_images = 0

for split in SPLITS:

    print(f"\n{split.upper()}")

    for class_name in CLASSES:

        folder = DATASET_ROOT / split / class_name

        images = []

        for extension in ["*.png", "*.jpg", "*.jpeg"]:
            images.extend(folder.glob(extension))

        print(f"{class_name:12s}: {len(images)}")

        total_images += len(images)

        for image_path in images:

            image_hash = file_hash(image_path)

            hash_locations[image_hash].append(
                (
                    split,
                    class_name,
                    image_path.name,
                )
            )


print("\nTotal images:", total_images)


# ---------------------------------------------------------
# CHECK DUPLICATES ACROSS SPLITS
# ---------------------------------------------------------

cross_split_duplicates = []

for image_hash, locations in hash_locations.items():

    splits = {
        location[0]
        for location in locations
    }

    if len(splits) > 1:

        cross_split_duplicates.append(
            locations
        )


print("\n" + "=" * 60)
print("LEAKAGE CHECK")
print("=" * 60)

print(
    "Duplicate images across train/validation/test:",
    len(cross_split_duplicates),
)


if cross_split_duplicates:

    print("\nExamples:")

    for duplicate in cross_split_duplicates[:20]:

        print(duplicate)

else:

    print(
        "PASS - No exact image duplicates across dataset splits."
    )