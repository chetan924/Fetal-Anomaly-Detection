from pathlib import Path
import zipfile
import io

import numpy as np
from PIL import Image
from tqdm import tqdm


# ============================================================
# PATHS
# ============================================================

DATASET_ROOT = Path(
    r"D:\Fetal_Abdominal_Dataset\Fetal Abdominal Structures Segmentation Dataset Using Ultrasonic Images"
)

ZIP_FILE = DATASET_ROOT / (
    "Fetal Abdominal Structures Segmentation Dataset Using Ultrasonic Images.zip"
)

OUTPUT_ROOT = Path(
    r"D:\Fetal_Abdomen_Processed"
)

IMAGE_DIR = OUTPUT_ROOT / "images"
MASK_DIR = OUTPUT_ROOT / "masks"


# ============================================================
# CLASSES
# ============================================================

STRUCTURES = [
    "artery",
    "liver",
    "stomach",
    "vein",
]


# ============================================================
# DIRECTORIES
# ============================================================

IMAGE_DIR.mkdir(parents=True, exist_ok=True)
MASK_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CHECK DATASET
# ============================================================

if not ZIP_FILE.exists():
    raise FileNotFoundError(
        f"Dataset ZIP not found:\n{ZIP_FILE}"
    )


print("=" * 60)
print("FETAL ABDOMINAL DATASET PREPARATION")
print("=" * 60)
print(f"ZIP:\n{ZIP_FILE}")
print(f"OUTPUT:\n{OUTPUT_ROOT}")
print()


# ============================================================
# OPEN ZIP
# ============================================================

print("Opening dataset ZIP...")

with zipfile.ZipFile(ZIP_FILE, "r") as archive:
    files = archive.namelist()


# ============================================================
# FIND NPY AND PNG FILES
# ============================================================

npy_files = [
    file_name
    for file_name in files
    if file_name.startswith("ARRAY_FORMAT/")
    and file_name.lower().endswith(".npy")
]

png_files = [
    file_name
    for file_name in files
    if file_name.startswith("IMAGES/")
    and file_name.lower().endswith(".png")
]

print(f"NPY files : {len(npy_files)}")
print(f"PNG files : {len(png_files)}")
print()


# ============================================================
# LOOKUP TABLES
# ============================================================

npy_lookup = {
    Path(file_name).name: file_name
    for file_name in npy_files
}

png_lookup = {
    Path(file_name).name: file_name
    for file_name in png_files
}


# ============================================================
# MATCH NPY + PNG
# ============================================================

matched = []

for npy_name, npy_path in npy_lookup.items():

    png_name = npy_name.replace(".npy", ".png")

    if png_name in png_lookup:
        matched.append(
            (
                npy_name,
                npy_path,
                png_lookup[png_name]
            )
        )


print(f"Matched image/NPY pairs: {len(matched)}")
print()


# ============================================================
# PROCESS DATASET
# ============================================================

processed = 0
failed = 0

structure_stats = {
    name: 0
    for name in STRUCTURES
}


with zipfile.ZipFile(ZIP_FILE, "r") as archive:

    for npy_name, npy_path, png_path in tqdm(
        matched,
        desc="Preparing dataset"
    ):

        try:

            # ------------------------------------------------
            # READ NPY
            # ------------------------------------------------

            npy_bytes = archive.read(npy_path)

            data = np.load(
                io.BytesIO(npy_bytes),
                allow_pickle=True
            ).item()


            # ------------------------------------------------
            # VALIDATION
            # ------------------------------------------------

            if not isinstance(data, dict):
                raise ValueError(
                    "NPY data is not a dictionary"
                )

            if "image" not in data:
                raise ValueError(
                    "Missing 'image'"
                )

            if "structures" not in data:
                raise ValueError(
                    "Missing 'structures'"
                )


            image = data["image"]
            structures = data["structures"]


            # ------------------------------------------------
            # IMAGE VALIDATION
            # ------------------------------------------------

            if image.ndim == 2:

                image = np.stack(
                    [image, image, image],
                    axis=-1
                )

            elif image.ndim == 3:

                # Handle grayscale with one channel
                if image.shape[-1] == 1:
                    image = np.repeat(
                        image,
                        3,
                        axis=-1
                    )

                # Handle RGBA
                elif image.shape[-1] == 4:
                    image = image[:, :, :3]

                elif image.shape[-1] != 3:
                    raise ValueError(
                        f"Unsupported image channels: {image.shape}"
                    )

            else:

                raise ValueError(
                    f"Unexpected image shape: {image.shape}"
                )


            image = np.asarray(
                image,
                dtype=np.uint8
            )


            # ------------------------------------------------
            # RESIZE IMAGE
            # ------------------------------------------------

            image_pil = Image.fromarray(image)

            image_pil = image_pil.resize(
                (512, 512),
                Image.Resampling.BILINEAR
            )


            sample_id = Path(
                npy_name
            ).stem


            image_output = (
                IMAGE_DIR /
                f"{sample_id}.png"
            )


            image_pil.save(
                image_output
            )


            # ------------------------------------------------
            # CREATE MULTI-CLASS MASK
            #
            # 0 = Background
            # 1 = Artery
            # 2 = Liver
            # 3 = Stomach
            # 4 = Vein
            # ------------------------------------------------

            height, width = image.shape[:2]

            mask = np.zeros(
                (height, width),
                dtype=np.uint8
            )


            for class_id, structure_name in enumerate(
                STRUCTURES,
                start=1
            ):

                if structure_name not in structures:
                    continue


                structure_mask = structures[
                    structure_name
                ]


                if structure_mask is None:
                    continue


                structure_mask = np.asarray(
                    structure_mask
                )


                if structure_mask.shape != (height, width):

                    raise ValueError(
                        f"{structure_name} mask shape "
                        f"{structure_mask.shape} does not match "
                        f"image shape {(height, width)}"
                    )


                binary_mask = (
                    structure_mask > 0
                )


                pixel_count = int(
                    binary_mask.sum()
                )


                if pixel_count > 0:

                    mask[binary_mask] = class_id

                    structure_stats[
                        structure_name
                    ] += 1


            # ------------------------------------------------
            # RESIZE MASK
            # ------------------------------------------------

            mask_pil = Image.fromarray(
                mask
            )

            mask_pil = mask_pil.resize(
                (512, 512),
                Image.Resampling.NEAREST
            )


            mask_output = (
                MASK_DIR /
                f"{sample_id}.png"
            )


            mask_pil.save(
                mask_output
            )


            processed += 1


        except Exception as exc:

            failed += 1

            print(
                f"\nERROR: {npy_name}"
            )

            print(
                f"Reason: {exc}"
            )


# ============================================================
# FINAL SUMMARY
# ============================================================

print()

print("=" * 60)
print("DATASET PREPARATION COMPLETE")
print("=" * 60)

print(
    f"Processed : {processed}"
)

print(
    f"Failed    : {failed}"
)

print()

print("Structure coverage:")

for structure, count in structure_stats.items():

    print(
        f"{structure:10s}: {count}"
    )

print()

print(
    f"Images : {IMAGE_DIR}"
)

print(
    f"Masks  : {MASK_DIR}"
)

print()