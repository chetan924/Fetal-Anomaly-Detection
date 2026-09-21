from pathlib import Path
import json
import shutil
import random


# ============================================================
# CONFIG
# ============================================================

SOURCE_ROOT = Path(
    r"D:\FUSSD3\FUSSD"
)

OUTPUT_ROOT = Path(
    r"D:\Fetal_Spine_YOLO"
)

SEED = 42

CLASS_NAMES = [
    "SC",
    "VAOC",
    "MS",
    "MC",
    "VOC",
    "DS",
]

CATEGORY_TO_CLASS = {
    1: 0,  # SC
    2: 1,  # VAOC
    3: 2,  # MS
    4: 3,  # MC
    5: 4,  # VOC
    6: 5,  # DS
}


# ============================================================
# PRINT CONFIG
# ============================================================

print("=" * 70)
print("FUSSD FETAL SPINE -> YOLO DATASET PREPARATION")
print("=" * 70)

print(f"Source : {SOURCE_ROOT}")
print(f"Output : {OUTPUT_ROOT}")

print("\nClasses:")

for idx, name in enumerate(
    CLASS_NAMES
):
    print(
        f"{idx}: {name}"
    )


# ============================================================
# VALIDATE SOURCE
# ============================================================

if not SOURCE_ROOT.exists():
    raise FileNotFoundError(
        f"FUSSD source directory not found:\n{SOURCE_ROOT}"
    )


# ============================================================
# CLEAR OLD OUTPUT
# ============================================================

if OUTPUT_ROOT.exists():

    print("\nRemoving existing output...")

    shutil.rmtree(
        OUTPUT_ROOT
    )


# ============================================================
# CREATE DIRECTORIES
# ============================================================

for split in [
    "train",
    "val",
    "test",
]:

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
# HELPERS
# ============================================================

def normalize_bbox(
    bbox,
    image_width,
    image_height
):
    """
    COCO bbox:
        [x, y, width, height]

    YOLO:
        [x_center, y_center, width, height]
        all normalized to 0..1
    """

    x, y, w, h = bbox

    x_center = (
        x + (w / 2.0)
    )

    y_center = (
        y + (h / 2.0)
    )

    x_center /= image_width
    y_center /= image_height

    w /= image_width
    h /= image_height

    # Clamp values for safety
    x_center = min(
        max(x_center, 0.0),
        1.0
    )

    y_center = min(
        max(y_center, 0.0),
        1.0
    )

    w = min(
        max(w, 0.0),
        1.0
    )

    h = min(
        max(h, 0.0),
        1.0
    )

    return (
        x_center,
        y_center,
        w,
        h
    )


# ============================================================
# SOURCE SPLITS
# ============================================================

SOURCE_PARTS = [
    "GE",
    "PH",
    "SA",
]

SOURCE_SPLITS = [
    "train",
    "val",
    "test",
]


# ============================================================
# PROCESS
# ============================================================

total_images = 0
total_annotations = 0
skipped_annotations = 0
copied_images = 0

global_seen_names = set()


