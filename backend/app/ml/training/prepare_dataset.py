from pathlib import Path

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit


DATASET_ROOT = Path(r"D:\Fetal_Dataset")
CSV_PATH = DATASET_ROOT / "Fetal Dataset.csv"
IMAGES_DIR = DATASET_ROOT / "Images"

OUTPUT_DIR = Path(__file__).resolve().parent / "splits"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("Loading dataset...")

    df = pd.read_csv(CSV_PATH, sep=";")

    print(f"CSV rows: {len(df)}")

    # -------------------------------------------------
    # Check image files
    # -------------------------------------------------

    df["image_path"] = df["Image_name"].apply(
        lambda name: str(IMAGES_DIR / f"{name}.png")
    )

    df["image_exists"] = df["image_path"].apply(
        lambda path: Path(path).exists()
    )

    missing = (~df["image_exists"]).sum()

    print(f"Images found: {df['image_exists'].sum()}")
    print(f"Missing images: {missing}")

    if missing > 0:
        print("\nWARNING: Some images are missing!")

    df = df[df["image_exists"]].copy()

    # -------------------------------------------------
    # Patient-wise Train / Validation Split
    # -------------------------------------------------

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.20,
        random_state=42,
    )

    train_idx, val_idx = next(
        splitter.split(
            df,
            groups=df["Patient_num"],
        )
    )

    train_df = df.iloc[train_idx].copy()
    val_df = df.iloc[val_idx].copy()

    # -------------------------------------------------
    # Leakage check
    # -------------------------------------------------

    train_patients = set(train_df["Patient_num"])
    val_patients = set(val_df["Patient_num"])

    overlap = train_patients.intersection(val_patients)

    print("\n--- SPLIT RESULTS ---")

    print(f"Train images: {len(train_df)}")
    print(f"Validation images: {len(val_df)}")

    print(f"Train patients: {len(train_patients)}")
    print(f"Validation patients: {len(val_patients)}")

    print(f"Patient overlap: {len(overlap)}")

    # -------------------------------------------------
    # Class distribution
    # -------------------------------------------------

    print("\nTRAIN CLASS DISTRIBUTION")
    print(train_df["Plane"].value_counts())

    print("\nVALIDATION CLASS DISTRIBUTION")
    print(val_df["Plane"].value_counts())

    # -------------------------------------------------
    # Save splits
    # -------------------------------------------------

    train_df.to_csv(
        OUTPUT_DIR / "train.csv",
        index=False,
    )

    val_df.to_csv(
        OUTPUT_DIR / "val.csv",
        index=False,
    )

    print("\nSaved:")
    print(OUTPUT_DIR / "train.csv")
    print(OUTPUT_DIR / "val.csv")

    if len(overlap) == 0:
        print("\nDataset split successful - no patient leakage.")
    else:
        print("\nWARNING: Patient leakage detected!")


if __name__ == "__main__":
    main()