from pathlib import Path
from io import BytesIO

import numpy as np
import pandas as pd
from PIL import Image


SOURCE = Path(
    r"D:\FetoPlac\data\test-00000-of-00001.parquet"
)

OUTPUT = Path(
    r"D:\Fetal_Placenta_Seg"
)

IMAGE_DIR = OUTPUT / "images"
MASK_DIR = OUTPUT / "masks"


IMAGE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

MASK_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def decode_image(value):
    """
    Decode Hugging Face image dictionary:
    {'bytes': ..., 'path': ...}
    """

    if value is None:
        return None

    if isinstance(value, dict):

        raw = value.get("bytes")

        if raw is not None:
            return np.array(
                Image.open(
                    BytesIO(raw)
                )
            )

        path = value.get("path")

        if path:
            return np.array(
                Image.open(path)
            )

    if isinstance(value, Image.Image):
        return np.array(value)

    return np.asarray(value)


def prepare_image(value):
    image = decode_image(value)

    if image is None:
        raise ValueError(
            "Image is None"
        )

    image = np.squeeze(image)

    # RGB/RGBA -> RGB
    if image.ndim == 3:

        if image.shape[2] >= 3:
            image = image[:, :, :3]

        else:
            raise ValueError(
                f"Unexpected image shape: {image.shape}"
            )

    elif image.ndim != 2:

        raise ValueError(
            f"Unexpected image shape: {image.shape}"
        )

    return image.astype(
        np.uint8
    )


def prepare_mask(value):
    """
    Decode RGB mask and convert to
    binary mask.

    Any non-black pixel = foreground.
    """

    mask = decode_image(value)

    if mask is None:
        raise ValueError(
            "Mask is None"
        )

    mask = np.squeeze(mask)

    # RGB/RGBA mask
    if mask.ndim == 3:

        if mask.shape[2] >= 3:

            # Any channel > 0 => foreground
            mask = np.any(
                mask[:, :, :3] > 0,
                axis=2
            )

        else:

            raise ValueError(
                f"Unexpected mask shape: {mask.shape}"
            )

    elif mask.ndim == 2:

        mask = mask > 0

    else:

        raise ValueError(
            f"Unexpected mask shape: {mask.shape}"
        )

    return (
        mask.astype(np.uint8)
        * 255
    )


print("=" * 70)
print("FETOPLAC DATASET PREPARATION")
print("=" * 70)


if not SOURCE.exists():
    raise FileNotFoundError(
        f"Parquet not found:\n{SOURCE}"
    )


df = pd.read_parquet(
    SOURCE
)

print(
    f"Annotated rows: {len(df)}"
)

print(
    "\nMask types:"
)

print(
    df["mask_type"]
    .value_counts(
        dropna=False
    )
)


success = 0
failed = 0
empty_masks = 0


for index, row in df.iterrows():

    image_id = str(
        row["image_id"]
    )

    try:

        image = prepare_image(
            row["image"]
        )

        mask = prepare_mask(
            row["mask"]
        )

        if image.shape[:2] != mask.shape[:2]:

            raise ValueError(
                "Image/mask size mismatch: "
                f"{image.shape} vs {mask.shape}"
            )

        foreground = int(
            np.sum(
                mask > 0
            )
        )

        if foreground == 0:
            empty_masks += 1

        image_path = (
            IMAGE_DIR
            / f"{image_id}.png"
        )

        mask_path = (
            MASK_DIR
            / f"{image_id}.png"
        )

        Image.fromarray(
            image
        ).save(
            image_path
        )

        Image.fromarray(
            mask,
            mode="L"
        ).save(
            mask_path
        )

        success += 1

    except Exception as exc:

        failed += 1

        print(
            f"FAILED {image_id}: {exc}"
        )


print("\n" + "=" * 70)
print("PLACENTA DATASET PREPARATION COMPLETE")
print("=" * 70)

print(
    f"Successful : {success}"
)

print(
    f"Failed     : {failed}"
)

print(
    f"Empty masks: {empty_masks}"
)

print(
    f"Images     : {IMAGE_DIR}"
)

print(
    f"Masks      : {MASK_DIR}"
)

print("=" * 70)