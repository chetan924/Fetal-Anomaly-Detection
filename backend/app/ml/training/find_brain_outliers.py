from pathlib import Path
import sys

import pandas as pd
from PIL import Image

# ------------------------------------------------------------
# Allow importing from backend root
# ------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[3]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ml.predict_brain_anomaly import predict_brain_anomaly


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TEST_CSV = (
    BASE_DIR
    / "brain_anomaly_splits"
    / "test.csv"
)

OUTPUT_CSV = (
    BASE_DIR
    / "brain_anomaly_splits"
    / "brain_outliers.csv"
)


# ============================================================
# LOAD TEST DATA
# ============================================================

print("=" * 70)
print("FETAL BRAIN TEST-SET OUTLIER SEARCH")
print("=" * 70)

df = pd.read_csv(TEST_CSV)

print("\nTest images:", len(df))


# ============================================================
# ANALYZE IMAGES
# ============================================================

results = []

for index, row in df.iterrows():

    image_path = Path(
        row["image_path"]
    )

    brain_plane = row[
        "Brain_plane"
    ]

    try:

        image = Image.open(
            image_path
        ).convert("RGB")

        result = predict_brain_anomaly(
            image,
            brain_plane,
        )

        results.append(
            {
                "Image_name": row[
                    "Image_name"
                ],

                "Patient_num": row[
                    "Patient_num"
                ],

                "Brain_plane": (
                    brain_plane
                ),

                "image_path": str(
                    image_path
                ),

                "anomaly_score": result[
                    "anomaly_score"
                ],

                "threshold": result[
                    "threshold"
                ],

                "threshold_ratio": result[
                    "threshold_ratio"
                ],

                "is_outlier": result[
                    "is_outlier"
                ],

                "status": result[
                    "status"
                ],
            }
        )

    except Exception as exc:

        print(
            f"\nERROR processing "
            f"{image_path.name}: {exc}"
        )

    processed = index + 1

    if processed % 25 == 0:
        print(
            f"Processed "
            f"{processed}/{len(df)}"
        )


# ============================================================
# RESULTS DATAFRAME
# ============================================================

result_df = pd.DataFrame(
    results
)


# ============================================================
# SORT BY ANOMALY SCORE
# ============================================================

result_df = result_df.sort_values(
    by="threshold_ratio",
    ascending=False,
)


# ============================================================
# OUTLIERS ONLY
# ============================================================

outlier_df = result_df[
    result_df["is_outlier"] == True
].copy()


print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)

print(
    "Successfully analyzed:",
    len(result_df),
)

print(
    "Statistical outliers:",
    len(outlier_df),
)

if len(result_df) > 0:

    percentage = (
        len(outlier_df)
        / len(result_df)
        * 100
    )

    print(
        "Outlier percentage:",
        f"{percentage:.2f}%",
    )


# ============================================================
# OUTLIERS BY PLANE
# ============================================================

print("\n" + "=" * 70)
print("OUTLIERS BY BRAIN PLANE")
print("=" * 70)

if len(outlier_df) > 0:

    plane_summary = (
        outlier_df
        .groupby("Brain_plane")
        .size()
    )

    print(
        plane_summary.to_string()
    )

else:

    print(
        "No statistical outliers found."
    )


# ============================================================
# TOP OUTLIERS
# ============================================================

print("\n" + "=" * 70)
print("TOP STATISTICAL OUTLIERS")
print("=" * 70)

columns = [
    "Image_name",
    "Patient_num",
    "Brain_plane",
    "anomaly_score",
    "threshold",
    "threshold_ratio",
]

if len(outlier_df) > 0:

    print(
        outlier_df[
            columns
        ]
        .head(20)
        .to_string(
            index=False
        )
    )


# ============================================================
# SAVE CSV
# ============================================================

outlier_df.to_csv(
    OUTPUT_CSV,
    index=False,
)

print("\n" + "=" * 70)
print("COMPLETE")
print("=" * 70)

print(
    "Outlier CSV saved to:"
)

print(
    OUTPUT_CSV
)

print(
    "\nIMPORTANT:"
)

print(
    "These are statistical outliers only. "
    "They are NOT clinically confirmed fetal anomalies."
)