for part in SOURCE_PARTS:

    part_root = (
        SOURCE_ROOT / part
    )

    if not part_root.exists():

        print(
            f"\nWARNING: Missing part: {part}"
        )

        continue

    image_dir = (
        part_root / "src"
    )

    if not image_dir.exists():

        print(
            f"\nWARNING: Missing src directory: {image_dir}"
        )

        continue

    print(
        f"\n{'=' * 70}"
    )

    print(
        f"PROCESSING: {part}"
    )

    print(
        f"{'=' * 70}"
    )

    for split in SOURCE_SPLITS:

        json_path = (
            part_root
            / f"{split}.json"
        )

        if not json_path.exists():

            print(
                f"Skipping missing: {json_path}"
            )

            continue

        with open(
            json_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        images = data.get(
            "images",
            []
        )

        annotations = data.get(
            "annotations",
            []
        )

        print(
            f"\n{part} / {split}"
        )

        print(
            f"Images       : {len(images)}"
        )

        print(
            f"Annotations  : {len(annotations)}"
        )

        # ----------------------------------------------------
        # Annotation lookup by image ID
        # ----------------------------------------------------

        annotations_by_image = {}

        for annotation in annotations:

            image_id = annotation.get(
                "image_id"
            )

            annotations_by_image.setdefault(
                image_id,
                []
            ).append(
                annotation
            )

        # ----------------------------------------------------
        # Process images
        # ----------------------------------------------------

        for image_info in images:

            file_name = image_info.get(
                "file_name"
            )

            image_id = image_info.get(
                "id"
            )

            image_width = image_info.get(
                "width"
            )

            image_height = image_info.get(
                "height"
            )

            if not file_name:
                continue

            if not image_width or not image_height:
                continue

            source_image = (
                image_dir
                / file_name
            )

            if not source_image.exists():

                print(
                    f"WARNING: Missing image: "
                    f"{source_image}"
                )

                continue

            # ------------------------------------------------
            # Make unique filename
            # ------------------------------------------------

            stem = Path(
                file_name
            ).stem

            extension = (
                Path(file_name)
                .suffix
                .lower()
            )

            unique_name = (
                f"{part}_{split}_{stem}"
            )

            if unique_name in global_seen_names:

                print(
                    f"WARNING: Duplicate image "
                    f"{unique_name}"
                )

                continue

            global_seen_names.add(
                unique_name
            )

            output_image_name = (
                unique_name
                + extension
            )

            output_label_name = (
                unique_name
                + ".txt"
            )

            destination_image = (
                OUTPUT_ROOT
                / "images"
                / split
                / output_image_name
            )

            destination_label = (
                OUTPUT_ROOT
                / "labels"
                / split
                / output_label_name
            )

            # ------------------------------------------------
            # Copy image
            # ------------------------------------------------

            shutil.copy2(
                source_image,
                destination_image
            )

            copied_images += 1

            total_images += 1

            # ------------------------------------------------
            # Convert annotations
            # ------------------------------------------------

            yolo_lines = []

            image_annotations = (
                annotations_by_image.get(
                    image_id,
                    []
                )
            )

            for annotation in image_annotations:

                category_id = annotation.get(
                    "category_id"
                )

                if category_id not in CATEGORY_TO_CLASS:

                    skipped_annotations += 1

                    continue

                bbox = annotation.get(
                    "bbox"
                )

                if not bbox or len(bbox) != 4:

                    skipped_annotations += 1

                    continue

                class_id = (
                    CATEGORY_TO_CLASS[
                        category_id
                    ]
                )

                (
                    x_center,
                    y_center,
                    width,
                    height
                ) = normalize_bbox(
                    bbox,
                    image_width,
                    image_height
                )

                # Ignore invalid boxes
                if width <= 0 or height <= 0:

                    skipped_annotations += 1

                    continue

                yolo_line = (
                    f"{class_id} "
                    f"{x_center:.6f} "
                    f"{y_center:.6f} "
                    f"{width:.6f} "
                    f"{height:.6f}"
                )

                yolo_lines.append(
                    yolo_line
                )

                total_annotations += 1

            # ------------------------------------------------
            # Save labels
            # ------------------------------------------------

            with open(
                destination_label,
                "w",
                encoding="utf-8"
            ) as label_file:

                if yolo_lines:

                    label_file.write(
                        "\n".join(
                            yolo_lines
                        )
                    )

                    label_file.write(
                        "\n"
                    )

                else:

                    # Empty label file is valid for
                    # images without annotations.
                    label_file.write(
                        ""
                    )


# ============================================================
# DATASET YAML
# ============================================================

yaml_path = (
    OUTPUT_ROOT
    / "data.yaml"
)

yaml_text = f"""path: {OUTPUT_ROOT.as_posix()}
train: images/train
val: images/val
test: images/test

nc: {len(CLASS_NAMES)}

names:
"""

for idx, name in enumerate(
    CLASS_NAMES
):

    yaml_text += (
        f"  {idx}: {name}\n"
    )


with open(
    yaml_path,
    "w",
    encoding="utf-8"
) as file:

    file.write(
        yaml_text
    )


# ============================================================
# SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("FUSSD YOLO DATASET PREPARATION COMPLETE")
print("=" * 70)

print(
    f"Images copied       : {copied_images}"
)

print(
    f"Annotations converted: {total_annotations}"
)

print(
    f"Skipped annotations : {skipped_annotations}"
)

print(
    f"Output directory    : {OUTPUT_ROOT}"
)

print(
    f"YAML file           : {yaml_path}"
)

print("\nYOLO classes:")

for idx, name in enumerate(
    CLASS_NAMES
):

    print(
        f"{idx}: {name}"
    )

print("=" * 70)