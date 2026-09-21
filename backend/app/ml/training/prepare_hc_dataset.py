from pathlib import Path
import csv
import random
import shutil


# =========================================================
# CONFIGURATION
# =========================================================

HC18_ROOT = Path(
    r"C:\Users\Lenovo\Downloads\HC18_extract"
)

IMAGE_ROOT = (
    HC18_ROOT
    / "training_extracted"
)

CSV_PATH = (
    HC18_ROOT
    / "training_set_pixel_size_and_HC.csv"
)

OUTPUT_ROOT = (
    HC18_ROOT
    / "hc_prepared"
)

RANDOM_SEED = 42

TRAIN_RATIO = 0.80


# =========================================================
# VALIDATE INPUTS
# =========================================================

if not IMAGE_ROOT.exists():

    raise FileNotFoundError(
        f"Training image directory not found: "
        f"{IMAGE_ROOT}"
    )


if not CSV_PATH.exists():

    raise FileNotFoundError(
        f"HC18 CSV not found: "
        f"{CSV_PATH}"
    )


# =========================================================
# LOAD LABELS
# =========================================================

records = []

with CSV_PATH.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    reader = csv.DictReader(file)

    required_columns = {
        "filename",
        "pixel size",
        "head circumference (mm)",
    }

    missing = (
        required_columns
        - set(reader.fieldnames or [])
    )

    if missing:

        raise ValueError(
            f"Missing CSV columns: {missing}"
        )

    for row in reader:

        filename = (
            row["filename"]
            .strip()
        )

        pixel_size = float(
            row["pixel size"]
        )

        head_circumference = float(
            row["head circumference (mm)"]
        )

        records.append(
            {
                "filename": filename,
                "pixel_size": pixel_size,
                "head_circumference_mm":
                    head_circumference,
            }
        )


# =========================================================
# FIND IMAGES
# =========================================================

image_map = {}

for image_path in IMAGE_ROOT.rglob("*.png"):

    image_map[
        image_path.name
    ] = image_path


print()
print("=" * 65)
print("HC18 DATASET PREPARATION")
print("=" * 65)

print(
    "CSV records:",
    len(records),
)

print(
    "Images found:",
    len(image_map),
)


# =========================================================
# MATCH CSV WITH IMAGES
# =========================================================

matched_records = []

missing_images = []

for record in records:

    image_path = image_map.get(
        record["filename"]
    )

    if image_path is None:

        missing_images.append(
            record["filename"]
        )

        continue

    record["source_path"] = image_path

    matched_records.append(
        record
    )


print(
    "Matched records:",
    len(matched_records),
)

print(
    "Missing images:",
    len(missing_images),
)


if not matched_records:

    raise RuntimeError(
        "No images matched the HC18 CSV."
    )


# =========================================================
# CLEAN OLD OUTPUT
# =========================================================

if OUTPUT_ROOT.exists():

    print(
        f"\nRemoving previous output: "
        f"{OUTPUT_ROOT}"
    )

    shutil.rmtree(
        OUTPUT_ROOT
    )


TRAIN_DIR = (
    OUTPUT_ROOT
    / "train"
)

VALIDATION_DIR = (
    OUTPUT_ROOT
    / "validation"
)

TRAIN_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

VALIDATION_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# SHUFFLE
# =========================================================

random.seed(
    RANDOM_SEED
)

random.shuffle(
    matched_records
)


# =========================================================
# TRAIN / VALIDATION SPLIT
# =========================================================

train_count = int(
    len(matched_records)
    * TRAIN_RATIO
)

train_records = (
    matched_records[
        :train_count
    ]
)

validation_records = (
    matched_records[
        train_count:
    ]
)


print()
print("=" * 65)
print("SPLIT")
print("=" * 65)

print(
    "Training:",
    len(train_records),
)

print(
    "Validation:",
    len(validation_records),
)


# =========================================================
# COPY IMAGES + WRITE METADATA
# =========================================================

def copy_records(
    records,
    destination,
    metadata_filename,
):

    metadata_path = (
        destination
        / metadata_filename
    )

    with metadata_path.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow(
            [
                "filename",
                "pixel_size",
                "head_circumference_mm",
            ]
        )

        for record in records:

            source = (
                record["source_path"]
            )

            destination_file = (
                destination
                / source.name
            )

            shutil.copy2(
                source,
                destination_file,
            )

            writer.writerow(
                [
                    source.name,
                    record["pixel_size"],
                    record[
                        "head_circumference_mm"
                    ],
                ]
            )


copy_records(
    train_records,
    TRAIN_DIR,
    "metadata.csv",
)

copy_records(
    validation_records,
    VALIDATION_DIR,
    "metadata.csv",
)


# =========================================================
# SAVE COMPLETE METADATA
# =========================================================

all_metadata_path = (
    OUTPUT_ROOT
    / "all_metadata.csv"
)

with all_metadata_path.open(
    "w",
    encoding="utf-8",
    newline=""
) as file:

    writer = csv.writer(
        file
    )

    writer.writerow(
        [
            "filename",
            "pixel_size",
            "head_circumference_mm",
            "split",
        ]
    )

    for record in train_records:

        writer.writerow(
            [
                record["filename"],
                record["pixel_size"],
                record[
                    "head_circumference_mm"
                ],
                "train",
            ]
        )

    for record in validation_records:

        writer.writerow(
            [
                record["filename"],
                record["pixel_size"],
                record[
                    "head_circumference_mm"
                ],
                "validation",
            ]
        )


# =========================================================
# SUMMARY
# =========================================================

print()
print("=" * 65)
print("HC18 PREPARATION COMPLETE")
print("=" * 65)

print(
    "Output:",
    OUTPUT_ROOT,
)

print(
    "Training images:",
    len(train_records),
)

print(
    "Validation images:",
    len(validation_records),
)

print(
    "Training metadata:",
    TRAIN_DIR / "metadata.csv",
)

print(
    "Validation metadata:",
    VALIDATION_DIR / "metadata.csv",
)

print(
    "Complete metadata:",
    all_metadata_path,
)

print("=" * 65)