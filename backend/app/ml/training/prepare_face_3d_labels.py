from pathlib import Path

import pandas as pd


# ============================================================
# CONFIG
# ============================================================

INPUT_CSV = Path(
    r"D:\Fetal_Face_3D\features\fetal_face_3d_features.csv"
)

OUTPUT_CSV = Path(
    r"D:\Fetal_Face_3D\features\fetal_face_3d_labeled.csv"
)


# ============================================================
# FACIAL-RELATED CATEGORIES SUPPORTED BY THIS DATASET
# ============================================================

FACE_ABNORMAL = {
    "Isolated cleft",
    "Cleft + syndrome",
    "Eye pathology",
    "Postnatal dysmorphic features",
}


EXCLUDE = {
    "Lost to follow up",
    "?",
    "Other",
    "T18",
    "T21",
    "T13",
    "Genetic abnormality",
    "Skeletal dysplasia",
    "Hydrops",
    "Polyhydramnios",
    "Cornelia De Lange",
    "Noonan",
}


# ============================================================
# LOAD
# ============================================================

print("=" * 70)
print("FETAL FACE 3D LABEL PREPARATION")
print("=" * 70)

if not INPUT_CSV.exists():
    raise FileNotFoundError(
        f"Input feature CSV not found:\n{INPUT_CSV}"
    )


df = pd.read_csv(
    INPUT_CSV
)


print(
    f"Input shape: {df.shape}"
)


# ============================================================
# CLEAN CATEGORY
# ============================================================

df["followup_category"] = (
    df["followup_category"]
    .fillna("")
    .astype(str)
    .str.strip()
)


print("\nOriginal categories:")

print(
    df["followup_category"]
    .value_counts()
)


# ============================================================
# SELECT SUPPORTED CASES
# ============================================================

face_cases = df[
    df["followup_category"].isin(
        FACE_ABNORMAL
    )
].copy()


normal_cases = df[
    df["followup_category"] == "Normal"
].copy()


excluded_cases = df[
    ~df["followup_category"].isin(
        FACE_ABNORMAL | {"Normal"}
    )
].copy()


# ============================================================
# CREATE BINARY LABEL
# ============================================================

normal_cases["face_label"] = 0

face_cases["face_label"] = 1


labeled = pd.concat(
    [
        normal_cases,
        face_cases,
    ],
    ignore_index=True
)


# ============================================================
# LABEL NAME
# ============================================================

labeled["face_label_name"] = (
    labeled["face_label"]
    .map(
        {
            0: "normal",
            1: "facial_abnormality",
        }
    )
)


# ============================================================
# SORT
# ============================================================

labeled = labeled.sort_values(
    by=[
        "face_label",
        "case_number",
    ]
).reset_index(
    drop=True
)


# ============================================================
# SAVE
# ============================================================

OUTPUT_CSV.parent.mkdir(
    parents=True,
    exist_ok=True
)

labeled.to_csv(
    OUTPUT_CSV,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("LABELING COMPLETE")
print("=" * 70)

print(
    f"Original cases       : {len(df)}"
)

print(
    f"Normal cases         : {len(normal_cases)}"
)

print(
    f"Facial abnormal cases: {len(face_cases)}"
)

print(
    f"Excluded cases       : {len(excluded_cases)}"
)

print(
    f"Final labeled cases  : {len(labeled)}"
)

print("\nFinal class distribution:")

print(
    labeled["face_label_name"]
    .value_counts()
)


print("\nAbnormal categories included:")

if len(face_cases) > 0:

    print(
        face_cases[
            "followup_category"
        ].value_counts()
    )

else:

    print(
        "None"
    )


print(
    f"\nOutput:\n{OUTPUT_CSV}"
)

print("=" * 70)