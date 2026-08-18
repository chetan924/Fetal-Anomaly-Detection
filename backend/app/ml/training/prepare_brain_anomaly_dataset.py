from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


# ============================================================
# CONFIG
# ============================================================

CSV_PATH = Path(r"D:\Fetal_Dataset\Fetal Dataset.csv")
IMAGE_DIR = Path(r"D:\Fetal_Dataset\Images")

OUTPUT_DIR = Path(
    r"D:\Fetal Anomaly Detection\backend"
    r"\app\ml\training\brain_anomaly_splits"
)

VALID_BRAIN_PLANES = [
    "Trans-thalamic",
    "Trans-cerebellum",
    "Trans-ventricular",
]

RANDOM_STATE = 42

# Patient-level:
# 70% train
# 15% validation
# 15% test
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15


# ============================================================
# LOAD DATASET
# ============================================================

print("=" * 65)
print("FETAL BRAIN DATASET PREPARATION")
print("=" * 65)

print("\nLoading CSV...")

df = pd.read_csv(
    CSV_PATH,
    sep=";",
)

print("Total CSV rows:", len(df))


# ============================================================
# FILTER STANDARD FETAL BRAIN PLANES
# ============================================================

brain_df = df[
    (df["Plane"] == "Fetal brain")
    & (df["Brain_plane"].isin(VALID_BRAIN_PLANES))
].copy()

print(
    "Standard fetal-brain rows:",
    len(brain_df),
)


# ============================================================
# BUILD IMAGE PATHS
# ============================================================

brain_df["image_path"] = brain_df[
    "Image_name"
].apply(
    lambda name: str(
        IMAGE_DIR / f"{name}.png"
    )
)


# ============================================================
# CHECK MISSING IMAGES
# ============================================================

brain_df["image_exists"] = brain_df[
    "image_path"
].apply(
    lambda path: Path(path).exists()
)

missing_df = brain_df[
    ~brain_df["image_exists"]
]

print(
    "Images found:",
    brain_df["image_exists"].sum(),
)

print(
    "Missing images:",
    len(missing_df),
)

if len(missing_df) > 0:

    print("\nERROR: Missing images detected.")

    print(
        missing_df[
            [
                "Image_name",
                "Patient_num",
                "Brain_plane",
            ]
        ].head(20)
    )

    raise SystemExit(
        "Dataset preparation stopped."
    )


brain_df = brain_df.drop(
    columns=["image_exists"]
)


# ============================================================
# UNIQUE PATIENTS
# ============================================================

patients = (
    brain_df["Patient_num"]
    .drop_duplicates()
    .tolist()
)

print(
    "Unique patients:",
    len(patients),
)


# ============================================================
# PATIENT-LEVEL TRAIN / TEMP SPLIT
# ============================================================

train_patients, temp_patients = train_test_split(
    patients,
    test_size=(
        VAL_RATIO + TEST_RATIO
    ),
    random_state=RANDOM_STATE,
    shuffle=True,
)


# ============================================================
# TEMP -> VALIDATION / TEST
# ============================================================

relative_test_ratio = (
    TEST_RATIO
    / (VAL_RATIO + TEST_RATIO)
)

val_patients, test_patients = train_test_split(
    temp_patients,
    test_size=relative_test_ratio,
    random_state=RANDOM_STATE,
    shuffle=True,
)


# ============================================================
# CREATE DATAFRAME SPLITS
# ============================================================

train_df = brain_df[
    brain_df["Patient_num"].isin(
        train_patients
    )
].copy()

val_df = brain_df[
    brain_df["Patient_num"].isin(
        val_patients
    )
].copy()

test_df = brain_df[
    brain_df["Patient_num"].isin(
        test_patients
    )
].copy()


# ============================================================
# PATIENT LEAKAGE CHECK
# ============================================================

train_set = set(
    train_df["Patient_num"]
)

val_set = set(
    val_df["Patient_num"]
)

test_set = set(
    test_df["Patient_num"]
)


train_val_overlap = (
    train_set & val_set
)

train_test_overlap = (
    train_set & test_set
)

val_test_overlap = (
    val_set & test_set
)


print("\n" + "=" * 65)
print("PATIENT LEAKAGE CHECK")
print("=" * 65)

print(
    "Train / Validation overlap:",
    len(train_val_overlap),
)

print(
    "Train / Test overlap:",
    len(train_test_overlap),
)

print(
    "Validation / Test overlap:",
    len(val_test_overlap),
)


if (
    train_val_overlap
    or train_test_overlap
    or val_test_overlap
):

    raise RuntimeError(
        "Patient leakage detected!"
    )


print(
    "\nPASS - No patient leakage."
)


# ============================================================
# REPORT FUNCTION
# ============================================================

def print_split_report(
    name,
    split_df,
):

    print(
        "\n" + "=" * 65
    )

    print(name)

    print("=" * 65)

    print(
        "Images:",
        len(split_df),
    )

    print(
        "Patients:",
        split_df[
            "Patient_num"
        ].nunique(),
    )

    print(
        "\nBrain plane distribution:"
    )

    print(
        split_df[
            "Brain_plane"
        ].value_counts()
    )


# ============================================================
# REPORT SPLITS
# ============================================================

print_split_report(
    "TRAIN",
    train_df,
)

print_split_report(
    "VALIDATION",
    val_df,
)

print_split_report(
    "TEST",
    test_df,
)


# ============================================================
# SAVE CSV FILES
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

train_path = (
    OUTPUT_DIR / "train.csv"
)

val_path = (
    OUTPUT_DIR / "val.csv"
)

test_path = (
    OUTPUT_DIR / "test.csv"
)


train_df.to_csv(
    train_path,
    index=False,
)

val_df.to_csv(
    val_path,
    index=False,
)

test_df.to_csv(
    test_path,
    index=False,
)


# ============================================================
# FINAL CHECK
# ============================================================

total_after_split = (
    len(train_df)
    + len(val_df)
    + len(test_df)
)

if total_after_split != len(brain_df):

    raise RuntimeError(
        "Image count mismatch after split."
    )


print("\n" + "=" * 65)
print("DATASET PREPARATION COMPLETE")
print("=" * 65)

print(
    "Total images:",
    total_after_split,
)

print(
    "Total patients:",
    brain_df[
        "Patient_num"
    ].nunique(),
)

print("\nSaved:")

print(train_path)
print(val_path)
print(test_path)

print(
    "\nDataset split successful "
    "- zero patient leakage."
)