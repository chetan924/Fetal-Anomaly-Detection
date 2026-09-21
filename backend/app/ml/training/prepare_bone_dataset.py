from pathlib import Path
import csv
import math
import shutil


# ============================================================
# CONFIG
# ============================================================

SOURCE_ROOT = Path(
    r"D:\Fetal_Bone_Dataset\FetalBiometry-Multicentre-Landmarks-2026"
)

OUTPUT_ROOT = Path(
    r"D:\Fetal_Bone_YOLO"
)

DATASETS = {
    "FP": {
        "images": SOURCE_ROOT / "images" / "FP" / "Femur",
        "annotations": SOURCE_ROOT / "annotations" / "FP",
    },
    "UCL": {
        "images": SOURCE_ROOT / "images" / "UCL" / "Femur",
        "annotations": SOURCE_ROOT / "annotations" / "UCL",
    },
}

CLASS_ID = 0
CLASS_NAME = "femur"


# ============================================================
# HELPERS
# ============================================================

def read_csv(path: Path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def clamp(value, low, high):
    return max(low, min(value, high))


def make_bbox(x1, y1, x2, y2, width, height):
    left = min(x1, x2)
    right = max(x1, x2)
    top = min(y1, y2)
    bottom = max(y1, y2)

    # Add padding around the two femur endpoints.
    femur_len = math.hypot(
        x2 - x1,
        y2 - y1
    )

    pad = max(
        20.0,
        femur_len * 0.08
    )

    left = clamp(
        left - pad,
        0,
        width - 1
    )

    right = clamp(
        right + pad,
        0,
        width - 1
    )

    top = clamp(
        top - pad,
        0,
        height - 1
    )

    bottom = clamp(
        bottom + pad,
        0,
        height - 1
    )

    bbox_w = max(
        1.0,
        right - left
    )

    bbox_h = max(
        1.0,
        bottom - top
    )

    cx = left + bbox_w / 2.0
    cy = top + bbox_h / 2.0

    return (
        cx / width,
        cy / height,
        bbox_w / width,
        bbox_h / height,
    )


# ============================================================
# VALIDATE
# ============================================================

print("=" * 70)
print("FETAL FEMUR -> YOLO DATASET PREPARATION")
print("=" * 70)

if not SOURCE_ROOT.exists():
    raise FileNotFoundError(
        f"Source dataset not found:\n{SOURCE_ROOT}"
    )


# ============================================================
# RESET OUTPUT
# ============================================================

if OUTPUT_ROOT.exists():
    print("\nRemoving old output...")
    shutil.rmtree(OUTPUT_ROOT)


for split in (
    "train",
    "val",
    "test",
):
    (
        OUTPUT_ROOT
        / "images"
        / split
    ).mkdir(
        parents=True,
        exist_ok=True
    )

    (
        OUTPUT_ROOT
        / "labels"
        / split
    ).mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# PROCESS
# ============================================================

total_images = 0
total_labels = 0
missing_images = 0
invalid_rows = 0

# Prevent the same image from being copied twice.
seen = set()

for dataset_name, config in DATASETS.items():

    image_root = config["images"]
    annotation_root = config["annotations"]

    print("\n" + "=" * 70)
    print(f"PROCESSING {dataset_name}")
    print("=" * 70)

    if not image_root.exists():
        print(
            f"WARNING: Image directory missing:\n{image_root}"
        )
        continue

    # --------------------------------------------------------
    # Pick the dedicated femur train/test CSVs.
    # Validation images, when present, are handled through the
    # main Femur.csv Split column.
    # --------------------------------------------------------

    femur_csv = (
        annotation_root / "Femur.csv"
    )

    if not femur_csv.exists():
        print(
            f"WARNING: Missing annotation file:\n{femur_csv}"
        )
        continue

    rows = read_csv(
        femur_csv
    )

    print(
        f"Annotation rows: {len(rows)}"
    )

    for row in rows:

        image_name = (
            row.get("image_name", "")
            .strip()
        )

        if not image_name:
            invalid_rows += 1
            continue

        try:
            x1 = float(
                row["fl_1_x"]
            )
            y1 = float(
                row["fl_1_y"]
            )
            x2 = float(
                row["fl_2_x"]
            )
            y2 = float(
                row["fl_2_y"]
            )

        except (
            KeyError,
            TypeError,
            ValueError
        ):
            invalid_rows += 1
            continue

        source_image = (
            image_root
            / image_name
        )

        if not source_image.exists():
            missing_images += 1
            continue

        # ----------------------------------------------------
        # Determine split from annotation.
        # ----------------------------------------------------

        source_split = (
            row.get("Split", "")
            .strip()
            .lower()
        )

        if source_split == "train":
            split = "train"
        elif source_split in {
            "test",
            "testing",
        }:
            split = "test"
        elif source_split in {
            "val",
            "validation",
        }:
            split = "val"
        else:
            # Conservative fallback.
            split = "train"

        # ----------------------------------------------------
        # Unique filename.
        # ----------------------------------------------------

        stem = source_image.stem
        suffix = source_image.suffix.lower()

        unique_stem = (
            f"{dataset_name}_{stem}"
        )

        if unique_stem in seen:
            continue

        seen.add(
            unique_stem
        )

        # ----------------------------------------------------
        # Read image dimensions.
        # Avoid requiring OpenCV/PIL just for dimensions.
        # Use PIL if available.
        # ----------------------------------------------------

        try:
            from PIL import Image

            with Image.open(
                source_image
            ) as img:
                width, height = img.size

        except Exception as exc:
            print(
                f"WARNING: Cannot read image "
                f"{source_image.name}: {exc}"
            )
            continue

        # ----------------------------------------------------
        # Clamp landmark points.
        # ----------------------------------------------------

        x1 = clamp(
            x1,
            0,
            width - 1
        )

        y1 = clamp(
            y1,
            0,
            height - 1
        )

        x2 = clamp(
            x2,
            0,
            width - 1
        )

        y2 = clamp(
            y2,
            0,
            height - 1
        )

        # Reject zero-length landmarks.
        if (
            abs(x1 - x2) < 1e-6
            and
            abs(y1 - y2) < 1e-6
        ):
            invalid_rows += 1
            continue

        (
            cx,
            cy,
            bw,
            bh,
        ) = make_bbox(
            x1,
            y1,
            x2,
            y2,
            width,
            height,
        )

        # ----------------------------------------------------
        # Save image.
        # ----------------------------------------------------

        destination_image = (
            OUTPUT_ROOT
            / "images"
            / split
            / f"{unique_stem}{suffix}"
        )

        shutil.copy2(
            source_image,
            destination_image
        )

        # ----------------------------------------------------
        # Save YOLO label.
        # ----------------------------------------------------

        destination_label = (
            OUTPUT_ROOT
            / "labels"
            / split
            / f"{unique_stem}.txt"
        )

        with open(
            destination_label,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                f"{CLASS_ID} "
                f"{cx:.6f} "
                f"{cy:.6f} "
                f"{bw:.6f} "
                f"{bh:.6f}\n"
            )

        total_images += 1
        total_labels += 1


# ============================================================
# DATASET YAML
# ============================================================

yaml_path = (
    OUTPUT_ROOT
    / "data.yaml"
)

yaml_content = f"""path: {OUTPUT_ROOT.as_posix()}
train: images/train
val: images/val
test: images/test

nc: 1

names:
  0: {CLASS_NAME}
"""

with open(
    yaml_path,
    "w",
    encoding="utf-8"
) as f:
    f.write(
        yaml_content
    )


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("FETAL FEMUR YOLO DATASET READY")
print("=" * 70)

print(
    f"Images created      : {total_images}"
)

print(
    f"Labels created      : {total_labels}"
)

print(
    f"Missing images      : {missing_images}"
)

print(
    f"Invalid rows        : {invalid_rows}"
)

print(
    f"Output directory    : {OUTPUT_ROOT}"
)

print(
    f"YAML                : {yaml_path}"
)

print("\nClass:")
print(
    "0 = femur"
)

print("=" * 70)