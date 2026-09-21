from pathlib import Path
from PIL import Image
import numpy as np


# ============================================================
# FOCUS Heart Dataset Preparation
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATASET_ROOT = PROJECT_ROOT / "FOCUS-dataset"
OUTPUT_ROOT = PROJECT_ROOT / "backend" / "app" / "ml" / "heart_data"

IMAGE_SIZE = (256, 256)


def process_split(split_name: str):
    image_dir = DATASET_ROOT / split_name / "images"
    mask_dir = DATASET_ROOT / split_name / "annfiles_mask"

    output_image_dir = OUTPUT_ROOT / split_name / "images"
    output_mask_dir = OUTPUT_ROOT / split_name / "masks"

    output_image_dir.mkdir(parents=True, exist_ok=True)
    output_mask_dir.mkdir(parents=True, exist_ok=True)

    image_files = sorted(image_dir.glob("*.png"))

    processed = 0
    skipped = 0

    print()
    print(f"Processing {split_name}...")
    print(f"Images found: {len(image_files)}")

    for image_path in image_files:

        image_id = image_path.stem
        mask_path = mask_dir / f"{image_id}-cardiac.png"

        if not mask_path.exists():
            print(f"WARNING: Missing mask for {image_path.name}")
            skipped += 1
            continue

        try:
            # Load ultrasound image
            image = Image.open(image_path).convert("L")

            # Load cardiac mask
            mask = Image.open(mask_path).convert("L")

            # Resize image
            image = image.resize(
                IMAGE_SIZE,
                Image.Resampling.BILINEAR
            )

            # Resize mask without interpolation
            mask = mask.resize(
                IMAGE_SIZE,
                Image.Resampling.NEAREST
            )

            # Convert mask to binary
            mask_array = np.array(mask)

            mask_array = np.where(
                mask_array > 0,
                255,
                0
            ).astype(np.uint8)

            mask = Image.fromarray(mask_array)

            # Save processed files
            image.save(
                output_image_dir / f"{image_id}.png"
            )

            mask.save(
                output_mask_dir / f"{image_id}.png"
            )

            processed += 1

        except Exception as exc:
            print(
                f"ERROR processing {image_path.name}: {exc}"
            )

            skipped += 1

    print(f"Processed: {processed}")
    print(f"Skipped: {skipped}")


def main():
    print("=" * 60)
    print("FOCUS HEART DATASET PREPARATION")
    print("=" * 60)

    print()
    print(f"Dataset: {DATASET_ROOT}")
    print(f"Output : {OUTPUT_ROOT}")
    print(f"Size   : {IMAGE_SIZE}")

    for split in [
        "training",
        "validation",
        "testing",
    ]:
        process_split(split)

    print()
    print("=" * 60)
    print("DATASET PREPARATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()