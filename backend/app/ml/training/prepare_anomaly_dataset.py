from pathlib import Path
from collections import defaultdict, Counter
import hashlib
import random
import shutil


# =========================================================
# CONFIGURATION
# =========================================================

SOURCE_ROOT = Path(r"D:\Fetal_Anomaly_Dataset\Datasets")
OUTPUT_ROOT = Path(r"D:\Fetal_Anomaly_Clean")

SOURCE_SPLITS = [
    "train",
    "validation",
    "test",
]

CLASSES = [
    "normal",
    "benign",
    "malignant",
]

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
}

RANDOM_SEED = 42

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15


# =========================================================
# HASH FUNCTION
# =========================================================

def calculate_hash(path: Path) -> str:
    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


# =========================================================
# COLLECT ALL IMAGES
# =========================================================

print("=" * 65)
print("PREPARING CLEAN FETAL ANOMALY DATASET")
print("=" * 65)

hash_records = defaultdict(list)

total_source_images = 0


for split in SOURCE_SPLITS:

    for class_name in CLASSES:

        folder = SOURCE_ROOT / split / class_name

        if not folder.exists():
            print(f"WARNING: Folder not found: {folder}")
            continue

        for image_path in folder.iterdir():

            if (
                image_path.is_file()
                and image_path.suffix.lower() in IMAGE_EXTENSIONS
            ):
                total_source_images += 1

                image_hash = calculate_hash(image_path)

                hash_records[image_hash].append(
                    {
                        "path": image_path,
                        "class": class_name,
                        "split": split,
                    }
                )


print(f"\nOriginal images: {total_source_images}")
print(f"Unique image hashes: {len(hash_records)}")


# =========================================================
# REMOVE LABEL CONFLICTS + SAME-LABEL DUPLICATES
# =========================================================

clean_records = []

conflicting_hashes = []
same_label_duplicates_removed = 0


for image_hash, records in hash_records.items():

    labels = {
        record["class"]
        for record in records
    }

    # Same exact image has multiple labels.
    # Unsafe for supervised training -> remove entire hash group.
    if len(labels) > 1:
        conflicting_hashes.append(
            {
                "hash": image_hash,
                "records": records,
            }
        )
        continue

    # Same image + same label:
    # keep only one physical copy.
    clean_records.append(records[0])

    same_label_duplicates_removed += len(records) - 1


print("\n" + "=" * 65)
print("DEDUPLICATION RESULTS")
print("=" * 65)

print(
    "Conflicting unique image groups removed:",
    len(conflicting_hashes),
)

print(
    "Same-label duplicate copies removed:",
    same_label_duplicates_removed,
)

print(
    "Clean unique images remaining:",
    len(clean_records),
)


# =========================================================
# SHOW CONFLICT EXAMPLES
# =========================================================

if conflicting_hashes:

    print("\nConflict examples:")

    for conflict in conflicting_hashes[:10]:

        print("-" * 50)

        for record in conflict["records"]:
            print(
                record["split"],
                record["class"],
                record["path"].name,
            )


# =========================================================
# GROUP CLEAN IMAGES BY CLASS
# =========================================================

records_by_class = defaultdict(list)

for record in clean_records:
    records_by_class[record["class"]].append(record)


print("\n" + "=" * 65)
print("CLEAN CLASS DISTRIBUTION")
print("=" * 65)

for class_name in CLASSES:
    print(
        f"{class_name:12s}: "
        f"{len(records_by_class[class_name])}"
    )


# =========================================================
# CREATE NEW OUTPUT DIRECTORY
# =========================================================

if OUTPUT_ROOT.exists():

    print(
        f"\nRemoving previous clean dataset: "
        f"{OUTPUT_ROOT}"
    )

    shutil.rmtree(OUTPUT_ROOT)


for split in ["train", "validation", "test"]:

    for class_name in CLASSES:

        (
            OUTPUT_ROOT
            / split
            / class_name
        ).mkdir(
            parents=True,
            exist_ok=True,
        )


# =========================================================
# STRATIFIED SPLIT
# =========================================================

random.seed(RANDOM_SEED)

split_records = {
    "train": [],
    "validation": [],
    "test": [],
}


for class_name in CLASSES:

    records = records_by_class[class_name].copy()

    random.shuffle(records)

    total = len(records)

    train_count = int(
        total * TRAIN_RATIO
    )

    val_count = int(
        total * VAL_RATIO
    )

    train_records = records[:train_count]

    val_records = records[
        train_count:
        train_count + val_count
    ]

    test_records = records[
        train_count + val_count:
    ]

    split_records["train"].extend(
        train_records
    )

    split_records["validation"].extend(
        val_records
    )

    split_records["test"].extend(
        test_records
    )


# =========================================================
# COPY CLEAN IMAGES
# =========================================================

for split_name, records in split_records.items():

    for index, record in enumerate(
        records,
        start=1,
    ):

        source = record["path"]

        class_name = record["class"]

        destination_folder = (
            OUTPUT_ROOT
            / split_name
            / class_name
        )

        # Hash prefix prevents filename collisions.
        image_hash = calculate_hash(source)

        destination_name = (
            f"{image_hash[:12]}_"
            f"{source.name}"
        )

        destination = (
            destination_folder
            / destination_name
        )

        shutil.copy2(
            source,
            destination,
        )


# =========================================================
# FINAL REPORT
# =========================================================

print("\n" + "=" * 65)
print("NEW DATASET SPLIT")
print("=" * 65)


for split_name in [
    "train",
    "validation",
    "test",
]:

    print(
        f"\n{split_name.upper()}"
    )

    total_split = 0

    for class_name in CLASSES:

        folder = (
            OUTPUT_ROOT
            / split_name
            / class_name
        )

        count = sum(
            1
            for path in folder.iterdir()
            if (
                path.is_file()
                and path.suffix.lower()
                in IMAGE_EXTENSIONS
            )
        )

        total_split += count

        print(
            f"{class_name:12s}: {count}"
        )

    print(
        f"{'TOTAL':12s}: {total_split}"
    )


print("\n" + "=" * 65)
print("CLEAN DATASET CREATED")
print("=" * 65)

print(f"Location: {OUTPUT_ROOT}")

print(
    "\nIMPORTANT:"
    "\n- Exact duplicate copies were removed."
    "\n- Exact images with conflicting labels were removed entirely."
    "\n- Original dataset was not modified."
    "\n- A new stratified train/validation/test split was created."
)
